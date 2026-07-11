"""Review report module kept for public review-gate structure."""

from __future__ import annotations

from typing import Any


def report_status_passed(report: dict[str, Any]) -> bool:
    return report.get("candidate_review_passed") is True
