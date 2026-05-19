import fitz
from pathlib import Path


def load_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text as a single string

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the PDF is corrupted or invalid
    """
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        doc = fitz.open(file_path)
        text_parts = []

        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(page_text)

        doc.close()

        # Join all pages with double newline
        full_text = "\n\n".join(text_parts)

        # Clean up extra whitespace
        return full_text.strip()

    except fitz.FileDataError as e:
        raise ValueError(f"Corrupted or invalid PDF: {e}")
    except Exception as e:
        raise ValueError(f"Error reading PDF: {e}")
