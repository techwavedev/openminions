# openminions Documentation

Welcome to the **openminions** documentation site. openminions is the next-generation multi-agent orchestrator powered by the `@techwavedev/agi-agent-kit`.

## Overview

Unlike standard multi-agent frameworks that require you to manually wire everything up, openminions utilizes a powerful three-layer architecture:

1. **Directives**: You create your pipeline structure via `squad.json` or interactively via the Architect Wizard.
2. **Orchestration**: The python-based execution engine (`runner.py`) handles memory, checkpoints, and Qdrant integration asynchronously.
3. **Execution**: The React UI serves as a real-time command center, plotting activities geographically on your dashboard through WebSocket sync.

## Navigation

- [Guides](guides/getting-started.md) — Architectural deep-dives and getting started.
- [API Reference](api/cli.md) — Documentation for the openminions CLI and runner APIs.
- [Tutorials](tutorials/first-squad.md) — Step-by-step blueprints for your first orchestrated AI team.
