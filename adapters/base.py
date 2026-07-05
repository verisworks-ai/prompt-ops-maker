"""
ModelAdapter — 모델별 프롬프트 포맷 어댑터

원칙: 약한 모델 = 명시적 단계 + 포맷 강제
      강한 모델 = 목표 위임 + 자율성 부여
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


InstructionStyle = Literal["delegative", "explicit", "rigid"]


@dataclass
class ModelAdapter:
    name: str
    instruction_style: InstructionStyle
    needs_step_numbering: bool
    needs_output_fence: bool
    needs_repetition: bool
    max_constraints: int
    system_header: str = ""
    output_suffix: str = ""

    def wrap_system(self, content: str) -> str:
        parts = []
        if self.system_header:
            parts.append(self.system_header)
        parts.append(content)
        return "\n\n".join(parts)

    def wrap_output_directive(self, schema_hint: str) -> str:
        if self.needs_output_fence:
            return f"Respond ONLY with valid JSON inside a ```json fence.\nSchema: {schema_hint}\n{self.output_suffix}"
        return f"Output: {schema_hint}. {self.output_suffix}".strip()

    def number_rules(self, rules: list[str]) -> str:
        if self.needs_step_numbering:
            return "\n".join(f"{i+1}. {r}" for i, r in enumerate(rules))
        return "\n".join(f"- {r}" for r in rules)

    def truncate_constraints(self, constraints: list[str]) -> list[str]:
        return constraints[: self.max_constraints]
