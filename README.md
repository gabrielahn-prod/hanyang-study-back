# Google ADK Local Agent

`Google ADK` 기반의 로컬 테스트용 멀티 에이전트 예제입니다. 현재 저장소는 `env_agent` 루트 에이전트가 3개의 서브에이전트(`time_agent`, `runtime_agent`, `general_agent`)를 오케스트레이션하고, 이를 `FastAPI` 또는 `adk web`으로 실행할 수 있게 구성되어 있습니다.

모델 공급자는 환경 변수로 전환합니다.

- `MODEL_PROVIDER=gemini` (기본값)
- `MODEL_PROVIDER=openai`
- `MODEL_PROVIDER=ollama`

OpenAI나 Ollama를 사용할 때는 `LiteLlm`을 통해 연결되므로 각각의 모델을 해당 형식에 맞게 지정합니다:

```env
OPENAI_MODEL=openai/gpt-4o-mini
OLLAMA_MODEL=ollama_chat/llama3.1:8b
# 원격 터널을 사용하는 경우 OLLAMA_API_BASE도 지정 가능합니다.
```

## 구성 개요

- `app.py`: `google.adk.cli.fast_api.get_fast_api_app(...)`로 ADK FastAPI 앱 생성
- `agents/env_agent/agent.py`: 루트 에이전트와 3개 서브에이전트 정의
- `agents/agent.py`: 루트 디렉터리에서 `adk web` 실행 시 호환용 엔트리포인트
- `docker-compose.yml`: 로컬 Docker 실행용 기본 설정

## 파일 구조

```text
.
├── .env.example
├── AGENT_ARCHITECTURE.md
├── Dockerfile
├── README.md
├── agents
│   ├── __init__.py
│   ├── agent.py
│   └── env_agent
│       ├── __init__.py
│       └── agent.py
├── app.py
├── docker-compose.yml
├── requirements.txt
```

## 환경 변수

먼저 예제 파일을 복사합니다.

```bash
cp .env.example .env
```

### Ollama 예시 (로컬 LLM)

```env
# 사용할 모델 제공자: gemini, openai 또는 ollama
MODEL_PROVIDER=ollama

# Ollama 설정
# Docker에서 호스트 PC의 Ollama를 사용할 때는 아래 값을 사용
# 원격 터널을 사용할 시 OLLAMA_API_BASE=https://... 처럼 입력
OLLAMA_API_BASE=http://host.docker.internal:11434
OLLAMA_MODEL=ollama_chat/llama3.1:8b

APP_NAME=env_agent
AGENTS_DIR=agents
HOST=0.0.0.0
PORT=8000
SESSION_DB_URI=sqlite:////data/sessions.db
ALLOW_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

### Gemini 예시

```env
MODEL_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-2.0-flash
APP_NAME=env_agent
AGENTS_DIR=agents
HOST=0.0.0.0
PORT=8000
SESSION_DB_URI=sqlite:////data/sessions.db
ALLOW_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

### OpenAI 예시

```env
MODEL_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=openai/gpt-4o-mini
APP_NAME=env_agent
AGENTS_DIR=agents
HOST=0.0.0.0
PORT=8000
SESSION_DB_URI=sqlite:////data/sessions.db
ALLOW_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

## Docker로 로컬 실행

이 저장소는 로컬 Docker 실행을 기본 지원합니다. `docker-compose.yml`은 현재 디렉터리를 컨테이너 `/app`에 마운트하고, 세션 DB 저장용 `./data` 디렉터리도 함께 연결합니다. 쉘 엔트리포인트 없이 Compose가 실행 명령을 직접 지정합니다.

`MODEL_PROVIDER=ollama`일 때 Docker 컨테이너 안의 `localhost`는 호스트 PC가 아니라 컨테이너 자신을 가리킵니다. 그래서 Docker Desktop(Windows/macOS)에서 호스트 Ollama를 쓰려면 `OLLAMA_API_BASE=http://host.docker.internal:11434`를 사용해야 합니다. 이 저장소의 Compose 설정은 기본값도 그 주소로 맞춰 두었습니다.

### 1. 환경 변수 준비

```bash
cp .env.example .env
```

필요한 API 키를 `.env`에 채웁니다.

### 2. 컨테이너 실행

```bash
docker compose up --build
```

백그라운드 실행:

```bash
docker compose up --build -d
```

중지:

```bash
docker compose down
```

로그 확인:

```bash
docker compose logs -f
```

### 3. 기본 API 모드 확인

기본 서비스 `adk-agent`는 아래 명령으로 서버를 올립니다.

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

접속 주소:

- API 루트: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- 헬스 체크: `http://localhost:8000/healthz`
- 앱 목록: `http://localhost:8000/list-apps`

### 4. Docker에서 ADK Web 모드로 실행

Web UI가 필요하면 `web` 프로필로 `adk-web` 서비스를 실행합니다.

```bash
docker compose --profile web up --build adk-web
```

백그라운드 실행:

```bash
docker compose --profile web up --build -d adk-web
```

이 서비스는 아래 명령으로 실행됩니다.

```bash
python -m google.adk.cli web --host 0.0.0.0 --port 8000 agents
```

접속 주소는 아래입니다.

- Web UI: `http://localhost:8000/dev-ui/`

다시 API 모드로 되돌리려면 기본 서비스를 다시 실행하면 됩니다.

```bash
docker compose down
docker compose up --build
```

### 5. Docker 내부 상태 확인

실행 중 컨테이너에 들어가려면:

```bash
docker compose exec adk-agent sh
```

앱 파일이 마운트되었는지 확인:

```bash
docker compose exec adk-agent ls /app
```

세션 DB 저장 경로 확인:

```bash
docker compose exec adk-agent ls /data
```

## 로컬 API 테스트

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

### 루트 엔드포인트 확인

```bash
curl http://localhost:8000/
```

### 헬스 체크

```bash
curl http://localhost:8000/healthz
```

## Python으로 로컬 실행

Docker 없이 직접 실행하려면:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export SESSION_DB_URI=sqlite:///./local_sessions.db
uvicorn app:app --host 0.0.0.0 --port 8000
```

## ADK Web 직접 실행

프로젝트 루트에서 직접 실행할 수도 있습니다.

```bash
python -m google.adk.cli web --host 0.0.0.0 --port 8000 agents
```

또는 설치 환경에 따라:

```bash
adk web agents
```

이 저장소는 루트에서 `adk web`를 실행했을 때의 로딩 차이를 흡수하기 위해 `agents/agent.py`에서 `env_agent.root_agent`를 다시 export 하도록 구성되어 있습니다.

## 현재 에이전트 구성

- `root_agent`: 요청 분류 및 서브에이전트 위임
- `time_agent`: 현재 시간과 타임존 관련 요청 처리
- `runtime_agent`: 현재 모델 공급자와 모델 설정 확인
- `general_agent`: 일반 대화 및 fallback 처리

## 참고

- `get_runtime_config()`는 현재 provider, model, app name만 반환하며 API 키는 노출하지 않습니다.
- `SESSION_DB_URI`, `ARTIFACT_SERVICE_URI`, `MEMORY_SERVICE_URI`, `EVAL_STORAGE_URI`는 `app.py`에서 ADK 런타임으로 전달됩니다.
- 더 자세한 구조 설명은 `AGENT_ARCHITECTURE.md`를 참고하면 됩니다.
