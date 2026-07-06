#!/usr/bin/env python3
"""Universal prompt maker for Fable 5 and other AI runtimes.

Generates prompts from project configs or ad-hoc type presets with explicit effort,
boundaries, verification gates, target-AI guidance, and environment notes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "configs"
EXAMPLE_CONFIG_DIR = CONFIG_DIR / "examples"
TYPE_DIR = CONFIG_DIR / "_types"
OUTPUT_DIR = ROOT / "outputs"
DEFAULT_LESSONS_PATH = Path.cwd() / ".prompt-ops" / "lessons.md"

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

ANALYZE_CHECKS = [
    {
        "id": "execution_boundary",
        "label": "Execution boundary",
        "severity": "BLOCKER",
        "needles": ["승인", "approval", "do not", "하지 말", "수정", "배포", "upload", "deploy"],
        "recommendation": "State what the agent must not change before explicit approval: files, DB, deploy, uploads, accounts, and paid APIs.",
    },
    {
        "id": "deny_list",
        "label": "Deny list",
        "severity": "HIGH",
        "needles": ["금지", "deny", "forbidden", "must not", "secret", "개인정보", "환경변수"],
        "recommendation": "Add a short deny list for secret output, unrelated edits, destructive commands, private routes, and credential values.",
    },
    {
        "id": "verification_gates",
        "label": "Verification gates",
        "severity": "HIGH",
        "needles": ["검증", "test", "pytest", "build", "smoke", "curl", "evidence", "확인"],
        "recommendation": "List the exact evidence required before completion: tests, build, file diff, HTTP smoke, logs, or MCP tool output.",
    },
    {
        "id": "unverified_reporting",
        "label": "Unverified item reporting",
        "severity": "MEDIUM",
        "needles": ["미검증", "unverified", "unknown", "not verified", "assumption", "가정"],
        "recommendation": "Require unverified items and assumptions to be reported separately from completed work.",
    },
    {
        "id": "evidence_first_report",
        "label": "Evidence-first report format",
        "severity": "MEDIUM",
        "needles": ["결론", "확인한 증거", "evidence", "result", "BLOCKER", "HIGH", "LOW"],
        "recommendation": "Define a result-first report shape with conclusion, evidence, blockers, risks, and next actions.",
    },
    {
        "id": "tool_result_grounding",
        "label": "Tool-result grounding",
        "severity": "MEDIUM",
        "needles": ["도구", "tool", "command output", "명령", "파일", "source", "log"],
        "recommendation": "Require claims to be grounded in files, command output, logs, URL responses, screenshots, or tool results.",
    },
    {
        "id": "assumption_surfacing",
        "label": "Assumption surfacing",
        "severity": "MEDIUM",
        "needles": ["assumption", "assume", "가정", "presuppose", "전제", "surface assumption", "가정을 명시"],
        "recommendation": "Require the AI to state its assumptions before executing. Use --deep-reasoning to inject the full assumption scaffold.",
    },
    {
        "id": "adversarial_check",
        "label": "Adversarial / failure-mode check",
        "severity": "MEDIUM",
        "needles": ["failure mode", "what would this miss", "adversarial", "edge case", "abuse", "counter", "red team", "실패 시나리오", "놓친 것"],
        "recommendation": "Require failure-mode and adversarial analysis, not just the happy path. Use --deep-reasoning or mode=deep-audit.",
    },
    {
        "id": "confidence_calibration",
        "label": "Confidence calibration",
        "severity": "LOW",
        "needles": ["confidence", "verified", "inferred", "unknown", "calibrat", "확신", "미확인", "불확실"],
        "recommendation": "Require per-finding confidence levels (HIGH/MEDIUM/LOW) and an explicit UNKNOWN section. Use --deep-reasoning.",
    },
]

SEVERITY_PENALTY = {"BLOCKER": 30, "HIGH": 18, "MEDIUM": 10, "LOW": 5}

MODE_PURPOSES = {
    "audit": "현재 상태를 평가하고 출시·운영 리스크를 우선순위별로 정리해줘.",
    "fix": "승인된 항목만 최소 변경으로 수정하고 실제 검증 결과까지 확인해줘.",
    "deploy": "승인된 변경사항만 배포 또는 업로드 준비 상태까지 검증해줘.",
    "ad-qa": "광고 연동 상태를 대상 플랫폼 기준으로 평가하고 실제 앱/서비스 환경 검증 필요 항목을 분리해줘.",
    "seo-geo": "검색 노출, AI 인용, 구조화 데이터, discovery asset 상태를 평가해줘.",
    "appsec": "공개/비공개 경계, API 응답, secret 노출, 인증 흐름을 평가해줘.",
    "ux": "사용자 흐름과 CTA, 화면 깨짐, 결과/재시작 루프를 평가해줘.",
    "deep-audit": "가정 명시 → 증거 체인 → 실행 → 적대적 패스 → 신뢰도 보정 순서로 전체 리스크를 심층 평가해줘.",
}

MODE_DEFAULT_DENY = {
    "audit": ["파일 수정", "DB 변경", "배포", "업로드", "환경변수 값 출력"],
    "ad-qa": ["파일 수정", "콘솔 변경", "live 광고 ID 반복 테스트", "secret 출력"],
    "seo-geo": ["파일 수정", "배포", "환경변수 값 출력", "private route 노출"],
    "appsec": ["파일 수정", "배포", "secret 출력", "개인정보 출력"],
    "ux": ["파일 수정", "배포", "업로드"],
    "fix": ["unrelated file 수정", "승인 없는 배포", "승인 없는 DB 변경", "secret 출력"],
    "deploy": ["unrelated dirty file 포함", "secret 출력", "승인 범위 밖 배포"],
    "deep-audit": ["파일 수정", "DB 변경", "배포", "업로드", "환경변수 값 출력", "가정을 사실로 보고"],
}

MODE_VERB = {
    "audit": "아직 수정하지 말고 평가만 해.",
    "ad-qa": "수정하지 말고 광고 연동 상태만 평가해.",
    "seo-geo": "아직 수정하지 말고 검색·AI 노출 상태만 평가해.",
    "appsec": "아직 수정하지 말고 보안 경계만 평가해.",
    "ux": "아직 수정하지 말고 UX만 평가해.",
    "fix": "이제 수정 단계로 전환한다. 단, 아래 승인된 항목만 수정해.",
    "deploy": "배포/업로드 단계로 전환한다. 승인된 변경사항만 반영해.",
    "deep-audit": "수정하지 않는다. 아래 REASONING SCAFFOLD를 단계별로 이행하면서 심층 평가만 해.",
}

TARGET_AI_GUIDANCE = {
    "fable5": {
        "label": "Claude Fable 5",
        "items": [
            "RESEARCH → PLAN → EXECUTE → VERIFY → REPORT 순서로 진행하고 단계를 건너뛰지 마.",
            "실행 전 가정 3개를 명시해. 형식: ASSUMPTION: <내용> | BASIS: <근거> | RISK IF WRONG: <영향>. 검증 가능하면 먼저 검증해.",
            "모든 주장에 증거 체인을 붙여. 형식: CLAIM → SOURCE(파일:줄번호 또는 명령 출력) → CONFIDENCE(HIGH/MEDIUM/LOW). SOURCE 없으면 HYPOTHESIS로 표시해.",
            "결론을 내기 전에 적대적 패스를 실행해. '이 분석이 놓친 것은 무엇인가? 어떤 입력이나 환경이 이 결론을 깨뜨리는가?' 를 구체적으로 답해.",
            "지식 상태를 3단계로 구분해. VERIFIED(직접 확인), INFERRED(검증된 사실에서 추론), UNKNOWN(확인 불가 항목과 해소 방법).",
            "검증은 단일 패스가 아니다. (a) 요구사항 충족 여부 (b) 인접 기능 영향 (c) 적대적 패스에서 발견한 실패 모드 — 세 단계를 모두 거쳐.",
            "해피패스만 감사하지 마. 각 흐름마다 실패 모드 1개, 엣지 케이스 1개, 오남용 시나리오 1개를 포함해.",
            "확신이 낮으면 모호한 언어로 채우지 말고 불확실성의 원인과 해소 실험을 명시해.",
            "보고서 끝에 캘리브레이션 블록을 추가해. CONFIDENT(>90%), NEEDS_CONFIRMATION(50-90%), OPEN_QUESTION(<50%) 3단계로 분류해. OPEN_QUESTION은 절대 생략하지 마.",
        ],
    },
    "claude": {
        "label": "Claude",
        "items": [
            "긴 맥락을 활용하되 첫 문장에는 결과만 써.",
            "내부 추론은 쓰지 말고 확인한 출력 중심으로 보고해.",
            "수정·삭제·배포는 명시 승인 후 진행해.",
        ],
    },
    "codex": {
        "label": "Codex",
        "items": [
            "코드 변경 전 관련 파일과 테스트 seam을 확인해.",
            "최소 변경으로 구현하고 실제 명령 출력으로 검증해.",
            "파일 수정, 테스트, 빌드 결과를 분리해서 보고해.",
        ],
    },
    "hermes": {
        "label": "Hermes Agent",
        "items": [
            "관련 skill을 먼저 로드하고 skill 지침을 우선 적용해.",
            "도구 호출 결과를 근거로 보고하고 추정 성공을 금지해.",
            "gateway, cron, plugin, profile 변경은 승인 범위를 분리해.",
        ],
    },
    "mcp": {
        "label": "MCP Agent",
        "items": [
            "사용 가능한 MCP tool/resource/prompt를 먼저 열거해.",
            "MCP 도구 호출 결과와 로컬 파일/명령 결과를 구분해.",
            "권한·비용·외부 API 부작용이 있으면 실행 전 승인 항목으로 분리해.",
        ],
    },
    "gemini": {
        "label": "Gemini",
        "items": [
            "빠른 초안과 비교 분석은 간결하게 처리해.",
            "최신 정보·리서치 결과는 출처와 확인 시각을 분리해.",
            "코드 수정이 필요하면 구현 담당 agent에게 넘길 변경 요구사항으로 정리해.",
        ],
    },
    "generic": {
        "label": "Generic AI Agent",
        "items": [
            "결론 먼저, 근거는 실제 출력 중심으로 보고해.",
            "평가와 실행을 분리하고 승인 없는 상태 변경을 금지해.",
            "확인하지 못한 항목은 미검증으로 표시해.",
        ],
    },
}

ENVIRONMENT_GUIDANCE = {
    "local": {
        "label": "Local CLI",
        "items": [
            "로컬 파일, git diff, 테스트, 빌드 출력을 우선 증거로 사용해.",
            "환경변수 값은 출력하지 말고 존재 여부와 비어 있음 여부만 표시해.",
        ],
    },
    "discord": {
        "label": "Discord",
        "items": [
            "메시지는 짧게 나누고 긴 표 대신 코드블록/카드형 목록을 사용해.",
            "첨부 파일이 필요하면 파일 경로와 생성 여부를 별도 보고해.",
        ],
    },
    "mcp": {
        "label": "MCP",
        "items": [
            "도구 호출 결과, resource 내용, prompt 출력의 출처를 각각 표시해.",
            "도구 권한이 없으면 대체 경로와 필요한 추가 권한을 제시해.",
        ],
    },
    "ci": {
        "label": "CI/CD",
        "items": [
            "CI 로그, artifact, exit code를 핵심 증거로 사용해.",
            "재시도 전 flaky 가능성과 실제 실패 원인을 분리해.",
        ],
    },
    "browser": {
        "label": "Browser/UI",
        "items": [
            "렌더링, 콘솔 오류, 네트워크 응답, 스크린샷을 분리해 확인해.",
            "source 확인만으로 visible UI 완료를 주장하지 마.",
        ],
    },
    "api": {
        "label": "API/Server",
        "items": [
            "요청, 응답 코드, 응답 body marker, 로그를 분리해.",
            "인증·rate limit·외부 API 비용이 있으면 승인 항목으로 표시해.",
        ],
    },
    "generic": {
        "label": "Generic Runtime",
        "items": [
            "실제 실행 가능한 확인 경로를 먼저 찾고, 불가한 항목은 미검증으로 표시해.",
        ],
    },
}


FABLE5_REASONING_SCAFFOLD = """\
## REASONING SCAFFOLD (필수 — 순서대로 이행)

### Phase 0 — 가정 명시 (분석·실행 전에 완료)
이 작업에 대한 가정 3개를 아래 형식으로 작성해. 검증 가능한 가정은 진행 전에 검증해.
- ASSUMPTION: <한 문장>
- BASIS: <근거 — 증거 또는 관례>
- RISK IF WRONG: <틀렸을 때 분석에 미치는 영향>
- VERIFIABLE NOW?: yes → 먼저 검증 / no → 플래그 리스크로 보유

### Phase 1 — 증거 체인 (모든 발견 항목에 적용)
결론만 보고하지 마. 각 발견 항목은 아래 구조를 따라:
- CLAIM: <발견 내용, 한 문장>
- SOURCE: <파일:줄번호, 명령 + 출력, 또는 설정 키 — 직접 확인 가능한 것>
- REASONING: <SOURCE가 CLAIM을 지지하는 이유, 1-2 문장>
- CONFIDENCE: HIGH(직접 검증) | MEDIUM(검증된 사실에서 추론) | LOW(그럴 듯하나 미검증)
SOURCE가 없는 발견 항목은 "HYPOTHESIS"로 표시하고 Open Questions로 이동해.

### Phase 2 — 적대적 패스 (분석 완료 후 실행)
자신의 분석에 질문해: "내가 놓친 것은 무엇인가?" 구체적으로 답해:
1. 검토하지 않은 입력, 설정, 환경은 무엇인가?
2. HIGH 확신 발견 항목 중 SOURCE가 가장 약한 것은? 재검토해.
3. 내 결론을 틀리게 만들고 싶은 사람이 무엇을 지적할까?
수정 사항이 있으면 새 발견 항목으로 추가해. 기존 항목을 몰래 수정하지 마.

### Phase 3 — 캘리브레이션 보고서 (출력의 마지막 섹션, 필수)
발견 항목별 신뢰도 표:
| 발견 항목 | 확신도 | 확신을 바꿀 조건 |
|-----------|--------|-----------------|

종합:
- VERIFIED: <건수> 발견 항목
- INFERRED: <건수> 발견 항목
- UNKNOWN: <각 항목 + 가장 저렴한 해소 방법>

UNKNOWN 섹션은 절대 생략하지 마. 비어 있으면 분석이 불완전하다는 신호다.
"""


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"invalid config: {path}")
    return data


def project_config(project: str) -> dict[str, Any]:
    """Load a project config from root configs or public example configs."""
    candidates = [CONFIG_DIR / f"{project}.yaml", EXAMPLE_CONFIG_DIR / f"{project}.yaml"]
    for path in candidates:
        if path.exists():
            return load_yaml(path)
    raise SystemExit(f"config not found: {candidates[0]} or {candidates[1]}")


def type_config(project_type: str) -> dict[str, Any]:
    return load_yaml(TYPE_DIR / f"{project_type}.yaml")


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered(items: list[str]) -> str:
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))


def section(title: str, body: str) -> str:
    body = body.strip()
    return f"## {title}\n{body}\n" if body else f"## {title}\n"


def contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def secret_pattern_hits(text: str) -> list[str]:
    """Return secret-like pattern labels without echoing sensitive values."""
    lowered = text.lower()
    hits: list[str] = []
    if any(token in lowered for token in ["api_key=", "apikey=", "api-key:", "api_key:"]):
        hits.append("api_key_assignment")
    if "bearer " in lowered:
        hits.append("bearer_token")
    if "-----begin " in lowered and "private key-----" in lowered:
        hits.append("private_key_block")
    if any(token in lowered for token in ["token=", "secret=", "password=", "client_secret="]):
        hits.append("env_assignment")
    return hits


def analyze_prompt_text(text: str, *, name: str = "prompt") -> dict[str, Any]:
    """Analyze an existing prompt with deterministic public heuristics.

    This intentionally avoids AI calls, private-infra inference, and secret echo.
    """
    normalized = text.strip()
    line_count = 0 if not normalized else len(normalized.splitlines())
    word_count = len(normalized.split())
    checks: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    present: list[str] = []

    for check in ANALYZE_CHECKS:
        found = contains_any(normalized, check["needles"])
        item = {
            "id": check["id"],
            "label": check["label"],
            "severity": check["severity"],
            "present": found,
            "recommendation": check["recommendation"],
        }
        checks.append(item)
        if found:
            present.append(check["id"])
        else:
            missing.append({"id": check["id"], "severity": check["severity"], "recommendation": check["recommendation"]})

    secret_hits = secret_pattern_hits(normalized)
    if secret_hits:
        missing.insert(
            0,
            {
                "id": "secret_literal_risk",
                "severity": "BLOCKER",
                "recommendation": "Remove literal secrets from the prompt source. Keep only key names, presence checks, or redacted placeholders.",
            },
        )

    penalty = sum(SEVERITY_PENALTY.get(item["severity"], 5) for item in missing)
    return {
        "name": name,
        "score": max(0, 100 - penalty),
        "summary": {
            "line_count": line_count,
            "word_count": word_count,
            "present_checks": len(present),
            "missing_checks": len(missing),
            "secret_like_patterns": secret_hits,
            "source_policy": "deterministic-local-heuristics-no-ai-no-secret-echo",
        },
        "checks": checks,
        "missing": missing,
    }


def render_analysis_text(analysis: dict[str, Any]) -> str:
    secret_hits = analysis["summary"]["secret_like_patterns"]
    lines = [
        f"# Prompt Ops Analysis — {analysis['name']}",
        "",
        f"Score: {analysis['score']}/100",
        "",
        "## Summary",
        f"- Lines: {analysis['summary']['line_count']}",
        f"- Words: {analysis['summary']['word_count']}",
        f"- Present checks: {analysis['summary']['present_checks']}",
        f"- Missing checks: {analysis['summary']['missing_checks']}",
        f"- Secret-like patterns: {len(secret_hits)} detected" if secret_hits else "- Secret-like patterns: 0 detected",
        "- Source policy: deterministic local heuristics; no AI call; no secret value echo",
        "",
        "## Missing / Risk Items",
    ]
    if analysis["missing"]:
        for item in analysis["missing"]:
            lines.append(f"- [{item['severity']}] {item['id']}: {item['recommendation']}")
    else:
        lines.append("- None")

    lines.extend(["", "## Checks"])
    for item in analysis["checks"]:
        status = "present" if item["present"] else "missing"
        lines.append(f"- {item['label']}: {status} ({item['severity']})")
    return "\n".join(lines).strip() + "\n"


def mode_focus(config: dict[str, Any], mode: str) -> list[str]:
    focus = []
    focus.extend(config.get("core_focus", []))
    focus.extend(config.get("mode_focus", {}).get(mode, []))
    return focus


def deny_list(config: dict[str, Any], mode: str, extra_risks: list[str] | None = None) -> list[str]:
    out: list[str] = []
    out.extend(MODE_DEFAULT_DENY.get(mode, []))
    out.extend(config.get("forbidden", []))
    for risk in extra_risks or []:
        if "secret" in risk.lower() or "토큰" in risk or "키" in risk:
            out.append(risk)
    return list(dict.fromkeys(out))


def verification_gates(config: dict[str, Any], mode: str) -> list[str]:
    out: list[str] = []
    out.extend(config.get("verification_gates", []))
    out.extend(config.get("mode_verification", {}).get(mode, []))
    return list(dict.fromkeys(out))


def severity_block(config: dict[str, Any]) -> str:
    lines: list[str] = []
    severities = config.get("severity", {})
    for name in ["BLOCKER", "HIGH", "MEDIUM", "LOW"]:
        items = severities.get(name, [])
        if items:
            lines.append(f"{name}:")
            lines.append(bullet(items))
            lines.append("")
    return "\n".join(lines).strip()


def target_ai_block(target_ai: str) -> tuple[str, list[str]]:
    data = TARGET_AI_GUIDANCE.get(target_ai, TARGET_AI_GUIDANCE["generic"])
    return data["label"], data["items"]


def environment_block(environment: str) -> tuple[str, list[str]]:
    data = ENVIRONMENT_GUIDANCE.get(environment, ENVIRONMENT_GUIDANCE["generic"])
    return data["label"], data["items"]


def make_adhoc_config(args: argparse.Namespace) -> dict[str, Any]:
    base = type_config(args.type)
    config = dict(base)
    config["project"] = dict(base.get("project", {}))
    config["project"].update(
        {
            "name": args.name,
            "type": args.type,
            "agent_role": args.role or base.get("project", {}).get("agent_role", f"{args.name} 작업 에이전트"),
            "description": args.description or base.get("project", {}).get("description", "범용 작업"),
        }
    )
    if args.root:
        config["project"]["root"] = args.root
    if args.domain:
        config["project"]["domain"] = args.domain
    risks = split_csv(args.risk)
    if risks:
        config["core_focus"] = list(config.get("core_focus", [])) + [f"사용자가 지정한 리스크: {risk}" for risk in risks]
        config["_extra_risks"] = risks
    return config


def render_prompt(
    config: dict[str, Any],
    *,
    project: str,
    mode: str,
    task: str,
    effort: str,
    target_ai: str = "fable5",
    environment: str = "local",
    deep_reasoning: bool = False,
    include_lessons: bool = True,
) -> str:
    display_name = config["project"]["name"]
    project_type = config["project"].get("type", project)
    domain = config["project"].get("domain")
    root = config["project"].get("root")
    audience = config["project"].get("agent_role", f"{display_name} 프로젝트 QA 에이전트")
    mode_line = MODE_VERB.get(mode, "아직 수정하지 말고 평가만 해.")
    purpose = MODE_PURPOSES.get(mode, "현재 상태를 평가하고 리스크를 정리해줘.")
    focus_items = mode_focus(config, mode)
    gates = verification_gates(config, mode)
    special_rules = config.get("special_rules", [])
    dry_boundaries = deny_list(config, mode, config.get("_extra_risks"))
    live_notes = config.get("environment_notes", [])
    target_label, target_items = target_ai_block(target_ai)
    env_label, env_items = environment_block(environment)

    context_bits = [f"프로젝트명: {display_name}", f"프로젝트 유형: {project_type}"]
    if domain:
        context_bits.append(f"대표 URL/도메인: {domain}")
    if root:
        context_bits.append(f"기본 프로젝트 폴더: {root}")
    if config.get("project", {}).get("description"):
        context_bits.append(f"설명: {config['project']['description']}")

    text = f"""
너는 {audience}다.

이번 작업은 {effort} effort로 진행해.
대상 AI/실행자: {target_label}
실행 환경: {env_label}
{mode_line}

작업명:
{task}

목표:
{purpose}

프로젝트 맥락:
{bullet(context_bits)}
"""

    text += f"\n대상 AI 지침:\n{numbered(target_items)}\n"
    text += f"\n실행 환경 지침:\n{numbered(env_items)}\n"
    if deep_reasoning or mode == "deep-audit":
        text += f"\n{FABLE5_REASONING_SCAFFOLD}\n"
    if focus_items:
        text += f"\n점검 범위:\n{numbered(focus_items)}\n"
    if gates:
        text += f"\n검증 게이트:\n{numbered(gates)}\n"
    if live_notes:
        text += f"\n환경 구분:\n{bullet(live_notes)}\n"
    if dry_boundaries:
        text += f"\n금지:\n{bullet(dry_boundaries)}\n"
    if special_rules:
        text += f"\n특수 규칙:\n{numbered(special_rules)}\n"
    if include_lessons:
        text += lessons_block()

    sev = severity_block(config)
    if sev:
        text += f"\n우선순위 기준:\n{sev}\n"

    text += f"""
진행 방식:
1. 현재 source, 설정, 산출물, 실행 환경을 먼저 확인해.
2. 추정하지 말고 실제 파일, 명령 결과, URL 응답, 빌드/테스트 출력, 도구 호출 결과에 근거해.
3. source, build output, live/custom domain, 앱 실행 환경, MCP/tool 결과를 별도 gate로 구분해.
4. 확인하지 못한 항목은 완료라고 말하지 말고 “미검증”으로 표시해.
5. 수정·배포·업로드·계정 설정 변경이 필요하면 영향 범위와 되돌리는 방법을 먼저 제시해.

보고 형식:
첫 문장은 사용자가 가장 궁금해할 결과 하나만 말해.
내부 추론은 쓰지 말고, 결론 / 확인한 증거 / 미검증 항목만 보고해.

"""
    for report_section in config.get("report_sections", REPORT_SECTIONS):
        if report_section in {"BLOCKER", "HIGH", "MEDIUM", "LOW"}:
            text += section(report_section, "각 항목마다 문제 / 근거 / 영향 / 수정 방향 / 검증 방법을 적어.")
        elif report_section == "다음 실행안":
            text += section(report_section, "내가 바로 선택할 수 있게 3개 안으로 제안해.")
        else:
            text += section(report_section, "")

    return textwrap.dedent(text).strip() + "\n"


def write_or_print(prompt: str, *, dry_run: bool, output: str | None, label: str) -> int:
    if dry_run:
        print(f"# DRY RUN — {label}\n")
        print(prompt)
        return 0
    if output:
        out = Path(output).expanduser()
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_label = "".join(ch if ch.isalnum() else "-" for ch in label).strip("-")[:80] or "prompt"
        out = OUTPUT_DIR / f"{stamp}-{safe_label}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(prompt, encoding="utf-8")
    print(f"written: {out}")
    return 0


def list_projects() -> int:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    EXAMPLE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in CONFIG_DIR.glob("*.yaml") if path.is_file())
    files.extend(sorted(path for path in EXAMPLE_CONFIG_DIR.glob("*.yaml") if path.is_file()))
    if not files:
        print("no project configs")
        return 1
    for path in files:
        data = load_yaml(path)
        prefix = "examples/" if path.parent == EXAMPLE_CONFIG_DIR else ""
        print(f"{prefix}{path.stem}\t{data.get('project', {}).get('name', path.stem)}")
    return 0


def list_types() -> int:
    TYPE_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(TYPE_DIR.glob("*.yaml"))
    if not files:
        print("no type presets")
        return 1
    for path in files:
        data = load_yaml(path)
        print(f"{path.stem}\t{data.get('project', {}).get('name', path.stem)}")
    return 0


def format_analysis(analysis: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"
    if output_format == "yaml":
        return yaml.safe_dump(analysis, allow_unicode=True, sort_keys=False)
    return render_analysis_text(analysis)


def read_lessons(path: Path = DEFAULT_LESSONS_PATH) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def append_lesson(text: str, path: Path = DEFAULT_LESSONS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Prompt Ops Lessons\n\n"
    path.write_text(existing.rstrip() + f"\n\n## {stamp}\n{text.strip()}\n", encoding="utf-8")


def lessons_block(path: Path = DEFAULT_LESSONS_PATH) -> str:
    lessons = read_lessons(path)
    if not lessons:
        return ""
    lines = [line for line in lessons.splitlines() if line.strip()]
    tail = "\n".join(lines[-20:])
    return f"\n축적된 lessons/state:\n{tail}\n"


def improve_prompt_from_analysis(prompt: str, analysis: dict[str, Any]) -> str:
    if not analysis["missing"]:
        return prompt
    additions = [
        "## Prompt Ops Auto-Improvement",
        "아래 항목은 독립 verifier가 발견한 누락 게이트다. 실행자는 본문 지침과 함께 반드시 적용해.",
        "",
    ]
    for item in analysis["missing"]:
        additions.append(f"- [{item['severity']}] {item['id']}: {item['recommendation']}")
    additions.extend(
        [
            "",
            "완료 전 위 항목을 다시 점검하고, 충족하지 못한 항목은 미검증/차단 사유로 보고해.",
        ]
    )
    return prompt.rstrip() + "\n\n" + "\n".join(additions).strip() + "\n"


def loop_until_threshold(
    prompt: str,
    *,
    threshold: int,
    max_iterations: int,
    name: str,
    record_lessons: bool,
) -> tuple[str, dict[str, Any]]:
    history: list[dict[str, Any]] = []
    current = prompt
    iterations = max(1, max_iterations)
    for index in range(1, iterations + 1):
        analysis = analyze_prompt_text(current, name=f"{name} iteration {index}")
        history.append({"iteration": index, "score": analysis["score"], "missing": [item["id"] for item in analysis["missing"]]})
        if analysis["score"] >= threshold:
            break
        current = improve_prompt_from_analysis(current, analysis)

    final = analyze_prompt_text(current, name=f"{name} final")
    report = {
        "threshold": threshold,
        "max_iterations": iterations,
        "final_score": final["score"],
        "passed": final["score"] >= threshold,
        "history": history,
        "final_missing": [item["id"] for item in final["missing"]],
    }
    if record_lessons and not report["passed"]:
        append_lesson(
            f"Loop for {name} stopped at {final['score']}/100. Remaining: {', '.join(report['final_missing']) or 'none'}"
        )
    return current, report


def analyze(args: argparse.Namespace) -> int:
    if args.input == "-":
        source = sys.stdin.read()
        name = args.name or "stdin"
    else:
        path = Path(args.input).expanduser()
        if not path.exists():
            raise SystemExit(f"prompt file not found: {path}")
        source = path.read_text(encoding="utf-8")
        name = args.name or path.name

    analysis = analyze_prompt_text(source, name=name)
    rendered = format_analysis(analysis, args.format)
    if args.output:
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        print(f"written: {out}")
    else:
        print(rendered, end="")
    return 0


def _apply_post_generation(prompt: str, args: argparse.Namespace, config: dict[str, Any], label: str) -> int:
    if args.loop:
        prompt, report = loop_until_threshold(
            prompt,
            threshold=args.threshold,
            max_iterations=args.max_iterations,
            name=label,
            record_lessons=not args.no_lessons,
        )
        prompt += "\n## Prompt Ops Loop Report\n" + yaml.safe_dump(report, allow_unicode=True, sort_keys=False)
    if getattr(args, "self_verify", False):
        prompt += self_verify_block(threshold=args.threshold, max_iterations=min(args.max_iterations, 2))
    if getattr(args, "promptspec", False):
        gates = config.get("verification_gates", [])
        spec_text = render_promptspec(prompt, task=args.task, target_ai=args.target_ai, effort=args.effort, gates=gates if isinstance(gates, list) else [])
        out_path = args.output.replace(".md", ".promptspec.yaml") if args.output else None
        return write_or_print(spec_text, dry_run=args.dry_run, output=out_path, label=label + " [promptspec]")
    return write_or_print(prompt, dry_run=args.dry_run, output=args.output, label=label)


def make(args: argparse.Namespace) -> int:
    config = project_config(args.project)
    prompt = render_prompt(
        config,
        project=args.project,
        mode=args.mode,
        task=args.task,
        effort=args.effort,
        target_ai=args.target_ai,
        environment=args.environment,
        deep_reasoning=getattr(args, "deep_reasoning", False),
        include_lessons=not getattr(args, "no_lessons", False),
    )
    return _apply_post_generation(prompt, args, config, f"{args.project} / {args.mode} / {args.effort} / {args.target_ai} / {args.environment}")


def make_adhoc(args: argparse.Namespace) -> int:
    config = make_adhoc_config(args)
    prompt = render_prompt(
        config,
        project=args.name,
        mode=args.mode,
        task=args.task,
        effort=args.effort,
        target_ai=args.target_ai,
        environment=args.environment,
        deep_reasoning=getattr(args, "deep_reasoning", False),
        include_lessons=not getattr(args, "no_lessons", False),
    )
    return _apply_post_generation(prompt, args, config, f"adhoc / {args.type} / {args.mode} / {args.effort} / {args.target_ai} / {args.environment}")


_LLM_MODEL_ALIASES: dict[str, str] = {
    # Claude (Anthropic /v1/messages)
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "fable5": "claude-fable-5",
    "opus": "claude-opus-4-8",
    # GPT (OpenAI /v1/chat/completions)
    "gpt-mini": "gpt-5.4-mini",
    "gpt": "gpt-5.4",
    "gpt5": "gpt-5.5",
    "codex": "gpt-5.3-codex-spark",
    # Gemini (OpenAI /v1/chat/completions)
    "gemini": "gemini-3-flash",
    "gemini-pro": "gemini-3.1-pro-low",
}

# Models that use OpenAI-compatible /v1/chat/completions endpoint
_OPENAI_COMPAT_PREFIXES = ("gpt-", "gemini-", "codex-")

_LLM_VERIFIER_SYSTEM = """You are an independent prompt-ops verifier. Your only job is to score a prompt against 9 criteria and return structured JSON. You have no context from the prompt's author."""

_LLM_VERIFIER_USER_TMPL = """Score this prompt against each criterion. Return ONLY valid JSON — no explanation, no markdown.

PROMPT TO EVALUATE:
---
{prompt}
---

Criteria (answer true/false for each):
1. execution_boundary — Does it state what the agent must NOT change without approval (files, DB, deploy, uploads)?
2. deny_list — Does it have an explicit deny list (secrets, destructive commands, private routes)?
3. verification_gates — Does it list exact evidence required before completion (tests, files, URLs, logs)?
4. unverified_reporting — Does it require unverified items to be reported separately?
5. evidence_first_report — Does it define a result-first report with conclusion + evidence + blockers?
6. tool_result_grounding — Does it require claims grounded in files/command output/logs/URLs?
7. assumption_surfacing — Does it require stating assumptions before executing?
8. adversarial_check — Does it require failure-mode or adversarial analysis?
9. confidence_calibration — Does it require per-finding confidence levels (HIGH/MEDIUM/LOW)?

JSON format:
{{"checks":{{"execution_boundary":true,"deny_list":true,"verification_gates":true,"unverified_reporting":true,"evidence_first_report":true,"tool_result_grounding":true,"assumption_surfacing":true,"adversarial_check":true,"confidence_calibration":true}},"reasoning":"one sentence each, semicolon-separated"}}"""


def llm_verify_prompt(
    prompt_text: str,
    model_alias: str,
    *,
    proxy_base: str = "http://localhost:8317",
    timeout: int = 60,
) -> dict[str, Any]:
    """Call LLM independently to verify prompt. Routes Claude→/v1/messages, GPT/Gemini→/v1/chat/completions."""
    import requests  # lazy import — only needed for LLM verify path

    model_id = _LLM_MODEL_ALIASES.get(model_alias, model_alias)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "proxy-passthrough")
    use_openai_compat = model_id.startswith(_OPENAI_COMPAT_PREFIXES)

    if use_openai_compat:
        url = f"{proxy_base}/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        payload: dict[str, Any] = {
            "model": model_id,
            "max_tokens": 600,
            "messages": [
                {"role": "system", "content": _LLM_VERIFIER_SYSTEM},
                {"role": "user", "content": _LLM_VERIFIER_USER_TMPL.format(prompt=prompt_text[:8000])},
            ],
        }
    else:
        url = f"{proxy_base}/v1/messages"
        headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01", "x-api-key": api_key}
        payload = {
            "model": model_id,
            "max_tokens": 600,
            "system": _LLM_VERIFIER_SYSTEM,
            "messages": [{"role": "user", "content": _LLM_VERIFIER_USER_TMPL.format(prompt=prompt_text[:8000])}],
        }

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    raw = resp.json()

    if use_openai_compat:
        text = raw.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    else:
        text = next((b["text"] for b in raw.get("content", []) if b.get("type") == "text"), "{}")

    # parse — strip markdown fences if present
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        raise SystemExit(f"LLM verifier returned unparseable JSON:\n{text[:400]}")

    checks_raw: dict[str, bool] = parsed.get("checks", {})
    SEVERITY_MAP = {
        "execution_boundary": "BLOCKER", "deny_list": "HIGH", "verification_gates": "HIGH",
        "unverified_reporting": "MEDIUM", "evidence_first_report": "MEDIUM", "tool_result_grounding": "MEDIUM",
        "assumption_surfacing": "MEDIUM", "adversarial_check": "MEDIUM", "confidence_calibration": "LOW",
    }
    checks = []
    missing = []
    present = []
    for cid, severity in SEVERITY_MAP.items():
        found = bool(checks_raw.get(cid, False))
        checks.append({"id": cid, "severity": severity, "present": found})
        if found:
            present.append(cid)
        else:
            missing.append({"id": cid, "severity": severity})

    penalty = sum(SEVERITY_PENALTY.get(item["severity"], 5) for item in missing)
    return {
        "name": "llm-verifier",
        "score": max(0, 100 - penalty),
        "summary": {
            "present_checks": len(present),
            "missing_checks": len(missing),
            "secret_like_patterns": [],
            "source_policy": f"llm-independent-verifier:{model_id}",
            "reasoning": parsed.get("reasoning", ""),
        },
        "checks": checks,
        "missing": missing,
    }


def verify(args: argparse.Namespace) -> int:
    if args.input == "-":
        source = sys.stdin.read()
        name = args.name or "stdin"
    else:
        path = Path(args.input).expanduser()
        if not path.exists():
            raise SystemExit(f"prompt file not found: {path}")
        source = path.read_text(encoding="utf-8")
        name = args.name or path.name

    use_llm = args.verifier_model not in ("deterministic-local-verifier", "local", "")
    if use_llm:
        analysis = llm_verify_prompt(source, args.verifier_model)
    else:
        analysis = analyze_prompt_text(source, name=name)
    payload = {
        "verifier_model": args.verifier_model,
        "threshold": args.threshold,
        "passed": analysis["score"] >= args.threshold,
        "analysis": analysis,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    if args.output:
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        print(f"written: {out}")
    else:
        print(rendered, end="")
    if args.record_lessons and not payload["passed"]:
        missing = ", ".join(item["id"] for item in analysis["missing"]) or "none"
        append_lesson(f"Verify failed for {name}: {analysis['score']}/100 below {args.threshold}. Missing: {missing}")
    return 0 if payload["passed"] else 1


def self_verify_block(threshold: int = 90, max_iterations: int = 2) -> str:
    return f"""
## Self-Verification Protocol (Fable 5 — 완료 전 필수 실행)

이 블록은 외부 verifier 없이 네가 직접 출력을 검증하는 rubric이다.
완료를 선언하기 전에 아래 루프를 실행해. 최대 {max_iterations}회 재시도.

### Rubric (9항목 — 각 true/false로 자기 채점)
1. execution_boundary — 승인 없이 변경 금지 항목(파일/DB/배포/업로드)이 명시됐는가?
2. deny_list — 금지 행동 목록(비밀값/파괴적 명령/private route)이 있는가?
3. verification_gates — 완료 증거(테스트/파일/URL/로그)가 구체적으로 열거됐는가?
4. unverified_reporting — 미검증 항목이 완료와 분리돼 보고됐는가?
5. evidence_first_report — 결론 → 증거 → BLOCKER/HIGH 순서로 보고됐는가?
6. tool_result_grounding — 모든 주장에 파일:줄번호 또는 명령 출력이 근거로 붙었는가?
7. assumption_surfacing — 실행 전 가정 3개가 명시됐는가?
8. adversarial_check — 실패 모드 1개, 엣지 케이스 1개가 포함됐는가?
9. confidence_calibration — CONFIDENT/NEEDS_CONFIRMATION/OPEN_QUESTION 블록이 있는가?

### 판정
- 9/9 true → 완료 선언 가능
- false 항목 있음 → 해당 섹션 보완 후 재채점 (최대 {max_iterations}회)
- {max_iterations}회 후에도 false 남으면 → UNVERIFIED 항목으로 명시하고 완료 선언

### 재시도 조건
false 항목 발견 시 해당 섹션만 보완 (전체 재생성 금지).
"""


def render_promptspec(
    prompt: str,
    *,
    task: str,
    target_ai: str,
    effort: str,
    gates: list[str],
) -> str:
    spec = {
        "version": "1.0",
        "target_ai": target_ai,
        "effort": effort,
        "task": task,
        "system": prompt,
        "sub_agents": [
            {"role": "verifier", "model": "haiku", "trigger": "after each major step", "rubric": "prompt-ops 9-check"},
        ],
        "verification_gates": gates or ["task output exists", "no unverified items remain"],
        "checkpoint_schedule": {
            "interval": "after each EXECUTE phase",
            "artifact": ".prompt-ops/checkpoint.json",
            "resume_from_last": True,
        },
        "self_verify": {"enabled": True, "max_iterations": 2, "threshold": 90},
    }
    return yaml.safe_dump(spec, allow_unicode=True, sort_keys=False, default_flow_style=False)


def add_common_generation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mode", default="audit", choices=sorted(MODE_PURPOSES.keys()))
    parser.add_argument("--task", required=True)
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh"])
    parser.add_argument("--target-ai", default="fable5", choices=sorted(TARGET_AI_GUIDANCE.keys()))
    parser.add_argument("--environment", default="local", choices=sorted(ENVIRONMENT_GUIDANCE.keys()))
    parser.add_argument(
        "--deep-reasoning",
        action="store_true",
        dest="deep_reasoning",
        help="Inject the Fable 5 reasoning scaffold (assumption surfacing, evidence chains, adversarial pass, confidence calibration). Auto-enabled for --mode=deep-audit.",
    )
    parser.add_argument("--dry-run", action="store_true", help="print without writing")
    parser.add_argument("--output", help="write prompt to a specific file")
    parser.add_argument("--loop", action="store_true", help="run analyze/improve iterations until --threshold is reached")
    parser.add_argument("--threshold", type=int, default=90, help="minimum score for --loop or verify gates")
    parser.add_argument("--max-iterations", type=int, default=3, help="maximum auto-improvement iterations for --loop")
    parser.add_argument("--no-lessons", action="store_true", help="do not inject or write .prompt-ops/lessons.md")
    parser.add_argument("--self-verify", action="store_true", dest="self_verify", help="append Fable 5 self-verification rubric block to generated prompt")
    parser.add_argument("--promptspec", action="store_true", help="output .promptspec YAML (system+sub_agents+gates+checkpoints) instead of markdown")


def run_agentic(args: argparse.Namespace) -> int:
    """Run a generated prompt against LLM with eval cases and report pass rate."""
    import requests

    prompt_path = Path(args.prompt).expanduser()
    if not prompt_path.exists():
        raise SystemExit(f"prompt file not found: {prompt_path}")
    prompt_text = prompt_path.read_text(encoding="utf-8")

    evals_path = Path(args.evals).expanduser()
    if not evals_path.exists():
        raise SystemExit(f"evals file not found: {evals_path}")
    cases: list[dict[str, Any]] = yaml.safe_load(evals_path.read_text(encoding="utf-8")) or []

    model_id = _LLM_MODEL_ALIASES.get(args.model, args.model)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "proxy-passthrough")
    proxy_base = args.proxy or "http://localhost:8317"
    use_oai = model_id.startswith(_OPENAI_COMPAT_PREFIXES)

    results = []
    for i, case in enumerate(cases):
        user_input: str = case.get("input", "")
        expect: str = case.get("expect", "")
        label: str = case.get("label", f"case-{i+1}")

        if use_oai:
            url = f"{proxy_base}/v1/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            payload: dict[str, Any] = {"model": model_id, "max_tokens": 800, "messages": [
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": user_input},
            ]}
        else:
            url = f"{proxy_base}/v1/messages"
            headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01", "x-api-key": api_key}
            payload = {"model": model_id, "max_tokens": 800, "system": prompt_text,
                       "messages": [{"role": "user", "content": user_input}]}

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            raw = resp.json()
            if use_oai:
                output = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                output = next((b["text"] for b in raw.get("content", []) if b.get("type") == "text"), "")
            passed = expect.lower() in output.lower() if expect else True
            results.append({"label": label, "passed": passed, "expect": expect, "got": output[:120]})
        except Exception as e:
            results.append({"label": label, "passed": False, "expect": expect, "got": f"ERROR: {e}"})

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)
    pass_rate = round(passed_count / total * 100) if total else 0
    overall_pass = pass_rate >= args.threshold

    report = {"model": model_id, "pass_rate": pass_rate, "passed": overall_pass,
              "threshold": args.threshold, "cases": results}

    if args.record_lessons and not overall_pass:
        failed = [r["label"] for r in results if not r["passed"]]
        append_lesson(f"run --agentic failed: {pass_rate}% < {args.threshold}%. Failed cases: {', '.join(failed)}")

    if args.failures_out:
        fpath = Path(args.failures_out).expanduser()
        fpath.parent.mkdir(parents=True, exist_ok=True)
        failed_cases = [c for c, r in zip(cases, results) if not r["passed"]]
        fpath.write_text(json.dumps(failed_cases, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"failures written: {fpath}")

    print(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), end="")
    return 0 if overall_pass else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate universal AI prompts for Fable 5, Codex, Claude, Hermes, MCP, and other runtimes")
    sub = parser.add_subparsers(dest="command", required=True)

    make_parser = sub.add_parser("make", help="generate a prompt from a project config")
    make_parser.add_argument("--project", required=True, help="project config name")
    add_common_generation_args(make_parser)
    make_parser.set_defaults(func=make)

    adhoc_parser = sub.add_parser("make-adhoc", help="generate a prompt from a generic type preset without a project config")
    adhoc_parser.add_argument("--name", required=True, help="display project/task name")
    adhoc_parser.add_argument("--type", default="generic", help="type preset name")
    adhoc_parser.add_argument("--root", help="optional project folder")
    adhoc_parser.add_argument("--domain", help="optional URL/domain")
    adhoc_parser.add_argument("--description", help="optional one-line description")
    adhoc_parser.add_argument("--role", help="optional agent role sentence")
    adhoc_parser.add_argument("--risk", help="comma-separated user-specified risks")
    add_common_generation_args(adhoc_parser)
    adhoc_parser.set_defaults(func=make_adhoc)

    list_parser = sub.add_parser("list-projects", help="list available project configs")
    list_parser.set_defaults(func=lambda _args: list_projects())

    type_parser = sub.add_parser("list-types", help="list generic type presets")
    type_parser.set_defaults(func=lambda _args: list_types())

    analyze_parser = sub.add_parser("analyze", help="analyze an existing prompt for missing ops boundaries")
    analyze_parser.add_argument("--input", "-i", required=True, help="prompt file path, or '-' for stdin")
    analyze_parser.add_argument("--name", help="optional display name for the analyzed prompt")
    analyze_parser.add_argument("--format", choices=["text", "json", "yaml"], default="text", help="analysis output format")
    analyze_parser.add_argument("--output", "-o", help="write analysis to a file")
    analyze_parser.set_defaults(func=analyze)

    verify_parser = sub.add_parser("verify", help="independently verify a prompt score and fail below threshold")
    verify_parser.add_argument("--input", "-i", required=True, help="prompt file path, or '-' for stdin")
    verify_parser.add_argument("--name", help="optional display name for the verified prompt")
    verify_parser.add_argument("--format", choices=["json", "yaml"], default="json", help="verification output format")
    verify_parser.add_argument("--output", "-o", help="write verification report to a file")
    verify_parser.add_argument("--threshold", type=int, default=90, help="minimum accepted score")
    verify_parser.add_argument("--verifier-model", default="deterministic-local-verifier", help="label for the independent verifier used in reports")
    verify_parser.add_argument("--record-lessons", action="store_true", help="append failed verification patterns to .prompt-ops/lessons.md")
    verify_parser.set_defaults(func=verify)

    run_parser = sub.add_parser("run", help="run a prompt against LLM with eval cases and report pass rate")
    run_parser.add_argument("--prompt", "-p", required=True, help="generated prompt .md file")
    run_parser.add_argument("--evals", "-e", required=True, help="eval cases YAML (list of {label, input, expect})")
    run_parser.add_argument("--model", default="haiku", help="model alias (haiku/sonnet/fable5/gpt-mini/gemini)")
    run_parser.add_argument("--threshold", type=int, default=80, help="minimum pass rate %% to succeed")
    run_parser.add_argument("--agentic", action="store_true", help="flag: running in agentic mode (enables failures output)")
    run_parser.add_argument("--failures-out", default="feedback/failures.jsonl", help="write failed cases to this file")
    run_parser.add_argument("--record-lessons", action="store_true", help="append failures to .prompt-ops/lessons.md")
    run_parser.add_argument("--proxy", default="http://localhost:8317", help="proxy base URL")
    run_parser.set_defaults(func=run_agentic)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
