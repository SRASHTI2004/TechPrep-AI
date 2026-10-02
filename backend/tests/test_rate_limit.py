from app.core.rate_limit import limiter


def test_login_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(limiter, "enabled", True)
    limiter.reset()
    codes = [
        client.post(
            "/api/v1/auth/login", data={"username": "x@example.com", "password": "wrong-pass"}
        ).status_code
        for _ in range(12)
    ]
    limiter.reset()
    assert codes[:10] == [401] * 10
    assert 429 in codes[10:]
