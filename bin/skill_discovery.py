#!/usr/bin/env python3
"""
Skill Auto-Discovery Engine for openminions

Syncs skills from agi-agent-kit, builds a local searchable index,
and enables dynamic skill selection for team creation.

Usage:
    python3 bin/skill_discovery.py sync                    # Sync from agi-agent-kit
    python3 bin/skill_discovery.py discover --intent "..."  # Find matching skills
    python3 bin/skill_discovery.py list                    # List all skills
    python3 bin/skill_discovery.py info --skill webcrawler  # Skill details
    python3 bin/skill_discovery.py generate-team --intent "..." # Design a team
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from difflib import SequenceMatcher

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AGI_PATH = os.environ.get("AGI_PATH", os.path.expanduser("~/code/agi"))
INDEX_PATH = PROJECT_ROOT / ".openminions" / "skills_index.json"
BUNDLED_CATALOG = PROJECT_ROOT / "data" / "skills_catalog.json"


# ─── YAML Frontmatter Parser (no PyYAML dependency) ──────────────────────────
def parse_skill_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a SKILL.md file without PyYAML."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}

    frontmatter = match.group(1)
    result = {}
    current_key = None
    current_value = []

    for line in frontmatter.split("\n"):
        kv_match = re.match(r'^(\w[\w-]*)\s*:\s*(.*)', line)
        if kv_match:
            if current_key and current_value:
                result[current_key] = " ".join(current_value).strip().strip('"').strip("'")
            current_key = kv_match.group(1)
            value = kv_match.group(2).strip()
            if value in (">", "|", ">-", "|-"):
                current_value = []
            elif value.startswith('"') and value.endswith('"'):
                current_value = [value[1:-1]]
            elif value.startswith("'") and value.endswith("'"):
                current_value = [value[1:-1]]
            else:
                current_value = [value]
        elif current_key and line.startswith("  "):
            current_value.append(line.strip())

    if current_key and current_value:
        result[current_key] = " ".join(current_value).strip().strip('"').strip("'")

    return result


def parse_skill_metadata(skill_dir: Path) -> dict:
    """Extract full metadata from a skill directory."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {}

    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    frontmatter = parse_skill_frontmatter(skill_md)

    # Extract body sections
    body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)

    # When to Use
    triggers = []
    trigger_match = re.search(r'##\s*When to Use\s*\n(.*?)(?=\n##|\Z)', body, re.DOTALL)
    if trigger_match:
        for line in trigger_match.group(1).split("\n"):
            line = line.strip().lstrip("- ").strip()
            if line and not line.startswith("#"):
                triggers.append(line)

    # Scripts
    scripts = []
    script_dir = skill_dir / "scripts"
    if script_dir.exists():
        scripts = [f.name for f in script_dir.iterdir() if f.is_file()]

    # References
    references = []
    ref_dir = skill_dir / "references"
    if ref_dir.exists():
        references = [f.name for f in ref_dir.iterdir() if f.is_file()]

    # Build keyword set from description + triggers for search
    desc = frontmatter.get("description", "")
    keywords = set()
    # Extract meaningful words (3+ chars, not common words)
    stop_words = {"the", "and", "for", "are", "with", "that", "this", "from", "use", "when"}
    for text in [desc] + triggers:
        for word in re.findall(r'\b[a-z]{3,}\b', text.lower()):
            if word not in stop_words:
                keywords.add(word)

    return {
        "name": frontmatter.get("name", skill_dir.name),
        "description": desc,
        "description_pt_br": frontmatter.get("description_pt-BR", ""),
        "path": str(skill_dir),
        "triggers": triggers[:10],
        "scripts": scripts,
        "references": references,
        "has_eval": (skill_dir / "eval").exists(),
        "keywords": sorted(list(keywords))[:50],
    }


# ─── Sync ────────────────────────────────────────────────────────────────────
def sync_from_agi(agi_path: str) -> dict:
    """Scan agi-agent-kit skills and build local index."""
    skills_dir = Path(agi_path) / "skills"
    if not skills_dir.exists():
        return {"error": f"Skills directory not found: {skills_dir}"}

    skills = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        meta = parse_skill_metadata(skill_dir)
        if meta:
            skills.append(meta)

    # Save index locally
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    index = {
        "version": 1,
        "agi_path": agi_path,
        "skill_count": len(skills),
        "synced_at": __import__("datetime").datetime.now().isoformat(),
        "skills": skills,
    }
    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")

    # Also update the bundled catalog that ships with the repo
    BUNDLED_CATALOG.parent.mkdir(parents=True, exist_ok=True)
    BUNDLED_CATALOG.write_text(json.dumps(index, indent=2), encoding="utf-8")

    return index


def load_index() -> dict:
    """Load skill index with fallback chain: local → bundled catalog."""
    # 1. User's local synced index (freshest)
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))

    # 2. Bundled catalog that ships with the repo (works without agi-agent-kit)
    if BUNDLED_CATALOG.exists():
        return json.loads(BUNDLED_CATALOG.read_text(encoding="utf-8"))

    # 3. No index available
    return {}


# ─── Search ──────────────────────────────────────────────────────────────────
def score_skill(skill: dict, intent_words: set) -> float:
    """Score a skill against intent keywords."""
    score = 0.0

    # Keyword overlap
    skill_keywords = set(skill.get("keywords", []))
    overlap = intent_words & skill_keywords
    score += len(overlap) * 2.0

    # Description similarity
    desc = skill.get("description", "").lower()
    for word in intent_words:
        if word in desc:
            score += 1.5

    # Trigger match
    for trigger in skill.get("triggers", []):
        trigger_lower = trigger.lower()
        for word in intent_words:
            if word in trigger_lower:
                score += 1.0

    # Name match (strong signal)
    name = skill.get("name", "").lower().replace("-", " ")
    for word in intent_words:
        if word in name:
            score += 3.0

    return score


def discover_skills(intent: str, top_k: int = 5) -> list[dict]:
    """Find skills matching an intent from the local index."""
    index = load_index()
    if not index or not index.get("skills"):
        return []

    # Tokenize intent
    stop_words = {"the", "and", "for", "are", "with", "that", "this", "from",
                  "use", "when", "create", "make", "need", "want", "should"}
    intent_words = set()
    for word in re.findall(r'\b[a-z]{3,}\b', intent.lower()):
        if word not in stop_words:
            intent_words.add(word)

    # Score each skill
    scored = []
    for skill in index["skills"]:
        s = score_skill(skill, intent_words)
        if s > 0:
            scored.append({
                "name": skill["name"],
                "score": round(s, 2),
                "description": skill["description"][:150],
                "scripts": skill.get("scripts", []),
                "path": skill.get("path", ""),
            })

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ─── Team Generation ─────────────────────────────────────────────────────────
# Category order defines pipeline sequence: research first, delivery last
CATEGORY_ORDER = ["research", "security", "design", "writing", "general", "delivery"]

ROLE_TEMPLATES = {
    "webcrawler": {"role": "Research and gather information from web sources", "category": "research"},
    "pdf-reader": {"role": "Extract and analyze content from PDF documents", "category": "research"},
    "documentation": {"role": "Write, review, and organize documentation", "category": "writing"},
    "image-ai-generator": {"role": "Generate images, illustrations, and visual assets", "category": "design"},
    "resend": {"role": "Send emails and manage email campaigns", "category": "delivery"},
    "notebooklm": {"role": "Query knowledge bases for research insights", "category": "research"},
    "supply-chain-monitor": {"role": "Monitor supply chain security threats", "category": "security"},
    "qdrant-memory": {"role": "Manage memory and context persistence", "category": "infra"},
    "cowork-export": {"role": "Export and share session context", "category": "infra"},
    "upstream-sync": {"role": "Sync and manage upstream dependencies", "category": "infra"},
}


def generate_team(intent: str, matched_skills: list[dict]) -> dict:
    """Generate a full team config from matched skills with proper pipeline ordering."""
    roles = []
    categories_seen = set()

    for skill in matched_skills:
        name = skill["name"]
        template = ROLE_TEMPLATES.get(name, {"role": f"Handle {name} tasks", "category": "general"})

        # Skip infra skills unless explicitly needed
        if template["category"] == "infra":
            continue

        role_name = name.replace("-", " ").title().replace(" ", "")
        if template["category"] in categories_seen and len(roles) > 4:
            continue

        categories_seen.add(template["category"])
        roles.append({
            "name": role_name,
            "role": template["role"],
            "tools": [name],
            "scripts": skill.get("scripts", []),
            "_category": template["category"],
        })

    # Ensure minimum team: researcher + writer
    if not any(r.get("tools", [None])[0] in ("webcrawler", "pdf-reader", "notebooklm") for r in roles):
        roles.append({"name": "Researcher", "role": "Research the topic from web sources", "tools": ["webcrawler"], "scripts": [], "_category": "research"})
    if not any(r.get("tools", [None])[0] == "documentation" for r in roles):
        roles.append({"name": "Writer", "role": "Write and organize the final output", "tools": ["documentation"], "scripts": [], "_category": "writing"})

    # Reviewer always last (before delivery)
    roles.append({"name": "Reviewer", "role": "Review quality and validate all outputs", "tools": ["documentation"], "scripts": [], "_category": "writing"})

    # Sort by category order: research → security → design → writing → delivery
    def sort_key(r):
        cat = r.get("_category", "general")
        # Reviewer always goes second-to-last, delivery always last
        if r["name"] == "Reviewer":
            return (len(CATEGORY_ORDER), 0)
        try:
            return (CATEGORY_ORDER.index(cat), 0)
        except ValueError:
            return (len(CATEGORY_ORDER) - 1, 0)

    roles.sort(key=sort_key)

    # Clean internal fields
    for r in roles:
        r.pop("_category", None)

    squad_name = re.sub(r'[^a-z0-9]+', '-', intent.lower().strip())[:40].strip("-")

    return {
        "squad": {
            "squad_name": squad_name,
            "name": intent[:80],
            "description": intent,
            "icon": "🤖",
            "agents": [r["name"] for r in roles],
            "roles": roles,
            "pipeline_sequence": [r["name"] for r in roles],
            "checkpoints": ["Review research before proceeding", "Approve final output before delivery"],
        }
    }


# ─── Also push to Qdrant for cross-agent memory ─────────────────────────────
def push_index_to_qdrant(index: dict, agi_path: str):
    """Store the skill index in Qdrant for cross-agent access."""
    memory_manager = Path(agi_path) / "execution" / "memory_manager.py"
    if not memory_manager.exists():
        return

    skill_summary = "\n".join(
        f"- {s['name']}: {s['description'][:100]}"
        for s in index.get("skills", [])
    )

    try:
        subprocess.run(
            [
                "python3", str(memory_manager), "store",
                "--content", f"openminions skill index ({index.get('skill_count', 0)} skills):\n{skill_summary}",
                "--type", "technical",
                "--project", "openminions",
                "--tags", "skill-index catalog sync",
            ],
            capture_output=True, timeout=30, cwd=agi_path,
        )
    except Exception:
        pass


# ─── CLI ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Skill auto-discovery for openminions")
    parser.add_argument("command", choices=["sync", "discover", "list", "info", "generate-team"])
    parser.add_argument("--agi-path", default=DEFAULT_AGI_PATH)
    parser.add_argument("--intent", help="Intent for discovery/team generation")
    parser.add_argument("--skill", help="Skill name for info")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output-dir", help="Directory to save generated squad config")
    args = parser.parse_args()

    if args.command == "sync":
        print("🔄 Syncing skills from agi-agent-kit...")
        index = sync_from_agi(args.agi_path)

        if "error" in index:
            print(f"   ❌ {index['error']}")
            sys.exit(1)

        if args.json:
            print(json.dumps(index, indent=2, default=str))
        else:
            print(f"   ✅ Indexed {index['skill_count']} skills to {INDEX_PATH}")
            for s in index["skills"]:
                scripts = f" ({len(s['scripts'])} scripts)" if s["scripts"] else ""
                print(f"   • {s['name']}{scripts} — {s['description'][:70]}...")

        # Also push to Qdrant if available (optional — not required)
        print("\n📡 Pushing to Qdrant for cross-agent access...")
        try:
            push_index_to_qdrant(index, args.agi_path)
            print("   ✅ Done")
        except Exception:
            print("   ⚠️  Qdrant not available — local index is sufficient")

    elif args.command == "discover":
        if not args.intent:
            print("❌ --intent required"); sys.exit(1)

        # Auto-sync if no index exists at all (not even bundled)
        if not INDEX_PATH.exists() and not BUNDLED_CATALOG.exists():
            print("⚠️  No skill index found, syncing from agi-agent-kit...")
            agi = Path(args.agi_path)
            if (agi / "skills").exists():
                sync_from_agi(args.agi_path)
            else:
                print("   ❌ agi-agent-kit not found. Install it or run 'sync' with --agi-path")
                sys.exit(1)

        matches = discover_skills(args.intent, args.top_k)

        if args.json:
            print(json.dumps(matches, indent=2))
        elif matches:
            print(f"\n🔍 Skills for \"{args.intent}\":\n")
            for i, m in enumerate(matches, 1):
                print(f"   {i}. {m['name']} (score: {m['score']})")
                print(f"      {m['description'][:100]}")
                print()
        else:
            print("   No matches. Try 'sync' to refresh the index.")

    elif args.command == "list":
        if not INDEX_PATH.exists():
            sync_from_agi(args.agi_path)

        index = load_index()
        skills = index.get("skills", [])

        if args.json:
            print(json.dumps([{"name": s["name"], "description": s["description"][:200]} for s in skills], indent=2))
        else:
            print(f"\n📦 {len(skills)} skills (synced: {index.get('synced_at', 'never')}):\n")
            for s in skills:
                print(f"   • {s['name']} — {s['description'][:80]}")

    elif args.command == "info":
        if not args.skill:
            print("❌ --skill required"); sys.exit(1)

        if not INDEX_PATH.exists():
            sync_from_agi(args.agi_path)

        index = load_index()
        skill = next((s for s in index.get("skills", []) if s["name"] == args.skill), None)

        if not skill:
            print(f"❌ Skill '{args.skill}' not found"); sys.exit(1)

        if args.json:
            print(json.dumps(skill, indent=2))
        else:
            print(f"\n📦 {skill['name']}")
            print(f"   {skill['description']}")
            print(f"   Scripts: {', '.join(skill['scripts']) or 'none'}")
            print(f"   Keywords: {', '.join(skill['keywords'][:15])}")

    elif args.command == "generate-team":
        if not args.intent:
            print("❌ --intent required"); sys.exit(1)

        if not INDEX_PATH.exists():
            sync_from_agi(args.agi_path)

        print(f"🏗️  Generating team for: \"{args.intent}\"\n")

        matches = discover_skills(args.intent, args.top_k)
        team = generate_team(args.intent, matches)

        if args.json:
            print(json.dumps(team, indent=2))
        else:
            squad = team["squad"]
            print(f"   Team: {squad['name']}")
            print(f"   Agents: {len(squad['roles'])}\n")
            for i, role in enumerate(squad["roles"], 1):
                print(f"   {i}. {role['name']} → {role['role'][:70]}")
                print(f"      Tools: {', '.join(role['tools'])}")
            print(f"\n   Pipeline: {' → '.join(squad['pipeline_sequence'])}")
            print(f"   Checkpoints: {len(squad['checkpoints'])}")

        # Save if output dir specified
        if args.output_dir:
            out_dir = Path(args.output_dir) / team["squad"]["squad_name"]
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "squad.json").write_text(json.dumps(team, indent=2))
            print(f"\n   💾 Saved to {out_dir / 'squad.json'}")


if __name__ == "__main__":
    main()
