import json
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from time import perf_counter

from app.core.database import get_connection
from app.router.pipeline import route_query


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold())


def token_f1(expected: str, actual: str) -> float:
    expected_tokens = _tokens(expected)
    actual_tokens = _tokens(actual)
    if not expected_tokens or not actual_tokens:
        return 0.0

    overlap = sum((Counter(expected_tokens) & Counter(actual_tokens)).values())
    if not overlap:
        return 0.0
    precision = overlap / len(actual_tokens)
    recall = overlap / len(expected_tokens)
    return round(2 * precision * recall / (precision + recall), 4)


def _summarize(results: list[dict]) -> dict:
    count = len(results)
    answered = sum(bool(item.get("answer")) for item in results)
    referenced = [
        item["answer_f1"]
        for item in results
        if item.get("answer_f1") is not None
    ]
    document_scoped = [
        item["document_retrieved"]
        for item in results
        if item.get("document_retrieved") is not None
    ]
    evidence_hits = sum(bool(item["source_count"]) for item in results)
    return {
        "total_cases": count,
        "answered_cases": answered,
        "answer_rate": round(answered / count, 4) if count else 0.0,
        "reference_cases": len(referenced),
        "mean_answer_f1": (
            round(sum(referenced) / len(referenced), 4)
            if referenced
            else None
        ),
        "evidence_rate": round(evidence_hits / count, 4) if count else 0.0,
        "document_cases": len(document_scoped),
        "document_hit_rate": (
            round(sum(document_scoped) / len(document_scoped), 4)
            if document_scoped
            else None
        ),
        "mean_latency_ms": (
            round(sum(item["latency_ms"] for item in results) / count, 2)
            if count
            else 0.0
        ),
        "total_tokens": sum(
            (item.get("usage") or {}).get("total_tokens", 0)
            for item in results
        ),
    }


def run_evaluation(cases: list[dict]) -> dict:
    results = []
    for index, case in enumerate(cases, start=1):
        started = perf_counter()
        result = {
            "case_index": index,
            "query": case["query"],
            "expected_answer": case.get("expected_answer"),
            "document_id": case.get("document_id"),
        }
        try:
            response = route_query(
                query=case["query"],
                document_id=case.get("document_id"),
            )
            answer = response.get("answer")
            answer = answer.strip() if isinstance(answer, str) else ""
            sources = response.get("sources") or []
            expected_answer = case.get("expected_answer")
            expected_document_id = case.get("document_id")
            document_retrieved = None
            if expected_document_id:
                document_retrieved = any(
                    source.get("document_id") == expected_document_id
                    for source in sources
                )
                if (
                    not document_retrieved
                    and response.get("retrieval_method") == "graph"
                    and sources
                ):
                    # Graph entity citations are scoped by the selected document,
                    # even when the citation itself has no document_id field.
                    document_retrieved = True

            result.update(
                {
                    "status": "passed" if answer else "failed",
                    "answer": answer,
                    "answer_f1": (
                        token_f1(expected_answer, answer)
                        if expected_answer
                        else None
                    ),
                    "source_count": len(sources),
                    "sources": sources,
                    "document_retrieved": document_retrieved,
                    "retrieval_method": response.get("retrieval_method"),
                    "engine_used": response.get("engine_used"),
                    "model": response.get("model"),
                    "usage": response.get("usage") or {},
                    "error": None,
                }
            )
        except Exception as exc:
            result.update(
                {
                    "status": "error",
                    "answer": "",
                    "answer_f1": (
                        0.0 if case.get("expected_answer") else None
                    ),
                    "source_count": 0,
                    "sources": [],
                    "document_retrieved": (
                        False if case.get("document_id") else None
                    ),
                    "retrieval_method": None,
                    "engine_used": None,
                    "model": None,
                    "usage": {},
                    "error": str(exc),
                }
            )
        result["latency_ms"] = round(
            (perf_counter() - started) * 1000, 2
        )
        results.append(result)

    run = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": _summarize(results),
        "results": results,
    }
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO evaluation_runs
                (id, created_at, case_count, summary_json, results_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run["id"],
                run["created_at"],
                len(results),
                json.dumps(run["summary"]),
                json.dumps(results),
            ),
        )
        connection.commit()
    return run


def list_evaluation_runs(limit: int = 20) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, created_at, case_count, summary_json
            FROM evaluation_runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "created_at": row["created_at"],
            "case_count": row["case_count"],
            "summary": json.loads(row["summary_json"]),
        }
        for row in rows
    ]


def get_evaluation_run(run_id: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, created_at, summary_json, results_json
            FROM evaluation_runs
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "summary": json.loads(row["summary_json"]),
        "results": json.loads(row["results_json"]),
    }
