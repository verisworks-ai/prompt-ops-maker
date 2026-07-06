"""
Layered Cognition — L0~L5 레이어 데이터 모델

L0 SCOPE      → 실행 경계·deny_list·effort 등급 확정
L1 EVIDENCE   → 원시 증거 수집만 (해석 금지)
L2 ANALYZE    → 증거 → finding (evidence_ids 필수)
L3 HYPOTHESIZE → finding → 가설 + 검증 계획
L4 CRITIQUE   → 7-checks 자기 감사 루프
L5 REPORT     → 최종 보고 (REPORT_SECTIONS 형식)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import yaml

LAYER_DIR = Path(__file__).resolve().parent.parent / "configs" / "layers"


class LayerID(str, Enum):
    L0_SCOPE = "L0_scope"
    L1_EVIDENCE = "L1_evidence"
    L2_ANALYZE = "L2_analyze"
    L3_HYPOTHESIZE = "L3_hypothesize"
    L4_CRITIQUE = "L4_critique"
    L5_REPORT = "L5_report"


@dataclass
class LayerSpec:
    id: LayerID
    role: str
    input_schema: str
    output_schema: str
    role_directive: str
    hard_rules: list[str] = field(default_factory=list)
    output_format: str = "json"
    allow_retry: bool = False

    @classmethod
    def from_yaml(cls, path: Path) -> "LayerSpec":
        raw = yaml.safe_load(path.read_text())
        return cls(
            id=LayerID(raw["id"]),
            role=raw["role"],
            input_schema=raw.get("input_schema", ""),
            output_schema=raw.get("output_schema", ""),
            role_directive=raw["role_directive"],
            hard_rules=raw.get("hard_rules", []),
            output_format=raw.get("output_format", "json"),
            allow_retry=raw.get("allow_retry", False),
        )

    @classmethod
    def load_all(cls) -> dict[LayerID, "LayerSpec"]:
        specs: dict[LayerID, LayerSpec] = {}
        for p in sorted(LAYER_DIR.glob("*.yaml")):
            try:
                s = cls.from_yaml(p)
                specs[s.id] = s
            except Exception:
                pass
        return specs


CHAIN_ORDER: list[LayerID] = [
    LayerID.L0_SCOPE,
    LayerID.L1_EVIDENCE,
    LayerID.L2_ANALYZE,
    LayerID.L3_HYPOTHESIZE,
    LayerID.L4_CRITIQUE,
    LayerID.L5_REPORT,
]
