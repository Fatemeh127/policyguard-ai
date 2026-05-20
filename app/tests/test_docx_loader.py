"""Tests for DOCX document loader."""

from pathlib import Path

import pytest

from app.ingestion.loaders.docx_loader import load_docx


def test_load_docx_missing_file_raises_error() -> None:
    """Test that missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_docx("nonexistent.docx")


def test_load_docx_returns_string() -> None:
    """Test that load_docx returns a string."""
    # Skip if no sample documents available
    sample_docs = Path("data/sample_docs")
    if not sample_docs.exists():
        pytest.skip("No sample documents found")

    docx_files = list(sample_docs.glob("*.docx"))
    if not docx_files:
        pytest.skip("No DOCX files in sample_docs")

    text = load_docx(str(docx_files[0]))

    assert isinstance(text, str)
    assert len(text) > 0
