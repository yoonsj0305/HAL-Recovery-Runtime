"""Errors for simulation-only pipeline orchestration."""

from __future__ import annotations


class PipelineInputError(ValueError):
    """Raised when pipeline command inputs are missing or ambiguous."""


class PipelineStageError(RuntimeError):
    """Raised when an internal pipeline stage fails safely."""
