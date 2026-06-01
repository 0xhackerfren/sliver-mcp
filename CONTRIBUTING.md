# Contributing to sliver-mcp

Thanks for your interest in contributing. This project aims to be the most comprehensive Sliver C2 MCP server available.

## Development Setup

```bash
git clone https://github.com/SuzuLabs/sliver-mcp.git
cd sliver-mcp
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
```

You'll need a running Sliver server and operator config for integration testing.

## Project Structure

```
sliver-mcp/
  server.py              # Main MCP server (all tools)
  edr_processes.json     # EDR/AV process signatures for OPSEC guard
  cleanup_manifest.json  # Artifact paths for target cleanup
  mcp.json.template      # Template MCP client config
  pyproject.toml         # Package metadata
  requirements.txt       # Pip dependencies
  INSTRUCTIONS.md        # Agent-facing tool documentation
  evasion/               # Nim loader sources and build scripts (optional)
```

## Adding New Tools

1. Add your tool function in `server.py` using the `@mcp.tool()` decorator
2. Follow existing patterns for error handling and JSON output
3. Add the tool to the reference table in `INSTRUCTIONS.md`
4. If the tool is high-risk, add it to `edr_processes.json` under `high_risk_tools`
5. Test with a live Sliver server

### Tool conventions

- All tools are prefixed with `sliver_`
- Tools that interact with a session require `session_id: str` as the first parameter
- Return JSON strings for structured data, plain strings for simple results
- Wrap all Sliver API calls in try/except and return descriptive error messages
- Use type hints for all parameters

## Adding EDR Signatures

Edit `edr_processes.json` and add entries under `edr_signatures`:

```json
{
  "Product Name": ["process1.exe", "process2.exe"]
}
```

## Code Style

- Python 3.10+ with type hints
- No external dependencies beyond `sliver-py` and `mcp[cli]`
- Async functions for all tool implementations
- Docstrings on all public functions with Args documentation

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-tool`)
3. Make your changes
4. Test with a live Sliver server
5. Submit a pull request with a clear description

## Reporting Issues

When reporting bugs, include:
- Sliver server version (`sliver version`)
- Python version
- MCP client (Cursor, Claude Desktop, etc.)
- Full error message or tool output
- Steps to reproduce
