"""Compatibility entrypoint for running `adk web` from the project root.

ADK's web CLI treats the provided directory as `agents_dir` and expects each
direct child folder to expose `root_agent`. If the command is launched from the
repository root without an explicit path, the `agents/` folder itself is loaded
as an app named `agents`. Re-export the real sample agent so both layouts work.
"""

from .env_agent.agent import root_agent
