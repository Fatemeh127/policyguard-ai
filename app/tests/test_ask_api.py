"""
Tests for API authentication and authorization behavior.
"""

from fastapi.testclient import TestClient

from app.api.deps import get_ask_service
from app.api.main import app
from app.core.types import Role
from app.schemas.ask import AskRequest, AskResponse


class FakeAskService:
    async def answer_question(self, ask_request: AskRequest, user_role: Role) -> AskResponse:
        return AskResponse(
            answer="Test answer",
            sources=[],
            context_used=True,
            metadata={"cache": "MISS"},
        )


def override_get_ask_service() -> FakeAskService:
    return FakeAskService()


app.dependency_overrides[get_ask_service] = override_get_ask_service

client = TestClient(app)


def test_ask_endpoint_requires_auth() -> None:
    response = client.post(
        "/api/ask",
        json={"query": "test", "role": "employee", "limit": 5},
    )

    assert response.status_code == 401
    assert "detail" in response.json()