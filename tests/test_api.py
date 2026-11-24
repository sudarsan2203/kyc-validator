"""Tests that call the API over HTTP and check the database."""

from sqlalchemy import select

from app import auth
from app.models import ApiKey, ValidationLog
from app.rate_limiter import SlidingWindowRateLimiter
from tests.conftest import VALID_AADHAAR, VALID_GSTIN, VALID_IFSC, VALID_PAN

# ---------- Health and docs ----------


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_id_types(client):
    assert client.get("/id-types").json() == ["aadhaar", "gstin", "ifsc", "pan"]


# ---------- Authentication ----------


def test_request_without_key_is_rejected(client):
    response = client.post("/validate/pan", json={"value": VALID_PAN})
    assert response.status_code == 401


def test_request_with_wrong_key_is_rejected(client):
    response = client.post("/validate/pan", json={"value": VALID_PAN}, headers={"X-API-Key": "nope"})
    assert response.status_code == 401


def test_deactivated_key_is_rejected(client, headers, db):
    db.scalar(select(ApiKey)).is_active = False
    db.commit()
    response = client.post("/validate/pan", json={"value": VALID_PAN}, headers=headers)
    assert response.status_code == 401


# ---------- Single validation ----------


def test_validate_valid_pan(client, headers):
    response = client.post("/validate/pan", json={"value": VALID_PAN}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "id_type": "pan",
        "is_valid": True,
        "masked_value": "XXXXXX234A",
        "errors": [],
        "details": {"holder_type": "Individual"},
    }


def test_validate_invalid_pan_returns_200_with_errors(client, headers):
    response = client.post("/validate/pan", json={"value": "12345"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert body["errors"]


def test_validate_each_supported_type(client, headers):
    samples = {"pan": VALID_PAN, "aadhaar": VALID_AADHAAR, "gstin": VALID_GSTIN, "ifsc": VALID_IFSC}
    for id_type, value in samples.items():
        response = client.post(f"/validate/{id_type}", json={"value": value}, headers=headers)
        assert response.json()["is_valid"] is True, id_type


def test_unknown_id_type_returns_404(client, headers):
    response = client.post("/validate/passport", json={"value": "X1234567"}, headers=headers)
    assert response.status_code == 404


def test_empty_value_is_rejected(client, headers):
    response = client.post("/validate/pan", json={"value": ""}, headers=headers)
    assert response.status_code == 422


def test_response_never_contains_the_full_id(client, headers):
    response = client.post("/validate/aadhaar", json={"value": VALID_AADHAAR}, headers=headers)
    assert VALID_AADHAAR not in response.text


# ---------- Audit log ----------


def test_validation_is_logged_with_masked_value_only(client, headers, db):
    client.post("/validate/aadhaar", json={"value": VALID_AADHAAR}, headers=headers)

    logs = db.scalars(select(ValidationLog)).all()
    assert len(logs) == 1
    assert logs[0].id_type == "aadhaar"
    assert logs[0].is_valid is True
    assert logs[0].masked_value == "XXXXXXXX0124"
    assert logs[0].created_at is not None


def test_api_key_is_stored_hashed(api_key, db):
    stored = db.scalar(select(ApiKey))
    assert stored.key_hash != api_key
    assert stored.key_hash == auth.hash_key(api_key)


# ---------- Batch ----------


def test_batch_with_mixed_results(client, headers, db):
    body = {
        "items": [
            {"id_type": "pan", "value": VALID_PAN},
            {"id_type": "ifsc", "value": "WRONG"},
            {"id_type": "passport", "value": "X1234567"},
        ]
    }
    response = client.post("/validate/batch", json=body, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert (data["total"], data["valid"], data["invalid"]) == (3, 1, 2)
    assert [item["is_valid"] for item in data["results"]] == [True, False, False]
    assert "Unsupported" in data["results"][2]["errors"][0]

    # Only supported types are written to the audit log.
    assert len(db.scalars(select(ValidationLog)).all()) == 2


def test_batch_size_is_limited(client, headers):
    body = {"items": [{"id_type": "pan", "value": VALID_PAN}] * 101}
    assert client.post("/validate/batch", json=body, headers=headers).status_code == 422


def test_empty_batch_is_rejected(client, headers):
    assert client.post("/validate/batch", json={"items": []}, headers=headers).status_code == 422


# ---------- GSTIN-PAN match ----------


def test_gstin_and_pan_match(client, headers):
    body = {"gstin": VALID_GSTIN, "pan": VALID_PAN}
    response = client.post("/validate/gstin-pan-match", json=body, headers=headers)
    assert response.json() == {"gstin_valid": True, "pan_valid": True, "match": True}


def test_gstin_and_different_pan_do_not_match(client, headers):
    body = {"gstin": VALID_GSTIN, "pan": "BBBPB5678B"}
    response = client.post("/validate/gstin-pan-match", json=body, headers=headers)
    assert response.json() == {"gstin_valid": True, "pan_valid": True, "match": False}


def test_invalid_gstin_never_matches(client, headers):
    body = {"gstin": VALID_GSTIN[:14] + "A", "pan": VALID_PAN}
    response = client.post("/validate/gstin-pan-match", json=body, headers=headers)
    assert response.json() == {"gstin_valid": False, "pan_valid": True, "match": False}


# ---------- Rate limiting ----------


def test_rate_limit_returns_429(client, headers, monkeypatch):
    monkeypatch.setattr(auth, "limiter", SlidingWindowRateLimiter(max_requests=2, window_seconds=60))

    statuses = [
        client.post("/validate/pan", json={"value": VALID_PAN}, headers=headers).status_code
        for _ in range(3)
    ]
    assert statuses == [200, 200, 429]


def test_rate_limit_response_says_when_to_retry(client, headers, monkeypatch):
    monkeypatch.setattr(auth, "limiter", SlidingWindowRateLimiter(max_requests=1, window_seconds=60))
    client.get("/stats", headers=headers)
    response = client.get("/stats", headers=headers)
    assert response.status_code == 429
    assert 0 < int(response.headers["Retry-After"]) <= 60


# ---------- Stats ----------


def test_stats_for_a_new_key_are_empty(client, headers):
    response = client.get("/stats", headers=headers)
    assert response.json() == {"total_validations": 0, "by_type": [], "daily": []}


def test_stats_count_by_type_and_day(client, headers):
    client.post("/validate/pan", json={"value": VALID_PAN}, headers=headers)
    client.post("/validate/pan", json={"value": "BAD"}, headers=headers)
    client.post("/validate/ifsc", json={"value": VALID_IFSC}, headers=headers)

    data = client.get("/stats", headers=headers).json()
    assert data["total_validations"] == 3
    assert data["by_type"] == [
        {"id_type": "ifsc", "total": 1, "valid": 1, "invalid": 0},
        {"id_type": "pan", "total": 2, "valid": 1, "invalid": 1},
    ]
    assert len(data["daily"]) == 1
    assert data["daily"][0]["requests"] == 3
    assert data["daily"][0]["running_total"] == 3


def test_stats_only_show_the_callers_own_data(client, headers, db):
    client.post("/validate/pan", json={"value": VALID_PAN}, headers=headers)

    other_key = auth.generate_key()
    db.add(ApiKey(name="other-client", key_hash=auth.hash_key(other_key)))
    db.commit()

    data = client.get("/stats", headers={"X-API-Key": other_key}).json()
    assert data["total_validations"] == 0


# ---------- Admin: create API keys ----------


def test_admin_can_create_a_working_key(client, admin_token):
    response = client.post(
        "/api-keys", json={"name": "new-client"}, headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code == 201
    new_key = response.json()["api_key"]

    check = client.post("/validate/pan", json={"value": VALID_PAN}, headers={"X-API-Key": new_key})
    assert check.status_code == 200


def test_wrong_admin_token_is_rejected(client, admin_token):
    response = client.post("/api-keys", json={"name": "x"}, headers={"X-Admin-Token": "wrong"})
    assert response.status_code == 403


def test_missing_admin_token_is_rejected(client, admin_token):
    assert client.post("/api-keys", json={"name": "x"}).status_code == 403


def test_key_creation_is_off_when_no_admin_token_is_configured(client):
    response = client.post("/api-keys", json={"name": "x"}, headers={"X-Admin-Token": "anything"})
    assert response.status_code == 503
