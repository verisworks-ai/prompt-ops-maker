#!/usr/bin/env python3
"""Universal prompt maker for Fable 5 and other AI runtimes.

Generates prompts from project configs or ad-hoc type presets with explicit effort,
boundaries, verification gates, target-AI guidance, and environment notes.
"""
from __future__ import annotations

import argparse
import datetime as dt
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

MODE_PURPOSES = {
    "audit": "현재 상태를 평가하고 출시·운영 리스크를 우선순위별로 정리해줘.",
    "fix": "승인된 항목만 최소 변경으로 수정하고 실제 검증 결과까지 확인해줘.",
    "deploy": "승인된 변경사항만 배포 또는 업로드 준비 상태까지 검증해줘.",
    "ad-qa": "광고 연동 상태를 대상 플랫폼 기준으로 평가하고 실제 앱/서비스 환경 검증 필요 항목을 분리해줘.",
    "seo-geo": "검색 노출, AI 인용, 구조화 데이터, discovery asset 상태를 평가해줘.",
    "appsec": "공개/비공개 경계, API 응답, secret 노출, 인증 흐름을 평가해줘.",
    "ux": "사용자 흐름과 CTA, 화면 깨짐, 결과/재시작 루프를 평가해줘.",
}

MODE_DEFAULT_DENY = {
    "audit": ["파일 수정", "DB 변경", "배포", "업로드", "환경변수 값 출력"],
    "ad-qa": ["파일 수정", "콘솔 변경", "live 광고 ID 반복 테스트", "secret 출력"],
    "seo-geo": ["파일 수정", "배포", "환경변수 값 출력", "private route 노출"],
    "appsec": ["파일 수정", "배포", "secret 출력", "개인정보 출력"],
    "ux": ["파일 수정", "배포", "업로드"],
    "fix": ["unrelated file 수정", "승인 없는 배포", "승인 없는 DB 변경", "secret 출력"],
    "deploy": ["unrelated dirty file 포함", "secret 출력", "승인 범위 밖 배포"],
}

MODE_VERB = {
    "audit": "아직 수정하지 말고 평가만 해.",
    "ad-qa": "수정하지 말고 광고 연동 상태만 평가해.",
    "seo-geo": "아직 수정하지 말고 검색·AI 노출 상태만 평가해.",
    "appsec": "아직 수정하지 말고 보안 경계만 평가해.",
    "ux": "아직 수정하지 말고 UX만 평가해.",
    "fix": "이제 수정 단계로 전환한다. 단, 아래 승인된 항목만 수정해.",
    "deploy": "배포/업로드 단계로 전환한다. 승인된 변경사항만 반영해.",
}

TARGET_AI_GUIDANCE = {
    "fable5": {
        "label": "Claude Fable 5",
        "items": [
            "장기 목표를 끝까지 추적하되 평가와 실행 경계를 지켜.",
            "내부 추론은 공개하지 말고 결론, 증거, 미검증 항목만 보고해.",
            "중간 보고 전에는 이번 세션의 도구 결과와 주장 일치 여부를 확인해.",
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
    )
    return write_or_print(prompt, dry_run=args.dry_run, output=args.output, label=f"{args.project} / {args.mode} / {args.effort} / {args.target_ai} / {args.environment}")


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
    )
    return write_or_print(prompt, dry_run=args.dry_run, output=args.output, label=f"adhoc / {args.type} / {args.mode} / {args.effort} / {args.target_ai} / {args.environment}")


def add_common_generation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mode", default="audit", choices=sorted(MODE_PURPOSES.keys()))
    parser.add_argument("--task", required=True)
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh"])
    parser.add_argument("--target-ai", default="fable5", choices=sorted(TARGET_AI_GUIDANCE.keys()))
    parser.add_argument("--environment", default="local", choices=sorted(ENVIRONMENT_GUIDANCE.keys()))
    parser.add_argument("--dry-run", action="store_true", help="print without writing")
    parser.add_argument("--output", help="write prompt to a specific file")


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
