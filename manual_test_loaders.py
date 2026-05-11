# from app.ingestion.loaders.pdf_loader import load_pdf
# from app.ingestion.loaders.docx_loader import load_docx

# print("\n=== Test 2: Real files ===")
# try:
#     pdf_text = load_pdf("/home/fatemeh/Downloads/english/Makkar.pdf")
#     print(f"✅ PDF loaded: {len(pdf_text)} characters")
#     print(f"First 200 chars: {pdf_text[:200]}")
# except Exception as e:
#     print(f"❌ Failed: {e}")

# try:
#     docx_text = load_docx("/home/fatemeh/Downloads/day-1.docx")
#     print(f"✅ DOCX loaded: {len(docx_text)} characters")
#     print(f"First 200 chars: {docx_text[:200]}")
# except Exception as e:
#     print(f"❌ Failed: {e}")

from app.ingestion.loaders.pdf_loader import load_pdf
from app.ingestion.loaders.docx_loader import load_docx

print("=== Test 1: Non-existent files ===")
try:
    load_pdf("nonexistent.pdf")
    print("❌ Should have raised FileNotFoundError")
except FileNotFoundError as e:
    print(f"✅ Correct error: {e}")

try:
    load_docx("nonexistent.docx")
    print("❌ Should have raised FileNotFoundError")
except FileNotFoundError as e:
    print(f"✅ Correct error: {e}")