from __future__ import annotations

import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from fastmcp import Client
import anthropic

# -------------------------------------------------------------------
# Env / Globals
# -------------------------------------------------------------------
load_dotenv(".env.local")  # keep your current env layout

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-20241022")
# Path to the MCP server script in the mhacks25_server directory
MCP_SERVER = os.getenv("MCP_SERVER", "../../../mhacks25_server/server.py")
# Bearer token for your FastMCP deployment (if using cloud)
FASTMCP_BEARER_TOKEN = os.getenv("FASTMCP_BEARER_TOKEN")

if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY missing from .env.local")

anth = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

app = FastAPI(title="Mapping Registry + Agent", version="1.1.0")

# Allow your Next.js site to call this in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Models (existing)
# -------------------------------------------------------------------
class Mapping(BaseModel):
    id: str
    boardId: str
    partId: str
    role: str
    pins: List[int] = Field(default_factory=list)
    label: Optional[str] = None

class MappingBatch(BaseModel):
    mappings: List[Mapping] = Field(default_factory=list)

# -------------------------------------------------------------------
# Models (agent)
# -------------------------------------------------------------------
class ChatIn(BaseModel):
    text: str
    session_id: Optional[str] = "default"

# -------------------------------------------------------------------
# Storage (existing)
# -------------------------------------------------------------------
DATA_FILE = Path(__file__).with_name("mappings.json")

def load_all() -> List[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text())
    except Exception:
        return []

def save_all(items: List[dict]) -> None:
    DATA_FILE.write_text(json.dumps(items, indent=2))

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
        description = getattr(tool, "description", "")
        
        # FastMCP tools have input_schema as a standard attribute
        input_schema = getattr(tool, "input_schema", {})
        
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
                    "type": "input_image",
                    "image_data": data,
                    "mime_type": getattr(b, "mimeType", None) or getattr(b, "mime_type", None) or "image/png"
                })
            else:
                # best-effort fallback
                try:
                    blocks.append({"type": "text", "text": json.dumps(getattr(b, "__dict__", str(b)))})
                except Exception:
                    blocks.append({"type": "text", "text": str(b)})
    else:
        blocks.append({"type": "text", "text": "Tool returned no content."})

    ok = not getattr(result, "is_error", False)
    status = {"type": "text", "text": f"[tool {'ok' if ok else 'error'}]"}
    return {"content": [status] + blocks}

# -------------------------------------------------------------------
# Core: run one agent turn (ask Claude, run tools if requested, finalize)
# -------------------------------------------------------------------
async def run_agent_once(user_text: str) -> str:
    # Configure FastMCP client
    # For local server.py files, we don't need bearer tokens
    client_kwargs = {}
    
    # Only add bearer token for cloud deployments (https URLs)
    if FASTMCP_BEARER_TOKEN and MCP_SERVER.startswith("https://"):
        client_kwargs["headers"] = {"Authorization": f"Bearer {FASTMCP_BEARER_TOKEN}"}
    
    # Connect to the MCP server
    async with Client(MCP_SERVER, **client_kwargs) as mcp:
        # ensure server is reachable and enumerate tools
        await mcp.ping()
        tools = await mcp.list_tools()
        claude_tools = format_tools_for_claude(tools)

        # 1) Ask Claude what to do
        msg = anth.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": user_text}],
            tools=claude_tools,
            tool_choice={"type": "auto"},
        )

        # 2) If Claude decides to call tools, execute, then send back results
        if msg.stop_reason == "tool_use":
            tool_uses = [c for c in msg.content if getattr(c, "type", None) == "tool_use"]
            tool_results_content: List[Dict[str, Any]] = []

            for tu in tool_uses:
                try:
                    result = await mcp.call_tool(tu.name, tu.input)
                    tr = serialize_tool_result_for_claude(result)
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": tr["content"],
                    })
                except Exception as e:
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": [{"type": "text", "text": f"[tool error] {e}"}],
                        "is_error": True,
                    })

            # 3) Final natural-language answer
            final = anth.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": msg.content},          # includes tool_use blocks
                    {"role": "user", "content": tool_results_content},      # tool_result blocks
                ],
            )
            parts = [c.text for c in final.content if getattr(c, "type", None) == "text"]
            return ("".join(parts)).strip() or "(no reply)"
        else:
            # No tool call; just return text
            parts = [c.text for c in msg.content if getattr(c, "type", None) == "text"]
            return ("".join(parts)).strip() or "(no reply)"

# -------------------------------------------------------------------
# Routes (existing)
# -------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/mappings")
def get_mappings():
    return {"mappings": load_all()}

@app.post("/mappings", status_code=201)
def add_mappings(batch: MappingBatch):
    if not batch.mappings:
        raise HTTPException(400, "No mappings provided")
    current = load_all()
    # naive merge by id (replace if same id)
    ids = {m["id"] for m in current}
    for m in batch.mappings:
        d = m.model_dump()
        if m.id in ids:
            current = [d if x["id"] == m.id else x for x in current]
        else:
            current.append(d)
    save_all(current)
    return {"ok": True, "count": len(batch.mappings)}

@app.delete("/mappings/{mapping_id}")
def delete_mapping(mapping_id: str):
    current = load_all()
    new = [m for m in current if m.get("id") != mapping_id]
    if len(new) == len(current):
        raise HTTPException(404, "Mapping not found")
    save_all(new)
    return {"ok": True}

# -------------------------------------------------------------------
# New Routes (agent)
# -------------------------------------------------------------------
@app.get("/agent/health")
async def agent_health():
    # Basic checks: API key present and MCP server pings
    try:
        # Configure client with Bearer token if available
        client_kwargs = {}
        if FASTMCP_BEARER_TOKEN and MCP_SERVER.startswith("https://"):
            client_kwargs["headers"] = {"Authorization": f"Bearer {FASTMCP_BEARER_TOKEN}"}
        
        async with Client(MCP_SERVER, **client_kwargs) as mcp:
            await mcp.ping()
            tools = await mcp.list_tools()
        return {
            "ok": True, 
            "model": CLAUDE_MODEL, 
            "mcp_server": MCP_SERVER,
            "tools": [getattr(t, "name", str(t)) for t in tools]
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "mcp_server": MCP_SERVER}

@app.post("/agent/chat")
async def agent_chat(body: ChatIn):
    if not body.text.strip():
        raise HTTPException(400, "text is required")
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
    uvicorn.run(app, host="0.0.0.0", port=5057)
