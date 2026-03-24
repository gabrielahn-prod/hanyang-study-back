import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams

load_dotenv()


def get_local_time(city: str = "Seoul") -> dict:
    """Returns the current time for a supported city."""
    timezone_map = {
        "seoul": "Asia/Seoul",
        "korea": "Asia/Seoul",
        "tokyo": "Asia/Tokyo",
        "new york": "America/New_York",
        "san francisco": "America/Los_Angeles",
        "london": "Europe/London",
    }
    timezone_name = timezone_map.get(city.strip().lower(), "Asia/Seoul")
    now = datetime.now(ZoneInfo(timezone_name))
    return {
        "city": city,
        "timezone": timezone_name,
        "local_time": now.isoformat(),
    }


def get_runtime_config() -> dict:
    """Returns safe runtime settings without exposing secrets."""
    provider = os.getenv("MODEL_PROVIDER", "ollama").lower()
    if provider == "openai":
        active_model = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")
    elif provider == "ollama":
        active_model = os.getenv("OLLAMA_MODEL", "ollama_chat/llama3.1:8b")
    else:
        active_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    return {
        "provider": provider,
        "model": active_model,
        "app_name": os.getenv("APP_NAME", "env_agent"),
    }


def build_model():
    provider = os.getenv("MODEL_PROVIDER", "ollama").strip().lower()
    if provider == "ollama":
        ollama_api_base = os.getenv("OLLAMA_API_BASE")
        return LiteLlm(
            model=os.getenv("OLLAMA_MODEL", "ollama_chat/llama3.1:8b"),
            api_base=ollama_api_base if ollama_api_base else None
        )
    elif provider == "openai":
        model_name = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")
        return LiteLlm(model=model_name)
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def build_papago_toolset() -> McpToolset:
    papago_mcp_url = os.getenv("PAPAGO_MCP_URL")
    if not papago_mcp_url:
        default_host = "host.docker.internal" if os.path.exists("/.dockerenv") else "127.0.0.1"
        papago_mcp_url = f"http://{default_host}:8001/mcp"
    papago_mcp_timeout = float(os.getenv("PAPAGO_MCP_TIMEOUT", "10"))
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=papago_mcp_url,
            timeout=papago_mcp_timeout,
        ),
        tool_filter=["translate_text", "detect_and_translate"],
    )


time_agent = Agent(
    name="time_agent",
    model=build_model(),
    description="Handles local time and timezone requests.",
    instruction=(
        "You specialize in time-related questions. "
        "Always begin your final answer with '[time_agent] '. "
        "Answer in Korean by default. "
        "Use the get_local_time tool whenever the user asks for the current time, "
        "time in a city, or timezone-related information."
    ),
    tools=[get_local_time],
)


runtime_agent = Agent(
    name="runtime_agent",
    model=build_model(),
    description="Handles runtime and model configuration questions.",
    instruction=(
        "You specialize in runtime configuration questions. "
        "Always begin your final answer with '[runtime_agent] '. "
        "Answer in Korean by default. "
        "Use the get_runtime_config tool whenever the user asks which provider, "
        "model, or app configuration is currently active. "
        "Never reveal API keys or secret values."
    ),
    tools=[get_runtime_config],
)


general_agent = Agent(
    name="general_agent",
    model=build_model(),
    description="Handles general conversation and fallback requests.",
    instruction=(
        "You handle general conversation and requests that do not require tools. "
        "Always begin your final answer with '[general_agent] '. "
        "Answer in Korean by default. "
        "If a request is specifically about time or runtime configuration, let a "
        "more specialized agent handle it."
    ),
)


papago_agent = Agent(
    name="papago_agent",
    model=build_model(),
    description="Handles translation requests through the Papago MCP server.",
    instruction=(
        "You specialize in translation requests. "
        "Always begin your final answer with '[papago_agent] '. "
        "Answer in Korean by default. "
        "Use the detect_and_translate tool when the user only specifies the target language. "
        "Use the translate_text tool when the user provides both source and target languages. "
        "If the MCP tool returns translated_text, present that translation clearly."
    ),
    tools=[build_papago_toolset()],
)


root_agent = Agent(
    name=os.getenv("APP_NAME", "env_agent"),
    model=build_model(),
    description=(
        "A Google ADK sample root agent that coordinates three specialized "
        "sub-agents."
    ),
    instruction=(
        "You are the root coordinator for local ADK testing. "
        "Answer in Korean by default. "
        "Delegate time questions to time_agent, runtime configuration questions "
        "to runtime_agent, translation requests to papago_agent, and other "
        "general requests to general_agent. "
        "Return the delegated agent's response as-is so the agent label remains visible. "
        "Never reveal API keys or secret values."
    ),
    sub_agents=[time_agent, runtime_agent, papago_agent, general_agent],
)
