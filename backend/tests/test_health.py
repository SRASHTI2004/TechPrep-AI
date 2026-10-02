def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_ready_checks_database(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["checks"]["database"] == "ok"


def test_request_id_header_is_returned(client):
    r = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
