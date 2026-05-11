from app.ingestion.loaders.pdf_loader import load_pdf
import pytest

def test_load_pdf_success():
    """Test that PDF loading works."""
    text = load_pdf("data/sample_docs/default_handbook.pdf")
    assert len(text) > 50
    assert isinstance(text, str)

def test_load_pdf_missing_file():
    """Test that missing file raises error."""
    with pytest.raises(FileNotFoundError):
        load_pdf("nonexistent.pdf")

