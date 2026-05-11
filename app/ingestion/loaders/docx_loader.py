"""DOCX document loader using python-docx."""
from docx import Document
from pathlib import Path


def load_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file.
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        Extracted text as a single string
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the DOCX is corrupted or invalid
    """
    path = Path(file_path)
    
    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {file_path}")
    
    try:
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        # Join paragraphs with newline
        full_text = "\n".join(paragraphs)
        
        return full_text.strip()
        
    except Exception as e:
        raise ValueError(f"Error reading DOCX: {e}")