# Crédit Agricole — Rasa Pro Demo Bot

An intelligent banking assistant powered by Rasa Pro CALM, with MCP-connected sub-agents for card and payment queries, a FAISS knowledge base for financial FAQ, and flows for personal data management.

## Project Structure

- `actions/` — Custom Python actions (`action_session_start`, `action_update_address`, `action_get_profile`)
- `config.yml` — Rasa pipeline and policies configuration
- `credentials.yml` — Channel credentials
- `data/flows/` — CALM flow definitions (cards, payments, address, profile, welcome…)
- `docs/` — FAISS knowledge base documents (assurance, budget, crédit, épargne, fiscalité…)
- `domain/` — Domain files (slots, responses, actions)
- `endpoints.yml` — Action server and MCP server endpoints
- `mcp_server/` — FastMCP server exposing banking data tools + REST endpoints
- `prompts/` — Jinja2 prompt templates for LLM components
- `sub_agents/` — ReAct sub-agent configs for cards and payments
- `argocd/` — Helm values for Kubernetes deployment via ArgoCD

---

## Local Development

### Prerequisites

```bash
# Python 3.10+ required
pip install uv
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt --prerelease=allow
```

Set environment variables:
```bash
export RASA_PRO_LICENSE=<your-license>
export OPENAI_API_KEY=<your-openai-key>
```

### 1. Start the MCP server

In a dedicated terminal:

```bash
python mcp_server/server.py
```

The server starts on `http://localhost:8000`. Verify it's up:

```bash
curl http://localhost:8000/user-profile?user_id=825
```

### 2. Train the Rasa model

```bash
rasa train
```

### 3. Start the Rasa Inspector

In a second terminal:

```bash
rasa inspect --debug
```

Open the Inspector in your browser at the URL printed in the terminal (typically `http://localhost:5005/webhooks/socketio/inspect.html`).

> The MCP server must be running **before** `rasa inspect` so sub-agents can connect at startup.

---

