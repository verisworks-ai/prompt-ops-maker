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
from typing import Any
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


def resolve_chain_order(task_context: dict[str, Any] | None = None) -> list[LayerID]:
    """Return a complexity-calibrated L0-L5 chain.

    Fable-5급 프롬프트 제작 목표는 강한 모델의 고정 사고량을 흉내내는 것이
    아니라, 작은 모델도 태스크 난이도에 맞춰 레이어를 생략·반복하도록 만드는
    것이다. 이 함수는 기본 full chain을 유지하되, 명시적 low effort 작업은
    hypothesis/critique 비용을 줄이고, high/deep 작업은 full chain을 강제한다.
    """
    ctx = task_context or {}
    effort = str(ctx.get("effort", "") or ctx.get("effort_tier", "")).lower()
    mode = str(ctx.get("mode", "")).lower()
    task = str(ctx.get("goal", "") or ctx.get("task", "")).lower()

    high_markers = [
        "deep",
        "audit",
        "appsec",
        "deploy",
        "security",
        "auth",
        "migration",
        "release",
        "긴급",
        "보안",
        "배포",
        "마이그레이션",
    ]
    if effort in {"high", "xhigh"} or mode == "deep-audit" or any(marker in task for marker in high_markers):
        return CHAIN_ORDER

    if effort == "low" and mode not in {"fix", "deploy", "appsec"}:
        return [
            LayerID.L0_SCOPE,
            LayerID.L1_EVIDENCE,
            LayerID.L2_ANALYZE,
            LayerID.L5_REPORT,
        ]

    return CHAIN_ORDER
