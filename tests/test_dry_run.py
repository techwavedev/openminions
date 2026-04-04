#!/usr/bin/env python3
"""
End-to-end dry-run test for the openminions pipeline.

Validates that runner.py correctly produces a well-formed state.json when
executed with --dry-run against the mock test-squad config, and that the
security gate passes on all files in the repo.

Usage:
    python3 tests/test_dry_run.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQUAD_DIR = PROJECT_ROOT / "data" / "squads" / "test-squad"
RUNNER = PROJECT_ROOT / "bin" / "runner.py"
SECURITY_GATE = PROJECT_ROOT / "bin" / "security_gate.py"
STATE_JSON = SQUAD_DIR / "state.json"

_failures = []


def check(name: str, condition: bool, detail: str = "") -> None:
    """Record a named test assertion."""
    if condition:
        print(f"  ✅ {name}")
    else:
        msg = f"  ❌ {name}" + (f": {detail}" if detail else "")
        print(msg)
        _failures.append(name)


def main() -> None:
    print("\n" + "=" * 60)
    print("🧪 openminions — End-to-End Dry-Run Test")
    print("=" * 60 + "\n")

    # ------------------------------------------------------------------
    # 1. Verify mock squad config exists and is structurally valid
    # ------------------------------------------------------------------
    print("📋 Validating mock squad config...")

    squad_json_path = SQUAD_DIR / "squad.json"
    check("data/squads/test-squad/squad.json exists", squad_json_path.exists())

    if not squad_json_path.exists():
        print("\n❌ Cannot continue — squad.json missing.")
        sys.exit(1)

    with open(squad_json_path) as f:
        raw = json.load(f)

    # runner.py supports both {"squad": {...}} and flat config formats
    squad = raw.get("squad", raw) if isinstance(raw, dict) else raw

    check(
        "squad.json has required keys (roles, pipeline_sequence)",
        all(k in squad for k in ["roles", "pipeline_sequence"]),
        f"present keys: {list(squad.keys())}",
    )
    check("squad has exactly 2 agents", len(squad.get("roles", [])) == 2)
    check("pipeline has exactly 2 steps", len(squad.get("pipeline_sequence", [])) == 2)

    agent_names = {r["name"] for r in squad.get("roles", [])}
    pipeline_names = set(squad.get("pipeline_sequence", []))
    check(
        "pipeline_sequence agents match roles",
        pipeline_names == agent_names,
        f"pipeline={pipeline_names}, roles={agent_names}",
    )

    # ------------------------------------------------------------------
    # 2. Execute runner with --dry-run using a temporary mock AGI dir
    # ------------------------------------------------------------------
    print("\n📍 Running pipeline with --dry-run...")

    # Remove any leftover state.json from a previous run
    if STATE_JSON.exists():
        STATE_JSON.unlink()

    with tempfile.TemporaryDirectory() as mock_agi:
        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--squad", str(SQUAD_DIR),
                "--dry-run",
                "--agi-path", mock_agi,
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )

    print(result.stdout)
    if result.stderr:
        # store_to_qdrant warnings are expected when AGI is not installed
        for line in result.stderr.splitlines():
            print(f"  [stderr] {line}")

    check(
        "runner exited with code 0",
        result.returncode == 0,
        f"exit code: {result.returncode}",
    )

    # ------------------------------------------------------------------
    # 3. Validate state.json structure
    # ------------------------------------------------------------------
    print("📊 Validating state.json...")

    check("state.json was produced", STATE_JSON.exists())

    if not STATE_JSON.exists():
        print("\n❌ Cannot continue — state.json not produced.")
        _report_results()
        return

    with open(STATE_JSON) as f:
        state = json.load(f)

    required_keys = ["squad", "status", "step", "agents", "startedAt", "updatedAt"]
    missing = [k for k in required_keys if k not in state]
    check("state.json contains all required top-level keys", not missing, f"missing: {missing}")

    check(
        "state.json status is 'completed'",
        state.get("status") == "completed",
        f"got: {state.get('status')}",
    )
    check(
        "state.json squad name matches config",
        state.get("squad") == squad.get("squad_name", SQUAD_DIR.name),
        f"got: {state.get('squad')}",
    )
    check(
        "state.json step.total equals pipeline length",
        state.get("step", {}).get("total") == len(squad["pipeline_sequence"]),
        f"got: {state.get('step', {}).get('total')}",
    )
    check(
        "state.json agents list has correct count",
        len(state.get("agents", [])) == len(squad["roles"]),
        f"got: {len(state.get('agents', []))}",
    )
    check(
        "all agents have status 'done'",
        all(a.get("status") == "done" for a in state.get("agents", [])),
        f"statuses: {[a.get('status') for a in state.get('agents', [])]}",
    )
    check(
        "each agent has a desk grid position",
        all(
            "desk" in a and "col" in a["desk"] and "row" in a["desk"]
            for a in state.get("agents", [])
        ),
    )
    check(
        "each agent has an icon",
        all(a.get("icon") for a in state.get("agents", [])),
        f"icons: {[a.get('icon') for a in state.get('agents', [])]}",
    )

    # ------------------------------------------------------------------
    # 4. Security gate check on all repo files
    # ------------------------------------------------------------------
    print("\n🔒 Running security gate...")

    sec = subprocess.run(
        [sys.executable, str(SECURITY_GATE)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    if sec.stdout:
        for line in sec.stdout.splitlines():
            print(f"  {line}")

    check(
        "security gate passes on all repo files",
        sec.returncode == 0,
        (sec.stderr or sec.stdout or "")[-300:],
    )

    # ------------------------------------------------------------------
    # 5. Clean up runtime artifacts (state.json is a runtime artifact)
    # ------------------------------------------------------------------
    for artifact in (STATE_JSON, SQUAD_DIR / "runs.md", SQUAD_DIR / "memories.md"):
        if artifact.exists():
            artifact.unlink()

    _report_results()


def _report_results() -> None:
    print("\n" + "=" * 60)
    if _failures:
        print(f"❌ {len(_failures)} test(s) failed:")
        for name in _failures:
            print(f"   • {name}")
        print("=" * 60 + "\n")
        sys.exit(1)
    else:
        print("✅ All tests passed!")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
