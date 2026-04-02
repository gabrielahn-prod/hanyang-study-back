# 에이전트 아키텍처 설명

이 저장소의 아키텍처는 `Google ADK` 런타임 위에 `env_agent` 루트 에이전트를 올리고, 그 아래에 역할별 서브에이전트를 둔 뒤, `FastAPI`로 이를 서빙하는 구조입니다. 모델 공급자를 환경 변수로 바꾸는 실행 환경 중심 설계는 유지하면서, 간단한 멀티 에이전트 오케스트레이션을 추가했습니다.

## 1. 전체 구조

```text
Client / ADK Web / curl
        |
        v
     FastAPI app
     (app.py)
        |
        v
 Google ADK Runtime
 get_fast_api_app(...)
        |
        v
   agents_dir = agents/
        |
        v
   env_agent.root_agent
        |
   +----+-----------+---------------+-------------+
   |                |               |             |
   v                v               v             v
time_agent     runtime_agent   everytime_agent  general_agent
   |                |               |
   v                v               v
get_local_time()  get_runtime_config()  Everytime MCP tools
        |
        v
   Model Resolver
   build_model()
    - Gemini
    - OpenAI(LiteLlm)
```

## 2. 핵심 파일 역할

### [`app.py`](/Users/ahngab/Desktop/temp-agent/hanyang-study-back/app.py)

- 애플리케이션 진입점입니다.
- `google.adk.cli.fast_api.get_fast_api_app(...)`를 호출해 ADK 런타임을 FastAPI 앱으로 노출합니다.
- `AGENTS_DIR`, `SESSION_DB_URI`, `ALLOW_ORIGINS`, `PORT` 같은 운영 설정을 환경 변수에서 읽습니다.
- 추가로 `/`, `/healthz` 같은 메타 엔드포인트를 붙여 상태 확인을 단순화합니다.

즉, 이 파일은 직접 추론을 수행하지 않고, "ADK 런타임을 웹 서버 형태로 감싸는 부트스트랩 레이어" 역할을 합니다.

### [`agents/env_agent/agent.py`](/Users/ahngab/Desktop/temp-agent/hanyang-study-back/agents/env_agent/agent.py)

- 실제 에이전트 정의가 있는 핵심 파일입니다.
- `root_agent = Agent(...)` 형태로 ADK가 읽을 루트 에이전트를 선언합니다.
- 루트 에이전트 아래에 여러 서브에이전트를 둡니다.
  - `time_agent`: 시간/타임존 질의 담당
  - `runtime_agent`: 현재 모델/런타임 설정 질의 담당
  - `everytime_agent`: Everytime 게시판 조회 MCP 연동 담당
  - `general_agent`: 일반 대화와 fallback 담당
- 모델 선택 로직(`build_model`)과 툴 함수(`get_local_time`, `get_runtime_config`)도 함께 가집니다.
- Everytime용 MCP 연결 로직은 [`agents/env_agent/everytime_agent.py`](/Users/ahngab/Desktop/temp-agent/hanyang-study-back/agents/env_agent/everytime_agent.py)로 분리되어 있습니다.
- 프롬프트 수준 정책도 여기서 정의합니다.
  - 기본 응답 언어는 한국어
  - 요청 유형에 따라 적절한 서브에이전트로 위임
  - API 키 같은 비밀값은 노출 금지

### [`agents/agent.py`](/Users/ahngab/Desktop/temp-agent/hanyang-study-back/agents/agent.py)

- 호환성용 엔트리포인트입니다.
- 프로젝트 루트에서 `adk web`를 실행했을 때 ADK가 `agents/` 자체를 하나의 앱으로 오인할 수 있어서, 실제 `env_agent.root_agent`를 다시 export 합니다.
- 실질적인 비즈니스 로직은 없고, 런타임 로딩 경로 차이를 흡수하는 어댑터입니다.

## 3. 요청 처리 흐름

사용자 요청은 아래 순서로 처리됩니다.

1. 클라이언트가 FastAPI 엔드포인트로 요청을 보냅니다.
2. [`app.py`](/Users/ahngab/Desktop/temp-agent/hanyang-study-back/app.py)에서 생성한 ADK FastAPI 앱이 요청을 받습니다.
3. ADK 런타임은 `agents_dir` 아래 앱을 찾고, `env_agent`의 `root_agent`를 로드합니다.
4. `root_agent`는 요청 성격을 보고 적절한 서브에이전트로 위임합니다.
5. `time_agent` 또는 `runtime_agent`가 필요한 경우 등록된 Python 함수 툴을 호출합니다.
6. Everytime 게시판/홈 조회 요청은 `everytime_agent`가 MCP 서버를 통해 처리합니다.
7. 일반 요청은 `general_agent`가 처리합니다.
8. 최종 응답은 다시 FastAPI를 통해 클라이언트로 반환됩니다.

## 4. 모델 선택 아키텍처

이 프로젝트의 중요한 특징은 "에이전트 코드는 거의 고정하고, 모델만 환경 변수로 바꾼다"는 점입니다.

### 선택 규칙

- `MODEL_PROVIDER=openai`
  - `OPENAI_MODEL` 값을 읽습니다.
  - `LiteLlm(model=...)`로 OpenAI 계열 모델을 ADK에 연결합니다.
- 그 외 기본값
  - `GEMINI_MODEL` 값을 직접 모델 식별자로 사용합니다.

### 의미

- 애플리케이션 계층은 공급자 차이를 거의 모르고 동작합니다.
- 모델 교체가 코드 수정이 아니라 배포 설정 변경으로 해결됩니다.
- 같은 에이전트 instruction, tool 구성을 유지하면서 모델만 바꿔 비교 실험하기 쉽습니다.

## 5. 툴 아키텍처

현재 툴은 로컬 함수 2개와 Everytime MCP toolset 1개로 구성됩니다.

### `get_local_time(city="Seoul")`

- 도시 이름을 내부 타임존 맵으로 변환합니다.
- `datetime`과 `ZoneInfo`를 사용해 현재 시각을 계산합니다.
- 외부 API 호출 없이 로컬 런타임만으로 동작합니다.

### `get_runtime_config()`

- 현재 활성 모델 공급자와 모델명을 반환합니다.
- `APP_NAME`도 함께 반환합니다.
- API 키는 반환하지 않도록 제한되어 있습니다.

즉, 이 구조는 "LLM + 안전한 읽기 전용 도구 몇 개" 패턴입니다. 아직 데이터베이스 조회, 외부 SaaS 호출, 워크플로 오케스트레이션 같은 복합 툴 계층은 없습니다.

### `everytime_agent` MCP toolset

- `EVERYTIME_MCP_URL`과 `EVERYTIME_MCP_TIMEOUT`을 사용합니다.
- `health_check`, `get_home_summary`, `list_boards`, `get_board_posts`, `debug_board` tool만 허용합니다.
- 현재 범위는 읽기 전용 조회이며, 글 본문 단건 조회, 댓글 조회, 로그인 자동화, 쿠키 자동 갱신은 지원하지 않습니다.

## 6. 세션 및 상태 관리

세션 관리는 직접 구현하지 않고 ADK 런타임 설정에 위임합니다.

- `SESSION_DB_URI`
- `ARTIFACT_SERVICE_URI`
- `MEMORY_SERVICE_URI`
- `EVAL_STORAGE_URI`

이 값들은 [`app.py`](/Users/ahngab/Desktop/temp-agent/hanyang-study-back/app.py)에서 `get_fast_api_app(...)`로 전달됩니다. 따라서 애플리케이션 코드가 상태 저장소를 직접 다루지 않고, 인프라 설정으로 세션/메모리 저장소를 교체할 수 있습니다.

## 7. 이 아키텍처의 성격

이 저장소는 다음 성격의 예제입니다.

- 루트 + 다중 서브에이전트 구조
- 환경 변수 기반 모델 전환 아키텍처
- ADK 런타임 위임형 웹 서빙 구조
- 로컬 함수 툴과 Everytime MCP toolset을 함께 사용하는 경량 툴링
- 운영 설정과 에이전트 정의를 분리한 구조

반대로, 아직 포함되지 않은 것은 아래와 같습니다.

- 복잡한 플래너/실행기 분리
- 다단계 역할별 협업 워크플로
- 장기 메모리 정책 구현
- 커스텀 인증/인가 레이어

## 8. 한 줄로 요약

이 프로젝트는 "FastAPI가 ADK 런타임을 감싸고, ADK 런타임이 `env_agent` 루트 에이전트를 로드하며, 루트가 여러 서브에이전트에 요청을 위임하고, 각 에이전트가 환경 변수에 따라 Gemini 또는 OpenAI 모델과 로컬 툴 또는 MCP 툴을 사용해 응답하는 구조"입니다.
