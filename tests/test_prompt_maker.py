import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "prompt_ops_maker.py"
WRAPPER_CLI = ROOT / "fable5_prompt_maker.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def run_wrapper_cli(*args):
    return subprocess.run(
        [sys.executable, str(WRAPPER_CLI), *args],
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


def test_backward_compatible_fable5_wrapper_lists_types():
    result = run_wrapper_cli("list-types")

    assert result.returncode == 0, result.stderr
    assert "automation-pipeline" in result.stdout
    assert "web-public" in result.stdout


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
