"""Production-grade RAG Evaluation Framework"""

import csv
import json
import logging
import time
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer, util

from app.api.deps import get_vector_store
from app.llm.answer_service import generate_answer

logger = logging.getLogger(__name__)

# Embedding model for evaluation
model = SentenceTransformer("all-MiniLM-L6-v2")


# Load dataset
def load_eval_questions(csv_path: str = "app/eval/questions.csv") -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []

    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                questions.append(row)

        logger.info("Loaded %d questions", len(questions))
        return questions

    except FileNotFoundError:
        logger.warning("File not found: %s", csv_path)
        return []


# Retrieval Metrics
def recall_at_k(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    # Clean both lists: strip whitespace, lowercase, remove empty strings
    retrieved_ids = [r.strip().lower() for r in retrieved_ids if r.strip()]
    expected_ids = [e.strip().lower() for e in expected_ids if e.strip()]

    if not expected_ids:
        return 0.0

    if not retrieved_ids:
        return 0.0

    retrieved = set(retrieved_ids)
    expected = set(expected_ids)

    return len(retrieved & expected) / len(expected)


def mrr(retrieved_ids: list[str], expected_id: str) -> float:
    if not expected_id:
        return 0.0
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id == expected_id:
            return 1 / (i + 1)
    return 0.0


# extract filename prefix from document_id:
def extract_source(document_id: str) -> str:
    """Extracts the source filename from document_id like 'default_handbook.pdf_abc123'"""
    # If document_id contains the filename prefix, extract it
    parts = document_id.strip().lower().split("_")
    # Rebuild until we find .pdf
    for i, part in enumerate(parts):
        if part.endswith(".pdf"):
            return "_".join(parts[: i + 1])
    return document_id.strip().lower()


# Answer Metrics
def semantic_similarity(expected: str, answer: str) -> float:
    if not expected:
        return 0.0

    return util.cos_sim(model.encode(expected), model.encode(answer)).item()


def faithfulness(answer: str, contexts: list[str]) -> float:

    if not answer or not contexts:
        return 0.0

    answer_embedding = model.encode(answer)

    similarities = []

    for chunk in contexts:
        if not chunk.strip():
            continue

        chunk_embedding = model.encode(chunk)

        score = util.cos_sim(answer_embedding, chunk_embedding).item()

        similarities.append(score)

    if not similarities:
        return 0.0

    return max(similarities)


# LLM-as-a-Judge
def llm_judge(question: str, expected: str, answer: str) -> int:
    """
    Uses an LLM to evaluate RAG answer quality.
    Returns integer score from 1 to 5.
    """

    prompt = f"""
        You are an evaluator for a RAG system.

        Question: {question}

        Expected Answer:
        {expected}

        Model Answer:
        {answer}

        Evaluate the answer on:
        - correctness
        - completeness
        - grounding

        Return ONLY a single integer from 1 to 5.
        """

    try:
        result = generate_answer(query=prompt, context_chunks=[])

        raw_score = result.get("answer", "").strip()

        # Extract first numeric token
        score = int(raw_score)

        # Validate range
        if score < 1 or score > 5:
            raise ValueError("Score out of range")

        return score

    except Exception as e:
        logger.warning("LLM judge parsing failed: %s", str(e))

        # Safe fallback
        return 0


# Main Evaluation
def run_evaluation(questions: list[dict[str, str]]) -> dict[str, Any]:

    vector_store = get_vector_store()
    results = []

    for i, q in enumerate(questions, 1):
        logger.info("Evaluating %d/%d", i, len(questions))

        try:
            start = time.perf_counter()

            expected_answer = q.get("expected_contains", "")
            expected_id = q.get("expected_sources", "")
            expected_ids = [e.strip().lower() for e in expected_id.split(",") if e.strip()]

            # Retrieval (Qdrant)
            chunks = vector_store.search(
                query=q["question"], role=q.get("role") or "employee", limit=5
            )

            retrieved_ids = [
                extract_source(c.get("document_id", ""))
                for c in chunks
                if c.get("document_id", "").strip()
            ]

            context_texts = [c.get("text", "") for c in chunks]

            # Generation
            result = generate_answer(query=q["question"], context_chunks=chunks)

            answer = result.get("answer", "")
            latency = time.perf_counter() - start

            # Metrics
            rec_k = recall_at_k(retrieved_ids, expected_ids)
            mrr_score = mrr(retrieved_ids, expected_ids[0] if expected_ids else "")

            sem_score = semantic_similarity(expected_answer, answer)
            faith_score = faithfulness(answer, context_texts)

            judge_score = None

            results.append(
                {
                    "question": q["question"],
                    "answer": answer,
                    "recall@k": round(rec_k, 3),
                    "mrr": round(mrr_score, 3),
                    "semantic_similarity": round(sem_score, 3),
                    "faithfulness": round(faith_score, 3),
                    "latency": round(latency, 3),
                    "llm_judge_score": judge_score,
                }
            )

        except Exception as e:
            logger.error("Error: %s", e)
            results.append({"question": q["question"], "error": str(e)})

    # Summary
    total = len(results)
    valid = [r for r in results if "error" not in r]

    return {
        "results": results,
        "summary": {
            "total": total,
            "avg_recall@k": sum(r.get("recall@k", 0) for r in valid) / len(valid) if valid else 0.0,
            "avg_mrr": sum(r.get("mrr", 0) for r in valid) / len(valid) if valid else 0.0,
            "avg_semantic": (
                sum(r.get("semantic_similarity", 0) for r in valid) / len(valid) if valid else 0.0
            ),
            "avg_faithfulness": (
                sum(r.get("faithfulness", 0) for r in valid) / len(valid) if valid else 0.0
            ),
            "avg_latency": sum(r.get("latency", 0) for r in valid) / len(valid) if valid else 0.0,
        },
    }


# Save results
def save_results(data: dict[str, Any], filename: str = "eval_results.json") -> None:
    path = Path(__file__).resolve().parent / "result"
    path.mkdir(exist_ok=True)

    with open(path / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Saved results")


# Run
if __name__ == "__main__":
    questions = load_eval_questions()

    if not questions:
        print("No evaluation questions found.")
        exit()

    results = run_evaluation(questions)

    save_results(results)

    print(results)
