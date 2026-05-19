from app.ingestion.chunkers.simple_chunker import chunk_text


def test_chunking_creates_correct_size():
    text = "A" * 1000 + "B" * 1000
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)

    # Should create ~4 chunks
    assert len(chunks) >= 3
    assert all(len(c["text"]) <= 500 for c in chunks)
