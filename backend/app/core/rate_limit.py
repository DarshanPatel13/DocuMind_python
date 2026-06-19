"""Shared slowapi limiter, keyed by client IP. Wired into the app in main.py
and applied to /api/ask only."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
