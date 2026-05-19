from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_ask_endpoint_requires_auth():
    """Test that /ask requires API key."""
    response = client.post("/api/ask", json={"query": "test", "role": "employee", "limit": 5})

    assert response.status_code == 401
    assert "detail" in response.json()
