"""
prompt-ops-maker MCP Server

Tools:
  - build_layer_prompt : 레이어 프롬프트 생성 (모델 어댑터 적용)
  - validate_output    : 레이어 출력 스키마 검증 (LLM 아닌 코드가 게이트)
  - build_chain_prompts: 전체 L0-L5 체인 프롬프트 배열 반환
  - analyze_prompt     : 기존 프롬프트 ANALYZE_CHECKS 감사

Resources:
  - config://{name}   : YAML 설정 파일
  - schema://{name}   : JSON 스키마 파일

사용:
  python mcp_server/server.py          # stdio (Claude Desktop / Hermes)
  python mcp_server/server.py --http   # HTTP (Gemini / Codex API)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise SystemExit("mcp package not installed. Run: pip install mcp")

from adapters import MODEL_ADAPTERS  # noqa: E402
from core.composer import LayerComposer  # noqa: E402
from core.layers import LayerSpec, LAYER_DIR, CHAIN_ORDER  # noqa: E402
from core.validator import Validator  # noqa: E402

CONFIG_DIR = ROOT / "configs"
SCHEMA_DIR = ROOT / "schemas"
SAFE_RESOURCE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")

mcp = FastMCP("prompt-ops-maker")


def safe_resource_path(base: Path, name: str, suffix: str, *subdirs: str) -> Path | None:
    """Resolve a named resource under base without allowing path traversal."""
    if not SAFE_RESOURCE_NAME.fullmatch(name):
        return None
    candidate = (base.joinpath(*subdirs) / f"{name}{suffix}").resolve()
    allowed_root = base.resolve()
    return candidate if candidate.is_relative_to(allowed_root) else None


# ── Tools ──────────────────────────────────────────────────────────────────

@mcp.tool()
def build_layer_prompt(
    layer_id: str,
    model: str,
    task_context: dict,
    prev_output: str = "",
) -> dict:
    """
    특정 레이어 프롬프트 생성.

    layer_id: L0_scope | L1_evidence | L2_analyze | L3_hypothesize | L4_critique | L5_report
    model: claude | gemini | codex | hermes | generic
    task_context: {goal, config_name?, constraints?, ...}
    prev_output: 이전 레이어의 JSON 출력 (체인 진행 시)
    """
    adapter = MODEL_ADAPTERS.get(model, MODEL_ADAPTERS["generic"])
    composer = LayerComposer(adapter)

    layer_path = LAYER_DIR / f"{layer_id}.yaml"
    if not layer_path.exists():
        return {"error": f"Layer spec not found: {layer_id}"}

    spec = LayerSpec.from_yaml(layer_path)
    prompt = composer.build(spec, task_context, prev_output=prev_output or None)
    return {
        "layer_id": layer_id,
        "model": model,
        "prompt": prompt,
        "output_schema": spec.output_schema,
    }


@mcp.tool()
def validate_output(
    output: str,
    schema_name: str,
    strict: bool = True,
) -> dict:
    """
    레이어 출력 스키마 검증. LLM 아닌 코드가 게이트.

    schema_name: evidence_ledger | findings | hypotheses | critique
    """
    validator = Validator.from_schema_name(schema_name, strict=strict)
    result = validator.validate(output)
    return {
        "valid": result.ok,
        "violations": result.violations,
        "repair_hints": result.hints,
    }


@mcp.tool()
def build_chain_prompts(
    model: str,
    task_context: dict,
) -> dict:
    """
    L0→L5 전체 레이어 체인 프롬프트 배열 반환.

    반환값: {"chain": [{"layer_id": ..., "prompt": ...}, ...]}
    에이전트가 순서대로 실행하고 prev_output을 다음 레이어에 전달.
    """
    adapter = MODEL_ADAPTERS.get(model, MODEL_ADAPTERS["generic"])
    composer = LayerComposer(adapter)

    specs = LayerSpec.load_all()
    chain_specs = [specs[lid] for lid in CHAIN_ORDER if lid in specs]

    chain = []
    for spec in chain_specs:
        prompt = composer.build(spec, task_context)
        chain.append({
            "layer_id": spec.id.value,
            "role": spec.role,
            "prompt": prompt,
            "output_schema": spec.output_schema,
            "allow_retry": spec.allow_retry,
        })

    return {"model": model, "chain": chain, "total_layers": len(chain)}


@mcp.tool()
def analyze_prompt(
    prompt_text: str,
    format: str = "json",
) -> dict:
    """
    기존 프롬프트를 ANALYZE_CHECKS 7항목으로 로컬 감사.
    LLM 호출 없음. 결정론적 휴리스틱.
    """
    from prompt_ops_maker import ANALYZE_CHECKS, _run_checks  # type: ignore
    checks = _run_checks(prompt_text, ANALYZE_CHECKS)
    present = [c for c in checks if c["present"]]
    missing = [c for c in checks if not c["present"]]
    score = round(100 * len(present) / max(len(checks), 1))
    return {
        "score": score,
        "present": len(present),
        "missing": len(missing),
        "items": checks,
        "format": format,
    }


# ── Resources ──────────────────────────────────────────────────────────────

@mcp.resource("config://{name}")
def get_config(name: str) -> str:
    """YAML 설정 파일 반환 (configs/ 기준)."""
    for subdir in ("", "_types", "examples", "layers"):
        p = safe_resource_path(CONFIG_DIR, name, ".yaml", subdir) if subdir else safe_resource_path(CONFIG_DIR, name, ".yaml")
        if p and p.exists():
            return p.read_text()
    return f"Config not found: {name}"


@mcp.resource("schema://{name}")
def get_schema(name: str) -> str:
    """JSON 스키마 파일 반환."""
    p = safe_resource_path(SCHEMA_DIR, name, ".schema.json")
    return p.read_text() if p and p.exists() else f"Schema not found: {name}"


# ── Prompts ────────────────────────────────────────────────────────────────

@mcp.prompt()
def layered_cognition(goal: str, model: str = "claude") -> str:
    """Layered Cognition 체인 실행 안내 프롬프트."""
    return (
        f"## Layered Cognition 실행\n\n"
        f"목표: {goal}\n"
        f"모델: {model}\n\n"
        "실행 순서:\n"
        f"1. `build_chain_prompts(model='{model}', task_context={{goal: ...}})` 호출\n"
        "2. 반환된 chain 배열을 L0 → L5 순서로 순차 실행\n"
        "3. 각 레이어 출력을 `validate_output(schema_name=...)` 으로 검증\n"
        "4. L4 critique의 verdict:\n"
        "   - pass → L5 실행\n"
        "   - re-collect → L1 재실행 (최대 2회)\n"
        "   - revise → L2/L3 재실행\n"
        "5. L5 리포트를 최종 산출물로 반환\n"
    )


if __name__ == "__main__":
    mcp.run()
