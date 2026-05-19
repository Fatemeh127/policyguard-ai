from unittest.mock import patch
from app.api.deps import get_vector_store


def test_employee_cannot_access_manager_docs():
    """Employee should not see manager-only documents."""

    with patch("app.retrieval.embeddings.client.embeddings.create") as mock_embed:
        mock_embed.return_value.data = [type("obj", (object,), {"embedding": [0.1] * 1536})]

        vs = get_vector_store()

        results = vs.search(query="manager salary", role="employee", limit=10)

        assert all(r["role"] != "manager" for r in results)
