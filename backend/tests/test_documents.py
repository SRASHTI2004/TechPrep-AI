from pathlib import Path

from tests.helpers import make_pdf


def _upload(
    client, headers, name="notes.md", content=b"# Title\n\nSome notes.", ctype="text/markdown"
):
    return client.post("/api/v1/documents", headers=headers, files={"file": (name, content, ctype)})


def test_upload_list_get_delete(client, auth_headers, settings):
    r = _upload(client, auth_headers)
    assert r.status_code == 202, r.text
    doc = r.json()
    assert doc["filename"] == "notes.md"
    assert doc["size_bytes"] > 0

    listing = client.get("/api/v1/documents", headers=auth_headers).json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == doc["id"]
    assert client.get(f"/api/v1/documents/{doc['id']}", headers=auth_headers).status_code == 200

    stored = list(Path(settings.upload_dir).rglob(f"{doc['id']}*"))
    assert len(stored) == 1

    assert client.delete(f"/api/v1/documents/{doc['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/documents/{doc['id']}", headers=auth_headers).status_code == 404
    assert not stored[0].exists()


def test_users_cannot_see_each_others_documents(client, auth_headers, other_auth_headers):
    doc = _upload(client, auth_headers).json()
    assert client.get("/api/v1/documents", headers=other_auth_headers).json()["total"] == 0
    assert (
        client.get(f"/api/v1/documents/{doc['id']}", headers=other_auth_headers).status_code == 404
    )
    assert (
        client.delete(f"/api/v1/documents/{doc['id']}", headers=other_auth_headers).status_code
        == 404
    )


def test_path_traversal_filename_is_neutralised(client, auth_headers, settings):
    r = _upload(client, auth_headers, name="../../../evil.md")
    assert r.status_code == 202
    assert r.json()["filename"] == "evil.md"
    for p in Path(settings.upload_dir).rglob("*"):
        assert Path(settings.upload_dir) in p.resolve().parents


def test_rejects_unsupported_type(client, auth_headers):
    r = _upload(
        client, auth_headers, name="run.exe", content=b"MZ...", ctype="application/octet-stream"
    )
    assert r.status_code == 415


def test_rejects_fake_pdf(client, auth_headers):
    r = _upload(client, auth_headers, name="x.pdf", content=b"not a pdf", ctype="application/pdf")
    assert r.status_code == 400


def test_accepts_real_pdf(client, auth_headers):
    r = _upload(
        client,
        auth_headers,
        name="x.pdf",
        content=make_pdf(["Hello page one"]),
        ctype="application/pdf",
    )
    assert r.status_code == 202


def test_rejects_too_large(client, auth_headers, settings, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    r = _upload(client, auth_headers, content=b"a" * (1024 * 1024 + 10))
    assert r.status_code == 413


def test_duplicate_upload_conflict(client, auth_headers, other_auth_headers):
    first = _upload(client, auth_headers).json()
    r = _upload(client, auth_headers, name="copy.md")
    assert r.status_code == 409
    assert r.json()["detail"]["document_id"] == first["id"]
    # A different user may upload the same file.
    assert _upload(client, other_auth_headers).status_code == 202


def test_empty_file_rejected(client, auth_headers):
    assert _upload(client, auth_headers, content=b"").status_code == 400
