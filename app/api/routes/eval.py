# app/api/routes/eval.py
"""Eval endpoint — run retrieval quality evaluation via API."""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.retrieval.vector_store import VectorStore
from app.services.evaluation_service import EvaluationService
from app.schemas.eval import EvalCase, EvalCaseResult, EvalRequest, EvalResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Dependency ---
def get_vector_store():
    return VectorStore()


# --- Endpoint ---
@router.post("/eval")
async def run_eval(request: EvalRequest, vs: VectorStore = Depends(get_vector_store)):
    """
    Run full RAG evaluation (retrieval + generation + scoring)
    """

    service = EvaluationService(vector_store=vs)

    report = service.run_evaluation(
        dataset=[c.model_dump(mode="json") for c in request.dataset],
        role=request.role,
        top_k=request.top_k,
        min_score=request.min_score,
    )

    logger.info(
        "Eval complete | total=%d | avg_score=%.3f", report["total"], report["average_score"]
    )

    return report
