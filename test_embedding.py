from app.retrieval.embeddings import get_embedding

# Test 1: Normal text
text = "Employees are entitled to 20 days of annual leave"
embedding = get_embedding(text)
print(f"✅ Embedding generated: {len(embedding)} dimensions")
print(f"First 5 values: {embedding[:5]}")

# Test 2: Empty text (should raise error)
try:
    get_embedding("")
    print("❌ Should have raised ValueError")
except ValueError as e:
    print(f"✅ Correctly raised error: {e}")