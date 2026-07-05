"""
JSON 스키마 검증 — 레이어 출력이 계약을 지키는지 코드가 게이트

LLM이 아닌 코드가 검증. violation 시 repair_hints 반환.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


@dataclass
class ValidationResult:
    ok: bool
    violations: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)


class Validator:
    def __init__(self, schema: dict[str, Any], strict: bool = True):
        self.schema = schema
        self.strict = strict

    def validate(self, raw_output: str) -> ValidationResult:
        violations: list[str] = []
        hints: list[str] = []

        # JSON 파싱
        data = self._parse_json(raw_output)
        if data is None:
            return ValidationResult(
                ok=False,
                violations=["output_not_json: Could not parse JSON from output"],
                hints=["Ensure output is valid JSON. Remove any prose outside the JSON block."],
            )

        required = self.schema.get("required", [])
        props = self.schema.get("properties", {})

        for key in required:
            if key not in data:
                violations.append(f"missing_required_field: '{key}'")
                hints.append(f"Add '{key}' field to output.")

        # evidence_ids 특수 검사 (findings 스키마)
        if "findings" in data:
            for i, finding in enumerate(data.get("findings", [])):
                if not finding.get("evidence_ids"):
                    violations.append(f"finding[{i}]_missing_evidence_ids")
                    hints.append(
                        f"finding[{i}]: Add at least one evidence_id or remove this finding."
                    )

        # confidence 유효 값 검사
        valid_confidence = {"high", "medium", "low"}
        for i, finding in enumerate(data.get("findings", [])):
            conf = finding.get("confidence", "")
            if conf and conf not in valid_confidence:
                violations.append(f"finding[{i}]_invalid_confidence: '{conf}'")
                hints.append(f"finding[{i}].confidence must be one of: high, medium, low")

        ok = len(violations) == 0
        return ValidationResult(ok=ok, violations=violations, hints=hints)

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        # ```json ... ``` fence 제거
        fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if fence:
            text = fence.group(1)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return None

    @classmethod
    def from_schema_name(cls, name: str, strict: bool = True) -> "Validator":
        path = SCHEMA_DIR / f"{name}.schema.json"
        schema = json.loads(path.read_text()) if path.exists() else {}
        return cls(schema, strict=strict)
