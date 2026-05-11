from app.ingestion.chunkers.simple_chunker import chunk_text
from app.ingestion.chunkers.recursive_chunker import recursive_chunk_text
from app.ingestion.loaders.pdf_loader import load_pdf

# Load a real document
text = load_pdf("/home/fatemeh/Downloads/file.pdf")

# Test simple chunker
simple_chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
print(f"Simple chunker: {len(simple_chunks)} chunks")
print(f"First chunk: {simple_chunks[0]['text'][:200]}...")

# Test recursive chunker
recursive_chunks = recursive_chunk_text(text, chunk_size=500, chunk_overlap=100)
print(f"\nRecursive chunker: {len(recursive_chunks)} chunks")
print(f"First chunk: {recursive_chunks[0]['text'][:200]}...")