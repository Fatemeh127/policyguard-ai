from app.api.deps import get_vector_store

def test_employee_cannot_access_manager_docs():
    """Employee should not see manager-only documents."""
    vs = get_vector_store()
    
    # Search as employee
    results = vs.search(
        query="manager salary",
        role="employee",
        limit=10
    )
    
    # Should return no manager documents
    assert all(r["role"] != "manager" for r in results)