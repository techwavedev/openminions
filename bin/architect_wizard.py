#!/usr/bin/env python3
"""
Architect Wizard (Atlas) — openminions

Queries AGI's Qdrant index to retrieve relevant skills, agents, and templates
based on the user's intent. Then uses a local LLM to dynamically build a
phased execution pipeline (a Squad).

Usage:
    python3 bin/architect_wizard.py --intent "Write a blog post about AI trends"
    python3 bin/architect_wizard.py --intent "Scrape competitor pricing" --agi-path /custom/agi
"""

import argparse
import sys
import json
import subprocess
import os

# ---------------------------------------------------------------------------
# Configuration — Resolve AGI path from env or argument
# ---------------------------------------------------------------------------
DEFAULT_AGI_PATH = os.environ.get("AGI_PATH", os.path.expanduser("~/code/agi"))


def resolve_agi_path(cli_arg: str | None) -> str:
    """Return the AGI project root, validated."""
    agi = cli_arg or DEFAULT_AGI_PATH
    if not os.path.isdir(agi):
        print(f"❌ AGI path not found: {agi}", file=sys.stderr)
        print("   Set AGI_PATH env var or use --agi-path", file=sys.stderr)
        sys.exit(1)
    return agi


def call_local_agent(prompt: str, agi_path: str) -> str:
    """Route prompt to AGI's local micro agent."""
    micro_agent = os.path.join(agi_path, "execution", "local_micro_agent.py")
    try:
        cmd = ["python3", micro_agent, "--task", prompt]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"⚠️  Agent warning: {result.stderr}", file=sys.stderr)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print("⚠️  Agent timed out after 120s", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"⚠️  Agent execution failed: {e}", file=sys.stderr)
        return ""


def query_qdrant(intent: str, agi_path: str) -> str:
    """Query AGI's Qdrant memory for relevant skills and patterns."""
    sys.path.insert(0, os.path.join(agi_path, "execution"))
    try:
        from memory_manager import retrieve_context
        context_res = retrieve_context(intent, top_k=8, score_threshold=0.45, project="agi")
        chunks = context_res.get("chunks", [])
        if chunks:
            print(f"✅ Found {len(chunks)} relevant patterns in knowledge base.")
            return "\n".join(f"- {c.get('content', '')}" for c in chunks)
        else:
            print("⚠️  No strong matches found in Qdrant. Using default heuristics.")
            return "Use default multi-agent design patterns."
    except Exception as e:
        print(f"⚠️  Error querying memory: {e}. Using default heuristics.")
        return "Use default multi-agent design patterns."


def design_squad(intent: str, context_string: str, agi_path: str) -> dict:
    """Let the LLM architect a squad pipeline from intent + context."""
    agent_prompt = f"""
    You are the Architect Agent (Atlas). Based on the user's intent: "{intent}"
    Design a JSON configuration for a 'Squad' composed of multiple specialized sub-agents.
    Use the following retrieved capabilities from our index to assign the best skills/tools:
    {context_string}

    Output ONLY a precise JSON in this format:
    {{
      "squad_name": "name-of-squad",
      "description": "Short description",
      "roles": [
         {{"name": "AgentName", "role": "Description", "tools": ["tool1", "tool2"]}}
      ],
      "pipeline_sequence": ["AgentName1"],
      "checkpoints": ["Description of checkpoint"]
    }}
    Do not output markdown code blocks. Output exactly the raw JSON.
    """

    design_str = call_local_agent(agent_prompt, agi_path)

    # Strip accidental markdown fences
    for fence in ("```json", "```"):
        if design_str.startswith(fence):
            design_str = design_str[len(fence):]
    if design_str.endswith("```"):
        design_str = design_str[:-3]

    return json.loads(design_str.strip())


def save_squad(squad_design: dict, output_dir: str | None = None) -> str:
    """Persist the squad config to data/squads/<name>/."""
    squad_name = squad_design.get("squad_name", "unnamed-squad")
    base = output_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "squads")
    squad_dir = os.path.join(base, squad_name)
    os.makedirs(squad_dir, exist_ok=True)

    # Prefer YAML, fall back to JSON
    yaml_path = os.path.join(squad_dir, "squad.yaml")
    try:
        import yaml
        with open(yaml_path, "w") as f:
            yaml.dump({"squad": squad_design}, f, sort_keys=False)
    except ImportError:
        json_path = os.path.join(squad_dir, "squad.json")
        with open(json_path, "w") as f:
            json.dump({"squad": squad_design}, f, indent=2)

    return squad_dir


def main():
    parser = argparse.ArgumentParser(description="Architect Wizard for Squad Design")
    parser.add_argument("--intent", required=True, help="Squad goal in natural language")
    parser.add_argument("--agi-path", default=None, help=f"Path to AGI project (default: {DEFAULT_AGI_PATH})")
    parser.add_argument("--output-dir", default=None, help="Custom output directory for squad config")
    parser.add_argument("--json", action="store_true", help="Output raw JSON to stdout (for piping)")
    args = parser.parse_args()

    agi_path = resolve_agi_path(args.agi_path)
    print(f"🏗️  Architect (Atlas) analyzing intent: '{args.intent}'")
    print(f"   AGI backend: {agi_path}")

    # 1. Consult Memory (Qdrant)
    print("🧠 Querying AGI Qdrant index for matching skills and agents...")
    context_string = query_qdrant(args.intent, agi_path)

    # 2. Design the Pipeline
    print("🎨 Designing Squad pipeline... (Invoking local LLM)")
    try:
        squad_design = design_squad(args.intent, context_string, agi_path)
    except json.JSONDecodeError:
        print("❌ Failed to parse Architect output as JSON.")
        sys.exit(1)

    if args.json:
        print(json.dumps(squad_design, indent=2))
    else:
        print("\n✨ Squad Design Draft:")
        print(json.dumps(squad_design, indent=2))

    # 3. Save
    squad_dir = save_squad(squad_design, args.output_dir)
    print(f"\n✅ Design saved to {squad_dir}")
    print("Ready for human approval.")

    return squad_design


if __name__ == "__main__":
    main()
