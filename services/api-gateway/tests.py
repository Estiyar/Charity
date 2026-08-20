from fastapi.testclient import TestClient

from app import app, match_service


def test_match_ecp_to_identity():
    assert match_service("/api/auth/ecp/challenge") == "identity"


def test_match_payment_session_to_payments():
    assert match_service("/api/payments/session") == "payments"
    assert match_service("/api/payments/webhook/freedompay") == "payments"


def test_match_catalog_to_cards():
    assert match_service("/api/catalog") == "cards"
    assert match_service("/api/catalog/references") == "cards"


def test_match_redistribution_and_closed_refunds_to_payments():
    assert match_service("/api/redistribution/my/") == "payments"
    assert match_service("/api/refunds/my/") == "payments"


def test_match_donate_to_payments():
    assert match_service("/api/cards/12/donate/") == "payments"


def test_match_documents_nested():
    assert match_service("/api/cards/12/documents/") == "documents"


def test_match_profile_me_to_profile():
    assert match_service("/api/profile/me") == "profile"
    assert match_service("/api/profile/12") == "profile"


def test_match_beneficiaries_to_profile():
    assert match_service("/api/beneficiaries") == "profile"
    assert match_service("/api/representations/verify") == "profile"


def test_match_medregistry_lookup_to_verification():
    assert match_service("/api/medregistry/lookup/") == "verification"


def test_health_endpoint_shape():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "api-gateway"
    assert "dependencies" in payload
