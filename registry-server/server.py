from __future__ import annotations

import os
import json
import base64
import importlib.util
import re
import sys
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from fastmcp import Client
from fastmcp.exceptions import ToolError
import anthropic

SERVICE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_DIR.parent
load_dotenv(SERVICE_DIR / ".env.local")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
FASTMCP_BEARER_TOKEN = os.getenv("FASTMCP_BEARER_TOKEN")

configured_mcp_server = os.getenv("MCP_SERVER")
if configured_mcp_server and not configured_mcp_server.startswith(("http://", "https://")):
    MCP_SERVER = str((SERVICE_DIR / configured_mcp_server).resolve())
else:
    MCP_SERVER = configured_mcp_server or None

_local_mcp_module: Any = None

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app = FastAPI(title="Conductor Registry and Agent", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_local_mcp_module():
    """Load the bundled MCP server once so its serial bridge remains persistent."""
    global _local_mcp_module
    if _local_mcp_module is not None:
        return _local_mcp_module

    server_directory = REPO_ROOT / "mcp-server"
    server_path = server_directory / "server.py"
    module_name = "conductor_hardware_server"
    spec = importlib.util.spec_from_file_location(module_name, server_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load bundled MCP server at {server_path}")

    if str(server_directory) not in sys.path:
        sys.path.insert(0, str(server_directory))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _local_mcp_module = module
    return module


def create_mcp_client() -> Client:
    """Create a client for a configured remote server or the bundled in-memory server."""
    target = MCP_SERVER or load_local_mcp_module().create_server()
    client_kwargs: Dict[str, Any] = {}
    if (
        FASTMCP_BEARER_TOKEN
        and isinstance(target, str)
        and target.startswith("https://")
    ):
        client_kwargs["auth"] = FASTMCP_BEARER_TOKEN
    return Client(target, **client_kwargs)

# -------------------------------------------------------------------
# Models (existing)
# -------------------------------------------------------------------
class Mapping(BaseModel):
    id: str
    boardId: str
    partId: str
    role: str
    pins: List[Any] = Field(default_factory=list)  # Can be numbers or strings like 'A0', 'SDA'
    label: Optional[str] = None

class MappingBatch(BaseModel):
    mappings: List[Mapping] = Field(default_factory=list)

class CodeGenerationRequest(BaseModel):
    mappings: List[Mapping] = Field(default_factory=list)
    boardId: str

# -------------------------------------------------------------------
# Models (agent)
# -------------------------------------------------------------------
class ChatIn(BaseModel):
    text: str
    session_id: Optional[str] = "default"

class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)

# -------------------------------------------------------------------
# Storage (existing)
# -------------------------------------------------------------------
DATA_FILE = Path(__file__).with_name("mappings.json")
DATA_LOCK = threading.RLock()

def load_all() -> List[dict]:
    with DATA_LOCK:
        if not DATA_FILE.exists():
            return []
        try:
            items = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Unable to read mapping registry: {error}") from error
        if not isinstance(items, list):
            raise RuntimeError("Mapping registry must contain a JSON array")
        return items

def save_all(items: List[dict]) -> None:
    with DATA_LOCK:
        temporary_file = DATA_FILE.with_suffix(".json.tmp")
        temporary_file.write_text(json.dumps(items, indent=2), encoding="utf-8")
        temporary_file.replace(DATA_FILE)


def ensure_unique_mappings(mappings: List[Mapping | dict]) -> None:
    """Reject IDs or component types that would make routing/codegen ambiguous."""
    seen_ids: set[str] = set()
    seen_hardware: set[tuple[str, str]] = set()
    for mapping in mappings:
        if isinstance(mapping, Mapping):
            mapping_id = mapping.id
            board_id = mapping.boardId
            part_id = mapping.partId
        else:
            mapping_id = str(mapping.get("id", ""))
            board_id = str(mapping.get("boardId", ""))
            part_id = str(mapping.get("partId", ""))

        if mapping_id in seen_ids:
            raise HTTPException(400, f"Duplicate mapping ID: {mapping_id}")
        seen_ids.add(mapping_id)

        hardware_key = (board_id, part_id)
        if hardware_key in seen_hardware:
            raise HTTPException(
                400,
                f"{part_id} is already mapped on {board_id}",
            )
        seen_hardware.add(hardware_key)

# -------------------------------------------------------------------
# Firmware generation
# -------------------------------------------------------------------
MULTI_PIN_NAMES = {
    "hcsr04": ("TRIGGER", "ECHO"),
}


def identifier(value: str) -> str:
    """Return a safe C/Python identifier derived from a hardware ID."""
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return normalized or "HARDWARE"


def mapping_pin_names(mapping: Mapping) -> List[str]:
    """Return stable, unique identifiers for every pin in a mapping."""
    part_name = identifier(mapping.partId)
    if len(mapping.pins) == 1:
        return [f"{part_name}_PIN"]

    known_names = MULTI_PIN_NAMES.get(mapping.partId.lower(), ())
    return [
        f"{part_name}_{known_names[index] if index < len(known_names) else f'PIN_{index + 1}'}"
        for index in range(len(mapping.pins))
    ]


def generate_pin_definitions(mappings: List[Mapping]) -> List[str]:
    """Generate one C preprocessor definition for every configured pin."""
    definitions: List[str] = []
    for mapping in mappings:
        for pin_name, actual_pin in zip(mapping_pin_names(mapping), mapping.pins):
            definitions.append(f"#define {pin_name} {actual_pin}")
    return definitions

def get_boilerplate_code() -> str:
    """Load the versioned Arduino firmware template."""
    boilerplate_path = REPO_ROOT / "firmware" / "boilerplate.c"
    return boilerplate_path.read_text()

def generate_raspberry_pi_code(mappings: List[Mapping], board_id: str) -> str:
    """Generate a runnable Raspberry Pi GPIO scaffold using physical pin numbers."""
    code_lines = [
        f"# Generated Python code for {board_id}",
        "# Hardware control script",
        "",
        "import RPi.GPIO as GPIO",
        "import time",
        "",
        "# Pin definitions",
    ]

    for mapping in mappings:
        for pin_name, actual_pin in zip(mapping_pin_names(mapping), mapping.pins):
            code_lines.append(
                f"{pin_name} = {actual_pin!r}  # {mapping.label or mapping.role}"
            )

    code_lines.extend([
        "",
        "# GPIO setup",
        "GPIO.setmode(GPIO.BOARD)",
        "GPIO.setwarnings(False)",
        "",
        "# Setup pins based on part types",
    ])

    for mapping in mappings:
        pin_names = mapping_pin_names(mapping)
        part_id = mapping.partId.lower()
        if part_id in {"led", "relay", "piezo_buzzer", "micro_servo_sg90"}:
            code_lines.extend(f"GPIO.setup({name}, GPIO.OUT)" for name in pin_names)
        elif part_id == "hcsr04" and len(pin_names) >= 2:
            code_lines.append(f"GPIO.setup({pin_names[0]}, GPIO.OUT)")
            code_lines.append(f"GPIO.setup({pin_names[1]}, GPIO.IN)")
        else:
            code_lines.extend(
                f"GPIO.setup({name}, GPIO.IN, pull_up_down=GPIO.PUD_UP)"
                for name in pin_names
            )

    code_lines.extend([
        "",
        "def cleanup():",
        "    \"\"\"Clean up GPIO pins\"\"\"",
        "    GPIO.cleanup()",
        "",
        "def main():",
        "    \"\"\"Main control loop\"\"\"",
        "    try:",
        f"        print('Hardware controller started for {board_id}')",
        "        print('Available pins:')",
    ])

    for mapping in mappings:
        for actual_pin in mapping.pins:
            code_lines.append(
                f"        print('  {mapping.partId} ({mapping.role}): physical pin {actual_pin}')"
            )

    code_lines.extend([
        "",
        "        # Main control loop",
        "        while True:",
        "            # Add your control logic here",
        "            time.sleep(0.1)",
        "",
        "    except KeyboardInterrupt:",
        "        print('\\nShutting down...')",
        "    finally:",
        "        cleanup()",
        "",
        "if __name__ == '__main__':",
        "    main()",
    ])

    return "\n".join(code_lines)

def generate_arduino_code(mappings: List[Mapping], board_id: str) -> str:
    """Generate complete Arduino code with pin definitions and boilerplate"""
    pin_definitions = generate_pin_definitions(mappings)
    boilerplate = get_boilerplate_code()

    # Combine pin definitions with boilerplate
    code_lines = [
        f"// Generated Arduino code for {board_id}",
        "// Pin Definitions",
    ]

    for pin_def in pin_definitions:
        code_lines.append(pin_def)

    code_lines.extend(["", boilerplate])

    return "\n".join(code_lines)

def generate_code_for_board(mappings: List[Mapping], board_id: str) -> tuple[str, str]:
    """Generate code appropriate for the board type. Returns (code, file_extension)"""
    if board_id.startswith('pi') or 'raspberry' in board_id.lower():
        # Raspberry Pi - generate Python code
        code = generate_raspberry_pi_code(mappings, board_id)
        return code, "py"
    else:
        # Arduino - generate Arduino code
        code = generate_arduino_code(mappings, board_id)
        return code, "ino"

# -------------------------------------------------------------------
# Helper: format MCP tools for Claude
# -------------------------------------------------------------------
def format_tools_for_claude(mcp_tools: List[Any]) -> List[Dict[str, Any]]:
    """
    Convert FastMCP Tool objects to Claude-compatible format.
    FastMCP tools have a more standardized structure.
    """
    tools_out: List[Dict[str, Any]] = []
    for tool in mcp_tools:
        # FastMCP tools should have standard attributes
        name = getattr(tool, "name", "unnamed_tool")
        description = getattr(tool, "description", "") or ""

        # FastMCP tools have input_schema as a standard attribute
        input_schema = (
            getattr(tool, "input_schema", None)
            or getattr(tool, "inputSchema", None)
            or {}
        )

        # If input_schema is properly formatted, use it directly
        if isinstance(input_schema, dict) and "properties" in input_schema:
            schema = input_schema
        else:
            # Fallback: create basic schema structure
            schema = {
                "type": "object",
                "properties": {},
                "required": []
            }

            # Try to extract parameters if available
            if hasattr(tool, "parameters"):
                params = getattr(tool, "parameters", {})
                if isinstance(params, dict):
                    for pname, pinfo in params.items():
                        ptype = "string"
                        pdesc = f"Parameter: {pname}"

                        if isinstance(pinfo, dict):
                            ptype = pinfo.get("type", "string")
                            pdesc = pinfo.get("description", pdesc)

                            # Normalize type names
                            if ptype in ("int", "integer"):
                                ptype = "integer"
                            elif ptype in ("float", "number"):
                                ptype = "number"
                            elif ptype == "bool":
                                ptype = "boolean"

                        schema["properties"][pname] = {
                            "type": ptype,
                            "description": pdesc
                        }

                        # Add to required if specified
                        if isinstance(pinfo, dict) and pinfo.get("required", False):
                            schema["required"].append(pname)

        tools_out.append({
            "name": name,
            "description": description,
            "input_schema": schema
        })
    return tools_out

# -------------------------------------------------------------------
# Helper: convert MCP tool result for Claude tool_result
# -------------------------------------------------------------------
def serialize_tool_result_for_claude(result) -> Dict[str, Any]:
    blocks: List[Dict[str, Any]] = []

    if hasattr(result, "content") and result.content:
        for b in result.content:
            t = getattr(b, "type", None)
            if t == "text" and hasattr(b, "text"):
                blocks.append({"type": "text", "text": b.text})
            elif t == "image" and hasattr(b, "data"):
                data = b.data
                if isinstance(data, (bytes, bytearray)):
                    data = base64.b64encode(data).decode("utf-8")
                blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": (
                            getattr(b, "mimeType", None)
                            or getattr(b, "mime_type", None)
                            or "image/png"
                        ),
                        "data": data,
                    },
                })
            else:
                # best-effort fallback
                try:
                    blocks.append({"type": "text", "text": json.dumps(getattr(b, "__dict__", str(b)))})
                except Exception:
                    blocks.append({"type": "text", "text": str(b)})
    else:
        blocks.append({"type": "text", "text": "Tool returned no content."})

    is_error = bool(
        getattr(result, "isError", False) or getattr(result, "is_error", False)
    )
    ok = not is_error
    status = {"type": "text", "text": f"[tool {'ok' if ok else 'error'}]"}
    return {"content": [status] + blocks, "isError": is_error}

# -------------------------------------------------------------------
# Core: run one agent turn (ask Claude, run tools if requested, finalize)
# -------------------------------------------------------------------
async def run_agent_once(user_text: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("Agent chat requires ANTHROPIC_API_KEY in registry-server/.env.local")

    anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    async with create_mcp_client() as mcp:
        await mcp.ping()
        tools = await mcp.list_tools()
        claude_tools = format_tools_for_claude(tools)
        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": user_text}
        ]
        tool_options: Dict[str, Any] = {}
        if claude_tools:
            tool_options = {
                "tools": claude_tools,
                "tool_choice": {"type": "auto"},
            }

        for _ in range(6):
            message = await anthropic_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                messages=messages,
                **tool_options,
            )
            messages.append({"role": "assistant", "content": message.content})

            if message.stop_reason != "tool_use":
                parts = [
                    content.text
                    for content in message.content
                    if getattr(content, "type", None) == "text"
                ]
                return "".join(parts).strip() or "(no reply)"

            tool_uses = [
                content
                for content in message.content
                if getattr(content, "type", None) == "tool_use"
            ]
            tool_results_content: List[Dict[str, Any]] = []

            for tool_use in tool_uses:
                try:
                    result = await mcp.call_tool(tool_use.name, tool_use.input)
                    serialized = serialize_tool_result_for_claude(result)
                    tool_result = {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": serialized["content"],
                    }
                    if serialized["isError"]:
                        tool_result["is_error"] = True
                    tool_results_content.append(tool_result)
                except Exception as error:
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": [
                            {"type": "text", "text": f"[tool error] {error}"}
                        ],
                        "is_error": True,
                    })

            messages.append({"role": "user", "content": tool_results_content})

    raise RuntimeError("Agent exceeded the maximum number of tool-call rounds")

# -------------------------------------------------------------------
# Routes (existing)
# -------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True, "agent_configured": bool(ANTHROPIC_API_KEY)}

@app.get("/tools")
async def list_mcp_tools():
    """Return the tools exposed by the configured MCP hardware server."""
    try:
        async with create_mcp_client() as mcp:
            tools = await mcp.list_tools()
        return {"tools": format_tools_for_claude(tools)}
    except Exception as error:
        raise HTTPException(502, f"MCP server unavailable: {error}") from error

@app.post("/call")
async def call_mcp_tool(request: ToolCall):
    """Invoke a named MCP tool and return a JSON-safe result."""
    try:
        async with create_mcp_client() as mcp:
            result = await mcp.call_tool(request.name, request.args)
        serialized = serialize_tool_result_for_claude(result)
    except ToolError as error:
        raise HTTPException(422, str(error)) from error
    except Exception as error:
        raise HTTPException(502, f"MCP tool call failed: {error}") from error

    if serialized["isError"]:
        raise HTTPException(422, "MCP tool rejected the request")
    return serialized

@app.get("/mappings")
def get_mappings():
    return {"mappings": load_all()}

@app.post("/mappings", status_code=201)
def replace_mappings(batch: MappingBatch):
    """Replace all mappings with the provided batch (complete replacement)."""
    ensure_unique_mappings(batch.mappings)
    new_mappings = [m.model_dump() for m in batch.mappings]
    save_all(new_mappings)
    return {"ok": True, "count": len(batch.mappings)}

@app.patch("/mappings", status_code=200)
def add_mappings(batch: MappingBatch):
    """Add/merge mappings with existing ones (merge operation)."""
    if not batch.mappings:
        raise HTTPException(400, "No mappings provided")
    with DATA_LOCK:
        current = load_all()
        ids = {m["id"] for m in current}
        for m in batch.mappings:
            data = m.model_dump()
            if m.id in ids:
                current = [data if item["id"] == m.id else item for item in current]
            else:
                current.append(data)
        ensure_unique_mappings(current)
        save_all(current)
    return {"ok": True, "count": len(batch.mappings)}

@app.delete("/mappings/{mapping_id}")
def delete_mapping(mapping_id: str):
    with DATA_LOCK:
        current = load_all()
        new = [m for m in current if m.get("id") != mapping_id]
        if len(new) == len(current):
            raise HTTPException(404, "Mapping not found")
        save_all(new)
    return {"ok": True}

@app.post("/generate-code")
def generate_code(request: CodeGenerationRequest):
    """Generate code from mappings (Python for Pi, Arduino for Arduino boards)"""
    board_mappings = [
        mapping for mapping in request.mappings if mapping.boardId == request.boardId
    ]
    if not board_mappings:
        raise HTTPException(400, "No mappings provided for the selected board")
    ensure_unique_mappings(board_mappings)

    try:
        code, file_extension = generate_code_for_board(board_mappings, request.boardId)
        return {
            "ok": True,
            "code": code,
            "boardId": request.boardId,
            "mappingCount": len(board_mappings),
            "fileExtension": file_extension
        }
    except Exception as e:
        raise HTTPException(500, f"Code generation failed: {str(e)}")

# -------------------------------------------------------------------
# New Routes (agent)
# -------------------------------------------------------------------
@app.get("/agent/health")
async def agent_health():
    try:
        async with create_mcp_client() as mcp:
            await mcp.ping()
            tools = await mcp.list_tools()
        return {
            "ok": True,
            "agent_configured": bool(ANTHROPIC_API_KEY),
            "model": CLAUDE_MODEL,
            "tools": [getattr(t, "name", str(t)) for t in tools]
        }
    except Exception as e:
        return {"ok": False, "agent_configured": bool(ANTHROPIC_API_KEY), "error": str(e)}

@app.post("/agent/chat")
async def agent_chat(body: ChatIn):
    if not body.text.strip():
        raise HTTPException(400, "text is required")
    if not ANTHROPIC_API_KEY:
        raise HTTPException(503, "Agent chat is not configured")
    try:
        reply = await run_agent_once(body.text)
        return {"reply": reply}
    except anthropic.APIStatusError as e:
        # Anthropic-specific error path
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        # Generic error
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------------
# Startup
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5057)
