<p align="center">
  <img src=".github/assets/prompt-ops-maker-logo.svg" alt="prompt-ops-maker" width="640">
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="#빠른-사용">빠른 사용</a> ·
  <a href="#기존-프롬프트-역분석">기존 프롬프트 역분석</a> ·
  <a href="#보안-경계">보안 경계</a>
</p>

<p align="center">
  <img src=".github/assets/prompt-ops-maker-hero.svg" alt="기존 프롬프트 역분석 흐름" width="960">
</p>

# Prompt Ops Maker

Prompt Ops Maker는 Fable 5, Claude, Codex, Hermes, MCP, Gemini, 범용 AI 에이전트에 재사용할 작업 운영 프롬프트를 생성하고, 기존 프롬프트의 운영 경계 누락을 로컬에서 분석한다.

Fable 5와 동급 성능을 주장하지 않는다. 장기 작업에 필요한 effort, 실행 경계, 검증 게이트, 증거 기반 보고, 미검증 항목 보고 규칙을 템플릿화한다.

## 기존 프롬프트 역분석

```bash
prompt-ops-maker analyze --input existing-prompt.txt --format text
prompt-ops-maker analyze --input existing-prompt.txt --format json --output analysis.json
```

```text
점검 항목
- 실행 경계
- 금지 행동 / deny-list
- 검증 게이트
- 미검증 항목 보고
- evidence-first 보고
- tool 결과 기반 grounding
- secret-like 패턴

보안 경계
- AI 호출 0
- 외부 API 호출 0
- private 인프라 추론 0
- secret 원문 출력 0
```

## 결과물

```text
입력  project config 또는 type preset + task + target AI + runtime
입력  existing prompt file
출력  범위, 금지 행동, 검증 게이트, 보고 형식이 포함된 prompt
출력  기존 prompt의 누락된 운영 경계 분석 결과
```

## 설치

```bash
python3 -m pip install -e '.[test]'
prompt-ops-maker list-types
```

직접 실행도 된다.

```bash
python3 prompt_ops_maker.py list-projects
python3 prompt_ops_maker.py list-types
```

`fable5_prompt_maker.py`는 기존 사용자를 위한 호환 wrapper다.

## 빠른 사용

```bash
prompt-ops-maker make \
  --project mobile-miniapp \
  --mode ad-qa \
  --task "광고 연동 QA" \
  --effort high \
  --target-ai codex \
  --environment local \
  --dry-run
```

프로젝트 설정 없이 생성:

```bash
prompt-ops-maker make-adhoc \
  --name "Webhook monitor" \
  --type automation-pipeline \
  --task "운영 점검" \
  --risk "중복 실행, secret 출력, 알림 실패" \
  --effort high \
  --target-ai hermes \
  --environment mcp \
  --dry-run
```

기존 프롬프트 역분석:

```bash
prompt-ops-maker analyze --input existing-prompt.txt --format text
prompt-ops-maker analyze --input existing-prompt.txt --format json --output analysis.json
```

역분석은 로컬 deterministic 규칙만 사용한다. AI 모델을 호출하지 않고, private 인프라를 추론하지 않고, secret으로 보이는 값은 출력하지 않는다.

## target AI

```text
fable5   Claude Fable 5 장기작업용 구조
claude   Claude 일반 사용
codex    코드 구현·테스트·검증 중심
hermes   Hermes Agent skill/tool/gateway 환경
mcp      MCP tool/resource/prompt 환경
gemini   리서치·초안·비교 분석 중심
generic  범용 AI 에이전트
```

## environment

```text
local    로컬 CLI, 파일, git, 테스트
mcp      MCP tools/resources/prompts
discord  Discord 보고
ci       CI/CD 로그와 artifact
browser  브라우저/UI 검증
api      API/server 검증
generic  범용 실행 환경
```

## 검증

```bash
python3 -m pytest -q
python3 prompt_ops_maker.py list-projects
python3 prompt_ops_maker.py list-types
python3 prompt_ops_maker.py make --project brand-hub --mode audit --task 'smoke test' --effort high --target-ai codex --environment local --dry-run
python3 prompt_ops_maker.py analyze --input README.md --format json
```

## 보안 경계

- configs에 API key, token, private key, 고객 데이터, `.env` 값을 넣지 않는다.
- 예제에는 placeholder path를 쓴다.
- 생성된 prompt는 지시문이다. 대상 프로젝트 검증 완료 증거가 아니다.
- deploy, upload, DB, 계정 설정 변경은 명시 승인 뒤에만 진행한다.

## 라이선스

MIT
