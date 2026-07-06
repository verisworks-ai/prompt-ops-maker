# Universal AI Prompt Maker Roadmap

## 목적

이 프로젝트는 두 가지 목적을 가진다.

```text
1. GitHub 오픈소스 공개
   1-1. WebView miniapp 프로젝트 공개/운영 프롬프트 지원
   1-2. Kakao PlayMCP 등 MCP 기반 환경 공개/운영 프롬프트 지원

2. Claude Fable 5 한정 제공 종료 대비
   - Fable 5가 2026-07-07까지만 제한적으로 제공될 수 있으므로,
     Fable 5 prompting guide에서 제시한 장기작업 운영 패턴을
     모델 비종속 템플릿으로 재사용할 수 있게 한다.
   - Fable 5의 모델 성능 자체를 대체하거나 보장하지 않는다.
```

## 제품 방향

현재 이름은 `fable5-prompt-maker`지만 공개 제품 방향은 모델 성능 대체제가 아니라 범용 prompt operations 도구다.

공개 문서에서는 다음 표현을 금지한다.

```text
금지:
- Fable 5급 성능 제공
- Fable 5 대체
- Fable 5 성능 재현
- Claude Fable 5와 동급 결과
- 모델 성능이 낮아도 Fable 5처럼 작동

허용:
- Fable 5 prompting guide에서 추출한 작업 운영 패턴을 템플릿화
- 장기 작업용 prompt structure 제공
- effort / verification / execution boundary / memory 규칙 표준화
- 모델 비종속 agent prompt workflow 제공
- 특정 모델 성능을 보장하지 않음
```

권장 공개명 후보:

```text
universal-ai-prompt-maker
agent-prompt-maker
prompt-ops-maker
model-agnostic-prompt-maker
```

내부 호환성 때문에 CLI 파일명은 당분간 유지할 수 있으나, GitHub 공개 전 README/패키지명/명령어는 범용 이름으로 정리한다.

## 공개 대상

```text
대상 사용자:
- Claude/Fable/Codex/Gemini 사용자
- Hermes Agent 사용자
- MCP tool/resource/prompt 기반 자동화 사용자
- WebView miniapp, web-public, automation-pipeline 운영자

핵심 가치:
- 특정 모델 성능 동등성을 주장하지 않고 작업 경계, effort, 검증, 보고 형식을 표준화
- 평가와 실행을 분리해 승인 없는 수정/배포/삭제 방지
- tool output 기반 검증과 미검증 항목 보고를 기본값으로 제공
```

## GitHub 공개 전 필수 작업

```text
BLOCKER
- 공개 repo 이름 확정
- LICENSE 추가
- README 영어 기본본 작성
- README-ko_kr.md 작성
- 로컬 절대경로와 개인 프로젝트명 노출 여부 점검
- 샘플 config에서 민감 정보/개인 경로 제거
- package/test 실행법 검증

HIGH
- CLI 명령명 범용화 완료: `prompt-ops-maker` console script와 `prompt_ops_maker.py` 직접 실행으로 통일
- pyproject.toml 추가 및 console_scripts 제공
- GitHub Actions 테스트 추가
- examples/ 디렉토리 추가
- WebView miniapp 예제와 MCP 예제 분리

MEDIUM
- wizard 모드 추가
- JSON 출력 모드 추가
- prompt pack export/import
- target-ai/environment 확장 문서화

LOW
- 로고/배지/스크린샷
- PyPI 배포 검토
```

## 공개 예제 구조 제안

```text
examples/
  apps-in-toss/
    README.md
    config.yaml
    ad-qa.prompt.md
  kakao-playmcp/
    README.md
    config.yaml
    mcp-audit.prompt.md
  web-public/
    config.yaml
  automation-pipeline/
    config.yaml
```

## Fable 5 한정 제공 종료 대비 설계 원칙

```text
1. Fable 5 고유 기능을 하드코딩하지 않는다.
2. target-ai는 실행자 힌트일 뿐, 품질 기준은 공통 gate로 유지한다.
3. Fable 5 prompting guide의 장기작업 운영 방식은 아래 구조로 재사용한다.
   - 목표 단위 분해
   - effort 지정
   - 평가/실행 분리
   - 금지 행동 명시
   - 검증 gate
   - 미검증 항목 보고
   - evidence-first reporting
4. 모델 성능 동등성은 주장하지 않는다. 프롬프트는 작업 경계와 검증 습관을 명시적으로 요구하는 역할만 한다.
```

## Kakao PlayMCP 관점

MCP 환경용 프롬프트는 다음을 기본 포함한다.

```text
- 사용 가능한 MCP tools/resources/prompts 먼저 열거
- tool 호출 결과와 로컬 파일/명령 결과 분리
- 권한/외부 API/비용/계정 로그인 부작용 사전 승인
- tool이 없거나 실패하면 fallback 경로 제안
- resource 기반 증거와 추정 분리
```

## WebView miniapp 관점

WebView miniapp 예제는 다음을 기본 포함한다.

```text
- source와 bundle 내부 산출물 분리
- SDK/API 호출 확인
- 광고 load/show flow 확인
- live 광고 ID 반복 호출 금지
- 콘솔 업로드/배포는 명시 승인 후 진행
- 실제 앱 환경에서만 검증 가능한 항목은 미검증으로 분리
```
