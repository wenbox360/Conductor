import json
import os
from pathlib import Path

from fastmcp import FastMCP
from dotenv import load_dotenv

SERVICE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_DIR.parent
load_dotenv(SERVICE_DIR / ".env.local")

from resources import register_resources  # noqa: E402
from serial_bridge import start_serial_bridge  # noqa: E402
from tools import register_tools  # noqa: E402


configured_mappings_file = os.getenv("MAPPINGS_FILE")
if configured_mappings_file:
    mappings_path = Path(configured_mappings_file)
    MAPPINGS_FILE = (
        mappings_path if mappings_path.is_absolute() else SERVICE_DIR / mappings_path
    ).resolve()
else:
    MAPPINGS_FILE = REPO_ROOT / "registry-server" / "mappings.json"


def get_available_hardware() -> set[str]:
    """Return Leonardo part IDs supported by the serial hardware bridge."""
    if not MAPPINGS_FILE.exists():
        return set()

    try:
        mappings = json.loads(MAPPINGS_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return set()

    return {
        mapping["partId"]
        for mapping in mappings
        if (
            isinstance(mapping, dict)
            and mapping.get("boardId") == "leonardo"
            and mapping.get("partId")
        )
    }


def create_server() -> FastMCP:
    """Create an MCP server exposing tools backed by configured hardware."""
    mcp = FastMCP("Conductor Hardware Server")
    available_hardware = get_available_hardware()

    register_tools(mcp, available_hardware)
    register_resources(mcp, available_hardware)
    start_serial_bridge()

    return mcp


mcp = create_server()


if __name__ == "__main__":
    mcp.run()
