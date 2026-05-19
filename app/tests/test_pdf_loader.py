"""Tests for PDF document loader."""

import pytest
from pathlib import Path
from app.ingestion.loaders.pdf_loader import load_pdf


def test_load_pdf_missing_file_raises_error():
    """Test that missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_pdf("nonexistent.pdf")


def test_load_pdf_returns_string():
    """Test that load_pdf returns a string."""
    # Skip if no sample PDF available
    sample_pdf = Path("data/sample_docs")
    if not sample_pdf.exists():
        pytest.skip("No sample documents found")

    pdf_files = list(sample_pdf.glob("*.pdf"))
    if not pdf_files:
        pytest.skip("No PDF files in sample_docs")

    text = load_pdf(str(pdf_files[0]))
    assert isinstance(text, str)
    assert len(text) > 0
