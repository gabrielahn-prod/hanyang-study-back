import os

from fastapi import FastAPI
from pydantic import BaseModel
from google.adk.cli.fast_api import get_fast_api_app

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agents.env_agent.agent import root_agent

def _parse_allow_origins(value: str | None) -> list[str] | None:
    if not value:
        return None
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return origins or None

APP_NAME = os.getenv("APP_NAME", "env_agent")
USER_ID = "demo_user"
SESSION_ID = "demo_session"

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

class AskRequest(BaseModel):
    prompt: str


def create_app() -> FastAPI:
    app = get_fast_api_app(
        agents_dir=os.getenv("AGENTS_DIR", "agents"),
        session_service_uri=os.getenv("SESSION_DB_URI"),
        artifact_service_uri=os.getenv("ARTIFACT_SERVICE_URI"),
        memory_service_uri=os.getenv("MEMORY_SERVICE_URI"),
        eval_storage_uri=os.getenv("EVAL_STORAGE_URI"),
        allow_origins=_parse_allow_origins(os.getenv("ALLOW_ORIGINS")),
        web=os.getenv("ADK_WEB_UI", "false").lower() == "true",
        a2a=os.getenv("ADK_A2A", "false").lower() == "true",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        trace_to_cloud=os.getenv("TRACE_TO_CLOUD", "false").lower() == "true",
        reload_agents=os.getenv("RELOAD_AGENTS", "false").lower() == "true",
    )

    @app.on_event("startup")
    async def startup_event():
        # 서버 시작 시 커스텀 데모 세션 1개 생성
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )

    @app.post("/ask", tags=["custom"])
    async def ask_agent(request: AskRequest):
        try:
            content = types.Content(
                role="user",
                parts=[types.Part(text=request.prompt)]
            )

            events = runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=content,
            )

            final_text = None

            async for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    final_text = event.content.parts[0].text

            return {
                "status": "success",
                "response": final_text or "응답을 생성하지 못했습니다."
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "name": "google-adk-agent",
            "status": "ok",
            "docs": "/docs",
            "apps": "/list-apps",
        }

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
