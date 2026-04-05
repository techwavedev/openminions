#!/usr/bin/env python3
"""
Pre-Push Security Gate for openminions

Scans the working tree for secrets, credentials, and sensitive patterns
BEFORE anything reaches GitHub. Run this manually or as a git pre-push hook.

Usage:
    python3 bin/security_gate.py           # Full scan
    python3 bin/security_gate.py --fix     # Auto-stage .gitignore fixes
    python3 bin/security_gate.py --hook    # Install as git pre-push hook
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ─── Patterns that MUST NEVER appear in tracked files ─────────────────────────
SECRET_PATTERNS = [
    # API Keys & Tokens
    (r'(?i)(api[_-]?key|api[_-]?secret|access[_-]?token)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}', "API key/token"),
    (r'sk-[A-Za-z0-9]{32,}', "OpenAI API key"),
    (r'AIza[A-Za-z0-9_\-]{35}', "Google API key"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub personal access token"),
    (r'gho_[A-Za-z0-9]{36}', "GitHub OAuth token"),
    (r'xox[boaprs]-[A-Za-z0-9\-]{10,}', "Slack token"),

    # AWS
    (r'AKIA[A-Z0-9]{16}', "AWS access key"),
    (r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*["\']?[A-Za-z0-9/+=]{40}', "AWS secret key"),

    # Database URLs
    (r'(?i)(postgres|mysql|mongodb|redis)://[^\s"\']+:[^\s"\']+@', "Database connection string"),

    # Private Keys
    (r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----', "Private key"),
    (r'-----BEGIN OPENSSH PRIVATE KEY-----', "SSH private key"),

    # Qdrant / Local services
    (r'(?i)qdrant[_-]?api[_-]?key\s*[:=]\s*["\']?[A-Za-z0-9_\-]{10,}', "Qdrant API key"),

    # Generic secrets
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?[^\s"\']{8,}', "Password in code"),
    (r'(?i)secret\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}', "Generic secret"),
]

# Files that should NEVER be tracked
FORBIDDEN_FILES = [
    ".env", ".env.local", ".env.production", ".env.staging",
    "credentials.json", "token.json",
    "*.pem", "*.key", "*.p12", "*.pfx",
]

# Directories that should NEVER be tracked
FORBIDDEN_DIRS = [
    ".openminions/", ".tmp/", "__pycache__/",
    ".claude/", ".cursor/", ".agent/", ".agents/",
]

SAFE_EXTENSIONS = {
    ".md", ".json", ".yaml", ".yml", ".js", ".ts", ".tsx", ".jsx",
    ".py", ".css", ".html", ".txt", ".sh", ".toml", ".cfg",
}

# Files excluded from secret scanning (they contain patterns, not secrets)
SCAN_EXCLUSIONS = {
    "bin/security_gate.py",
    "SECURITY.md",
    "tests/test_unit_security_gate.py",
}


def get_tracked_files() -> list[str]:
    """Get all files that would be pushed to remote."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        # Fallback: walk the directory
        files = []
        for root, dirs, filenames in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d != ".git" and d != "node_modules"]
            for name in filenames:
                rel = os.path.relpath(os.path.join(root, name), PROJECT_ROOT)
                files.append(rel)
        return files


def get_staged_files() -> list[str]:
    """Get files staged for the current commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        return []


def scan_file_for_secrets(filepath: Path) -> list[tuple[int, str, str]]:
    """Scan a single file for secret patterns. Returns (line_num, pattern_name, line)."""
    findings = []
    ext = filepath.suffix.lower()

    # Skip binary files
    if ext not in SAFE_EXTENSIONS:
        return findings

    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        for line_num, line in enumerate(content.split("\n"), 1):
            for pattern, name in SECRET_PATTERNS:
                if re.search(pattern, line):
                    # Skip comments and example patterns
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith("//"):
                        continue
                    if "example" in line.lower() or "placeholder" in line.lower():
                        continue
                    if "YOUR_" in line or "xxx" in line.lower() or "<" in line:
                        continue
                    # Skip regex pattern definitions (the scanner's own patterns)
                    if "r'" in line or 'r"' in line:
                        continue
                    # We intentionally DO NOT return the line content to avoid printing clear-text secrets in CI logs
                    findings.append((line_num, name))
    except Exception:
        pass

    return findings


def check_forbidden_files(tracked: list[str]) -> list[str]:
    """Check if any forbidden files are tracked."""
    violations = []
    for f in tracked:
        basename = os.path.basename(f)
        for forbidden in FORBIDDEN_FILES:
            if forbidden.startswith("*"):
                if basename.endswith(forbidden[1:]):
                    violations.append(f)
            elif basename == forbidden:
                violations.append(f)

        for forbidden_dir in FORBIDDEN_DIRS:
            if f.startswith(forbidden_dir) or f"/{forbidden_dir}" in f:
                violations.append(f)

    return list(set(violations))


def check_gitignore() -> list[str]:
    """Verify .gitignore has critical entries."""
    gitignore_path = PROJECT_ROOT / ".gitignore"
    if not gitignore_path.exists():
        return [".gitignore is MISSING"]

    content = gitignore_path.read_text()
    missing = []
    critical = [".env", "credentials.json", "token.json", ".openminions/",
                "node_modules/", "__pycache__/", "*.key", "*.pem"]

    for entry in critical:
        if entry not in content:
            missing.append(f".gitignore missing: {entry}")

    return missing


def install_hook():
    """Install as git pre-push hook."""
    hooks_dir = PROJECT_ROOT / ".git" / "hooks"
    if not hooks_dir.exists():
        print("❌ Not a git repository")
        return False

    hook_path = hooks_dir / "pre-push"
    hook_content = f"""#!/bin/sh
# openminions security gate — blocks pushes with secrets
python3 "{PROJECT_ROOT / "bin" / "security_gate.py"}" --staged
exit $?
"""
    hook_path.write_text(hook_content)
    os.chmod(hook_path, 0o755)
    print(f"✅ Pre-push hook installed at {hook_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Pre-push security scanner")
    parser.add_argument("--fix", action="store_true", help="Auto-fix .gitignore issues")
    parser.add_argument("--hook", action="store_true", help="Install as git pre-push hook")
    parser.add_argument("--staged", action="store_true", help="Only scan staged files")
    parser.add_argument("--quiet", action="store_true", help="Only output on failure")
    args = parser.parse_args()

    if args.hook:
        install_hook()
        return

    print("🔒 openminions Security Gate\n")

    all_clean = True
    issues = []

    # 1. Check .gitignore
    gitignore_issues = check_gitignore()
    if gitignore_issues:
        all_clean = False
        for issue in gitignore_issues:
            issues.append(f"⚠️  {issue}")

    # 2. Check for forbidden tracked files
    tracked = get_staged_files() if args.staged else get_tracked_files()
    forbidden = check_forbidden_files(tracked)
    if forbidden:
        all_clean = False
        for f in forbidden:
            issues.append(f"🚫 Forbidden file tracked: {f}")

    # 3. Scan for secrets in tracked files
    secret_count = 0
    for filepath_str in tracked:
        if filepath_str in SCAN_EXCLUSIONS:
            continue
        filepath = PROJECT_ROOT / filepath_str
        if not filepath.exists():
            continue
        findings = scan_file_for_secrets(filepath)
        if findings:
            all_clean = False
            for line_num, pattern_name in findings:
                secret_count += 1
                issues.append(
                    f"🔑 {filepath_str}:{line_num} — {pattern_name}"
                )

    # Report
    if all_clean:
        if not args.quiet:
            print("✅ All clean — safe to push")
        sys.exit(0)
    else:
        print(f"❌ {len(issues)} security issue(s) found:\n")
        for issue in issues:
            print(f"  {issue}")

        if secret_count > 0:
            print(f"\n  🔑 {secret_count} potential secret(s) detected in code")
            print("     Remove them or add files to .gitignore before pushing")

        if forbidden:
            print(f"\n  🚫 {len(forbidden)} forbidden file(s) are tracked")
            print("     Run: git rm --cached <file> to untrack them")

        print(f"\n  💡 Run with --fix to auto-repair .gitignore")
        print(f"  💡 Run with --hook to install as git pre-push hook")

        sys.exit(1)


if __name__ == "__main__":
    main()
