from pydantic import BaseModel
from typing import List, Optional


class EvalCase(BaseModel):
    question: str
    expected: str


class EvalRequest(BaseModel):
    dataset: List[EvalCase]
    role: str = "employee"
    top_k: int = 5
    min_score: float = 0.5


class EvalCaseResult(BaseModel):
    question: str
    expected: str
    chunks_found: int
    top_score: Optional[float]
    passed: bool


class EvalResponse(BaseModel):
    total: int
    average_score: float
    duration_seconds: float
    results: List[EvalCaseResult]
