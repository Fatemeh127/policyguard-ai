"""
RAG Evaluation Script.

Features:
- Saves results in app/eval/result/
- Creates timestamped output file
- Adds request ID for traceability
- Tracks evaluation latency
- Supports external JSON datasets
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.middleware.request_context import (
    reset_request_id,
    set_request_id,
)
from app.retrieval.vector_store import VectorStore
from app.services.evaluation_service import EvaluationService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("rag-eval")


def _validate_dataset(dataset: Any) -> list[dict[str, str]]:
    """Validate evaluation dataset format."""

    if not isinstance(dataset, list):
        raise ValueError("Dataset must be a list of evaluation cases")

    validated: list[dict[str, str]] = []

    for index, case in enumerate(dataset, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} must be an object")

        question = case.get("question")
        expected = case.get("expected")

        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"Case {index} has invalid or missing question")

        if not isinstance(expected, str) or not expected.strip():
            raise ValueError(f"Case {index} has invalid or missing expected answer")

        validated.append(
            {
                "question": question,
                "expected": expected,
            }
        )

    return validated


def _load_dataset(dataset_path: str | None) -> list[dict[str, str]]:
    """Load dataset from file or return default dataset."""

    if dataset_path is None:
        return [
            {
                "question": "What is the refund policy?",
                "expected": "Refunds are available within 30 days of purchase.",
            }
        ]

    path = Path(dataset_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON dataset: {dataset_path}") from exc

    return _validate_dataset(raw_data)


def run_eval(
    dataset: list[dict[str, str]],
    output_dir: str = "app/eval/result",
) -> dict[str, Any]:
    """Run RAG evaluation and save a timestamped report."""

    request_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    token = set_request_id(request_id)

    start_time = time.perf_counter()

    try:
        logger.info(
            "Starting RAG evaluation | request_id=%s | cases=%d",
            request_id,
            len(dataset),
        )

        service = EvaluationService(VectorStore())

        report = service.run_evaluation(dataset)

        latency = round(time.perf_counter() - start_time, 3)

        report["latency_seconds"] = latency
        report["request_id"] = request_id

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / f"evaluation_{request_id}.json"

        file_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info(
            "Evaluation complete | avg_score=%.3f | latency=%.3fs | saved=%s",
            float(report.get("average_score", 0.0)),
            latency,
            file_path,
        )

        return report

    finally:
        reset_request_id(token)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="RAG Evaluation Runner")

    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to JSON dataset",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="app/eval/result",
        help="Output directory",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    evaluation_dataset = _load_dataset(args.dataset)

    run_eval(
        dataset=evaluation_dataset,
        output_dir=args.output_dir,
    )
