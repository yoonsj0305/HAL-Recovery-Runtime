"""Errors raised by candidate review gate operations."""

from __future__ import annotations


class ReviewError(ValueError):
    """Raised when candidate review input cannot be processed safely."""
