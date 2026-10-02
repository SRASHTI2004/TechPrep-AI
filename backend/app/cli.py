"""Small admin CLI.

uv run python -m app.cli create-user you@example.com 'password' [--admin]
uv run python -m app.cli promote-admin you@example.com
uv run python -m app.cli seed-sample you@example.com        # ingest data/sample/*.md
uv run python -m app.cli search you@example.com "what is consistent hashing"
"""

import argparse
import io
import sys
from pathlib import Path

from app.core.config import REPO_DIR, get_settings
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import Role
from app.repositories.users import UserRepository
from app.services.document_service import DocumentService, DuplicateDocumentError
from app.services.ingestion_service import ingest_document

SAMPLE_DIR = REPO_DIR / "data" / "sample"


def _user(db, email: str):
    user = UserRepository(db).get_by_email(email)
    if user is None:
        sys.exit(f"No user with email {email}")
    return user


def create_user(email: str, password: str, admin: bool) -> None:
    with SessionLocal() as db:
        repo = UserRepository(db)
        if repo.get_by_email(email):
            print(f"{email} already exists")
            return
        repo.create(email, hash_password(password), Role.ADMIN if admin else Role.USER)
        db.commit()
        print(f"created {email}{' (admin)' if admin else ''}")


def promote_admin(email: str) -> None:
    with SessionLocal() as db:
        user = _user(db, email)
        user.role = Role.ADMIN
        db.commit()
        print(f"{email} is now an admin")


def seed_sample(email: str) -> None:
    with SessionLocal() as db:
        user = _user(db, email)
        for path in sorted(SAMPLE_DIR.glob("*.md")):
            if path.name == "ATTRIBUTION.md":
                continue
            try:
                doc = DocumentService(db).create_from_upload(
                    user.id, path.name, io.BytesIO(path.read_bytes())
                )
            except DuplicateDocumentError as exc:
                print(f"skip {path.name}: already uploaded")
                doc = exc.existing
            status = ingest_document(doc.id)
            db.refresh(doc)
            print(f"{path.name}: {status} ({doc.num_chunks} chunks)")


def search(email: str, query: str) -> None:
    from app.rag.retrieval import Retriever

    with SessionLocal() as db:
        user = _user(db, email)
        result = Retriever(db).search(user.id, query)
        print(f"mode={result.mode} reranked={result.reranked} timings={result.timings_ms}")
        for i, c in enumerate(result.chunks, 1):
            where = f"p.{c.page}" if c.page else (c.section or "")
            print(f"[{i}] score={c.score:.3f} sim={c.similarity:.3f} {c.filename} | {where}")
            print("    " + c.content[:160].replace("\n", " "))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-user")
    p.add_argument("email")
    p.add_argument("password")
    p.add_argument("--admin", action="store_true")
    sub.add_parser("promote-admin").add_argument("email")
    sub.add_parser("seed-sample").add_argument("email")
    p = sub.add_parser("search")
    p.add_argument("email")
    p.add_argument("query")
    args = parser.parse_args()

    if args.cmd == "create-user":
        create_user(args.email, args.password, args.admin)
    elif args.cmd == "promote-admin":
        promote_admin(args.email)
    elif args.cmd == "seed-sample":
        seed_sample(args.email)
    elif args.cmd == "search":
        search(args.email, args.query)


if __name__ == "__main__":
    Path(get_settings().upload_dir).mkdir(parents=True, exist_ok=True)
    main()
