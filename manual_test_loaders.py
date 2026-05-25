from app.ingestion.loaders.docx_loader import load_docx
from app.ingestion.loaders.pdf_loader import load_pdf

print("=== Test 1: Non-existent files ===")
try:
    load_pdf("nonexistent.pdf")
    print("Should have raised FileNotFoundError")
except FileNotFoundError as e:
    print(f"Correct error: {e}")

try:
    load_docx("nonexistent.docx")
    print("Should have raised FileNotFoundError")
except FileNotFoundError as e:
    print(f"Correct error: {e}")
