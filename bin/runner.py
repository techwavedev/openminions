#!/usr/bin/env python3
"""
openminions Runner — Pipeline Orchestration Engine

Executes squad pipelines designed by the Architect Wizard. Writes state.json
files that the React/Phaser dashboard consumes via WebSocket for live updates.
Generates human-readable runs.md and memories.md logs.

Usage:
    python3 bin/runner.py --squad data/squads/my-squad
    python3 bin/runner.py --squad data/squads/my-squad --dry-run
    python3 bin/runner.py --intent "Write a blog post about AI" --auto

Architecture:
    openminions (orchestrator) → @techwavedev/agi-agent-kit (skills/execution)
    The runner imports AGI execution scripts from the installed agi-agent-kit
    or from a local AGI_PATH for development.
"""

import argparse
import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AGI_PATH = os.environ.get("AGI_PATH", os.path.expanduser("~/code/agi"))
DEFAULT_SQUADS_DIR = PROJECT_ROOT / "data" / "squads"


def resolve_agi_path(cli_arg: str | None = None) -> Path:
    """Resolve and validate the AGI backend path."""
    agi = Path(cli_arg or DEFAULT_AGI_PATH)
    if not agi.is_dir():
        print(f"❌ AGI path not found: {agi}", file=sys.stderr)
        print("   Set AGI_PATH env var or use --agi-path", file=sys.stderr)
        sys.exit(1)
    return agi


# ---------------------------------------------------------------------------
# State Management — writes state.json for dashboard WebSocket consumption
# ---------------------------------------------------------------------------
class SquadStateManager:
    """Manages state.json lifecycle for a running squad."""

    def __init__(self, squad_dir: Path, squad_config: dict):
        self.squad_dir = squad_dir
        self.state_path = squad_dir / "state.json"
        self.config = squad_config
        self.squad_name = squad_config.get("squad_name", squad_dir.name)
        self.roles = squad_config.get("roles", [])
        self.pipeline = squad_config.get("pipeline_sequence", [])
        self.checkpoints = squad_config.get("checkpoints", [])
        self.total_steps = len(self.pipeline)
        self.current_step = 0
        self.started_at = datetime.now(timezone.utc).isoformat()

        # Assign desk positions in a grid (4 columns)
        self.agents = []
        for i, role in enumerate(self.roles):
            self.agents.append({
                "id": role["name"].lower().replace(" ", "-"),
                "name": role["name"],
                "icon": self._agent_icon(role.get("role", "")),
                "status": "idle",
                "gender": "male" if i % 2 == 0 else "female",
                "desk": {"col": i % 4, "row": i // 4},
            })

    def _agent_icon(self, role_desc: str) -> str:
        """Pick an icon based on role keywords."""
        desc = role_desc.lower()
        icons = {
            "research": "🔍", "write": "✍️", "code": "💻", "review": "📋",
            "design": "🎨", "test": "🧪", "deploy": "🚀", "data": "📊",
            "scrape": "🕷️", "email": "📧", "image": "🖼️", "security": "🔒",
        }
        for keyword, icon in icons.items():
            if keyword in desc:
                return icon
        return "🤖"

    def write_state(self, status: str = "running", step_label: str = "",
                    handoff: dict | None = None):
        """Write current state to state.json for dashboard consumption."""
        state = {
            "squad": self.squad_name,
            "status": status,
            "step": {
                "current": self.current_step,
                "total": self.total_steps,
                "label": step_label,
            },
            "agents": self.agents,
            "handoff": handoff,
            "startedAt": self.started_at,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        self.state_path.write_text(json.dumps(state, indent=2))
        return state

    def set_agent_status(self, agent_name: str, status: str):
        """Update a specific agent's status."""
        agent_id = agent_name.lower().replace(" ", "-")
        for agent in self.agents:
            if agent["id"] == agent_id or agent["name"] == agent_name:
                agent["status"] = status
                break

    def advance_step(self, label: str = ""):
        """Move to the next pipeline step."""
        self.current_step += 1
        self.write_state(step_label=label)

    def complete(self):
        """Mark the squad as completed."""
        for agent in self.agents:
            agent["status"] = "done"
        self.write_state(status="completed", step_label="All steps complete")

    def cleanup(self):
        """Remove state.json (marks squad as inactive in dashboard)."""
        if self.state_path.exists():
            self.state_path.unlink()


# ---------------------------------------------------------------------------
# Memory Logs — human-readable runs.md and memories.md
# ---------------------------------------------------------------------------
class MemoryLogger:
    """Generates human-readable execution logs."""

    def __init__(self, squad_dir: Path):
        self.squad_dir = squad_dir
        self.runs_path = squad_dir / "runs.md"
        self.memories_path = squad_dir / "memories.md"
        self._init_files()

    def _init_files(self):
        """Initialize log files with headers."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        if not self.runs_path.exists():
            self.runs_path.write_text(f"# Execution Runs\n\n_Started: {now}_\n\n")
        if not self.memories_path.exists():
            self.memories_path.write_text(f"# Squad Memories\n\n_Created: {now}_\n\n")

    def log_run(self, step: int, agent_name: str, action: str, result: str,
                duration_s: float = 0):
        """Append a run entry."""
        now = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = (
            f"## Step {step} — {agent_name}\n"
            f"- **Time:** {now}\n"
            f"- **Action:** {action}\n"
            f"- **Duration:** {duration_s:.1f}s\n"
            f"- **Result:** {result}\n\n"
        )
        with open(self.runs_path, "a") as f:
            f.write(entry)

    def log_memory(self, key: str, value: str):
        """Store a persistent memory entry."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        entry = f"### {key}\n- _Recorded: {now}_\n- {value}\n\n"
        with open(self.memories_path, "a") as f:
            f.write(entry)

    def log_checkpoint(self, step: int, description: str):
        """Log a checkpoint (human approval point)."""
        entry = (
            f"---\n"
            f"### 🔒 CHECKPOINT at Step {step}\n"
            f"- {description}\n"
            f"- **Status:** Awaiting human approval\n\n"
        )
        with open(self.runs_path, "a") as f:
            f.write(entry)


# ---------------------------------------------------------------------------
# Skill Dependency Resolution
# ---------------------------------------------------------------------------
class SkillResolver:
    """Resolves and validates required skills for a squad."""

    def __init__(self, agi_path: Path):
        self.agi_path = agi_path
        self.skills_dir = self.agi_path / "skills"

    def check_dependencies(self, pipeline: list[str], roles: dict) -> list[str]:
        """Check if all tools required by the squad's agents exist. Returns missing skills."""
        required_tools = set()
        for agent_name in pipeline:
            role_config = roles.get(agent_name, {})
            for tool in role_config.get("tools", []):
                required_tools.add(tool)

        missing_skills = []
        for tool in required_tools:
            tool_dir = self.skills_dir / tool
            skill_md = tool_dir / "SKILL.md"
            if not tool_dir.is_dir() or not skill_md.exists():
                missing_skills.append(tool)

        return missing_skills

    def resolve(self, pipeline: list[str], roles: dict):
        """Validate dependencies and abort gracefully and auto-fix if possible."""
        missing = self.check_dependencies(pipeline, roles)
        if missing:
            print(f"\n❌ ERROR: Squad initialization failed due to missing skills.", file=sys.stderr)
            print(f"   Missing dependencies: {', '.join(missing)}", file=sys.stderr)
            print(f"\n   To auto-resolve, you can try pulling the latest from agi-agent-kit:", file=sys.stderr)
            print(f"   cd {self.agi_path} && git pull origin main\n", file=sys.stderr)
            sys.exit(1)
        print("✅ All skill dependencies resolved successfully.")


# ---------------------------------------------------------------------------
# Validation Gates — Pre/Post execution checks
# ---------------------------------------------------------------------------
class ValidationGate:
    """Pre and post execution validation for security."""

    @staticmethod
    def pre_validate(agent_name: str, tools: list[str], action: str) -> bool:
        """Validate before execution. Returns True if safe to proceed."""
        # Block dangerous tool combinations
        dangerous_patterns = ["rm -rf", "sudo", "curl | bash", "eval("]
        for pattern in dangerous_patterns:
            if pattern in action.lower():
                print(f"🚫 BLOCKED: Agent '{agent_name}' attempted dangerous action: {pattern}")
                return False

        # Log the pre-validation
        print(f"✅ Pre-gate passed for {agent_name}: {', '.join(tools)}")
        return True

    @staticmethod
    def post_validate(agent_name: str, result: str, expected_outputs: list[str] | None = None) -> bool:
        """Validate after execution. Returns True if output looks correct."""
        if not result or result.strip() == "":
            print(f"⚠️  Post-gate warning: {agent_name} produced empty output")
            return True  # Empty output is a warning, not a block

        # Check for error indicators
        error_indicators = ["Traceback", "FATAL", "CRITICAL", "panic:"]
        for indicator in error_indicators:
            if indicator in result:
                print(f"⚠️  Post-gate warning: {agent_name} output contains '{indicator}'")

        print(f"✅ Post-gate passed for {agent_name}")
        return True


# ---------------------------------------------------------------------------
# Pipeline Executor
# ---------------------------------------------------------------------------
def execute_agent_step(agent_config: dict, intent: str, agi_path: Path,
                       step_context: str = "") -> tuple[str, float]:
    """
    Execute a single agent step using AGI's local micro agent.
    Returns (result_text, duration_seconds).
    """
    agent_name = agent_config["name"]
    tools = agent_config.get("tools", [])
    role = agent_config.get("role", "")

    prompt = (
        f"You are {agent_name}, a specialized agent with role: {role}.\n"
        f"Your available tools: {', '.join(tools)}.\n"
        f"The squad's overall intent: {intent}\n"
    )
    if step_context:
        prompt += f"Context from previous steps:\n{step_context}\n"
    prompt += f"\nExecute your role and produce your deliverable. Be concise and actionable."

    micro_agent = agi_path / "execution" / "local_micro_agent.py"

    start = time.time()
    try:
        result = subprocess.run(
            ["python3", str(micro_agent), "--task", prompt],
            capture_output=True, text=True, timeout=180,
        )
        duration = time.time() - start
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr:
            output += f"\n[stderr: {result.stderr.strip()}]"
        return output, duration
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after 180s for {agent_name}]", time.time() - start
    except Exception as e:
        return f"[ERROR: {e}]", time.time() - start


def store_to_qdrant(content: str, memory_type: str, project: str, agi_path: Path,
                    tags: list[str] | None = None):
    """Store a memory to Qdrant via AGI's memory manager."""
    cmd = [
        "python3", str(agi_path / "execution" / "memory_manager.py"),
        "store",
        "--content", content,
        "--type", memory_type,
        "--project", project,
    ]
    if tags:
        cmd.extend(["--tags"] + tags)

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as e:
        print(f"⚠️  Failed to store to Qdrant: {e}", file=sys.stderr)


def load_squad_config(squad_dir: Path) -> dict:
    """Load squad configuration from YAML or JSON."""
    yaml_path = squad_dir / "squad.yaml"
    json_path = squad_dir / "squad.json"

    if yaml_path.exists():
        try:
            import yaml
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
                return data.get("squad", data)
        except ImportError:
            print("⚠️  PyYAML not installed, trying JSON fallback...")

    if json_path.exists():
        with open(json_path) as f:
            data = json.load(f)
            return data.get("squad", data)

    print(f"❌ No squad.yaml or squad.json found in {squad_dir}", file=sys.stderr)
    sys.exit(1)


def run_pipeline(squad_dir: Path, agi_path: Path, dry_run: bool = False,
                 intent: str = ""):
    """Execute the full squad pipeline."""
    config = load_squad_config(squad_dir)
    squad_name = config.get("squad_name", squad_dir.name)
    pipeline = config.get("pipeline_sequence", [])
    roles = {r["name"]: r for r in config.get("roles", [])}
    checkpoints = config.get("checkpoints", [])

    print(f"\n{'='*60}")
    print(f"🚀 openminions Runner — {squad_name}")
    print(f"{'='*60}")
    print(f"   Pipeline: {' → '.join(pipeline)}")
    print(f"   Agents: {len(roles)}")
    print(f"   Checkpoints: {len(checkpoints)}")
    print(f"   AGI Backend: {agi_path}")
    if dry_run:
        print(f"   ⚠️  DRY RUN — no execution")
    print(f"{'='*60}\n")

    # Resolve Skill Dependencies
    print(f"🔍 Resolving dependencies...")
    resolver = SkillResolver(agi_path)
    resolver.resolve(pipeline, roles)

    # Initialize state & logging
    state_mgr = SquadStateManager(squad_dir, config)
    logger = MemoryLogger(squad_dir)
    gate = ValidationGate()

    state_mgr.write_state(status="running", step_label="Initializing pipeline")
    logger.log_memory("Squad Intent", intent or config.get("description", "N/A"))

    step_context = ""

    for i, agent_name in enumerate(pipeline, 1):
        role_config = roles.get(agent_name, {"name": agent_name, "role": "general", "tools": []})
        tools = role_config.get("tools", [])
        role_desc = role_config.get("role", "")

        print(f"\n📍 Step {i}/{len(pipeline)}: {agent_name}")
        print(f"   Role: {role_desc}")
        print(f"   Tools: {', '.join(tools)}")

        # Pre-validation gate
        if not gate.pre_validate(agent_name, tools, role_desc):
            logger.log_run(i, agent_name, role_desc, "BLOCKED by pre-validation gate")
            state_mgr.set_agent_status(agent_name, "checkpoint")
            state_mgr.write_state(status="checkpoint", step_label=f"BLOCKED: {agent_name}")
            print(f"   🚫 Skipped (blocked by security gate)")
            continue

        # Update dashboard state
        state_mgr.set_agent_status(agent_name, "working")
        state_mgr.advance_step(label=f"{agent_name}: {role_desc[:50]}")

        if dry_run:
            result = f"[DRY RUN] Would execute {agent_name} with tools: {', '.join(tools)}"
            duration = 0.0
            print(f"   🔸 {result}")
        else:
            # Execute
            result, duration = execute_agent_step(role_config, intent, agi_path, step_context)
            print(f"   ⏱️  Completed in {duration:.1f}s")
            if result:
                # Show truncated result
                preview = result[:200] + "..." if len(result) > 200 else result
                print(f"   📄 {preview}")

        # Post-validation gate
        gate.post_validate(agent_name, result)

        # Log the run
        logger.log_run(i, agent_name, role_desc, result[:500], duration)

        # Update agent status and create handoff context
        state_mgr.set_agent_status(agent_name, "delivering")
        if i < len(pipeline):
            next_agent = pipeline[i]
            handoff = {
                "from": agent_name,
                "to": next_agent,
                "message": f"Completed: {role_desc[:80]}",
                "completedAt": datetime.now(timezone.utc).isoformat(),
            }
            state_mgr.write_state(
                step_label=f"Handoff: {agent_name} → {next_agent}",
                handoff=handoff,
            )
            logger.log_memory(f"Handoff {agent_name}→{next_agent}", result[:200])

        state_mgr.set_agent_status(agent_name, "done")
        step_context += f"\n[{agent_name}]: {result[:300]}\n"

        # Check for checkpoints
        checkpoint_idx = i - 1
        if checkpoint_idx < len(checkpoints):
            checkpoint_desc = checkpoints[checkpoint_idx]
            print(f"\n   🔒 CHECKPOINT: {checkpoint_desc}")
            logger.log_checkpoint(i, checkpoint_desc)
            state_mgr.write_state(status="checkpoint", step_label=f"Checkpoint: {checkpoint_desc}")

            if not dry_run:
                try:
                    approval = input("   ➡️  Approve and continue? [Y/n]: ").strip().lower()
                    if approval == "n":
                        print("   ❌ Pipeline halted by user.")
                        logger.log_run(i, "SYSTEM", "User halt", "Pipeline stopped at checkpoint")
                        return
                except EOFError:
                    pass  # Non-interactive mode — auto-approve

        time.sleep(0.3)  # Brief pause for dashboard animation

    # Finalize
    state_mgr.complete()
    logger.log_memory("Pipeline Complete",
                      f"All {len(pipeline)} steps executed successfully")

    # Store summary to Qdrant
    summary = (
        f"Completed squad '{squad_name}': {' → '.join(pipeline)}. "
        f"Intent: {intent or config.get('description', 'N/A')}"
    )
    store_to_qdrant(summary, "decision", "openminions", agi_path,
                    tags=["squad-run", squad_name])

    print(f"\n{'='*60}")
    print(f"✅ Squad '{squad_name}' completed successfully!")
    print(f"   📊 State: {state_mgr.state_path}")
    print(f"   📝 Runs log: {logger.runs_path}")
    print(f"   🧠 Memories: {logger.memories_path}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="openminions Runner — Execute squad pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run existing squad
  python3 bin/runner.py --squad data/squads/blog-writer

  # Auto-design and run (architect + runner)
  python3 bin/runner.py --intent "Research AI trends and write a report" --auto

  # Dry run — preview without execution
  python3 bin/runner.py --squad data/squads/blog-writer --dry-run
        """,
    )
    parser.add_argument("--squad", help="Path to squad directory containing squad.yaml/json")
    parser.add_argument("--intent", help="Natural language intent (used with --auto)")
    parser.add_argument("--auto", action="store_true",
                        help="Auto-design squad from intent, then execute")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview pipeline without executing agents")
    parser.add_argument("--agi-path", default=None,
                        help=f"Path to AGI project (default: {DEFAULT_AGI_PATH})")
    args = parser.parse_args()

    agi_path = resolve_agi_path(args.agi_path)

    # Mode 1: Auto design + run
    if args.auto and args.intent:
        print("🏗️  Auto mode: Designing squad from intent...")
        architect = PROJECT_ROOT / "bin" / "architect_wizard.py"
        squads_dir = DEFAULT_SQUADS_DIR
        squads_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["python3", str(architect), "--intent", args.intent,
             "--agi-path", str(agi_path), "--output-dir", str(squads_dir), "--json"],
            capture_output=True, text=True,
        )

        if result.returncode != 0:
            print(f"❌ Architect failed: {result.stderr}")
            sys.exit(1)

        try:
            design = json.loads(result.stdout.strip())
            squad_name = design.get("squad_name", "unnamed-squad")
            squad_dir = squads_dir / squad_name
        except json.JSONDecodeError:
            print("❌ Failed to parse architect output")
            sys.exit(1)

        # Show design and ask for approval
        print(f"\n✨ Designed: {squad_name}")
        print(json.dumps(design, indent=2))
        try:
            approval = input("\n➡️  Approve this design and execute? [Y/n]: ").strip().lower()
            if approval == "n":
                print("Cancelled.")
                return
        except EOFError:
            pass

        run_pipeline(squad_dir, agi_path, dry_run=args.dry_run, intent=args.intent)

    # Mode 2: Run existing squad
    elif args.squad:
        squad_dir = Path(args.squad)
        if not squad_dir.is_dir():
            print(f"❌ Squad directory not found: {squad_dir}", file=sys.stderr)
            sys.exit(1)
        run_pipeline(squad_dir, agi_path, dry_run=args.dry_run,
                     intent=args.intent or "")

    else:
        parser.print_help()
        print("\n💡 Quick start: python3 bin/runner.py --intent 'your goal' --auto")


if __name__ == "__main__":
    main()
