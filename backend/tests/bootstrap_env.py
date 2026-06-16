"""Configure DATABASE_URL before app modules are imported (see conftest.py)."""

from __future__ import annotations

import os
import socket
from pathlib import Path

from dotenv import load_dotenv

# Repo-root .env (pytest runs from backend/, but compose env lives one level up).
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def _use_localhost_when_db_unresolvable() -> None:
    """Rewrite docker-compose host `db` → `localhost` for pytest on the host machine.

    Inside the backend container `db` resolves; on Windows/macOS it usually does not.
    CI already sets DATABASE_URL to localhost explicitly.
    """
    url = os.environ.get("DATABASE_URL", "")
    if "@db:" not in url and "@db/" not in url:
        return
    try:
        socket.getaddrinfo("db", 5432, type=socket.SOCK_STREAM)
    except OSError:
        os.environ["DATABASE_URL"] = url.replace("@db:", "@localhost:").replace(
            "@db/", "@localhost/"
        )


_use_localhost_when_db_unresolvable()
