# Architecture Overview

Openminions represents a new paradigm in multi-agent application design. We observed that traditional agent systems tightly couple execution logic with the actual reasoning models, causing extensive bloat and high token costs.

To solve this, Openminions is strictly split into three layers:

## 1. Directives Matrix
The highest layer. This dictates **what** the pipeline needs to accomplish without worrying about the implementation details. 
- You provide an intent via the `architect_wizard.py`.
- The intent is transformed into a `squad.json` describing strict roles, tool bindings, and pipeline sequences.

## 2. Orchestration Framework
The middle layer (`runner.py`). This engine acts as the operational brain of the pipeline.
- It parses the `squad.json`.
- It dynamically allocates memory, boots up temporary isolated sandboxes for execution, and routes context asynchronously.
- It is backed tightly by **Qdrant**, effectively ensuring every pipeline step stores its memories and learnings persistently for future runs.

## 3. Micro-Agent Execution (AGI-Kit)
The lowest layer. This actually performs the atomic steps assigned.
- Powered by `@techwavedev/agi-agent-kit`.
- Evaluates the complexity of each task. If it's a "stupid simple" text operation, it seamlessly routes the task locally to an Ollama `gemma4:e4b` model to save budget.
- For heavier logical lifting, it escalates to cloud intelligence.

## Pipeline Lifecycle
1. The orchestrator triggers agent $n$.
2. The agent executes within `.sandbox/${agent-slug}`.
3. Once completed, the outputs are formatted and logged.
4. The system stores the new checkpoint securely to `memories.md` and the Qdrant DB.
5. The orchestrator invokes Agent $n+1$ appending the contextual history.
