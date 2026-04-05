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
import concurrent.futures
import threading

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
        self.budget_tokens = squad_config.get("budget_tokens", 100000)  # Default 100k tokens
        self.flat_pipeline = self._flatten_pipeline(self.pipeline)
        self.checkpoints = squad_config.get("checkpoints", [])
        self.total_steps = len(self.pipeline)  # count top-level steps (phases)
        self.current_step = 0
        self.total_tokens_used = 0
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._lock = threading.Lock()

    def _flatten_pipeline(self, pipeline: list) -> list:
        flat = []
        for item in pipeline:
            if isinstance(item, list):
                flat.extend(self._flatten_pipeline(item))
            elif isinstance(item, dict) and "then" in item:
                # Add all possible conditional branches to tracking
                if "then" in item:
                    flat.extend(self._flatten_pipeline(item["then"]) if isinstance(item["then"], list) else [item["then"]])
                if "else" in item:
                    flat.extend(self._flatten_pipeline(item["else"]) if isinstance(item["else"], list) else [item["else"]])
            else:
                flat.append(item)
        return flat

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
        with self._lock:
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
                "metrics": {
                    "tokens_used": self.total_tokens_used,
                    "budget": self.budget_tokens,
                },
                "startedAt": self.started_at,
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }
            self.state_path.write_text(json.dumps(state, indent=2))
            return state

    def set_agent_status(self, agent_name: str, status: str):
        """Update a specific agent's status."""
        agent_id = agent_name.lower().replace(" ", "-")
        with self._lock:
            for agent in self.agents:
                if agent["id"] == agent_id or agent["name"] == agent_name:
                    agent["status"] = status
                    break

    def advance_step(self, label: str = ""):
        """Move to the next pipeline step."""
        with self._lock:
            self.current_step += 1
        self.write_state(step_label=label)

    def add_tokens(self, tokens: int):
        """Add tokens to the usage tracker."""
        with self._lock:
            self.total_tokens_used += tokens
        self.write_state()

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
        self._lock = threading.Lock()
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
        with self._lock:
            with open(self.runs_path, "a") as f:
                f.write(entry)

    def log_memory(self, key: str, value: str):
        """Store a persistent memory entry."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        entry = f"### {key}\n- _Recorded: {now}_\n- {value}\n\n"
        with self._lock:
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
# Inter-Agent Message Bus
# ---------------------------------------------------------------------------
class MessageBus:
    """Provides a shared pub/sub communication channel outside the formal handoff pipeline."""

    def __init__(self, squad_dir: Path):
        self.bus_path = squad_dir / "channels.json"
        self._lock = threading.Lock()
        self.channels = {"general": []}
        self.save()

    def save(self):
        with self._lock:
            self.bus_path.write_text(json.dumps(self.channels, indent=2))

    def load(self):
        with self._lock:
            if self.bus_path.exists():
                try:
                    self.channels = json.loads(self.bus_path.read_text())
                except json.JSONDecodeError:
                    pass

    def broadcast(self, sender: str, message: str, channel: str = "general"):
        self.load()
        msg_obj = {
            "from": sender,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if channel not in self.channels:
            self.channels[channel] = []
        self.channels[channel].append(msg_obj)
        self.save()

    def get_context(self, channel: str = "general", limit: int = 5) -> str:
        self.load()
        msgs = self.channels.get(channel, [])[-limit:]
        if not msgs:
            return ""
        return "\n".join([f"[{m['timestamp']}] {m['from']}: {m['message']}" for m in msgs])

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
            return False  # Empty output is an error

        # Check for error indicators
        error_indicators = ["Traceback", "FATAL", "CRITICAL", "panic:", "[TIMEOUT", "[ERROR"]
        for indicator in error_indicators:
            if indicator in result:
                print(f"⚠️  Post-gate warning: {agent_name} output contains '{indicator}'")
                return False

        print(f"✅ Post-gate passed for {agent_name}")
        return True


# ---------------------------------------------------------------------------
# Pipeline Executor
# ---------------------------------------------------------------------------
def execute_agent_step(agent_config: dict, intent: str, agi_path: Path,
                       step_context: str = "", message_bus: MessageBus | None = None) -> tuple[str, float]:
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
    
    if message_bus:
        channel_ctx = message_bus.get_context()
        if channel_ctx:
            prompt += f"\n[Live Comm Channel 'general']\n{channel_ctx}\n"

    if step_context:
        prompt += f"\nContext from previous steps:\n{step_context}\n"
        
    prompt += f"\nExecute your role and produce your deliverable. Be concise and actionable."

    micro_agent = agi_path / "execution" / "local_micro_agent.py"

    start = time.time()
    try:
        result = subprocess.run(
            ["python3", str(micro_agent), "--task", prompt],
            capture_output=True, text=True, timeout=180,
        )
        duration = time.time() - start
        output_raw = result.stdout.strip()
        tokens_used = 0
        output_text = output_raw
        
        try:
            data = json.loads(output_raw)
            if "response" in data:
                output_text = data["response"]
                tokens_used = data.get("metrics", {}).get("total_tokens", 0)
        except json.JSONDecodeError:
            pass

        if result.returncode != 0 and result.stderr:
            output_text += f"\n[stderr: {result.stderr.strip()}]"
            
        # Optional: heuristic to let agent broadcast if output includes a specific format
        if message_bus and "BROADCAST:" in output_text:
            for line in output_text.splitlines():
                if line.startswith("BROADCAST:"):
                    msg = line.replace("BROADCAST:", "").strip()
                    message_bus.broadcast(agent_name, msg)
                    
        return output_text, duration, tokens_used
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after 180s for {agent_name}]", time.time() - start, 0
    except Exception as e:
        return f"[ERROR: {e}]", time.time() - start, 0


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
        for t in tags:
            cmd.extend(["--tags", t])

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as e:
        print(f"⚠️  Failed to store to Qdrant: {e}", file=sys.stderr)


def retrieve_from_qdrant(query: str, project: str, agi_path: Path) -> str:
    """Retrieve historical context from Qdrant."""
    cmd = [
        "python3", str(agi_path / "execution" / "memory_manager.py"),
        "retrieve",
        "--query", query,
        "--project", project,
        "--limit", "3",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                chunks = data.get("context_chunks", [])
                if chunks:
                    return "\n\n".join(chunks)
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    return ""


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
    flat_pipeline = state_mgr._flatten_pipeline(pipeline)
            
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
    resolver.resolve(flat_pipeline, roles)

    # Initialize state & logging
    state_mgr = SquadStateManager(squad_dir, config)
    logger = MemoryLogger(squad_dir)
    gate = ValidationGate()
    message_bus = MessageBus(squad_dir)

    state_mgr.write_state(status="running", step_label="Initializing pipeline")
    logger.log_memory("Squad Intent", intent or config.get("description", "N/A"))

    print(f"🧠 Loading past squad memories from intelligence layer...")
    past_context = retrieve_from_qdrant(f"Goals and previous executions for {squad_name}", squad_name, agi_path)
    
    step_context = ""
    if past_context:
        step_context += f"--- MEMORY FROM PREVIOUS RUNS ---\n{past_context}\n----------------------------------\n\n"
        print(f"   ✅ Retrieved {len(past_context.splitlines())} lines of historical context.")
    else:
        print(f"   ℹ️  No historical context found (new squad or fresh run).")

    # Track outputs for conditional branching
    agent_outputs = {}

    try:
        for i, step in enumerate(pipeline, 1):
            if isinstance(step, dict) and "condition" in step:
                # Conditional branch logic
                condition = step["condition"]
                depends_on = condition.get("depends_on", "")
                contains_str = condition.get("contains", "")
                
                print(f"\n📍 Step {i}/{len(pipeline)}: [Conditional Branch] Evaluating {depends_on}")
                
                prev_output = agent_outputs.get(depends_on, "")
                
                # Default resolve to `then` if true, `else` if false
                if contains_str and contains_str in prev_output:
                    print(f"   ✅ Condition met ('{contains_str}' found). Executing 'then' branch...")
                    agents_to_run = step.get("then", [])
                else:
                    print(f"   ❌ Condition NOT met. Executing 'else' branch...")
                    agents_to_run = step.get("else", [])
                
                if not agents_to_run:
                    print(f"   ℹ️  No agents to run in this branch. Skipping.")
                    continue
                
                if not isinstance(agents_to_run, list):
                    agents_to_run = [agents_to_run]
                    
                step_label = f"Conditional Phase: {', '.join(agents_to_run)}"
            elif isinstance(step, list):
                agents_to_run = step
                step_label = f"Parallel Phase: {', '.join(agents_to_run)}"
            else:
                agents_to_run = [step]
                step_label = step

            print(f"\n📍 Step {i}/{len(pipeline)}: {step_label}")
            state_mgr.advance_step(label=step_label)

            def run_agent(agent_name, role_config=None, is_fallback=False):
                if not role_config:
                    role_config = roles.get(agent_name, {"name": agent_name, "role": "general", "tools": []})
                
                tools = role_config.get("tools", [])
                role_desc = role_config.get("role", "")
                max_retries = role_config.get("retries", 2)
                fallback = role_config.get("fallback", None)
                res, dur, tokens_used = None, 0, 0
                
                for attempt in range(max_retries + 1):
                    attempt_str = f" [Attempt {attempt+1}]" if attempt > 0 else ""
                    print(f"   [Thread] Starting {agent_name}{attempt_str} - Role: {role_desc}")
                    
                    # Pre-validation gate
                    if not gate.pre_validate(agent_name, tools, role_desc):
                        logger.log_run(i, agent_name, role_desc, "BLOCKED by pre-validation gate")
                        if not is_fallback:
                            state_mgr.set_agent_status(agent_name, "checkpoint")
                            state_mgr.write_state(status="checkpoint", step_label=f"BLOCKED: {agent_name}")
                        print(f"   🚫 Skipped {agent_name} (blocked by security gate)")
                        return agent_name, None, 0, role_desc

                    if not is_fallback:
                        state_mgr.set_agent_status(agent_name, "working")
                        # write state just for the first agent or occasionally
                        state_mgr.write_state(step_label=f"{agent_name}: {role_desc[:50]}")

                    if dry_run:
                        res = f"[DRY RUN] Would execute {agent_name} with tools: {', '.join(tools)}"
                        dur = 0.0
                        print(f"   🔸 {res}")
                        return agent_name, res, dur, role_desc
                    
                    # Execute
                    res, dur, tokens_used = execute_agent_step(
                        agent_config=role_config,
                        intent=intent,
                        agi_path=agi_path,
                        step_context=step_context,
                        message_bus=message_bus
                    )
                    
                    state_mgr.add_tokens(tokens_used)
                    if state_mgr.total_tokens_used > state_mgr.budget_tokens:
                        print(f"   🛑 BUDGET EXCEEDED! {state_mgr.total_tokens_used} > {state_mgr.budget_tokens}")
                        logger.log_memory(f"BUDGET ALARM", f"Used {state_mgr.total_tokens_used} limit {state_mgr.budget_tokens}")
                        return agent_name, f"[ERROR: Token budget exceeded ({state_mgr.total_tokens_used}/{state_mgr.budget_tokens})]", dur, role_desc
                    
                    # Post-validation gate
                    if gate.post_validate(agent_name, res):
                        return agent_name, res, dur, role_desc
                    else:
                        print(f"   ⚠️  Agent {agent_name} failed validation. Retrying...")
                
                # Over retries, engaging fallback
                if fallback and not is_fallback:
                    print(f"   🔄 All retries exhausted for {agent_name}. Engaging fallback agent: {fallback}")
                    fallback_config = roles.get(fallback, {"name": fallback, "role": f"Fallback for {agent_name}", "tools": []})
                    state_mgr.write_state(step_label=f"Fallback: {fallback}")
                    # Recursively run the fallback (it has its own retry loop if we didn't block it, but `is_fallback=True` prevents infinite fallback chains)
                    return run_agent(fallback, role_config=fallback_config, is_fallback=True)
                
                # Give up
                return agent_name, res, dur, role_desc

            # Execute step (single or parallel)
            step_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents_to_run)) as executor:
                futures = {executor.submit(run_agent, a): a for a in agents_to_run}
                for future in concurrent.futures.as_completed(futures):
                    a_name, res, dur, r_desc = future.result()
                    if res is not None:
                        print(f"   ⏱️  {a_name} completed in {dur:.1f}s")
                        preview = res[:200] + "..." if len(res) > 200 else res
                        print(f"   📄 [{a_name}] {preview}")
                        logger.log_run(i, a_name, r_desc, res[:500], dur)
                        step_results.append((a_name, res, r_desc))
                        agent_outputs[a_name] = res  # Global tracking for conditions

            # Process handoffs
            for a_name, res, r_desc in step_results:
                state_mgr.set_agent_status(a_name, "delivering")
                # Assuming next step agents as handoff targets
                if i < len(pipeline):
                    next_step = pipeline[i]
                    next_agents = next_step if isinstance(next_step, list) else [next_step]
                    for next_agent in next_agents:
                        handoff = {
                            "from": a_name,
                            "to": next_agent,
                            "message": f"Completed: {r_desc[:80]}",
                            "completedAt": datetime.now(timezone.utc).isoformat(),
                        }
                        state_mgr.write_state(
                            step_label=f"Handoff: {a_name} → {next_agent}",
                            handoff=handoff,
                        )
                        logger.log_memory(f"Handoff {a_name}→{next_agent}", res[:200])

                state_mgr.set_agent_status(a_name, "done")
                step_context += f"\n[{a_name}]: {res[:300]}\n"

            state_mgr.write_state(step_label=f"Completed Phase {i}")

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

    except KeyboardInterrupt:
        print("\n   ❌ Pipeline interrupted by user.")
        logger.log_run(i, "SYSTEM", "User interrupt", "Pipeline stopped forcibly")
    finally:
        # In case we exited early or crashed, clean up explicitly
        # But if it just completed normally, `state_mgr.complete()` will be called.
        pass

    # Finalize
    state_mgr.complete()
    logger.log_memory("Pipeline Complete",
                      f"All {len(pipeline)} steps executed successfully")

    if not dry_run:
        # Store summary to Qdrant
        print(f"\n🧠 Committing pipeline results to long-term memory...")
        summary = (
            f"Completed squad '{squad_name}': {' → '.join(pipeline)}. "
            f"Intent: {intent or config.get('description', 'N/A')}.\n\n"
            f"Final Context:\n{step_context[-1500:]}"
        )
        store_to_qdrant(summary, "decision", squad_name, agi_path,
                        tags=["squad-execution", "final-result"])

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
