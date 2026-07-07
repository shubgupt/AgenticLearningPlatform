"""
Settings, split the same way the reference project splits them:
- config.yaml    -> non-secret, checked-into-git settings (model names, mock
                     vs live, host/port). Edit this file directly.
- .env           -> secrets only (the API key). Never committed.

Both are optional. Missing config.yaml/.env just means "use the defaults
below," which are chosen so the app runs with zero configuration in mock
mode.
"""
from __future__ import annotations
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_PACKAGE_DIR = Path(__file__).resolve().parent          # src/learning_avatar
_PROJECT_ROOT = _PACKAGE_DIR.parent.parent               # repo root
_CONFIG_YAML_PATH = _PROJECT_ROOT / "config.yaml"

def _load_yaml() -> dict:
    if _CONFIG_YAML_PATH.exists():
        with open(_CONFIG_YAML_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


_yaml_config = _load_yaml()


def _yaml_get(*path: str, default=None):
    node = _yaml_config
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


class Settings:
    # --- secrets (env only) ---
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # --- everything else (config.yaml, with env var override, with a
    #     hardcoded default so the app runs out of the box) ---
    llm_mode: str = os.getenv("LLM_MODE", _yaml_get("llm", "mode", default="mock"))
    teaching_agent_model: str = os.getenv(
        "TEACHING_AGENT_MODEL", _yaml_get("llm", "teaching_agent_model", default="gpt-4o-mini")
    )
    assessment_agent_model: str = os.getenv(
        "ASSESSMENT_AGENT_MODEL", _yaml_get("llm", "assessment_agent_model", default="gpt-4o-mini")
    )

    host: str = _yaml_get("server", "host", default="127.0.0.1")
    port: int = int(_yaml_get("server", "port", default=8000))

    # The content-retrieval MCP server is now a separate, manually-started
    # process (`uv run learning-avatar-mcp-server`) rather than something
    # the web app spawns per request. This is the address the web app
    # connects to as a client -- if nothing is listening here, lesson
    # requests fail with a clear error instead of a hidden subprocess launch.
    mcp_host: str = os.getenv("MCP_HOST", _yaml_get("mcp", "host", default="127.0.0.1"))
    mcp_port: int = int(os.getenv("MCP_PORT", _yaml_get("mcp", "port", default=9000)))
    mcp_server_url: str = f"http://{mcp_host}:{mcp_port}/mcp"

    db_path: str = os.getenv("DB_PATH", _yaml_get("storage", "db_path", default="sessions.db"))

    # --- filesystem locations, computed once, used everywhere ---
    project_root: Path = _PROJECT_ROOT
    package_dir: Path = _PACKAGE_DIR
    content_dir: Path = _PACKAGE_DIR / "content"
    prompts_dir: Path = _PACKAGE_DIR / "agents" / "prompts"
    mcp_server_script: Path = _PACKAGE_DIR / "mcp" / "server.py"
    frontend_dir: Path = _PROJECT_ROOT / "frontend"


settings = Settings()
