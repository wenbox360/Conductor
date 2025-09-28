# Registry Server with Anthropic Agent

This server provides hardware mapping registry functionality and an AI agent powered by Anthropic's Claude.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
Create a `.env.local` file with:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-3-5-haiku-20241022
MCP_SERVER=../../../mhacks25_server/server.py
```

**Important**: The `MCP_SERVER` uses a relative path to the MCP server script in the `mhacks25_server` directory. Make sure the MCP server is running before starting this registry server.

3. Run the server:
```bash
python server.py
```

The server will start on `http://localhost:5057`

## Endpoints

- `GET /health` - Health check
- `GET /mappings` - Get all hardware mappings
- `POST /mappings` - Add hardware mappings
- `DELETE /mappings/{id}` - Delete a mapping
- `GET /agent/health` - Agent health check
- `POST /agent/chat` - Chat with the AI agent

## Agent Features

The AI agent can:
- Understand natural language hardware queries
- Execute MCP tools for hardware control
- Provide contextual responses based on your hardware mappings
- Handle temperature, humidity, relay control, and more
