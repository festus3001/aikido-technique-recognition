"""Validate records against tools/crawler/schema/entities.schema.json.

Uses the entity contract as the single source of truth. Format assertion is
turned on so `date` and `uri` are enforced, not merely annotated. If jsonschema
is not installed, validation degrades to a no-op with a clear warning so the
crawl still runs in a bare environment -- but a real run should validate.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "entities.schema.json"


class ValidationError(Exception):
    pass


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _build_validator(def_name: str):
    """Return a callable(record) -> list[str] of error messages, or None if
    jsonschema is unavailable."""
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError:
        return None

    schema = _load_schema()
    resource = Resource.from_contents(schema)
    registry = resource @ Registry()
    ref_schema = {"$ref": f"{schema['$id']}#/$defs/{def_name}"}
    validator = Draft202012Validator(
        ref_schema,
        registry=registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

    def check(record: dict) -> list[str]:
        return [
            f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(record), key=lambda e: list(e.absolute_path))
        ]

    return check


def validate_store(store, strict: bool = False) -> dict[str, list[str]]:
    """Validate every record in a JsonStore. Returns {record_id: [errors]}.

    With strict=True, raises ValidationError if any record is invalid.
    """
    from .store import COLLECTIONS

    problems: dict[str, list[str]] = {}
    available = True
    for collection, (_filename, def_name) in COLLECTIONS.items():
        check = _build_validator(def_name)
        if check is None:
            available = False
            break
        for record in store.all(collection):
            errors = check(record)
            if errors:
                problems[record["id"]] = errors

    if not available:
        print("WARNING: jsonschema/referencing not installed; skipping validation. "
              "Install them (pip install jsonschema) for a real run.")
        return {}

    if strict and problems:
        summary = "\n".join(f"  {rid}: {'; '.join(errs)}" for rid, errs in problems.items())
        raise ValidationError(f"{len(problems)} invalid record(s):\n{summary}")
    return problems
