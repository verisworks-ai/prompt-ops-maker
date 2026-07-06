<p align="center">
  <img src=".github/assets/prompt-ops-maker-logo.svg" alt="prompt-ops-maker" width="640">
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="#빠른-사용">빠른 사용</a> ·
  <a href="#fable-5-정렬-기능">Fable 5 기능</a> ·
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

## Fable 5 정렬 기능

세 가지 추가 기능이 구조화된 프롬프트와 모델 전반에서 일관된 동작을 강제하는 프롬프트 사이의 갭을 좁힌다.

### `--self-verify` — 9항목 자기검증 루브릭

생성된 프롬프트에 구조화된 자기 점검 블록을 추가한다. 모델은 완료를 선언하기 전에 9개 항목으로 스스로 점수를 매긴다.

```bash
prompt-ops-maker make-adhoc \
  --name "Webhook monitor" \
  --type automation-pipeline \
  --task "운영 점검" \
  --target-ai fable5 \
  --self-verify \
  --threshold 90 \
  --max-iterations 2 \
  --dry-run
```

루브릭 항목: 실행 경계, 금지 행동, 검증 게이트, 미검증 항목 보고, evidence-first 보고, tool 결과 grounding, 가정 명시, 적대적 점검, 신뢰도 캘리브레이션.

루브릭 실패 시 `--max-iterations`까지 재시도 후 보고. Fable 5는 실제로 결과물을 수정한다. 소형 모델은 ✓ 도장만 찍는 경향이 있다.

### `--promptspec` — YAML 미션 스펙

프롬프트와 함께 구조화된 YAML 스펙을 출력한다. 오케스트레이터, codex-hermes, MCP 도구에 구조적 컨텍스트를 전달할 때 유용하다.

```bash
prompt-ops-maker make-adhoc \
  --name "SEO 감사" \
  --type web-public \
  --task "런치 준비 점검" \
  --target-ai fable5 \
  --promptspec \
  --dry-run
```

스펙 필드: `version`, `target_ai`, `sub_agents`, `verification_gates`, `checkpoint_schedule`, `self_verify`.

### `run --agentic` — eval 기반 검증 루프

생성된 프롬프트를 eval 케이스에 실행하고 통과율을 측정한다. 실패 케이스는 `feedback/failures.jsonl`에 기록되고 교훈은 `.prompt-ops/lessons.md`에 추가된다.

```bash
# evals/cases.yaml 예시:
# - label: "실행경계 포함 확인"
#   input: "이 프롬프트에 실행 경계가 있나요?"
#   expect: "승인"
# - label: "deny list 확인"
#   input: "금지 행동 목록이 있나요?"
#   expect: "금지"

prompt-ops-maker run \
  --prompt outputs/my-prompt.md \
  --evals evals/cases.yaml \
  --model haiku \
  --threshold 80 \
  --agentic \
  --record-lessons
```

통과율 ≥ threshold이면 exit 0, 아니면 exit 1. CI에서 프롬프트 품질 게이트로 사용 가능.

### 크로스 모델 검증

Claude, GPT, Gemini 중 어느 모델이든 독립 검증에 사용할 수 있다.

```bash
prompt-ops-maker verify --input my-prompt.md --verifier-model haiku
prompt-ops-maker verify --input my-prompt.md --verifier-model gpt-mini
prompt-ops-maker verify --input my-prompt.md --verifier-model gemini

# 사용 가능 별칭: haiku, sonnet, fable5, opus, gpt-mini, gpt, gpt5, codex, gemini, gemini-pro
```

Claude 모델은 `/v1/messages`, GPT/Gemini는 `/v1/chat/completions`로 `localhost:8317` 프록시 경유 라우팅.

### Fable 5 vs 소형 모델 — 갭 표

프롬프트 구조는 모델에 무관하다. 차이는 구조를 얼마나 엄격하게 따르느냐다.

```text
구조               Fable 5                            Haiku / Sonnet / GPT-mini
──────────────────────────────────────────────────────────────────────────────────
실행 경계          의미적으로 이해. 범위 밖 작업 명시    규칙 목록 중 하나로 취급.
                   거부/보고.                           장 컨텍스트에서 범위 이탈.

검증 게이트        실제 체크포인트. FAIL → 진단 → 재시도  고무도장: 점검 없이 "PASS" 선언.
                                                        재시도 루프 없음.

9항목 self-verify  항목별 실제 대조. 오류 발견 → 재시도.  전 항목 all-pass 편향.
                                                        후반 항목 검증 품질 저하.

promptspec YAML    중첩 제약·필드 간 상호작용까지 반영.   상위 2-3 필드만 반영.
                                                        깊은 필드 무시. 스키마 드리프트.

run --agentic      멀티스텝 상태 유지. 에러 → 원인 분석   동일 액션 무한 재시도.
                   → 다른 접근.                         5스텝 이후 계획 망각. 조기 완료 선언.

오류 복구          FAIL → 원인 분석 → 새 전략.           같은 실패 액션 재시도. 복구 전략 없음.
```

구조는 모델 무관이다. 실행 품질은 모델 추론 깊이에 비례한다.

## v2: Layered Cognition

v2는 규칙을 어기는 것이 구조적으로 불가능한 6단계 레이어 체인을 도입한다.

```text
레이어  이름          역할
──────────────────────────────────────────────────────────────────────────
L0     Scope         작업 경계와 금지 행동 — 에이전트가 범위 밖으로 나갈 수 없음
L1     Evidence      모든 발견에 evidence_ids 필수 — 증거 없는 주장 불가
L2     Analyze       수집된 증거만 기반으로 구조적 분석
L3     Hypothesize   L1 증거에 연결된 순위별 가설
L4     Critique      L3 가설을 공개 전 적대적으로 검토
L5     Report        결론 먼저: 결론 → 증거 → BLOCKER/HIGH → 미검증 항목
```

evidence_ids는 스키마 수준에서 필수다. `evidence_ids`가 없는 finding은 직렬화 자체가 불가 — 게이트가 지시문이 아니라 코드다.

### MCP 서버 (v2)

```bash
cd mcp_server
python3 -m uvicorn server:app
```

tools 4개: `analyze_prompt`, `generate_prompt`, `list_types`, `get_layer_chain`  
resources 2개: `layer_specs`, `service_ontology`  
prompt 1개: `ops_workflow`

### 모델 어댑터

```text
어댑터    특화
──────────────────────────────────────────────
claude   확장 추론, evidence-first 보고
codex    코드+테스트 검증 게이트
gemini   리서치/비교 분석
hermes   skill/tool/gateway 환경
generic  모델별 특화 없음
```

## 검증

```bash
python3 -m pytest -q
python3 prompt_ops_maker.py list-projects
python3 prompt_ops_maker.py list-types
python3 prompt_ops_maker.py make --project brand-hub --mode audit --task 'smoke test' --effort high --target-ai codex --environment local --dry-run
python3 prompt_ops_maker.py analyze --input README.md --format json
python3 prompt_ops_maker.py make-adhoc --name "test" --type generic --task "test" --self-verify --dry-run
python3 prompt_ops_maker.py make-adhoc --name "test" --type generic --task "test" --promptspec --dry-run
python3 prompt_ops_maker.py verify --input README.md --verifier-model haiku
```

릴리스 스모크:

```text
pytest                            13 passed, 1 skipped
self-verify dry-run               9항목 루브릭 블록 추가 확인
promptspec dry-run                YAML 스펙 출력 확인
verify --verifier-model gpt-mini  LLM 독립 점수 확인
```

## 보안 경계

- configs에 API key, token, private key, 고객 데이터, `.env` 값을 넣지 않는다.
- 예제에는 placeholder path를 쓴다.
- 생성된 prompt는 지시문이다. 대상 프로젝트 검증 완료 증거가 아니다.
- deploy, upload, DB, 계정 설정 변경은 명시 승인 뒤에만 진행한다.

## 라이선스

MIT
