#!/usr/bin/env python3
"""
System Health Check for openminions

Checks hardware specs, available services, and recommends whether the user
can run local LLMs for simple/security-sensitive tasks.

Usage:
    python3 bin/health_check.py          # Full check
    python3 bin/health_check.py --json   # JSON output
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AGI_PATH = os.environ.get("AGI_PATH", os.path.expanduser("~/code/agi"))

# Minimum specs for local model tiers
LOCAL_MODEL_TIERS = {
    "gemma4:e4b": {
        "name": "Gemma 4 (4B)",
        "min_ram_gb": 8,
        "recommended_ram_gb": 16,
        "description": "Fast tier — handles simple tasks: summarize, classify, format, extract",
        "use_cases": [
            "Summarize error logs",
            "Classify text or log entries",
            "Convert naming conventions (camelCase ↔ snake_case)",
            "Parse JSON and extract fields",
            "Format code snippets",
        ],
    },
    "glm-4.7-flash": {
        "name": "GLM 4 Flash (12B)",
        "min_ram_gb": 16,
        "recommended_ram_gb": 32,
        "description": "Medium tier — handles moderate tasks with better reasoning",
        "use_cases": [
            "Generate boilerplate code",
            "Rewrite functions",
            "Analyze simple patterns",
            "Draft short documentation",
        ],
    },
}

# Tasks that MUST stay local (never sent to cloud)
SECURITY_SENSITIVE_TASKS = [
    "Parse .env files",
    "Extract API keys or tokens",
    "Read credentials.json",
    "Process private keys",
    "Handle OAuth tokens",
    "Read password files",
]


def get_system_ram_gb() -> float:
    """Get total system RAM in GB."""
    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5,
            )
            return int(result.stdout.strip()) / (1024 ** 3)
        elif system == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
        elif system == "Windows":
            result = subprocess.run(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                capture_output=True, text=True, timeout=5,
            )
            lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip().isdigit()]
            if lines:
                return int(lines[0]) / (1024 ** 3)
    except Exception:
        pass
    return 0


def get_cpu_info() -> dict:
    """Get CPU information."""
    system = platform.system()
    info = {
        "arch": platform.machine(),
        "cores": os.cpu_count() or 0,
        "processor": platform.processor() or "unknown",
    }

    try:
        if system == "Darwin":
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5,
            )
            info["model"] = result.stdout.strip()

            # Check for Apple Silicon
            if "Apple" in info.get("model", ""):
                info["apple_silicon"] = True
                # Get GPU cores
                result = subprocess.run(
                    ["sysctl", "-n", "hw.perflevel0.logicalcpu"],
                    capture_output=True, text=True, timeout=5,
                )
                info["performance_cores"] = int(result.stdout.strip()) if result.returncode == 0 else 0
        elif system == "Linux":
            result = subprocess.run(
                ["lscpu"], capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.split("\n"):
                if "Model name" in line:
                    info["model"] = line.split(":")[1].strip()
    except Exception:
        pass

    return info


def check_gpu() -> dict:
    """Check for GPU availability."""
    gpu = {"available": False, "type": "none", "details": ""}

    system = platform.system()
    try:
        if system == "Darwin":
            cpu_info = get_cpu_info()
            if cpu_info.get("apple_silicon"):
                gpu["available"] = True
                gpu["type"] = "apple_silicon"
                gpu["details"] = "Apple Silicon unified memory (Metal acceleration)"
        else:
            # Check for NVIDIA GPU
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                gpu["available"] = True
                gpu["type"] = "nvidia"
                gpu["details"] = result.stdout.strip()
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return gpu


def check_ollama() -> dict:
    """Check if Ollama is installed and running."""
    ollama = {"installed": False, "running": False, "models": []}

    if not shutil.which("ollama"):
        return ollama

    ollama["installed"] = True

    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            ollama["running"] = True
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            for line in lines:
                parts = line.split()
                if parts:
                    ollama["models"].append(parts[0])
    except Exception:
        pass

    return ollama


def check_qdrant() -> dict:
    """Check if Qdrant is available."""
    qdrant = {"available": False, "method": "none"}

    # Check Docker
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=qdrant", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and "qdrant" in result.stdout:
            qdrant["available"] = True
            qdrant["method"] = "docker"
            return qdrant
    except (FileNotFoundError, Exception):
        pass

    # Check direct HTTP
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:6333/collections", timeout=3)
        if resp.status == 200:
            qdrant["available"] = True
            qdrant["method"] = "local"
    except Exception:
        pass

    return qdrant


def check_agi_kit() -> dict:
    """Check if agi-agent-kit is available."""
    agi_path = Path(DEFAULT_AGI_PATH)
    result = {
        "installed": agi_path.exists(),
        "path": str(agi_path),
        "skills_count": 0,
    }

    if result["installed"]:
        skills_dir = agi_path / "skills"
        if skills_dir.exists():
            result["skills_count"] = len([
                d for d in skills_dir.iterdir()
                if d.is_dir() and (d / "SKILL.md").exists()
            ])

    return result


def recommend_local_model(ram_gb: float, gpu: dict) -> dict:
    """Recommend which local model tier the user can run."""
    rec = {
        "can_run_local": False,
        "recommended_model": None,
        "all_compatible": [],
        "security_benefit": (
            "Local models process security-sensitive tasks (secrets, tokens, .env files) "
            "without sending data to cloud APIs. This is a critical privacy measure."
        ),
    }

    for model_id, specs in LOCAL_MODEL_TIERS.items():
        if ram_gb >= specs["min_ram_gb"]:
            rec["can_run_local"] = True
            optimal = ram_gb >= specs["recommended_ram_gb"]
            rec["all_compatible"].append({
                "model": model_id,
                "name": specs["name"],
                "status": "optimal" if optimal else "viable",
                "description": specs["description"],
                "use_cases": specs["use_cases"],
            })

    # Pick best recommendation
    if rec["all_compatible"]:
        # Prefer the largest model that fits optimally
        optimal = [m for m in rec["all_compatible"] if m["status"] == "optimal"]
        rec["recommended_model"] = optimal[-1] if optimal else rec["all_compatible"][-1]

    return rec


def main():
    parser = argparse.ArgumentParser(description="System health check for openminions")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    # Gather all checks
    ram_gb = get_system_ram_gb()
    cpu = get_cpu_info()
    gpu = check_gpu()
    ollama = check_ollama()
    qdrant = check_qdrant()
    agi_kit = check_agi_kit()
    local_model = recommend_local_model(ram_gb, gpu)

    # Bundled catalog check
    bundled = (PROJECT_ROOT / "data" / "skills_catalog.json").exists()

    report = {
        "system": {
            "os": platform.system(),
            "arch": cpu["arch"],
            "cpu_model": cpu.get("model", "unknown"),
            "cpu_cores": cpu["cores"],
            "ram_gb": round(ram_gb, 1),
            "gpu": gpu,
        },
        "services": {
            "ollama": ollama,
            "qdrant": qdrant,
            "agi_kit": agi_kit,
        },
        "local_model": local_model,
        "skill_catalog": {
            "bundled": bundled,
            "local_synced": (PROJECT_ROOT / ".openminions" / "skills_index.json").exists(),
        },
        "ready": True,
    }

    # Determine readiness
    issues = []
    if not bundled and not agi_kit["installed"]:
        issues.append("No skill catalog available — install agi-agent-kit or run 'sync'")
    if not ollama["installed"] and local_model["can_run_local"]:
        issues.append("Ollama not installed — install it to run local models for security-sensitive tasks")

    report["issues"] = issues
    report["ready"] = len(issues) == 0

    if args.json:
        print(json.dumps(report, indent=2))
        return

    # Pretty print
    print("\n" + "=" * 60)
    print("🔍 openminions — System Health Check")
    print("=" * 60)

    # System
    print(f"\n💻 System")
    print(f"   OS: {report['system']['os']} ({report['system']['arch']})")
    print(f"   CPU: {report['system']['cpu_model']} ({report['system']['cpu_cores']} cores)")
    print(f"   RAM: {report['system']['ram_gb']} GB")
    if gpu["available"]:
        print(f"   GPU: ✅ {gpu['type']} — {gpu['details']}")
    else:
        print(f"   GPU: ❌ None detected")

    # Services
    print(f"\n🔧 Services")
    print(f"   Ollama: {'✅ Running' if ollama['running'] else '⚠️ Installed but not running' if ollama['installed'] else '❌ Not installed'}")
    if ollama["models"]:
        print(f"   Models: {', '.join(ollama['models'][:5])}")
    print(f"   Qdrant: {'✅ Available (' + qdrant['method'] + ')' if qdrant['available'] else '❌ Not available (local JSON index will be used)'}")
    print(f"   AGI Kit: {'✅ Installed (' + str(agi_kit['skills_count']) + ' skills)' if agi_kit['installed'] else '⚠️ Not found (using bundled catalog)' if bundled else '❌ Not installed'}")

    # Local Model Recommendation
    print(f"\n🧠 Local Model Recommendation")
    if local_model["can_run_local"]:
        rec = local_model["recommended_model"]
        print(f"   ✅ Your machine CAN run local models!")
        print(f"   Recommended: {rec['name']} ({rec['model']}) — {rec['status']}")
        print(f"   {rec['description']}")
        print(f"\n   What it handles locally (free, private, no cloud):")
        for uc in rec["use_cases"]:
            print(f"   • {uc}")
        print(f"\n   🔒 Security-sensitive tasks (ALWAYS local, never cloud):")
        for task in SECURITY_SENSITIVE_TASKS[:4]:
            print(f"   • {task}")
        if not ollama["installed"]:
            print(f"\n   ⚠️  Install Ollama to enable local models:")
            print(f"      brew install ollama && ollama pull {rec['model']}")
    else:
        print(f"   ⚠️  Insufficient RAM ({ram_gb:.0f} GB) for local models")
        print(f"   Minimum: 8 GB for Gemma 4 (4B)")
        print(f"   All tasks will use cloud LLM")
        print(f"\n   🔒 IMPORTANT: Security-sensitive tasks will be BLOCKED")
        print(f"   (secrets/tokens cannot be sent to cloud APIs)")

    # Skill Catalog
    print(f"\n📦 Skill Catalog")
    if report["skill_catalog"]["local_synced"]:
        print(f"   ✅ Local index synced from agi-agent-kit")
    elif bundled:
        print(f"   ✅ Bundled catalog available (run 'sync' for latest)")
    else:
        print(f"   ❌ No catalog — run: python3 bin/skill_discovery.py sync")

    # Overall
    print(f"\n{'✅' if report['ready'] else '⚠️'} Overall: {'Ready' if report['ready'] else 'Needs attention'}")
    for issue in issues:
        print(f"   ⚠️  {issue}")

    print()


if __name__ == "__main__":
    main()
