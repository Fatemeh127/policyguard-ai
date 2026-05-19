from pydantic import BaseModel


class EvalCase(BaseModel):
    question: str
    expected: str


class EvalRequest(BaseModel):
    dataset: list[EvalCase]
    role: str = "employee"
    top_k: int = 5
    min_score: float = 0.5


class EvalCaseResult(BaseModel):
    question: str
    expected: str
    chunks_found: int
    top_score: float | None
    passed: bool


class EvalResponse(BaseModel):
    total: int
    average_score: float
    duration_seconds: float
    results: list[EvalCaseResult]
