# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import secrets
import string
from pathlib import Path


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_state_dir() -> Path:
    """Get tsdbenv state directory path."""
    return Path.home() / ".tsdbenv"


def ensure_state_dir() -> Path:
    """Ensure state directory exists, create if needed."""
    state_dir = get_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir
