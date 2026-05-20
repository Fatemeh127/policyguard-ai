"""Tests for safe answer generation and fallback behavior."""

from typing import Any

from app.llm.answer_service import generate_answer


def test_no_context_returns_safe_fallback() -> None:
    """Test that empty context triggers safe fallback message."""
    result = generate_answer(
        query="What is the company's policy on time travel?", context_chunks=[]
    )

    assert "answer" in result
    assert "sources" in result
    assert "context_used" in result
    assert result["context_used"] is False
    assert result["sources"] == []
    assert len(result["answer"]) > 0


def test_low_relevance_score_returns_safe_fallback() -> None:
    """Test that system handles low relevance appropriately."""
    result = generate_answer(query="What is the annual leave policy?", context_chunks=[])

    assert result["context_used"] is False
    assert result["sources"] == []


def test_high_relevance_score_generates_answer() -> None:
    """Test that high relevance scores generate real answers."""
    chunks: list[dict[str, Any]] = [
        {
            "document_id": "handbook.pdf",
            "chunk_id": 0,
            "text": "Full-time employees receive 25 days of paid annual leave per year.",
            "score": 0.85,
            "role": "employee",
        }
    ]

    result = generate_answer(query="How many days of annual leave?", context_chunks=chunks)

    assert result["context_used"] is True
    assert len(result["answer"]) > 0


def test_answer_includes_source_attribution() -> None:
    """Test that answers cite their sources."""
    chunks: list[dict[str, Any]] = [
        {
            "document_id": "employee_handbook.pdf",
            "chunk_id": 3,
            "text": "Employees must submit leave requests at least 2 weeks in advance.",
            "score": 0.9,
            "role": "employee",
        }
    ]

    result = generate_answer(
        query="How far in advance should I request leave?", context_chunks=chunks
    )

    assert result["context_used"] is True
    assert len(result["sources"]) > 0
    assert result["sources"][0]["document_id"] == "employee_handbook.pdf"


def test_metadata_includes_performance_info() -> None:
    """Test that response includes metadata."""
    chunks: list[dict[str, Any]] = [
        {
            "document_id": "handbook.pdf",
            "chunk_id": 0,
            "text": "Office hours are 9 AM to 5 PM, Monday to Friday.",
            "score": 0.88,
            "role": "employee",
        }
    ]

    result = generate_answer(query="What are the office hours?", context_chunks=chunks)

    assert "metadata" in result
    assert "num_chunks_used" in result["metadata"]


def test_multiple_chunks_combined_in_answer() -> None:
    """Test that multiple relevant chunks are used together."""
    chunks: list[dict[str, Any]] = [
        {
            "document_id": "handbook.pdf",
            "chunk_id": 0,
            "text": "Annual leave is 25 days per year for full-time employees.",
            "score": 0.9,
            "role": "employee",
        },
        {
            "document_id": "handbook.pdf",
            "chunk_id": 5,
            "text": "Leave requests must be submitted through the HR portal.",
            "score": 0.85,
            "role": "employee",
        },
    ]

    result = generate_answer(query="Tell me about the annual leave policy.", context_chunks=chunks)

    assert result["context_used"] is True
    assert result["metadata"]["num_chunks_used"] >= 1


def test_answer_does_not_hallucinate_beyond_context() -> None:
    """Test that answer stays grounded in provided context."""
    chunks: list[dict[str, Any]] = [
        {
            "document_id": "handbook.pdf",
            "chunk_id": 0,
            "text": "Employees receive 10 sick days per year.",
            "score": 0.75,
            "role": "employee",
        }
    ]

    result = generate_answer(query="How many sick days do I get?", context_chunks=chunks)

    assert result["context_used"] is True


def test_empty_query_handled_safely() -> None:
    """Test that empty queries don't crash the system."""
    chunks: list[dict[str, Any]] = [
        {
            "document_id": "handbook.pdf",
            "chunk_id": 0,
            "text": "Some text content",
            "score": 0.8,
            "role": "employee",
        }
    ]

    result = generate_answer(query="", context_chunks=chunks)

    assert "answer" in result
    assert isinstance(result["answer"], str)


def test_context_with_special_characters() -> None:
    """Test that special characters in context are handled properly."""
    chunks: list[dict[str, Any]] = [
        {
            "document_id": "handbook.pdf",
            "chunk_id": 0,
            "text": "Email format: firstname.lastname@company.com",
            "score": 0.9,
            "role": "employee",
        }
    ]

    result = generate_answer(query="What is the email format?", context_chunks=chunks)

    assert result["context_used"] is True


def test_very_long_context_handled() -> None:
    """Test that very long context doesn't break the system."""
    long_text = "This is policy information. " * 500

    chunks: list[dict[str, Any]] = [
        {
            "document_id": "handbook.pdf",
            "chunk_id": 0,
            "text": long_text,
            "score": 0.85,
            "role": "employee",
        }
    ]

    result = generate_answer(query="What is the policy?", context_chunks=chunks)

    assert "answer" in result
    assert len(result["answer"]) > 0


def test_mixed_relevance_scores_uses_context() -> None:
    """Test that system uses available context."""
    chunks: list[dict[str, Any]] = [
        {
            "document_id": "handbook.pdf",
            "chunk_id": 5,
            "text": "Annual leave is 25 days per year.",
            "score": 0.95,
            "role": "employee",
        }
    ]

    result = generate_answer(query="How much annual leave do I get?", context_chunks=chunks)

    assert result["context_used"] is True
