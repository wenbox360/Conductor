from __future__ import annotations

import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

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
# Boilerplate Code Generation
# -------------------------------------------------------------------
def get_actual_pin_number(board_id: str, board_position: int) -> int:
    """Convert board position to actual pin number for Arduino boards"""
    # Arduino Leonardo pin mapping (board position -> actual pin)
    if board_id == 'leonardo':
        leonardo_mapping = {
            # Top row (left to right): SCL SDA AREF GND 13 12 11 10 9 8 7 6 5 4 3 2 1 0
            5: 13, 6: 12, 7: 11, 8: 10, 9: 9, 10: 8, 11: 7, 12: 6, 
            13: 5, 14: 4, 15: 3, 16: 2, 17: 1, 18: 0,
            # Bottom row analog pins
            26: 'A0', 27: 'A1', 28: 'A2', 29: 'A3', 30: 'A4', 31: 'A5'
        }
        return leonardo_mapping.get(board_position, board_position)
    
    # For Raspberry Pi or other boards, use the board position as-is
    return board_position

def generate_pin_definitions(mappings: List[Mapping]) -> List[str]:
    """Generate #define statements for pins from mappings"""
    pin_list = []
    for mapping in mappings:
        if mapping.pins:  # Only if pins are defined
            # The mapping now already contains the actual pin number
            actual_pin = mapping.pins[0]
            pin_str = f"#define {mapping.partId.upper()}_PIN {actual_pin}"
            pin_list.append(pin_str)
    return pin_list

def get_boilerplate_code() -> str:
    """Load the boilerplate C code template"""
    boilerplate_path = Path(__file__).parent.parent.parent / "boilerplate" / "boilerplate.c"
    if boilerplate_path.exists():
        return boilerplate_path.read_text()
    else:
        # Fallback boilerplate if file doesn't exist
        return '''#include <Servo.h>

Servo turretServo;

char inputBuffer[32];     // buffer for incoming serial data
byte bufferIndex = 0;

unsigned long lastIrSend = 0;    // timer for IR reporting
const unsigned long irInterval = 200; // send IR data every 200ms

void setup() {
  Serial.begin(9600);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  turretServo.attach(SERVO_PIN);
}

void servo_write(int angle) {
  turretServo.write(angle);
}

int irSensorReading() {
  return analogRead(IR_PIN);
}

void buzzer_duration(int duration) {
  tone(BUZZER_PIN, 1000);
  delay(duration);
  noTone(BUZZER_PIN);
}

void led_on() {
  digitalWrite(LED_PIN, HIGH);
}

void led_off() {
  digitalWrite(LED_PIN, LOW);
}

void processCommand(char *cmd) {
  // Find comma if present
  char *comma = strchr(cmd, ',');
  int command = 0;
  int param   = 0;

  if (comma) {
    *comma = '\\0'; // split string into two parts
    command = atoi(cmd);
    param   = atoi(comma + 1);
  } else {
    command = atoi(cmd);
  }

  // ---- Command handling ----
  if (command == 2) {           // Piezo test (no param)
    buzzer_duration(200);
    Serial.println("A");
  }
  else if (command == 20) {     // Servo write (needs param)
    servo_write(param);
    Serial.println("A");
  }
  else if (command == 30) {     // LED write (needs param)
    if (param == 1) led_on();
    else led_off();
    Serial.println("A");
  }
  else {
    Serial.println("E");        // Unknown command
  }
}

void loop() {
  // Handle incoming serial commands
  while (Serial.available() > 0) {
    char inChar = (char)Serial.read();

    if (inChar == ';') { // end of command
      inputBuffer[bufferIndex] = '\\0';  // null terminate
      processCommand(inputBuffer);
      bufferIndex = 0;
    }
    else {
      if (bufferIndex < sizeof(inputBuffer) - 1) {
        inputBuffer[bufferIndex++] = inChar;
      }
    }
  }

  // ---- Always stream IR values ----
  unsigned long now = millis();
  if (now - lastIrSend >= irInterval) {
    lastIrSend = now;
    int irValue = irSensorReading();
    Serial.print("40,");
    Serial.println(irValue);
  }
}'''

def generate_raspberry_pi_code(mappings: List[Mapping], board_id: str) -> str:
    """Generate Python code for Raspberry Pi"""
    code_lines = [
        f"# Generated Python code for {board_id}",
        "# Hardware control script",
        "",
        "import RPi.GPIO as GPIO",
        "import time",
        "import serial",
        "import json",
        "",
        "# Pin definitions",
    ]
    
    # Add pin definitions
    for mapping in mappings:
        if mapping.pins:
            pin_name = f"{mapping.partId.upper()}_PIN"
            # The mapping now already contains the actual pin number
            actual_pin = mapping.pins[0]
            code_lines.append(f"{pin_name} = {actual_pin}  # {mapping.label or mapping.role}")
    
    code_lines.extend([
        "",
        "# GPIO setup",
        "GPIO.setmode(GPIO.BCM)",
        "GPIO.setwarnings(False)",
        "",
        "# Setup pins based on part types",
    ])
    
    # Setup pins based on part types
    for mapping in mappings:
        if mapping.pins:
            pin_name = f"{mapping.partId.upper()}_PIN"
            if mapping.partId in ['led', 'buzzer', 'relay']:
                code_lines.append(f"GPIO.setup({pin_name}, GPIO.OUT)")
            elif mapping.partId in ['button', 'digital_sensor']:
                code_lines.append(f"GPIO.setup({pin_name}, GPIO.IN, pull_up_down=GPIO.PUD_UP)")
            elif mapping.partId == 'hcsr04':
                if mapping.role == 'Trigger':
                    code_lines.append(f"GPIO.setup({pin_name}, GPIO.OUT)")
                elif mapping.role == 'Echo':
                    code_lines.append(f"GPIO.setup({pin_name}, GPIO.IN)")
    
    code_lines.extend([
        "",
        "def cleanup():",
        "    \"\"\"Clean up GPIO pins\"\"\"",
        "    GPIO.cleanup()",
        "",
        "def main():",
        "    \"\"\"Main control loop\"\"\"",
        "    try:",
        "        print(f'Hardware controller started for {board_id}')",
        "        print('Available pins:')",
    ])
    
    # Print available pins
    for mapping in mappings:
        if mapping.pins:
            code_lines.append(f"        print('  {mapping.partId} ({mapping.role}): GPIO {mapping.pins[0]}')")
    
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

@app.post("/generate-code")
def generate_code(request: CodeGenerationRequest):
    """Generate code from mappings (Python for Pi, Arduino for Arduino boards)"""
    if not request.mappings:
        raise HTTPException(400, "No mappings provided")
    
    try:
        code, file_extension = generate_code_for_board(request.mappings, request.boardId)
        return {
            "ok": True,
            "code": code,
            "boardId": request.boardId,
            "mappingCount": len(request.mappings),
            "fileExtension": file_extension
        }
    except Exception as e:
        raise HTTPException(500, f"Code generation failed: {str(e)}")

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
