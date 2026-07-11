"""Read supported local shadow input files without recursion or device access."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .shadow_models import ShadowRawRow, ShadowReadResult
from .shadow_schema import MAX_SHADOW_INPUT_BYTES, SUPPORTED_SHADOW_FILES
from .shadow_validator import unsafe_shadow_fields


def read_shadow_directory(input_directory: str | Path) -> ShadowReadResult:
    root = Path(input_directory)
    if not root.is_dir():
        return ShadowReadResult(
            rows=(),
            files_discovered=(),
            files_supported=(),
            invalid_reasons=("input_path_must_be_directory",),
            events=(
                {
                    "event_type": "shadow_input_invalid",
                    "status": "invalid",
                    "reason": "input_path_must_be_directory",
                },
            ),
        )

    rows: list[ShadowRawRow] = []
    discovered: list[str] = []
    supported: list[str] = []
    ignored: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []
    invalid: list[str] = []
    violations: list[str] = []
    events: list[dict[str, Any]] = [
        {"event_type": "shadow_ingestion_started", "status": "ok"}
    ]
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if not path.is_file():
            continue
        discovered.append(path.name)
        if path.name not in SUPPORTED_SHADOW_FILES:
            ignored.append(path.name)
            reason = f"unknown_file_ignored:{path.name}"
            warnings.append(reason)
            events.append(
                {
                    "event_type": "shadow_file_ignored",
                    "status": "warning",
                    "file_name": path.name,
                    "reason": reason,
                }
            )
            continue
        supported.append(path.name)
        events.append(
            {
                "event_type": "shadow_file_discovered",
                "status": "ok",
                "file_name": path.name,
            }
        )
        if path.stat().st_size > MAX_SHADOW_INPUT_BYTES:
            skipped.append(path.name)
            reason = f"shadow_input_too_large:{path.name}"
            warnings.append(reason)
            events.append(
                {
                    "event_type": "shadow_file_skipped",
                    "status": "warning",
                    "file_name": path.name,
                    "reason": reason,
                }
            )
            continue
        try:
            file_rows = _read_supported_file(path)
        except ValueError as exc:
            skipped.append(path.name)
            reason = f"invalid_input_format:{path.name}:{exc}"
            invalid.append(reason)
            events.append(
                {
                    "event_type": "shadow_input_invalid",
                    "status": "invalid",
                    "reason": reason,
                }
            )
            continue
        file_violations = _safety_violations(file_rows)
        if file_violations:
            violations.extend(file_violations)
            for reason in file_violations:
                events.append(
                    {
                        "event_type": "shadow_safety_boundary_violation",
                        "status": "blocked",
                        "reason": reason,
                    }
                )
            continue
        rows.extend(file_rows)
        events.append(
            {
                "event_type": "shadow_file_parsed",
                "status": "ok",
                "file_name": path.name,
            }
        )

    return ShadowReadResult(
        rows=tuple(rows),
        files_discovered=tuple(discovered),
        files_supported=tuple(supported),
        files_ignored=tuple(ignored),
        files_skipped=tuple(skipped),
        warning_reasons=tuple(dict.fromkeys(warnings)),
        invalid_reasons=tuple(dict.fromkeys(invalid)),
        safety_boundary_violations=tuple(dict.fromkeys(violations)),
        events=tuple(events),
    )


def _read_supported_file(path: Path) -> list[ShadowRawRow]:
    if path.suffix == ".csv":
        return _read_csv(path)
    if path.suffix == ".json":
        return _read_json(path)
    if path.suffix == ".jsonl":
        return _read_jsonl(path)
    return []


def _read_csv(path: Path) -> list[ShadowRawRow]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("csv_header_missing")
            return [
                ShadowRawRow(path.name, index, dict(row))
                for index, row in enumerate(reader, start=1)
            ]
    except (csv.Error, OSError) as exc:
        raise ValueError("csv_parse_failed") from exc


def _read_json(path: Path) -> list[ShadowRawRow]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("json_parse_failed") from exc
    if isinstance(payload, dict):
        for key in ("observations", "rows", "data"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("json_root_must_be_object_or_list")
    rows: list[ShadowRawRow] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError("json_rows_must_be_objects")
        rows.append(ShadowRawRow(path.name, index, dict(item)))
    return rows


def _read_jsonl(path: Path) -> list[ShadowRawRow]:
    rows: list[ShadowRawRow] = []
    try:
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("jsonl_rows_must_be_objects")
            rows.append(ShadowRawRow(path.name, index, dict(payload)))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("jsonl_parse_failed") from exc
    return rows


def _safety_violations(rows: list[ShadowRawRow]) -> list[str]:
    violations: list[str] = []
    for row in rows:
        for field in unsafe_shadow_fields(row.values):
            violations.append(f"{field}_true")
    return list(dict.fromkeys(violations))
