from app.retrieval.vector_store import VectorStore
from app.ingestion.loaders.pdf_loader import load_pdf
from app.ingestion.chunkers.recursive_chunker import recursive_chunk_text

# Initialize vector store
vs = VectorStore()

# Delete collection
vs.client.delete_collection(vs.collection_name)
print("✅ Deleted collection")

# Recreate (happens automatically)
vs = VectorStore()
print("✅ Collection recreated")

# Verify it's empty
info = vs.client.get_collection(vs.collection_name)
print(f"Points in collection: {info.points_count}")


# Load and chunk a document
text = load_pdf("/home/fatemeh/Downloads/leave_policy.pdf")
chunks = recursive_chunk_text(text, chunk_size=500, chunk_overlap=100)

print(f"Loaded {len(chunks)} chunks")

# Add to vector store
count = vs.add_documents(
    chunks=chunks,
    document_id="employee_handbook.pdf",
    role="employee"
)
print(f"✅ Added {count} chunks to Qdrant")

# Search
results = vs.search(
    query="How many days of leave do employees get?",
    role="employee",
    limit=3
)

print(f"\n✅ Found {len(results)} results:")
for i, result in enumerate(results, 1):
    print(f"\n{i}. Score: {result['score']:.4f}")
    print(f"   Text: {result['text'][:150]}...")