# MiniCodex Local

MiniCodex Local is a small terminal-based Agent project for learning how local coding agents work.

It uses an OpenAI-compatible Chat Completions API, tool calling, local file tools, command whitelisting, human confirmation, and lightweight memory files.

## Features

- OpenAI-compatible LLM API calls
- Function/tool calling with JSON Schema
- `@tool` based tool registration
- Local file listing, reading, searching, writing, appending, and patching
- Human confirmation before high-risk tools
- Restricted command execution for Python validation
- `working-memory.md` for short-term task state
- `working-summary.md` for compressed context history
- `sessions/*.jsonl` runtime logs
- Terminal multi-line input with `:paste` and `:end`

## Project Structure

```text
minicodex/
  agent.py        # Agent loop, tool execution, message construction
  console.py      # CLI input and human confirmation
  llm_client.py   # LLM client and summary compression calls
  memory.py       # working-memory, working-summary, message trimming
  session_log.py  # JSONL session logging

tools/
  tool_registry.py  # @tool decorator and registry
  tool_loader.py    # imports tool modules to trigger registration
  file_tools.py     # local file tools
  command_tools.py  # restricted command tool
  weather_tools.py  # Amap weather tool

memory/
  working-memory.md
  working-summary.md
```

## Install

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Install the project in editable mode:

```powershell
pip install -e .
```

## Configure

Copy `.env.example` to `.env`:

```powershell
copy .env.example .env
```

Fill in your OpenAI-compatible API settings:

```env
MIMO_API_KEY=your_openai_compatible_api_key_here
MIMO_BASE_URL=https://your-openai-compatible-endpoint.example/v1
MIMO_MODEL=your_model_name_here
```

Weather lookup is optional. If you want to use the weather tool, also configure:

```env
GDMAP_KEY=your_amap_api_key_here
```

Never commit `.env`.

## Run

After activating the virtual environment, start MiniCodex:

```powershell
minicodex
```

Or run it through Python:

```powershell
python -m minicodex.agent
```

## Multi-Line Input

For a normal one-line question, type directly and press Enter.

For multi-line text, use paste mode:

```text
:paste
Write a short README for this project.

Requirements:
- Keep it concise.
- Mention the CLI command.
:end
```

## Safety Notes

- `.env` is ignored and must not be committed.
- File tools are restricted to the workspace.
- Sensitive folders such as `.env`, `.venv`, `.git`, and `.idea` are blocked.
- Write, append, patch, and command execution tools require confirmation.
- `run_command` only allows a small Python command whitelist.

## Development

Run syntax checks:

```powershell
python -m py_compile minicodex\agent.py minicodex\console.py minicodex\llm_client.py minicodex\memory.py minicodex\session_log.py
```
