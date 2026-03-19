import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

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
        "to runtime_agent, and other general requests to general_agent. "
        "Return the delegated agent's response as-is so the agent label remains visible. "
        "Never reveal API keys or secret values."
    ),
    sub_agents=[time_agent, runtime_agent, general_agent],
)
