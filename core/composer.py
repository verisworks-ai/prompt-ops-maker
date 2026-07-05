"""
LayerComposer — 레이어 스펙 + 모델 어댑터 → 최종 프롬프트 렌더링

사용:
    composer = LayerComposer(adapter=MODEL_ADAPTERS["claude"])
    prompt = composer.build(layer_spec, task_context, prev_output=None)
"""
from __future__ import annotations

import json
from typing import Any

from adapters.base import ModelAdapter
from core.layers import LayerSpec


CRITIQUE_CHECKS = [
    ("execution_boundary", "scope 밖의 행동을 전제한 finding이 있는가?"),
    ("tool_result_grounding", "evidence_id 역추적 시 raw 내용이 claim을 실제로 지지하는가?"),
    ("unverified_reporting", "confidence=low인데 결론에 영향을 주는 finding이 있는가?"),
    ("deny_list", "forbidden 항목을 위반하거나 접근한 흔적이 있는가?"),
    ("verification_gates", "모든 게이트를 통과한 증거가 있는가?"),
    ("evidence_first_report", "결론이 확인한 증거보다 먼저 나오는가?"),
    ("effort_calibration", "effort_tier 대비 과잉/과소 분석인가?"),
]

REPORT_SECTIONS = [
    "결론",
    "확인한 증거",
    "BLOCKER",
    "HIGH",
    "MEDIUM",
    "LOW",
    "미검증 항목",
    "적용 전 필요한 승인",
    "다음 실행안",
]


class LayerComposer:
    def __init__(self, adapter: ModelAdapter):
        self.adapter = adapter

    def build(
        self,
        spec: LayerSpec,
        task_context: dict[str, Any],
        prev_output: str | None = None,
    ) -> str:
        sections: list[str] = []

        # 1. System header
        system = self.adapter.wrap_system(spec.role_directive)
        sections.append(f"<system>\n{system}\n</system>")

        # 2. Task context
        ctx_json = json.dumps(task_context, ensure_ascii=False, indent=2)
        sections.append(f"<context>\n{ctx_json}\n</context>")

        # 3. Previous layer output (chain input)
        if prev_output:
            sections.append(f"<previous_output>\n{prev_output}\n</previous_output>")

        # 4. Hard rules
        if spec.hard_rules:
            rules_text = self.adapter.number_rules(
                self.adapter.truncate_constraints(spec.hard_rules)
            )
            sections.append(f"<hard_rules>\n{rules_text}\n</hard_rules>")

        # 5. L4 critique gets special checklist
        if "critique" in spec.id.value.lower():
            checks = "\n".join(
                f"- [{cid}] {question}" for cid, question in CRITIQUE_CHECKS
            )
            sections.append(f"<audit_checklist>\n{checks}\n</audit_checklist>")
            sections.append(
                "<verdict_rules>\n"
                "- violations 중 evidence 부족 → verdict: re-collect\n"
                "- 논리 결함 → verdict: revise\n"
                "- 이상 없음 → verdict: pass\n"
                "</verdict_rules>"
            )

        # 6. L5 report gets section template
        if "report" in spec.id.value.lower():
            sections_list = "\n".join(f"## {s}" for s in REPORT_SECTIONS)
            sections.append(
                f"<report_template>\n"
                f"Use exactly these sections in order:\n{sections_list}\n"
                f"Evidence-free claims → move to '미검증 항목'.\n"
                f"</report_template>"
            )

        # 7. Output directive
        out_directive = self.adapter.wrap_output_directive(spec.output_schema)
        sections.append(f"<output_directive>\n{out_directive}\n</output_directive>")

        # 8. Repetition for rigid models
        if self.adapter.needs_repetition and spec.hard_rules:
            critical = spec.hard_rules[0] if spec.hard_rules else ""
            sections.append(f"<reminder>CRITICAL: {critical}</reminder>")

        return "\n\n".join(sections)

    def build_chain(
        self,
        specs: list[LayerSpec],
        task_context: dict[str, Any],
    ) -> list[str]:
        """전체 레이어 체인 프롬프트 리스트 반환. 순차 실행용."""
        prompts = []
        prev = None
        for spec in specs:
            p = self.build(spec, task_context, prev_output=prev)
            prompts.append(p)
            prev = f"[Layer {spec.id.value} output pending]"
        return prompts
