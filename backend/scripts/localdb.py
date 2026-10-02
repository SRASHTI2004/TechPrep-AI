"""Docker-free local Postgres 16 + pgvector for development (uses the `pgserver` wheel).

    uv run --group localdb python scripts/localdb.py url             # start + print DATABASE_URL
    uv run --group localdb python scripts/localdb.py run -- <cmd...>  # with DATABASE_URL set
    uv run --group localdb python scripts/localdb.py stop

With Docker available, prefer `docker compose up db` instead (see README).
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PGDATA = BACKEND_DIR / ".pgdata"


def start(dbname: str = "techprep") -> str:
    import pgserver

    srv = pgserver.get_server(str(PGDATA), cleanup_mode=None)  # keep running between commands
    srv.psql("CREATE EXTENSION IF NOT EXISTS vector;")
    exists = srv.psql(f"SELECT 1 FROM pg_database WHERE datname = '{dbname}';")
    if "(1 row)" not in exists:
        srv.psql(f'CREATE DATABASE "{dbname}";')
    uri = srv.get_uri(database=dbname)
    return uri.replace("postgresql://", "postgresql+psycopg://", 1)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "url"
    if cmd == "url":
        print(start())
        return 0
    if cmd == "run":
        args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[2:]
        env = {**os.environ, "DATABASE_URL": start()}
        return subprocess.call(args, env=env, cwd=BACKEND_DIR)
    if cmd == "stop":
        import pgserver

        pgserver.get_server(str(PGDATA), cleanup_mode="stop").cleanup()
        print("stopped")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
