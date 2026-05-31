"""
Evaluation Service — unified retrieval and generation evaluation.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.config import settings
from app.llm.answer_service import generate_answer
from app.retrieval.retriever import retrieve_chunks_with_metadata
from app.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class EvaluationService:
    """Evaluate retrieval and generation quality for the RAG system."""

    def __init__(self, vector_store: VectorStore | None = None) -> None:
        self.vector_store = vector_store or VectorStore()

    def _score_answer_overlap(self, generated: str, expected: str) -> float:
        """
        Score answer similarity using simple word overlap.

        This is a lightweight baseline metric, not a semantic evaluation.
        """

        generated_words = set(generated.lower().split())
        expected_words = set(expected.lower().split())

        if not expected_words:
            return 0.0

        overlap = generated_words & expected_words

        return round(len(overlap) / len(expected_words), 3)

    def run_case(
        self,
        question: str,
        expected: str,
        role: str = "employee",
        top_k: int = 5,
        min_score: float | None = None,
    ) -> dict[str, Any]:
        """Run one evaluation case."""

        min_score = settings.min_retrieval_score if min_score is None else min_score

        start_time = time.perf_counter()

        chunks = retrieve_chunks_with_metadata(
            query=question,
            vector_store=self.vector_store,
            role=role,
            top_k=top_k,
            min_score=min_score,
        )

        retrieval_latency = round(time.perf_counter() - start_time, 3)

        top_score = max(
            (float(chunk.get("score") or 0.0) for chunk in chunks),
            default=0.0,
        )

        generation_start = time.perf_counter()

        generated_result = generate_answer(
            query=question,
            context_chunks=chunks,
            min_score=min_score,
        )

        generation_latency = round(time.perf_counter() - generation_start, 3)

        answer_text = str(generated_result.get("answer", ""))

        answer_score = self._score_answer_overlap(
            generated=answer_text,
            expected=expected,
        )

        passed = bool(chunks) and answer_score >= 0.3

        return {
            "question": question,
            "expected": expected,
            "answer": answer_text,
            "sources": generated_result.get("sources", []),
            "answer_score": answer_score,
            "chunks_found": len(chunks),
            "top_score": top_score,
            "retrieval_latency_seconds": retrieval_latency,
            "generation_latency_seconds": generation_latency,
            "passed": passed,
        }

    def run_evaluation(
        self,
        dataset: list[dict[str, str]],
        role: str = "employee",
        top_k: int = 5,
        min_score: float | None = None,
    ) -> dict[str, Any]:
        """Run evaluation for a full dataset."""

        start_time = time.perf_counter()

        results: list[dict[str, Any]] = []

        for case in dataset:
            try:
                result = self.run_case(
                    question=case["question"],
                    expected=case["expected"],
                    role=role,
                    top_k=top_k,
                    min_score=min_score,
                )
                results.append(result)

            except Exception:
                logger.exception(
                    "Evaluation case failed | question=%s",
                    case.get("question", "<missing>"),
                )

                results.append(
                    {
                        "question": case.get("question"),
                        "expected": case.get("expected"),
                        "error": True,
                        "passed": False,
                    }
                )

        total = len(results)

        passed_count = sum(1 for result in results if result.get("passed"))

        average_score = (
            round(
                sum(float(result.get("answer_score", 0.0)) for result in results) / total,
                3,
            )
            if total
            else 0.0
        )

        pass_rate = round(passed_count / total, 3) if total else 0.0

        return {
            "total": total,
            "passed": passed_count,
            "pass_rate": pass_rate,
            "average_score": average_score,
            "duration_seconds": round(time.perf_counter() - start_time, 3),
            "results": results,
        }
