import os

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams


def build_everytime_toolset() -> McpToolset:
    everytime_mcp_url = os.getenv("EVERYTIME_MCP_URL")
    if not everytime_mcp_url:
        default_host = "host.docker.internal" if os.path.exists("/.dockerenv") else "127.0.0.1"
        everytime_mcp_url = f"http://{default_host}:8001/"
    everytime_mcp_timeout = float(os.getenv("EVERYTIME_MCP_TIMEOUT", "10"))
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=everytime_mcp_url,
            timeout=everytime_mcp_timeout,
        ),
        tool_filter=[
            "health_check",
            "get_home_summary",
            "list_boards",
            "get_board_posts",
            "debug_board",
        ],
    )


def create_everytime_agent(model) -> Agent:
    return Agent(
        name="everytime_agent",
        model=model,
        description="Handles Everytime board and home page lookup requests through the Everytime MCP server.",
        instruction=(
            "You specialize in requests about the Everytime service and campus boards. "
            "Always begin your final answer with '[everytime_agent] '. "
            "Answer in Korean by default. "
            "When a request can be answered with an Everytime MCP tool, call the tool instead of answering from memory. "
            "Use get_home_summary for requests about the Everytime home page, main page summary, or overall portal overview. "
            "Use list_boards for requests about available boards, board discovery, or board id lookup. "
            "Use get_board_posts for requests about recent posts from a board. "
            "Use debug_board only when the user explicitly asks for debugging details or when tool results look inconsistent and structure inspection is needed. "
            "If the user names a board but does not provide a board id, always call list_boards first, find the closest matching board, and then call get_board_posts with that board id. "
            "If the user asks for board posts without specifying a limit, use the tool default. If a limit is provided, pass it through when it is a valid integer. "
            "If multiple boards have similar names, briefly mention the match you selected before summarizing posts. "
            "Summarize tool results clearly, and include board id or board title when useful. "
            "If the MCP call fails, say that the Everytime MCP connection failed and suggest checking EVERYTIME_MCP_URL, cookie validity, or the MCP server status. "
            "If the user asks for unsupported actions such as login automation, cookie refresh, article detail, or comments, state that the current MCP only supports read-only board and home lookups."
        ),
        tools=[build_everytime_toolset()],
    )
