import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from app.graph_rag.retriever import retrieve_graph_evidence

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


GRAPH_SYSTEM_PROMPT = (
    "You are a knowledge-graph reasoning assistant. Answer the user's "
    "question using ONLY the provided graph evidence (entities, "
    "relationships, and source mentions). Cite evidence using [E1], [E2] "
    "matching the entity list, and [R1], [R2] matching the relationship "
    "list. If the graph evidence is insufficient, say so explicitly. "
    "Do not invent facts that are not in the evidence."
)


def _build_graph_context(evidence: dict):
    blocks = []

    entities = evidence.get("matched_entities", [])
    if entities:
        blocks.append("ENTITIES:")
        for i, e in enumerate(entities, start=1):
            blocks.append(
                f"[E{i}] {e['name']} (type: {e['type']})"
                + (f" — {e['description']}" if e.get("description") else "")
            )

    relationships = evidence.get("relationships", [])
    if relationships:
        blocks.append("\nRELATIONSHIPS:")
        for i, r in enumerate(relationships, start=1):
            evidence_text = r.get("evidence") or ""
            evidence_str = f' | evidence: "{evidence_text}"' if evidence_text else ""
            blocks.append(
                f"[R{i}] {r['source_name']} --{r['relation_type']}--> "
                f"{r['target_name']}{evidence_str}"
            )

    mentions = evidence.get("mentions", [])
    if mentions:
        blocks.append("\nSOURCE MENTIONS:")
        seen = set()
        for m in mentions:
            key = (m.get("entity_name"), m.get("filename"), m.get("chunk_id"))
            if key in seen:
                continue
            seen.add(key)
            blocks.append(
                f"- {m.get('entity_name')} appears in "
                f"{m.get('filename')} (chunk: {m.get('chunk_id')})"
            )

    return "\n".join(blocks) if blocks else "(no graph evidence)"


def generate_graph_answer(query: str, depth: int = 2):
    api_key = os.getenv("GROQ_API_KEY")
    model_name = os.getenv("GROQ_MODEL")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    if not model_name:
        raise RuntimeError("GROQ_MODEL is not configured.")

    evidence = retrieve_graph_evidence(query=query, depth=depth)

    if not evidence["matched_entities"] and not evidence["relationships"]:
        return {
            "answer": (
                "I could not find matching entities or relationships in "
                "the knowledge graph for this question."
            ),
            "matched_entities": [],
            "relationships": [],
            "sources": [],
            "traversal_depth": evidence["traversal_depth"],
            "retrieval_method": "graph",
            "model": model_name,
            "usage": {},
        }

    graph_context = _build_graph_context(evidence)

    user_message = (
        f"Question: {query}\n\n"
        f"Graph Evidence:\n{graph_context}\n\n"
        "Answer using only the graph evidence above. Cite entities as "
        "[E1], [E2] and relationships as [R1], [R2]."
    )

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": GRAPH_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
    )

    answer_text = response.choices[0].message.content

    # Build citations
    sources = []

    for i, e in enumerate(evidence["matched_entities"], start=1):
        sources.append(
            {
                "source_type": "entity",
                "source_id": f"E{i}",
                "entity_id": e["id"],
                "entity_name": e["name"],
                "entity_type": e["type"],
            }
        )

    for i, r in enumerate(evidence["relationships"], start=1):
        sources.append(
            {
                "source_type": "relationship",
                "source_id": f"R{i}",
                "from_entity": r["source_name"],
                "to_entity": r["target_name"],
                "relation_type": r["relation_type"],
                "evidence": r.get("evidence", ""),
                "document_id": r.get("document_id"),
                "chunk_id": r.get("chunk_id"),
            }
        )

    usage = {}
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return {
        "answer": answer_text,
        "matched_entities": evidence["matched_entities"],
        "relationships": evidence["relationships"],
        "sources": sources,
        "traversal_depth": evidence["traversal_depth"],
        "retrieval_method": "graph",
        "model": model_name,
        "usage": usage,
    }