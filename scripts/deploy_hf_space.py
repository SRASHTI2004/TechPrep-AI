"""Upload the backend to a Hugging Face Docker Space.

Usage (from the repo root, after `uvx --from huggingface_hub hf auth login` with a write token):

    uv run --no-project --with huggingface_hub python scripts/deploy_hf_space.py <user>/<space>

The Space builds backend/Dockerfile itself. Secrets (DATABASE_URL, JWT_SECRET, API keys, ...)
are set in the Space settings, never uploaded. See docs/DEPLOYMENT.md.
"""

import sys
from pathlib import Path

from huggingface_hub import HfApi

REPO_DIR = Path(__file__).resolve().parents[1]
BACKEND_FILES = [
    "Dockerfile",
    "pyproject.toml",
    "uv.lock",
    "alembic.ini",
    "alembic/**",
    "app/**",
    "eval/**",
]
IGNORE = ["**/__pycache__/**", "**/*.pyc", "eval/reports/*.json"]


def main() -> None:
    if len(sys.argv) != 2 or "/" not in sys.argv[1]:
        sys.exit("usage: deploy_hf_space.py <hf-user>/<space-name>")
    space = sys.argv[1]
    api = HfApi()
    api.create_repo(space, repo_type="space", space_sdk="docker", exist_ok=True)
    api.upload_file(
        path_or_fileobj=REPO_DIR / "deploy" / "huggingface" / "README.md",
        path_in_repo="README.md",
        repo_id=space,
        repo_type="space",
        commit_message="Update Space card",
    )
    api.upload_folder(
        folder_path=REPO_DIR / "backend",
        repo_id=space,
        repo_type="space",
        allow_patterns=BACKEND_FILES,
        ignore_patterns=IGNORE,
        delete_patterns=["app/**", "alembic/**", "eval/**"],
        commit_message="Deploy backend from GitHub",
    )
    user, name = space.split("/")
    print(f"Uploaded. Build logs: https://huggingface.co/spaces/{space}")
    print(f"API URL once running: https://{user}-{name}.hf.space".lower().replace("_", "-"))


if __name__ == "__main__":
    main()
