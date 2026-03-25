"""
Utilities for loading local environment configuration.
"""

from __future__ import annotations

import os
from pathlib import Path


def _parse_env_line(line: str) -> tuple[str, str] | None:
    """Parse a simple KEY=VALUE environment line."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not key:
        return None

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]

    return key, value


def load_local_env() -> None:
    """
    Load environment variables from local project files if present.

    Precedence:
    - existing process environment wins
    - `.env.local`
    - `.env`
    """
    project_root = Path(__file__).resolve().parents[2]
    for filename in (".env", ".env.local"):
        env_path = project_root / filename
        if not env_path.exists():
            continue

        for line in env_path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(line)
            if parsed is None:
                continue

            key, value = parsed
            os.environ.setdefault(key, value)
