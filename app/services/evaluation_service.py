"""
Evaluation Service — unified retrieval + generation evaluation.
"""

import time
from typing import Any

from app.llm.answer_service import generate_answer
from app.retrieval.retriever import retrieve_chunks_with_metadata
from app.retrieval.vector_store import VectorStore


class EvaluationService:

    def __init__(self, vector_store: VectorStore | None = None):
        self.vector_store = vector_store or VectorStore()

    # Simple scoring
    def _score_answer(self, generated: str, expected: str) -> float:
        gen_words = set(generated.lower().split())
        exp_words = set(expected.lower().split())

        if not exp_words:
            return 0.0

        overlap = gen_words & exp_words
        return round(len(overlap) / len(exp_words), 2)

    # Single case
    def run_case(
        self,
        question: str,
        expected: str,
        role: str = "employee",
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> dict[str, Any]:

        # Retrieval
        chunks = retrieve_chunks_with_metadata(
            query=question,
            vector_store=self.vector_store,
            role=role,
            top_k=top_k,
            min_score=min_score,
        )

        top_score = chunks[0]["score"] if chunks else None

        # Generation
        generated = generate_answer(query=question, context_chunks=chunks)

        # Scoring
        answer_text = generated.get("answer", "")
        score = self._score_answer(answer_text, expected)

        return {
            "question": question,
            "expected": expected,
            "generated": generated,
            "score": score,
            "chunks_found": len(chunks),
            "top_score": top_score,
            "passed": len(chunks) > 0,
        }

    # Full evaluation
    def run_evaluation(
        self,
        dataset: list[dict[str, str]],
        role: str = "employee",
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> dict[str, Any]:

        start = time.time()

        results = []
        total_score = 0.0

        for case in dataset:
            result = self.run_case(
                question=case["question"],
                expected=case["expected"],
                role=role,
                top_k=top_k,
                min_score=min_score,
            )

            results.append(result)
            total_score += result["score"]

        avg_score = round(total_score / len(results), 3) if results else 0.0

        return {
            "total": len(results),
            "average_score": avg_score,
            "duration_seconds": round(time.time() - start, 3),
            "results": results,
        }
