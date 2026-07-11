"""Errors for read-only shadow ingestion."""

from __future__ import annotations


class ShadowInputError(ValueError):
    """Raised when a shadow input directory cannot be processed."""


class ShadowValidationError(ValueError):
    """Raised when built shadow artifacts cannot be validated."""
