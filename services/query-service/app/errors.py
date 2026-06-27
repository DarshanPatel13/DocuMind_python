"""Domain exceptions, mapped to HTTP responses in app/main.py."""
from __future__ import annotations


class ConversationNotFoundError(Exception):
    """No conversation history for the given id -> 404."""
