# Google ADK Local Agent

`google-adk` 기반의 로컬 테스트용 에이전트 예제입니다.  
`.env`에서 모델 공급자와 API 키를 분리하고, `uvicorn`으로 ADK FastAPI 앱을 직접 서빙할 수 있게 구성했습니다.  
현재는 루트 에이전트가 3개의 서브에이전트(`time_agent`, `runtime_agent`, `general_agent`)를 오케스트레이션합니다.

## 모델 지원

`Google ADK`는 기본적으로 Gemini 모델을 바로 사용할 수 있고, 공식 문서 기준으로 `LiteLlm` 래퍼를 통해 OpenAI 같은 외부 모델도 사용할 수 있습니다.

- Gemini: `MODEL_PROVIDER=gemini`
- OpenAI: `MODEL_PROVIDER=openai`

OpenAI를 사용할 때는 `OPENAI_MODEL` 값을 LiteLLM 형식으로 넣어야 합니다.

예시:

```env
OPENAI_MODEL=openai/gpt-4o-mini
```

## 파일 구조

```text
.
├── .env.example
├── agents
│   ├── __init__.py
│   ├── agent.py
│   └── env_agent
│       ├── __init__.py
│       └── agent.py
├── app.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 1. 환경 변수 준비

```bash
cp .env.example .env
```

### Gemini 사용 예시

```env
MODEL_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-2.0-flash
AGENTS_DIR=agents
PORT=8000
SESSION_DB_URI=sqlite:////data/sessions.db
ALLOW_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

### OpenAI 사용 예시

```env
MODEL_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=openai/gpt-4o-mini
AGENTS_DIR=agents
PORT=8000
SESSION_DB_URI=sqlite:////data/sessions.db
ALLOW_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

## 2. Docker Compose 실행

```bash
docker compose up --build
```

서버가 뜨면 기본 주소는 아래입니다.

```text
http://localhost:8000
```

Swagger 문서는 아래에서 확인할 수 있습니다.

```text
http://localhost:8000/docs
```

헬스 체크는 아래입니다.

```text
http://localhost:8000/healthz
```

## 3. 로컬 API 테스트

### 앱 목록 확인

```bash
curl http://localhost:8000/list-apps
```

### 세션 생성

```bash
curl -X POST http://localhost:8000/apps/env_agent/users/test-user/sessions/test-session \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 에이전트 실행

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "env_agent",
    "userId": "test-user",
    "sessionId": "test-session",
    "newMessage": {
      "role": "user",
      "parts": [
        {
          "text": "현재 설정된 모델이 뭐야?"
        }
      ]
    }
  }'
```

## 4. 로컬 Python 실행

Docker 없이 직접 돌리려면:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export SESSION_DB_URI=sqlite:///./local_sessions.db
uvicorn app:app --host 0.0.0.0 --port 8000
```

## 5. ADK Web 연결

백엔드가 뜬 상태에서 ADK Web은 별도로 백엔드를 바라보게 실행하면 됩니다.

```bash
npx @google/adk-devtools web --backend=http://localhost:8000
```

브라우저에서 `http://localhost:4200`으로 접속하면 됩니다.

직접 `adk web` CLI를 쓰는 경우에는 에이전트 루트 디렉터리를 명시하는 편이 안전합니다.

```bash
adk web agents
```

프로젝트 루트에서 그냥 `adk web`를 실행하면 현재 작업 디렉터리의 직계 하위 폴더를 앱으로 해석합니다. 이 저장소에서는 그 경우 `agents`가 앱 이름이 되므로, 호환용 `agents/agent.py`가 `env_agent`의 `root_agent`를 다시 내보내도록 구성했습니다.

## 참고

공식 문서 기준:

- `google.adk.cli.fast_api.get_fast_api_app(...)`로 ADK FastAPI 앱을 직접 만들 수 있습니다.
- ADK 런타임은 에이전트 디렉터리 아래의 각 하위 폴더를 하나의 앱으로 인식하므로, 런타임 대상은 `agents/`처럼 별도 폴더로 분리하는 편이 안전합니다.
- OpenAI 같은 외부 모델은 `from google.adk.models.lite_llm import LiteLlm` 방식으로 사용할 수 있습니다.
