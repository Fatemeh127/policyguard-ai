"""Production-ready DOCX text extractor using python-docx."""

from pathlib import Path

from docx import Document


def load_docx(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {file_path}")

    try:
        doc = Document(path)
        text_parts = []

        def add_text(text: str):
            text = text.strip()
            if text and text not in text_parts:
                text_parts.append(text)

        # 1. Paragraphs
        for p in doc.paragraphs:
            add_text(p.text)

        # 2. Tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    add_text(cell.text)

        text = "\n".join(text_parts).strip()

        if not text:
            raise ValueError("No extractable text found in DOCX (may contain only images/shapes).")

        return text

    except Exception as e:
        raise ValueError(f"Failed to read DOCX file: {e}") from e
