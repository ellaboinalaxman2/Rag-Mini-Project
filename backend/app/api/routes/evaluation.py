from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_all_documents
from app.evaluation.service import (
    get_evaluation_run,
    list_evaluation_runs,
    run_evaluation,
)

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


class EvaluationCase(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    expected_answer: str | None = Field(default=None, max_length=5000)
    document_id: str | None = None


class EvaluationRequest(BaseModel):
    cases: list[EvaluationCase] = Field(min_length=1, max_length=10)


@router.post("/run")
def evaluate_cases(request: EvaluationRequest):
    documents = {doc["id"] for doc in get_all_documents()}
    for case in request.cases:
        if case.document_id and case.document_id not in documents:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown document_id: {case.document_id}",
            )
    try:
        return {
            "success": True,
            **run_evaluation(
                [case.model_dump() for case in request.cases]
            ),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Evaluation run failed: {exc}"
        )


@router.get("/runs")
def evaluation_history():
    return {"success": True, "runs": list_evaluation_runs()}


@router.get("/runs/{run_id}")
def evaluation_run_details(run_id: str):
    run = get_evaluation_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    return {"success": True, **run}
