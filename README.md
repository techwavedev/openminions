<div align="center">

# 🤖 openminions

**Create AI teams that work together — powered by real intelligence, not templates.**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Node](https://img.shields.io/badge/node-%3E%3D18-brightgreen.svg)](https://nodejs.org)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://python.org)
[![Security](https://img.shields.io/badge/security-hardened-green.svg)](#-security)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/techwavedev/openminions/pulls)

*Describe what you need → openminions designs your team → agents execute with full transparency*

---

</div>

## What is openminions?

openminions is a **multi-agent orchestration framework** built on top of [@techwavedev/agi-agent-kit](https://www.npmjs.com/package/@techwavedev/agi-agent-kit). It creates teams of specialized AI agents that collaborate on complex tasks — from content creation to code reviews, competitive analysis to email campaigns.

Unlike template-based tools, openminions uses **Qdrant-backed semantic search** to automatically discover and wire the best skills for your task. Your agents aren't pre-built — they're **designed on the fly** based on your intent.

## What is a Team?

A team (internally called a "squad") is a group of AI agents that collaborate on a task. Each agent has a specific role and set of tools. They run in a pipeline with **checkpoints** where execution pauses for your approval before continuing.

Example — **Content Pipeline**:

```
📋 Researcher → ✍️ Writer → 🎨 Designer → ✅ Editor
                  ↑                          ↑
              checkpoint                 checkpoint
           "Review research"          "Approve final draft"
```

- **Researcher** gathers information from web sources
- **Writer** produces compelling long-form content
- **Designer** generates hero images and illustrations
- **Editor** reviews, polishes, and SEO-optimizes the piece

Each agent transitions through states: `idle` → `working` → `delivering` → `done` — all visible in the real-time dashboard.

## Who is it for?

- **Solo developers** — automate research, documentation, and code review pipelines
- **Content creators** — produce blog posts, social media campaigns, and newsletters with AI teams
- **Agencies & freelancers** — create reusable pipelines for client work
- **Marketing teams** — generate consistent content with human approval at key stages
- **Engineering teams** — automate code analysis, security audits, and documentation generation

## What can you do with it?

| Category | Examples |
|----------|----------|
| 📝 **Content production** | Blog posts, social media campaigns, newsletters, documentation |
| 🔍 **Research & analysis** | Competitive analysis, market research, trend monitoring |
| 💻 **Code operations** | Code review, security audit, documentation generation, refactoring plans |
| 📧 **Outreach** | Personalized email sequences, lead research, campaign management |
| 📊 **Data → Insights** | Transform raw data into reports, presentations, and dashboards |
| 🎨 **Visual content** | Generate images, design social media assets, create brand materials |

## Quick Start

**Prerequisites:** Node.js 18+ · Python 3.10+ · [agi-agent-kit](https://www.npmjs.com/package/@techwavedev/agi-agent-kit)

### 1. Clone & Install

```bash
git clone https://github.com/techwavedev/openminions.git
cd openminions
npm install
cd ui && npm install && cd ..
```

### 2. Interactive Setup

```bash
node bin/cli.js init
```

The setup wizard walks you through:
1. **Language** — English, Português, Español
2. **IDE** — Antigravity, Claude Code, Cursor, Copilot, OpenCode, Codex
3. **Scenario** — pick from 6 predefined templates or describe your own
4. **Review** — see the team lineup and approve before anything runs

### 3. Run Your Team

```bash
# From a scenario
python3 bin/runner.py --squad data/squads/blog-content-pipeline

# From natural language
python3 bin/runner.py --intent "Research AI trends and write a detailed report" --auto

# Preview without execution
python3 bin/runner.py --squad data/squads/blog-content-pipeline --dry-run
```

### 4. Watch in Real Time

```bash
npm run dev
# Open http://localhost:5173
```

The Phaser-powered dashboard shows your agents working as animated sprites, with live status transitions and step tracking.

## Supported IDEs

| IDE | Status |
|-----|--------|
| Antigravity (Gemini) | ✅ Available |
| Claude Code | ✅ Available |
| Cursor | ✅ Available |
| VS Code + Copilot | ✅ Available |
| OpenCode | ✅ Available |
| Codex (OpenAI) | ✅ Available |

## Predefined Scenarios

These are ready-to-use team templates. Pick one during `init` or create your own:

| Scenario | Agents | Description |
|----------|--------|-------------|
| ✍️ Blog Content Pipeline | Researcher → Writer → Designer → Editor | Research, write, illustrate, and polish blog posts |
| 🔍 Code Review Squad | Analyzer → SecurityAuditor → Optimizer → Reporter | Full codebase analysis with security and performance |
| 📱 Social Media Campaign | Strategist → Copywriter → VisualDesigner → Scheduler | Multi-platform social campaign with visuals |
| 📊 Competitive Analysis | Scout → PricingAnalyst → FeatureMapper → Strategist | Deep competitor research with strategic recommendations |
| 📧 Email Outreach | LeadResearcher → Copywriter → Reviewer → Sender | Prospect research, email crafting, and delivery via Resend |
| 📚 Documentation Generator | CodeScanner → APIDocWriter → GuideWriter → Formatter | Automated documentation from codebase analysis |

## Commands

| Command | What it does |
|---------|-------------|
| `node bin/cli.js init` | Interactive setup (language, IDE, scenario) |
| `node bin/cli.js scenarios` | List all available scenarios |
| `node bin/cli.js teams` | List created teams and their status |
| `node bin/cli.js run --intent "..."` | Design + execute a team from natural language |
| `node bin/cli.js run --squad <path>` | Execute an existing team |
| `node bin/cli.js dashboard` | Start the visual dashboard |
| `python3 bin/architect_wizard.py --intent "..."` | Design a team with Atlas (the architect) |

## Architecture

openminions follows a **3-layer architecture**: Directives → Orchestration → Execution.

```
┌─────────────────────────────────────────────────────────┐
│                     openminions                         │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  CLI     │  │ Architect│  │  Runner  │  │  Dash  │ │
│  │ (init)   │→ │ (Atlas)  │→ │(execute) │→ │ (view) │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│       ↕              ↕              ↕            ↕      │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Qdrant Memory Layer                 │  │
│  │    Skills index · Squad history · Decisions      │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↕                               │
│  ┌──────────────────────────────────────────────────┐  │
│  │         @techwavedev/agi-agent-kit               │  │
│  │    Skills · Execution scripts · Local LLM        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**What makes it different:**

- 🧠 **Intelligence, not templates** — skills are discovered via semantic search, not manually installed
- ⚡ **Dynamic teams** — agents are created on-the-fly from your intent, not predefined
- 🔒 **Validation gates** — security checks before and after every execution step
- 👁️ **Full transparency** — `runs.md` and `memories.md` log everything in human-readable format
- 🌍 **Multi-IDE, multi-language** — works across 6 IDEs and 3 languages out of the box

## Token Cost

openminions is **free and open source** as software. You can run it at zero cost with:
- **Antigravity** (Gemini free tier)
- **Local LLMs** via Ollama (Gemma, GLM, etc.)

If using paid stacks (Claude Code, OpenAI API), each team execution consumes tokens. The cost depends on:
- Number of agents in the pipeline
- Complexity of the task
- Model used for each step

> 💡 Use `--dry-run` to preview the full pipeline without consuming any tokens.

## 🔒 Security

This project takes security seriously:

- **Pre-push hook** — `bin/security_gate.py` scans for secrets before every push
- **GitHub Secret Scanning** — enabled with push protection
- **CodeQL Analysis** — runs on every PR (JavaScript/TypeScript + Python)
- **TruffleHog** — deep secret scanning in CI
- **Dependency Review** — blocks PRs introducing known vulnerabilities
- **Dependabot** — automatic security updates
- **Branch Protection** — all changes require PR with passing checks
- **Squash Merge Only** — clean commit history, no accidental leaks

See [SECURITY.md](SECURITY.md) for the full security policy and vulnerability reporting.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full development plan from v0.1.0 to v1.0.0.

## About

openminions is built and maintained by [Elton Machado](https://github.com/techwavedev) as the first product evolution from the [@techwavedev/agi-agent-kit](https://www.npmjs.com/package/@techwavedev/agi-agent-kit) framework.

The project was born from a real need to orchestrate AI agents intelligently — not with static templates, but with semantic understanding that adapts to each task.

Contributions are welcome via Issues and Pull Requests. See the [issue templates](.github/ISSUE_TEMPLATE/) before opening anything.

## License

Apache-2.0 — see [LICENSE](LICENSE) for details.
