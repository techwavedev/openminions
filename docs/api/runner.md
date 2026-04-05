# Runner Architecture

`runner.py` powers the operational synchronization block of every Openminions pipeline.

## Core Execution Path

1. Evaluates incoming Squad Config via JSON or YAML.
2. Synchronizes to Qdrant if historical vector memories of this pipeline exist.
3. Loops sequentially over the `pipeline_sequence` array.
4. Spawns isolated `.sandbox` configurations for agent isolation.
5. Invokes `subprocess.run(["python3", str(micro_agent)])` passing robust memory contexts.
6. Writes live checkpoint states directly to `state.json` allowing the Visual Dashboard to instantly map the node graphs.
7. Commits telemetry data to `data/benchmarks.json`.

## Local LLM Routing

To avoid expensive tokens where possible, lightweight and basic operational steps invoke `"gemma4:e4b"` via the innate `local_micro_agent.py` integration from AGI Kit. This guarantees massive performance speedups on un-complex data transformation.
