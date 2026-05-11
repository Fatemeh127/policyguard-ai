from app.ingestion.loaders.docx_loader import load_docx
import pytest

def test_load_pdf_success():
    """Test that PDF loading works."""
    text = load_docx("data/sample_docs/default_handbook.docx")
    assert len(text) > 50
    assert isinstance(text, str)

def test_load_pdf_missing_file():
    """Test that missing file raises error."""
    with pytest.raises(FileNotFoundError):
        load_docx("nonexistent.docx")

