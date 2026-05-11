from app.retrieval.vector_store import VectorStore
from app.llm.answer_service import generate_answer

vs = VectorStore()

# Test query
query = "How many days of annual leave do employees get?"

# Search
chunks = vs.search(query=query, role="employee", limit=3)
print(f"Found {len(chunks)} chunks")

# Generate answer
result = generate_answer(query=query, context_chunks=chunks)

print(f"\n✅ Answer: {result['answer']}")
print(f"\n📚 Sources: {len(result['sources'])}")
for source in result['sources']:
    print(f"  - {source['document_id']} (score: {source['score']:.3f})")
print(f"\n📊 Metadata: {result['metadata']}")