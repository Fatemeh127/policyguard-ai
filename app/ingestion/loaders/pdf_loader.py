from pathlib import Path

import fitz


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

    # Check if file exists
    def load_pdf(file_path: str) -> str:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        try:
            text_parts = []

            with fitz.open(file_path) as doc:
                for page in enumerate(doc, start=1):
                    page_text = page.get_text()
                    if page_text.strip():
                        text_parts.append(page_text)

            return "\n\n".join(text_parts).strip()

        except fitz.FileDataError as e:
            raise ValueError(f"Corrupted or invalid PDF: {file_path}") from e

        except Exception as e:
            raise ValueError(f"Unexpected error reading PDF: {file_path}") from e
