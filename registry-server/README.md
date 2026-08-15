# Conductor registry and agent service

This FastAPI service stores hardware mappings, generates board-specific firmware, proxies MCP tool discovery and invocation, and runs the natural-language hardware agent.

Copy `.env.example` to `.env.local`, then run:

```bash
uvicorn server:app --reload --port 5057
```

Interactive API documentation is available at `http://localhost:5057/docs`.
