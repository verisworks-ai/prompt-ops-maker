# Prompt Ops Maker

Prompt Ops Maker turns reusable agent operating rules into concrete prompts for Fable 5, Claude, Codex, Hermes, MCP, Gemini, and generic AI agents.

It does **not** claim Fable 5-equivalent model performance. It packages the work patterns often needed for long-running AI tasks: effort level, execution boundaries, verification gates, evidence-first reporting, and explicit unverified-item reporting.

## What it produces

```text
input   project config or type preset + task + target AI + runtime
output  a prompt with scope, deny list, verification gates, and report sections
```

## Install

### Local checkout

```bash
python3 -m pip install -e '.[test]'
prompt-ops-maker list-types
```

### Direct script use

```bash
python3 prompt_ops_maker.py list-projects
python3 prompt_ops_maker.py list-types
```

`fable5_prompt_maker.py` remains as a compatibility wrapper.

## Quick start

Generate a project prompt:

```bash
prompt-ops-maker make \
  --project second-salary \
  --mode ad-qa \
  --task "Ad integration QA" \
  --effort high \
  --target-ai codex \
  --environment local \
  --dry-run
```

Generate an ad-hoc prompt without a project config:

```bash
prompt-ops-maker make-adhoc \
  --name "Webhook monitor" \
  --type automation-pipeline \
  --task "Operational audit" \
  --risk "duplicate runs, secret output, failed alerts" \
  --effort high \
  --target-ai hermes \
  --environment mcp \
  --dry-run
```

## Built-in target AI values

```text
fable5   Claude Fable 5-style long-task prompt structure
claude   Claude general use
codex    code implementation, tests, verification
hermes   Hermes Agent skill/tool/gateway environment
mcp      MCP tool/resource/prompt environment
gemini   research, drafts, comparison analysis
generic  generic AI agent
```

## Built-in environments

```text
local    local CLI, files, git, tests
mcp      MCP tools/resources/prompts
discord  Discord reporting
ci       CI/CD logs and artifacts
browser  browser/UI verification
api      API/server verification
generic  generic runtime
```

## Modes

```text
audit    launch/operations audit
fix      approved minimal fixes
deploy   release/upload readiness checks
ad-qa    ads integration QA
seo-geo  search and AI citation readiness
appsec   public/private/security boundary audit
ux       user flow and mobile UX audit
```

## Type presets

```text
generic              generic task
automation-pipeline  scheduler/batch/alert/webhook
web-public           public web service
mobile-miniapp       WebView/miniapp/SDK/ads bundle
```

## Project configs

Add a YAML file under `configs/<project>.yaml`:

```yaml
project:
  name: "Example Service"
  type: "web-public"
  root: "/path/to/public-web-service"
  domain: "https://example.com"
  agent_role: "Example Service audit agent"
  description: "Public web service example."

core_focus:
  - "Public page UX"
  - "robots.txt, sitemap.xml, JSON-LD"

verification_gates:
  - "Run tests"
  - "Check live HTTP status"

forbidden:
  - "Unapproved deploy"
  - "Secret output"
```

Then run:

```bash
prompt-ops-maker make --project example --mode audit --task "Launch audit" --effort high --dry-run
```

## Verification

```bash
python3 -m pytest -q
python3 prompt_ops_maker.py list-projects
python3 prompt_ops_maker.py list-types
python3 prompt_ops_maker.py make --project veris-kr --mode audit --task 'smoke test' --effort high --target-ai codex --environment local --dry-run
```

## Security and privacy boundary

- Do not store API keys, tokens, private keys, customer data, or full `.env` values in configs.
- Use placeholder paths in examples.
- Treat generated prompts as instructions, not proof that the target project was verified.
- Keep deploy, upload, database, and account-setting changes behind explicit approval.

## License

MIT
