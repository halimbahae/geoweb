# GeoWeb MCP

A [Model Context Protocol](https://modelcontextprotocol.io) server that gives AI
assistants direct access to a GeoWeb archive — list sessions, read recons, start
new ones, and inspect video frames — over plain stdin/stdout (or SSE).

It is read-only except for starting recon jobs, which use the exact same
`uv run scripts/recon.py` subprocesses as the web console, so the two interfaces
never fight. All data stays on your machine.

> Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

## Run

```bash
# stdio (default — what assistants spawn)
GEOWEB_ROOT=~/geoweb-photos uv run mcp/geoweb_mcp.py

# server-sent events, for remote/multi-client setups
GEOWEB_ROOT=~/geoweb-photos uv run mcp/geoweb_mcp.py --transport sse --port 8989
```

The first run downloads the `mcp` Python package into a uv cache — nothing is
installed globally.

## Tools

| Tool            | What it does                                                        |
| --------------- | ------------------------------------------------------------------- |
| `sessions`      | list every archive session: kind, status, result, truth error       |
| `session`       | full session: meta, jobs, report, recon summary, live step digests  |
| `start_recon`   | kick off a quick/full recon (or one video frame) — returns the job  |
| `recon_status`  | per-step progress + summary, finished or not                        |
| `read_file`     | read any text file inside a session (`recon/prior/prior.json`, …)   |
| `frames`        | video sessions: extracted frame list + contact sheet path           |
| `tools`         | the curated CLI tools behind the console (textgeo, board, …)        |

## Client configs

Any MCP-capable assistant can drive GeoWeb. Replace `/absolute/path/to/geoweb`
with the checkout path and point `GEOWEB_ROOT` at your archive. The whole server
is a single stdio command: `uv run mcp/geoweb_mcp.py`.

### opencode

`opencode.json` (project) or `~/.config/opencode/opencode.json` (global):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "geoweb": {
      "type": "local",
      "command": ["uv", "run", "/absolute/path/to/geoweb/mcp/geoweb_mcp.py"],
      "environment": { "GEOWEB_ROOT": "/Users/you/geoweb-photos" },
      "enabled": true
    }
  }
}
```

### Claude Code

```bash
claude mcp add geoweb --scope user \
  --env GEOWEB_ROOT=/Users/you/geoweb-photos \
  -- uv run /absolute/path/to/geoweb/mcp/geoweb_mcp.py
```

Or commit a project `.mcp.json`:

```json
{
  "mcpServers": {
    "geoweb": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/geoweb/mcp/geoweb_mcp.py"],
      "env": { "GEOWEB_ROOT": "/Users/you/geoweb-photos" }
    }
  }
}
```

### Codex (OpenAI)

```bash
codex mcp add geoweb --env GEOWEB_ROOT=/Users/you/geoweb-photos \
  -- uv run /absolute/path/to/geoweb/mcp/geoweb_mcp.py
```

Or edit `~/.codex/config.toml` (project-scoped `.codex/config.toml` also works):

```toml
[mcp_servers.geoweb]
command = "uv"
args = ["run", "/absolute/path/to/geoweb/mcp/geoweb_mcp.py"]
env = { GEOWEB_ROOT = "/Users/you/geoweb-photos" }
```

### GitHub Copilot CLI

```bash
copilot mcp add geoweb --env GEOWEB_ROOT=/Users/you/geoweb-photos \
  -- uv run /absolute/path/to/geoweb/mcp/geoweb_mcp.py
```

Or edit `~/.copilot/mcp-config.json` (a project `.mcp.json` also works):

```json
{
  "mcpServers": {
    "geoweb": {
      "type": "local",
      "command": "uv",
      "args": ["run", "/absolute/path/to/geoweb/mcp/geoweb_mcp.py"],
      "env": { "GEOWEB_ROOT": "/Users/you/geoweb-photos" },
      "tools": ["*"]
    }
  }
}
```

### Grok CLI (xAI)

```bash
grok mcp add geoweb -e GEOWEB_ROOT=/Users/you/geoweb-photos \
  -- uv run /absolute/path/to/geoweb/mcp/geoweb_mcp.py
```

Or edit `~/.grok/config.toml` (or a project `.grok/config.toml`):

```toml
[mcp_servers.geoweb]
command = "uv"
args = ["run", "/absolute/path/to/geoweb/mcp/geoweb_mcp.py"]
env = { GEOWEB_ROOT = "/Users/you/geoweb-photos" }
```

Grok also reads the `.mcp.json` / Cursor form below.

### Cursor

`.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "geoweb": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/geoweb/mcp/geoweb_mcp.py"],
      "env": { "GEOWEB_ROOT": "/Users/you/geoweb-photos" }
    }
  }
}
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "geoweb": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/geoweb/mcp/geoweb_mcp.py"],
      "env": { "GEOWEB_ROOT": "/Users/you/geoweb-photos" }
    }
  }
}
```

### VS Code / Windsurf / any other client

Use the same `mcpServers` JSON as Cursor; VS Code stores it in
`.vscode/mcp.json` under the `servers` key instead of `mcpServers`.

### Remote MCP over SSE (ChatGPT, Claude web, …)

Hosted assistants — ChatGPT **Connectors**, Claude web/desktop remote servers,
and any other HTTP MCP client — speak MCP over SSE rather than stdio. Start the
SSE transport and point the client at the `/sse` URL:

```bash
GEOWEB_ROOT=~/geoweb-photos uv run mcp/geoweb_mcp.py --transport sse --port 8989
# → http://127.0.0.1:8989/sse
```

- **ChatGPT**: Settings → Connectors → *Advanced* → enable **Developer mode**,
  then add the MCP server URL above.
- **Claude / any remote client**: add the same URL as a remote MCP server.

A loopback URL only works when the client runs on the same machine. To reach it
from a hosted app, expose the port with a tunnel — e.g.
`cloudflared tunnel --url http://127.0.0.1:8989` or `ngrok http 8989` — and use
the public `…/sse` URL. Everything still runs on your machine; only the MCP
transport is forwarded.

### Verify

```bash
uv run mcp/geoweb_mcp.py --help    # smoke-test the server starts
```

Inside any assistant, list tools and you should see `sessions`, `session`,
`recon_status`, `start_recon`, `read_file`, `frames`, `tools`.