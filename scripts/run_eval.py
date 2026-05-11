"""
RAG Evaluation Script (Production-Ready)

Features:
✔ Save results in app/eval/result/
✔ Timestamped output file
✔ Request ID logging
✔ Latency tracking
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
import argparse

from app.services.evaluation_service import EvaluationService
from app.retrieval.vector_store import VectorStore
from app.core.request_context import set_request_id, get_request_id

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(request_id)s] | %(message)s"
)

logger = logging.getLogger("rag-eval")


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id() or "no-request-id"
        return True


logger.addFilter(RequestIDFilter())

# Main runner
def run_eval(dataset, output_dir="app/eval/result"):
    
    # Generate request ID for this run
    request_id = datetime.now().strftime("%Y%m%d%H%M%S")
    set_request_id(request_id)

    start_time = time.time()

    logger.info("Starting RAG evaluation | cases=%d", len(dataset))

    service = EvaluationService(VectorStore())

    report = service.run_evaluation(dataset)

    # Add latency
    latency = round(time.time() - start_time, 3)
    report["latency_seconds"] = latency
    report["request_id"] = request_id

    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Timestamped filename
    filename = f"evaluation_{request_id}.json"
    file_path = output_path / filename

    # Save results
    file_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    logger.info(
        "Evaluation complete | avg_score=%.3f | latency=%.3fs | saved=%s",
        report.get("average_score", 0),
        latency,
        file_path
    )

    return report


# CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Evaluation Runner")

    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to JSON dataset"
    )

    parser.add_argument(
        "--output_dir",
        type=str,
        default="app/eval/result",
        help="Output directory"
    )

    args = parser.parse_args()

    # Default dataset
    dataset = [
        {
            "question": "What is the refund policy?",
            "expected": "Refunds are available within 30 days of purchase."
        }
    ]

    # Load external dataset
    if args.dataset:
        dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))

    run_eval(dataset, output_dir=args.output_dir)