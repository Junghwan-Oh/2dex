# DexBot Project Overview

## Purpose
DexBot is a cryptocurrency perpetual DEX trading toolkit focused on:
- Delta-neutral hedge bot development (GRVT + Backpack exchanges)
- Multiple exchange integrations (Apex, Paradex, Lighter, EdgeX, Aster)
- Automated trading strategies with progressive sizing
- Hummingbot integration for market making

## Tech Stack
- **Language**: Python 3.11+
- **Package Manager**: uv (preferred), pip
- **Framework**: asyncio-based for exchange connections
- **Key Libraries**:
  - Exchange SDKs: apexomni, paradex-py, web3
  - Async: aiohttp, websocket-client
  - Data: pandas, numpy, scipy
  - Testing: pytest, pytest-asyncio, pytest-cov
  - Code Quality: black, ruff, mypy

## Project Structure
```
f:\Dropbox\dexbot\
├── .claude/           # Claude Code configuration and hooks
├── .moai/             # MoAI-ADK configuration
├── .serena/           # Serena MCP configuration
├── perpdex/           # Main trading code
│   ├── hedge/         # Hedge bot implementations
│   ├── hummingbot/    # Hummingbot integration
│   ├── paradex/       # Paradex exchange
│   └── apex/          # Apex exchange
├── evaluations/       # Development evaluations
└── claudedocs/        # Claude-generated documentation
```

## Platform
- Windows (MSYS_NT-10.0)
- Uses MSYS2/Git Bash for command execution
