#!/usr/bin/env python3
"""Fail if personal files, PDFs, images or secrets are about to be committed.

Usage:
    python scripts/check_forbidden_files.py          # check staged files (pre-commit hook)
    python scripts/check_forbidden_files.py --all    # check every tracked file (CI)

This is a second line of defence behind .gitignore: `git add -f` bypasses
.gitignore, but it does not bypass this check.
"""
from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from pathlib import PurePosixPath

# Paths (glob, matched case-insensitively against the repo-relative path) that must never be committed.
FORBIDDEN_PATH_PATTERNS = [
    ".env",
    "*/.env",
    ".env.*",
    "*/.env.*",
    "data/private/*",
    "data/uploads/*",
    "*uploads/*",
    "*resume*",
    "*my_profile*",
    "*.pdf",
    "*.doc",
    "*.docx",
    "*.lnk",
    "*.jpg",
    "*.jpeg",
    "*.heic",
    "*.pem",
    "*.key",
    "*.pgdata/*",
]
ALLOWED_PATH_PATTERNS = [
    ".env.example",
    "*/.env.example",
]

# Content patterns that look like real credentials.
SECRET_PATTERNS = {
    "Groq API key": re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    "OpenAI-style key": re.compile(r"sk-[A-Za-z0-9]{32,}"),
    "Langfuse secret key": re.compile(r"sk-lf-[A-Za-z0-9\-]{20,}"),
    "Private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
}
SKIP_CONTENT_SCAN = {"scripts/check_forbidden_files.py"}
MAX_SCAN_BYTES = 2_000_000


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def list_files(check_all: bool) -> list[str]:
    if check_all:
        out = _git("ls-files")
    else:
        out = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [line.strip() for line in out.splitlines() if line.strip()]


def is_forbidden_path(path: str) -> bool:
    p = PurePosixPath(path).as_posix().lower()
    if any(fnmatch.fnmatch(p, pat) for pat in ALLOWED_PATH_PATTERNS):
        return False
    return any(fnmatch.fnmatch(p, pat) for pat in FORBIDDEN_PATH_PATTERNS)


def find_secrets(path: str, check_all: bool) -> list[str]:
    if path in SKIP_CONTENT_SCAN:
        return []
    try:
        if check_all:
            with open(path, "rb") as fh:
                raw = fh.read(MAX_SCAN_BYTES)
        else:
            # Scan the staged blob, not the working-tree file.
            raw = subprocess.run(
                ["git", "show", f":{path}"], check=True, capture_output=True
            ).stdout[:MAX_SCAN_BYTES]
    except (OSError, subprocess.CalledProcessError):
        return []
    text = raw.decode("utf-8", errors="ignore")
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text)]


def main() -> int:
    check_all = "--all" in sys.argv
    problems: list[str] = []
    for path in list_files(check_all):
        if is_forbidden_path(path):
            problems.append(f"forbidden file: {path}")
            continue
        for secret in find_secrets(path, check_all):
            problems.append(f"possible {secret} in: {path}")

    if problems:
        print("Commit blocked: personal files or secrets detected.\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            "\nUnstage them with `git restore --staged <file>`. "
            "See docs/DECISIONS.md (D-002) for why this check exists.",
            file=sys.stderr,
        )
        return 1
    print(f"check_forbidden_files: OK ({'all tracked' if check_all else 'staged'} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
