"""Local .env file loader for multi-agent-runner.

Loads KEY=VALUE pairs from a .env file into os.environ.
No third-party dependencies required.

Rules:
- Ignore empty lines.
- Ignore lines starting with #.
- Only parse KEY=VALUE.
- Strip whitespace.
- Remove surrounding single or double quotes from values.
- Do not override existing environment variables unless override=True.
- Never print real secret values.
"""

from __future__ import annotations

import os
from pathlib import Path


def mask_secret(value: str, keep: int = 4) -> str:
    """Return a masked secret for safe logs.

    Examples:
        mask_secret("sk-1234567890") -> "sk-1...7890"
        mask_secret("ab") -> "****"
    """
    if len(value) <= keep:
        return "****"
    return value[:keep] + "..." + value[-keep:]


def load_dotenv_file(
    env_path: str | Path = ".env",
    override: bool = False,
) -> dict[str, str]:
    """Load simple KEY=VALUE pairs from a .env file.

    Args:
        env_path: Path to the .env file. Defaults to ".env" in cwd.
        override: If True, overwrite existing env vars. Default False.

    Returns:
        Dict of variables that were loaded into os.environ.
    """
    env_path = Path(env_path)
    if not env_path.is_absolute():
        env_path = Path.cwd() / env_path

    if not env_path.exists():
        return {}

    loaded: dict[str, str] = {}

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Only parse KEY=VALUE
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            if not key:
                continue

            # Remove surrounding quotes
            if len(value) >= 2:
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

            # Do not override existing env vars unless override=True
            if not override and key in os.environ:
                continue

            os.environ[key] = value
            loaded[key] = value

    return loaded
