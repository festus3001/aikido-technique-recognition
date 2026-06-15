"""Idempotent JSON store for techniques and keyframes (merge by id, sorted output).

Re-running ingestion regenerates the same deterministic ids, so upsert-by-id keeps
the output stable. Lives in the taxonomy dir (techniques.json, keyframes.json)."""

from __future__ import annotations

import json
from pathlib import Path


class Store:
    COLLECTIONS = {"techniques": "techniques.json", "keyframes": "keyframes.json"}

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.data: dict[str, dict[str, dict]] = {k: {} for k in self.COLLECTIONS}

    def load(self) -> "Store":
        for name, fn in self.COLLECTIONS.items():
            p = self.root / fn
            if p.exists():
                self.data[name] = {r["id"]: r for r in json.loads(p.read_text(encoding="utf-8"))}
        return self

    def upsert(self, collection: str, record: dict) -> None:
        self.data[collection][record["id"]] = record

    def upsert_many(self, collection: str, records: list[dict]) -> None:
        for r in records:
            self.upsert(collection, r)

    def count(self, collection: str) -> int:
        return len(self.data[collection])

    def all(self, collection: str) -> list[dict]:
        return sorted(self.data[collection].values(), key=lambda r: r["id"])

    def validate(self) -> dict[str, list[str]]:
        """Validate both collections against schema/ingest.schema.json $defs.
        Returns {record_id: [errors]}. Empty if valid or jsonschema absent."""
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            print("WARNING: jsonschema not installed; skipping validation.")
            return {}
        schema_path = Path(__file__).resolve().parents[2] / "schema" / "ingest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        problems: dict[str, list[str]] = {}
        for collection, defname in (("techniques", "technique"), ("keyframes", "keyframe")):
            v = Draft202012Validator({"$ref": f"#/$defs/{defname}", "$defs": schema["$defs"]})
            for rec in self.all(collection):
                errs = [e.message for e in v.iter_errors(rec)]
                if errs:
                    problems[rec["id"]] = errs
        return problems

    def save(self) -> list[Path]:
        self.root.mkdir(parents=True, exist_ok=True)
        written = []
        for name, fn in self.COLLECTIONS.items():
            p = self.root / fn
            p.write_text(json.dumps(self.all(name), ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
            written.append(p)
        return written
