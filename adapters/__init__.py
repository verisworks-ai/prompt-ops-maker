from .base import ModelAdapter

MODEL_ADAPTERS: dict[str, ModelAdapter] = {
    # Claude: 강함, 위임형. XML 태그 활용.
    "claude": ModelAdapter(
        name="claude",
        instruction_style="delegative",
        needs_step_numbering=False,
        needs_output_fence=False,
        needs_repetition=False,
        max_constraints=12,
        system_header="You are an expert analyst. Achieve the goal using sound judgment.",
    ),
    # Gemini: 강하지만 포맷 이탈 경향 → JSON fence 강제.
    "gemini": ModelAdapter(
        name="gemini",
        instruction_style="delegative",
        needs_step_numbering=False,
        needs_output_fence=True,
        needs_repetition=False,
        max_constraints=10,
        system_header="Follow the output schema exactly. Use judgment on approach.",
        output_suffix="Respond ONLY with the JSON object inside a ```json fence.",
    ),
    # Codex: 코드 특화, 단계 명시 효과적.
    "codex": ModelAdapter(
        name="codex",
        instruction_style="explicit",
        needs_step_numbering=True,
        needs_output_fence=True,
        needs_repetition=False,
        max_constraints=7,
        system_header="Follow the numbered steps in order. Do not skip steps.",
        output_suffix="Output the JSON object only. No explanation.",
    ),
    # Hermes: tool-call 스타일, 제약 명시적 반복.
    "hermes": ModelAdapter(
        name="hermes",
        instruction_style="rigid",
        needs_step_numbering=True,
        needs_output_fence=True,
        needs_repetition=True,
        max_constraints=6,
        system_header="You are a task executor. Follow every constraint. No improvisation.",
        output_suffix="IMPORTANT: Respond with JSON only. No text outside the JSON block.",
    ),
    # Generic fallback
    "generic": ModelAdapter(
        name="generic",
        instruction_style="explicit",
        needs_step_numbering=True,
        needs_output_fence=True,
        needs_repetition=False,
        max_constraints=8,
        system_header="Follow the instructions carefully.",
    ),
}

__all__ = ["ModelAdapter", "MODEL_ADAPTERS"]
