# agent.py
"""
Replacement agent that:
- Presents MCP tools + resources to Claude (Anthropic).
- Allows Claude to request tool/resource calls.
- Executes tool/resource calls sequentially.
- Feeds each tool result back to Claude as an assistant message so Claude can
  chain multiple calls in one conversation (e.g., read sensor -> beep -> final answer).
- Normalizes various MCP return shapes and explicitly highlights "No value" responses.

Notes:
- This file assumes your existing MCP server and tools (server.py) are running.
- It preserves the (synchronous) Anthropic client usage pattern from your original file.
"""

import asyncio
import os
import json
import re
import base64
from typing import Any, Dict, List, Tuple
from fastmcp import Client
import anthropic
from dotenv import load_dotenv

load_dotenv(".env.local")
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY not found in .env.local")

# configuration
FULL_CHAT_LOG_PATH = "/Users/wenboxu/Documents/mhacks_25/frontend-wjsons/registry-server/chat_log.txt"
CLAUDE_MODEL = "claude-3-5-haiku-20241022"  # keep as you had it; change if needed


# -----------------------
# Helpers: format tools/resources (kept from your original file, lightly adapted)
# -----------------------
def format_tools_for_claude(mcp_tools: List[Any]) -> List[Dict[str, Any]]:
    claude_tools = []

    for tool in (mcp_tools or []):
        name = getattr(tool, "name", None) or getattr(tool, "id", None) or str(tool)
        description = (
            getattr(tool, "description", None)
            or getattr(tool, "title", None)
            or ""
        )

        input_schema = (
            getattr(tool, "input_schema", None)
            or getattr(tool, "inputSchema", None)
            or getattr(tool, "schema", None)
            or getattr(tool, "inputSchemaJson", None)
            or {}
        )

        properties = {}
        if isinstance(input_schema, dict) and "properties" in input_schema:
            properties = input_schema.get("properties", {})
        else:
            params = getattr(tool, "parameters", None) or getattr(tool, "params", None) or {}
            if isinstance(params, dict):
                for pname, pinfo in params.items():
                    ptype = pinfo.get("type", "string") if isinstance(pinfo, dict) else "string"
                    if ptype in ("int", "integer"):
                        properties[pname] = {"type": "integer", "description": f"Parameter: {pname}"}
                    elif ptype in ("float", "number"):
                        properties[pname] = {"type": "number", "description": f"Parameter: {pname}"}
                    else:
                        properties[pname] = {"type": "string", "description": f"Parameter: {pname}"}

        claude_tools.append({
            "name": name or "<unnamed_tool>",
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": list(properties.keys())
            }
        })
    return claude_tools

def sanitize_messages_for_claude(msgs):
    """
    Ensure each message's content is a string and strip trailing whitespace.
    Converts accidental non-string content to a compact string.
    """
    for m in msgs:
        c = m.get("content")
        if isinstance(c, (list, dict)):
            try:
                m["content"] = json.dumps(c, default=str)
            except Exception:
                m["content"] = str(c)
        elif not isinstance(c, str):
            m["content"] = str(c or "")
        # remove trailing whitespace/newlines (keeps leading whitespace intact)
        m["content"] = m["content"].rstrip()
    return msgs

def _safe_tool_name_from_uri(uri: Any) -> str:
    if uri is None:
        return "read_resource_unknown"
    uri_str = str(uri)
    safe = re.sub(r"[^0-9A-Za-z]+", "_", uri_str).strip("_")
    return f"read_resource_{safe or 'unknown'}"


def format_resources_for_claude(mcp_resources: List[Any]) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    claude_resources: List[Dict[str, Any]] = []
    tool_to_uri: Dict[str, str] = {}

    for res in (mcp_resources or []):
        raw_uri = getattr(res, "uri", None) or getattr(res, "id", None) or getattr(res, "name", None) or res
        if raw_uri is None:
            continue

        uri = str(raw_uri)
        title = getattr(res, "title", None) or getattr(res, "description", None) or ""
        description = getattr(res, "description", None) or title or f"Resource {uri}"

        tool_name = _safe_tool_name_from_uri(uri)
        tool_to_uri[tool_name] = uri

        claude_resources.append({
            "name": tool_name,
            "description": f"Read resource {uri}. {description}",
            "input_schema": {  # read-only: no parameters
                "type": "object",
                "properties": {},
                "required": []
            }
        })

    return claude_resources, tool_to_uri


# -----------------------
# Fetch resource helper (keeps robust fallbacks from your original)
# -----------------------
async def fetch_resource_from_mcp(mcp_client: Client, uri: str):
    """Try several common client methods to read a resource."""
    for method_name in ("read_resource", "get_resource", "call_resource", "get_resource_value"):
        method = getattr(mcp_client, method_name, None)
        if callable(method):
            try:
                maybe = method(uri)
                if asyncio.iscoroutine(maybe):
                    maybe = await maybe
                return maybe
            except TypeError:
                # try alternative signature
                try:
                    maybe2 = method(uri, {})
                    if asyncio.iscoroutine(maybe2):
                        maybe2 = await maybe2
                    return maybe2
                except Exception:
                    pass
            except Exception:
                # surface via caller
                raise
    raise RuntimeError("No supported resource-read method found on mcp_client (tried read_resource/get_resource/call_resource)")


# -----------------------
# Keep original serialize helper (useful for tool call results)
# -----------------------
def serialize_tool_result(result) -> dict:
    def ser_block(b):
        t = getattr(b, "type", None)
        if t == "text" and hasattr(b, "text"):
            return {"type": "text", "text": b.text}
        if t == "image" and hasattr(b, "data"):
            data = b.data
            if isinstance(data, (bytes, bytearray)):
                data = base64.b64encode(data).decode("utf-8")
            return {
                "type": "image",
                "mimeType": getattr(b, "mimeType", None) or getattr(b, "mime_type", None),
                "data": data,
            }
        if hasattr(b, "__dict__"):
            d = {k: v for k, v in b.__dict__.items() if not k.startswith("_")}
            for k, v in list(d.items()):
                try:
                    json.dumps(v)
                except TypeError:
                    d[k] = str(v)
            return d
        return str(b)

    payload = {}
    payload["ok"] = not getattr(result, "is_error", False)
    if hasattr(result, "content"):
        blocks = result.content
        payload["content"] = [ser_block(b) for b in (blocks or [])]
    else:
        # last resort: try to map common dict/list shapes
        try:
            json.dumps(result)
            payload["content"] = [result]
        except Exception:
            payload["content"] = [str(result)]
    return payload


# -----------------------
# Normalizer & execution helper
# -----------------------
def _extract_text_like(obj: Any) -> List[str]:
    """
    Return a list of candidate text strings found inside obj.
    This is a best-effort extractor for many shapes returned by MCP.
    """
    out = []

    try:
        # If it's a plain string
        if isinstance(obj, str):
            out.append(obj)
            return out

        # If it's a dict-like
        if isinstance(obj, dict):
            # look for common keys
            for k in ("text", "value", "reading", "distance", "payload", "content"):
                if k in obj and obj[k] is not None:
                    out.append(str(obj[k]))
            # also flatten any nested simple strings
            for v in obj.values():
                if isinstance(v, (str, int, float)):
                    out.append(str(v))
            return out

        # If it's a list/tuple, recurse
        if isinstance(obj, (list, tuple)):
            for el in obj:
                out.extend(_extract_text_like(el))
            return out

        # If it's an object with attributes
        if hasattr(obj, "__dict__"):
            d = obj.__dict__
            for k in ("text", "value", "reading", "distance"):
                if k in d and d[k] is not None:
                    out.append(str(d[k]))
            # fallback: stringify
            out.append(str(obj))
            return out

        # fallback to str()
        out.append(str(obj))
        return out
    except Exception:
        try:
            out.append(str(obj))
        except Exception:
            out.append("<unserializable object>")
        return out


def normalize_mcp_result(raw: Any) -> Dict[str, Any]:
    """
    Convert the raw MCP return into a small canonical dict:
      {
        "ok": bool,
        "summary": str,     # short, first useful text-like piece
        "blocks": list,     # list of small dicts describing blocks found
        "raw": str          # safe string form of the raw object
      }
    """
    out = {"ok": True, "summary": "", "blocks": [], "raw": None}
    try:
        # If it's already a serialized tool result (dict with "content")
        if isinstance(raw, dict) and "content" in raw and isinstance(raw["content"], (list, tuple)):
            # content may contain dicts or strings
            for c in raw["content"]:
                if isinstance(c, dict):
                    out["blocks"].append(c)
                    # attempt to get text-like candidate
                    for k in ("text", "value", "reading", "distance"):
                        if k in c and c[k] is not None:
                            out["summary"] = str(c[k])
                            break
                else:
                    out["blocks"].append({"type": "raw", "value": str(c)})
            out["ok"] = raw.get("ok", True)
        else:
            # try to pull text-like pieces from raw
            texts = _extract_text_like(raw)
            for t in texts:
                # skip blank
                if t is None:
                    continue
                out["blocks"].append({"type": "text", "text": t})
            if texts:
                out["summary"] = texts[0]
            # set ok flag if obj has is_error attribute
            if hasattr(raw, "is_error"):
                out["ok"] = not getattr(raw, "is_error")
        # raw string fallback
        try:
            out["raw"] = json.dumps(raw, default=str)
        except Exception:
            out["raw"] = str(raw)
    except Exception as e:
        out["blocks"].append({"type": "error", "text": f"Error normalizing result: {e}"})
        out["raw"] = str(raw)
        out["ok"] = False

    # final heuristic: if summary still empty, pick first non-empty block text
    if not out["summary"]:
        for b in out["blocks"]:
            if isinstance(b, dict) and b.get("text"):
                out["summary"] = b.get("text")
                break

    return out


async def execute_tool_or_resource(mcp_client: Client, tool_name: str, tool_input: Dict[str, Any], resource_tool_map: Dict[str, str]) -> Dict[str, Any]:
    """
    Execute a tool (via mcp_client.call_tool) or read a resource (via fetch_resource_from_mcp).
    Returns normalized result dict from normalize_mcp_result.
    """
    try:
        if tool_name in resource_tool_map:
            uri = resource_tool_map[tool_name]
            raw = await fetch_resource_from_mcp(mcp_client, uri)
            return normalize_mcp_result(raw)
        else:
            # call normal tool
            result = await mcp_client.call_tool(tool_name, tool_input or {})
            # try to serialize first
            ser = serialize_tool_result(result)
            return normalize_mcp_result(ser)
    except Exception as e:
        return {"ok": False, "summary": f"Exception while executing {tool_name}: {e}", "blocks": [{"type": "error", "text": str(e)}], "raw": str(e)}


# -----------------------
# Main program
# -----------------------
async def main():
    mcp_client = Client("server.py")

    try:
        claude_client = anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        print(f"Error initializing Anthropic client: {e}")
        return

    async with mcp_client:
        print("Pinging MCP server...")
        try:
            await mcp_client.ping()
            print("Ping successful.\n")
        except Exception as e:
            print(f"Warning: ping failed: {e}\nContinuing — server may still accept calls.")

        print("Fetching available tools from MCP server...")
        try:
            available_mcp_tools = await mcp_client.list_tools()
        except Exception as e:
            print(f"Error listing tools: {e}")
            available_mcp_tools = []

        print(f"Found tools: {[getattr(t,'name', str(t)) for t in available_mcp_tools]}\n")

        available_mcp_resources = []
        try:
            if hasattr(mcp_client, "list_resources"):
                available_mcp_resources = await mcp_client.list_resources()
            elif hasattr(mcp_client, "list_resources_async"):
                available_mcp_resources = await mcp_client.list_resources_async()
            else:
                maybe = getattr(mcp_client, "list_resources", None)
                if callable(maybe):
                    maybe_result = maybe()
                    if asyncio.iscoroutine(maybe_result):
                        available_mcp_resources = await maybe_result
        except Exception as e:
            print(f"Warning: could not fetch resources list from MCP server: {e}")
            available_mcp_resources = []

        print(f"Found resources: {[str(getattr(r,'uri', getattr(r,'id', r))) for r in available_mcp_resources]}\n")

        # Prepare Claude-compatible tool/resource descriptions
        claude_formatted_tools = format_tools_for_claude(available_mcp_tools)
        claude_formatted_resources, resource_tool_map = format_resources_for_claude(available_mcp_resources)
        tools_payload = claude_formatted_tools + claude_formatted_resources

        # Read chat log content
        chat_log_content = ""
        try:
            with open(FULL_CHAT_LOG_PATH, 'r') as f:
                chat_log_content = f.read().strip()
                print("--- Chat Log Content ---")
                print(chat_log_content)
                print("--- End of Chat Log ---")
        except FileNotFoundError:
            print(f"Error: The chat log file was not found at {FULL_CHAT_LOG_PATH}")
        except Exception as e:
            print(f"An error occurred while trying to read the file: {e}")

        # Initialize conversation with chat log content
        messages_for_claude = [{"role": "user", "content": chat_log_content}] if chat_log_content else []

        # Loop safely with a maximum iteration guard to avoid infinite cycles (e.g., 10 iterations)
        MAX_ITER = 12
        iter_count = 0

        while True:
            iter_count += 1
            if iter_count > MAX_ITER:
                print(f"Reached max iterations ({MAX_ITER}). Aborting to avoid loop.")
                break

            print(f"\n--- Sending conversation to Claude (iteration {iter_count}) ---")
            try:
                messages_for_claude = sanitize_messages_for_claude(messages_for_claude)
                message = claude_client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=1024,
                    messages=messages_for_claude,
                    tools=tools_payload,
                    tool_choice={"type": "auto"}
                )
            except Exception as e:
                print(f"An error occurred with the Claude API call: {e}")
                return

            # If Claude did not request a tool/resource, print final response and stop
            if getattr(message, "stop_reason", None) != "tool_use":
                text_blocks = [b for b in message.content if getattr(b, "type", None) == "text"]
                final_response = text_blocks[0].text if text_blocks else str(message)
                print("\nFinal model response (no tool call):\n", final_response)
                break

            # Collect tool_use blocks (may be multiple)
            tool_calls = [c for c in message.content if getattr(c, "type", None) == "tool_use"]
            if not tool_calls:
                print("stop_reason indicates tool_use but no tool_use blocks found. Aborting.")
                break

            # Execute each tool/resource in the order Claude requested and append result messages
            for tool_call in tool_calls:
                tool_name = getattr(tool_call, "name", None)
                tool_input = getattr(tool_call, "input", None) or {}

                print(f"\nClaude requested tool/resource: '{tool_name}' with input: {tool_input}")

                normalized = await execute_tool_or_resource(mcp_client, tool_name, tool_input, resource_tool_map)

                # Create a short, clear tool-result text for Claude to consume
                summary = normalized.get("summary") or ""
                blocks = normalized.get("blocks") or []
                raw = normalized.get("raw") or ""

                # Make "No value" explicit so Claude doesn't mistake it for a numeric reading
                note = ""
                if isinstance(summary, str) and "no value" in summary.lower():
                    note = "[NOTE: sensor returned NO VALUE — check connection/polling on MCP server]"

                result_text = (
                    f"[TOOL_RESULT]\n"
                    f"name={tool_name}\n"
                    f"ok={normalized.get('ok')}\n"
                    f"summary={summary}\n"
                    f"{note}\n"
                    f"blocks={json.dumps(blocks, default=str)}\n"
                    f"raw={raw}\n"
                )
                result_text = result_text.rstrip()

                print("--- Tool execution normalized result ---")
                print(result_text)
                print("----------------------------------------")

                # Append result back to conversation as an assistant message so Claude can plan further calls
                messages_for_claude.append({"role": "assistant", "content": result_text})

            # loop and send the updated conversation back to Claude (it may call more tools or finish)

        # end async with mcp_client


if __name__ == "__main__":
    print("--- Make sure your server.py is running in a separate terminal ---")
    asyncio.run(main())
