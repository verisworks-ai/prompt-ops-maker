import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "prompt_ops_maker.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def test_mobile_miniapp_ad_qa_dry_run_includes_platform_guards():
    result = run_cli(
        "make",
        "--project",
        "mobile-miniapp",
        "--mode",
        "ad-qa",
        "--task",
        "광고 연동 QA",
        "--effort",
        "high",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "DRY RUN" in out
    assert "WebView miniapp" in out
    assert "Mobile Miniapp" in out
    assert "full-screen ad" in out
    assert "load/show" in out
    assert "legacy" in out or "GoogleAdMob" in out
    assert "bundle reader" in out
    assert "파일 수정" in out
    assert "승인" in out
    assert "## 확인한 증거" in out
    assert "## 미검증 항목" in out


def test_public_real_estate_audit_dry_run_includes_public_web_gates():
    result = run_cli(
        "make",
        "--project",
        "public-real-estate-service",
        "--mode",
        "audit",
        "--task",
        "공개 페이지 SEO/GEO 감사",
        "--effort",
        "high",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "DRY RUN" in out
    assert "Public Real Estate Service" in out
    assert "robots.txt" in out
    assert "sitemap.xml" in out
    assert "JSON-LD" in out
    assert "no-cookie" in out
    assert "source" in out
    assert "custom domain" in out


def test_output_file_is_written_when_requested(tmp_path):
    output = tmp_path / "prompt.md"
    result = run_cli(
        "make",
        "--project",
        "mobile-miniapp",
        "--mode",
        "audit",
        "--task",
        "출시 QA",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "Mobile Miniapp" in text
    assert "## 다음 실행안" in text
    assert str(output) in result.stdout


def test_list_projects_shows_seed_configs():
    result = run_cli("list-projects")

    assert result.returncode == 0, result.stderr
    assert "mobile-miniapp" in result.stdout
    assert "public-real-estate-service" in result.stdout


def test_list_types_shows_generic_presets():
    result = run_cli("list-types")

    assert result.returncode == 0, result.stderr
    assert "web-public" in result.stdout
    assert "automation-pipeline" in result.stdout
    assert "generic" in result.stdout


def test_adhoc_prompt_supports_codex_and_mcp_environment():
    result = run_cli(
        "make-adhoc",
        "--name",
        "새 자동화",
        "--type",
        "automation-pipeline",
        "--task",
        "운영 점검",
        "--target-ai",
        "codex",
        "--environment",
        "mcp",
        "--risk",
        "중복 실행, secret 출력, 알림 실패",
        "--effort",
        "high",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "DRY RUN" in out
    assert "새 자동화" in out
    assert "Codex" in out
    assert "MCP" in out
    assert "중복 실행" in out
    assert "secret 출력" in out
    assert "도구 호출 결과" in out
    assert "## 미검증 항목" in out


def test_automation_pipeline_prompt_includes_content_dedup_guards():
    result = run_cli(
        "make-adhoc",
        "--name",
        "todayfinder",
        "--type",
        "automation-pipeline",
        "--task",
        "포스팅 파이프라인에서 동일한 내용을 계속 올리는 문제",
        "--mode",
        "fix",
        "--target-ai",
        "codex",
        "--environment",
        "local",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "콘텐츠 fingerprint" in out
    assert "최근 게시 이력" in out
    assert "동일 제목" in out
    assert "동일 본문" in out
    assert "skip" in out
    assert "live 발행하지 않는다" in out


def test_project_prompt_can_target_claude_and_discord_environment():
    result = run_cli(
        "make",
        "--project",
        "public-real-estate-service",
        "--mode",
        "appsec",
        "--task",
        "공개 보안 점검",
        "--target-ai",
        "claude",
        "--environment",
        "discord",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "Claude" in out
    assert "Discord" in out
    assert "내부 추론" in out
    assert "메시지는 짧게" in out


def test_brand_hub_prompt_includes_public_boundaries():
    result = run_cli(
        "make",
        "--project",
        "brand-hub",
        "--mode",
        "seo-geo",
        "--task",
        "공개 브랜드 허브 SEO/GEO 감사",
        "--target-ai",
        "codex",
        "--environment",
        "local",
        "--effort",
        "high",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "Brand Hub" in out
    assert "brand hub" in out
    assert "https://example.com" in out
    assert "/path/to/brand-site" in out
    assert "llms.txt" in out
    assert "hosting project: brand-site-production" in out
    assert "reusable prompt-operation patterns" in out


def test_analyze_prompt_reports_missing_boundaries_without_secret_echo(tmp_path):
    prompt = tmp_path / "existing_prompt.txt"
    prompt.write_text(
        "You are a coding agent. Add the feature. API_KEY=sk-redacted-value",
        encoding="utf-8",
    )

    result = run_cli("analyze", "--input", str(prompt), "--format", "json")

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "sk-redacted-value" not in out
    data = json.loads(out)
    assert data["summary"]["source_policy"] == "deterministic-local-heuristics-no-ai-no-secret-echo"
    assert data["summary"]["secret_like_patterns"] == ["api_key_assignment"]
    missing_ids = {item["id"] for item in data["missing"]}
    assert "secret_literal_risk" in missing_ids
    assert "verification_gates" in missing_ids
    assert data["score"] < 100


def test_analyze_prompt_text_output_can_be_written(tmp_path):
    prompt = tmp_path / "safe_prompt.txt"
    output = tmp_path / "analysis.md"
    prompt.write_text(
        "결론 먼저 보고해. 승인 없는 배포 금지. 검증은 pytest와 build 결과로 확인. 미검증 항목을 분리.",
        encoding="utf-8",
    )

    result = run_cli("analyze", "--input", str(prompt), "--output", str(output))

    assert result.returncode == 0, result.stderr
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "Prompt Ops Analysis" in text
    assert "Secret-like patterns: 0 detected" in text
    assert "Verification gates: present" in text
    assert str(output) in result.stdout


def test_verify_fails_below_threshold_with_independent_report(tmp_path):
    prompt = tmp_path / "weak_prompt.txt"
    prompt.write_text("Fix it quickly.", encoding="utf-8")

    result = run_cli("verify", "--input", str(prompt), "--threshold", "90", "--format", "json")

    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["verifier_model"] == "deterministic-local-verifier"
    assert data["passed"] is False
    assert data["analysis"]["score"] < 90


def test_make_adhoc_loop_appends_loop_report():
    result = run_cli(
        "make-adhoc",
        "--name",
        "불멍 UI",
        "--type",
        "web-public",
        "--task",
        "탭하면 메뉴가 같이 번쩍이는 문제 개선",
        "--loop",
        "--threshold",
        "100",
        "--max-iterations",
        "2",
        "--no-lessons",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "Prompt Ops Loop Report" in out
    assert "final_score: 100" in out
    assert "passed: true" in out


def test_fable5_default_prompt_includes_variable_chain_context_and_external_validation():
    result = run_cli(
        "make-adhoc",
        "--name",
        "서비스 출시 점검",
        "--type",
        "web-public",
        "--task",
        "로그인 권한과 SSL 포함 출시 전 점검",
        "--effort",
        "high",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "작업 체인 제어" in out
    assert "L1/L2/L3는 L4 verdict" in out
    assert "컨텍스트 관리 프로토콜" in out
    assert "STATE CHECKPOINT" in out
    assert "외부 검증 훅" in out
    assert "프롬프트 키워드 린트" in out
    assert "prompt_ops_maker.py verify" in out
    assert "실행 산출물의 성공을 보증하지 않는다" in out
    assert "자기 감사" in out
    assert "검증되지 않은 내부 추론" in out


def test_verify_outputs_deterministic_external_verdict_for_failed_prompt(tmp_path):
    prompt = tmp_path / "weak_prompt.txt"
    prompt.write_text("Fix it quickly.", encoding="utf-8")

    result = run_cli("verify", "--input", str(prompt), "--threshold", "90", "--format", "json")

    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["external_verdict"]["verdict_source"] == "prompt-keyword-lint"
    assert data["external_verdict"]["scope"] == "prompt_text_only_no_runtime_execution_evidence"
    assert data["external_verdict"]["verdict"] == "re-collect"
    assert "verification_gates" in data["external_verdict"]["missing"]


def test_verify_outputs_pass_external_verdict_for_generated_prompt(tmp_path):
    prompt = tmp_path / "generated_prompt.md"
    make_result = run_cli(
        "make-adhoc",
        "--name",
        "서비스 출시 점검",
        "--type",
        "web-public",
        "--task",
        "로그인 권한과 SSL 포함 출시 전 점검",
        "--effort",
        "high",
        "--no-lessons",
        "--output",
        str(prompt),
    )
    assert make_result.returncode == 0, make_result.stderr

    verify_result = run_cli("verify", "--input", str(prompt), "--threshold", "90", "--format", "json")

    assert verify_result.returncode == 0, verify_result.stderr
    data = json.loads(verify_result.stdout)
    assert data["external_verdict"]["verdict"] == "pass"
    assert data["external_verdict"]["missing"] == []


def test_resolve_chain_order_skips_middle_layers_for_low_effort_readonly_tasks():
    from core.layers import LayerID, resolve_chain_order

    chain = resolve_chain_order({"effort": "low", "mode": "ux", "goal": "버튼 문구 확인"})

    assert chain == [
        LayerID.L0_SCOPE,
        LayerID.L1_EVIDENCE,
        LayerID.L2_ANALYZE,
        LayerID.L5_REPORT,
    ]


def test_resolve_chain_order_keeps_full_chain_for_security_release_tasks():
    from core.layers import CHAIN_ORDER, resolve_chain_order

    chain = resolve_chain_order({"effort": "medium", "mode": "audit", "goal": "auth security release check"})

    assert chain == CHAIN_ORDER


def test_mcp_chain_prompt_uses_resolved_chain_order():
    pytest.importorskip("mcp")
    from mcp_server.server import build_chain_prompts

    result = build_chain_prompts(
        model="generic",
        task_context={"effort": "low", "mode": "ux", "goal": "문구 확인"},
    )

    layer_ids = [item["layer_id"] for item in result["chain"]]
    assert layer_ids == ["L0_scope", "L1_evidence", "L2_analyze", "L5_report"]


def test_mcp_resources_reject_path_traversal():
    pytest.importorskip("mcp")
    from mcp_server.server import get_config, get_schema

    assert "Config not found" in get_config("../pyproject")
    assert "Config not found" in get_config("examples/brand-hub")
    assert "Schema not found" in get_schema("../pyproject")
    assert "project:" in get_config("brand-hub")
    assert '"type"' in get_schema("findings")
