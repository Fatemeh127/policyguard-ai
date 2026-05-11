"""Production-grade RAG Evaluation Framework"""

import json
import logging
import csv
import time
from typing import List, Dict, Any

from pathlib import Path
from sentence_transformers import SentenceTransformer, util

from app.retrieval.vector_store import VectorStore
from app.llm.answer_service import generate_answer
from app.api.deps import get_vector_store

logger = logging.getLogger(__name__)

# Embedding model for evaluation
model = SentenceTransformer("all-MiniLM-L6-v2")


# Load dataset
def load_eval_questions(csv_path: str = "app/eval/questions.csv") -> List[Dict[str, str]]:
    questions = []

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                questions.append(row)

        logger.info("Loaded %d questions", len(questions))
        return questions

    except FileNotFoundError:
        logger.warning("File not found: %s", csv_path)
        return []


# Retrieval Metrics
def recall_at_k(retrieved_ids: List[str], expected_ids: List[str]) -> float:
    if not expected_ids:
        return 0.0

    retrieved = set(retrieved_ids)
    expected = set(expected_ids)

    return len(retrieved & expected) / len(expected)


def mrr(retrieved_ids: List[str], expected_id: str) -> float:
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id == expected_id:
            return 1 / (i + 1)
    return 0.0


# Answer Metrics
def semantic_similarity(expected: str, answer: str) -> float:
    if not expected:
        return 0.0

    return util.cos_sim(
        model.encode(expected),
        model.encode(answer)
    ).item()


def faithfulness(answer: str, context: str) -> float:
    if not answer or not context:
        return 0.0

    return util.cos_sim(
        model.encode(answer),
        model.encode(context)
    ).item()


# LLM-as-a-Judge
def llm_judge(question: str, expected: str, answer: str) -> str:
    """
    Uses LLM to score answer quality.
    (Assumes your generate_answer can also be reused or replaced with OpenAI call)
    """

    prompt = f"""
        You are an evaluator for a RAG system.

        Question: {question}
        Expected Answer: {expected}
        Model Answer: {answer}

        Rate from 1 to 5:
        - correctness
        - completeness
        - grounding

        Return ONLY a number.
    """

    result = generate_answer(
        query=prompt,
        context_chunks=[]
    )

    return result["answer"]


# Main Evaluation
def run_evaluation(questions: List[Dict[str, str]]) -> Dict[str, Any]:

    vector_store = get_vector_store()
    results = []

    for i, q in enumerate(questions, 1):
        logger.info("Evaluating %d/%d", i, len(questions))

        try:
            start = time.perf_counter()

            # Retrieval (Qdrant)
            chunks = vector_store.search(
                query=q["question"],
                role=q.get("role", ""),
                limit=5
            )
            
            retrieved_ids = [
                c.get("document_id", "")
                for c in chunks
            ]
            context_text = " ".join([c.get("text", "") for c in chunks])

            # Generation
            result = generate_answer(
                query=q["question"],
                context_chunks=chunks
            )

            answer = result.get("answer", "")

            latency = time.perf_counter() - start

            # Metrics
            expected_answer = q.get("expected_contains", "")
            expected_id = q.get("expected_sources", "")

            rec_k = recall_at_k(retrieved_ids, [expected_id])
            mrr_score = mrr(retrieved_ids, expected_id)

            sem_score = semantic_similarity(expected_answer, answer)
            faith_score = faithfulness(answer, context_text)

            judge_score = llm_judge(
                q["question"],
                expected_answer,
                answer
            )

            results.append({
                "question": q["question"],
                "answer": answer,

                # retrieval
                "recall@k": round(rec_k, 3),
                "mrr": round(mrr_score, 3),

                # generation quality
                "semantic_similarity": round(sem_score, 3),
                "faithfulness": round(faith_score, 3),

                # system
                "latency": round(latency, 3),

                # LLM judge
                "llm_judge_score": judge_score
            })

        except Exception as e:
            logger.error("Error: %s", e)

            results.append({
                "question": q["question"],
                "error": str(e)
            })

    # Summary
    total = len(results)
    valid = [r for r in results if "error" not in r]

    return {
        "results": results,
        "summary": {
            "total": total,
            "avg_recall@k": sum(r.get("recall@k", 0) for r in valid) / len(valid),
            "avg_mrr": sum(r.get("mrr", 0) for r in valid) / len(valid),
            "avg_semantic": sum(r.get("semantic_similarity", 0) for r in valid) / len(valid),
            "avg_faithfulness": sum(r.get("faithfulness", 0) for r in valid) / len(valid),
            "avg_latency": sum(r.get("latency", 0) for r in valid) / len(valid),
        }
    }


# Save results
def save_results(data: Dict[str, Any], filename: str = "eval_results.json"):
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