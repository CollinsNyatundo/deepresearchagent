from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from research_engine.api import app, verify_supabase_jwt
from research_engine.citations.verifier import CitationStatus

client = TestClient(app)


def test_verify_citation_unauthorized():
    """Verify that POST /citations/verify returns 401 without token."""
    response = client.post("/citations/verify", json={
        "citation_text": "See https://doi.org/10.1234/example"
    })
    assert response.status_code == 401


@patch("research_engine.api.CitationVerifier")
def test_verify_citation_with_valid_token(mock_verifier_class):
    """Verify that POST /citations/verify returns 200 with valid token."""
    app.dependency_overrides[verify_supabase_jwt] = lambda: {"sub": "test-user-id"}

    mock_verifier = AsyncMock()
    mock_verifier.verify.return_value = AsyncMock(
        status=CitationStatus.VERIFIED,
        found=True,
        title="Test Paper",
        authors=["Smith, John"],
        year=2020,
        doi="10.1234/example",
        url="https://doi.org/10.1234/example",
        confidence=0.95,
        sources=2,
        databases=[],
    )
    mock_verifier_class.return_value = mock_verifier

    response = client.post("/citations/verify", json={
        "citation_text": "See https://doi.org/10.1234/example"
    })

    # Clean up override
    app.dependency_overrides.pop(verify_supabase_jwt, None)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["found"] is True
    assert data["confidence"] == 0.95
    assert data["sources"] == 2


@patch("research_engine.api.CitationVerifier")
def test_verify_citation_empty_text(mock_verifier_class):
    """Verify that empty citation text returns failed status."""
    app.dependency_overrides[verify_supabase_jwt] = lambda: {"sub": "test-user-id"}

    mock_verifier = AsyncMock()
    mock_verifier.verify.return_value = AsyncMock(
        status=CitationStatus.FAILED,
        found=False,
        title="",
        authors=None,
        year=None,
        doi="",
        url="",
        confidence=0.0,
        sources=0,
        databases=[],
    )
    mock_verifier_class.return_value = mock_verifier

    response = client.post("/citations/verify", json={
        "citation_text": ""
    })

    # Clean up override
    app.dependency_overrides.pop(verify_supabase_jwt, None)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["found"] is False
