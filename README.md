# Conductor

Conductor is a no-code embedded-development platform that turns visual hardware configurations and natural-language requests into discoverable MCP tools, generated Arduino firmware, and Raspberry Pi GPIO scaffolds.

**1st Place — Embedder (Embedded Systems) Track, MHacks 2025**

[View the project on Devpost](https://devpost.com/software/temp-cbdzve)

## What it does

- Maps components onto Raspberry Pi and Arduino pins through an interactive web interface.
- Exposes supported Leonardo mappings as discoverable MCP tools and sensor resources.
- Routes natural-language requests through an agent that selects and invokes hardware actions.
- Generates board-specific Arduino or Raspberry Pi code from saved pin configurations.
- Bridges MCP calls to Arduino hardware through a reconnecting serial command worker.

The current control path targets an Arduino Leonardo. Raspberry Pi mappings are supported by the visual mapper and Python code generator, but do not register serial MCP controls.

## Architecture

```text
Next.js UI
   │
   ▼
FastAPI registry + agent ──► code generator ──► Arduino / Raspberry Pi source
   │
   ▼
FastMCP hardware server ──► serial bridge ──► Arduino hardware
```

Saved mappings are the shared contract between the UI, firmware generator, and MCP server. The server exposes only tools backed by configured hardware, while the agent uses those tool schemas to translate user intent into device actions.

## Repository layout

| Path | Purpose |
| --- | --- |
| `web/` | Next.js interface for pin mapping, tool discovery, chat, and code generation |
| `registry-server/` | FastAPI mapping registry, firmware generator, and MCP-aware agent |
| `mcp-server/` | FastMCP tools/resources and the serial hardware bridge |
| `firmware/` | Arduino serial-protocol firmware template |

## Local development

### Prerequisites

- Node.js 20.19+ (LTS)
- Python 3.11+
- Optional: Arduino Leonardo connected over serial

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r mcp-server/requirements.txt -r registry-server/requirements.txt

cd web
npm ci
cd ..
```

### 2. Configure the services

```bash
cp registry-server/.env.example registry-server/.env.local
cp mcp-server/.env.example mcp-server/.env.local
cp web/.env.example web/.env.local
```

Add an Anthropic API key to `registry-server/.env.local` to enable agent chat. Mapping and firmware-generation endpoints work without it. Set `SERIAL_PORT` in `mcp-server/.env.local` to enable physical hardware I/O; leave it blank to run the UI and code generator without a connected board.

By default, the registry loads the bundled MCP server in-process so serial state persists across requests. Set `MCP_SERVER` only when connecting to a separately hosted MCP endpoint.

### 3. Run the registry and web app

```bash
# Terminal 1
cd registry-server
uvicorn server:app --reload --port 5057

# Terminal 2
cd web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The registry API is available at [http://localhost:5057](http://localhost:5057).

## Validation

```bash
python -m unittest discover -s tests -v

cd web
npm run lint
npx tsc --noEmit
npm run build
```

The tests cover mapping persistence, board-specific code generation, MCP tool/resource discovery, offline hardware errors, and stale-command expiry. GitHub Actions runs the Python and web checks on every pull request.

## Security

Never commit `.env` files or API keys. Use the checked-in `.env.example` files for local configuration. The services are intended for trusted local development; add authentication and TLS before exposing hardware-control endpoints to a network.
