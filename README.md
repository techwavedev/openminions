# 🤖 openminions

**Next-generation multi-agent orchestrator** powered by [@techwavedev/agi-agent-kit](https://www.npmjs.com/package/@techwavedev/agi-agent-kit).

Describe your goal in natural language → openminions designs a team of specialized AI agents → they execute the pipeline while you watch in a real-time dashboard. Full human oversight with validation gates, checkpoints, and transparent execution logs.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🏗️ **Qdrant-Backed Architect** | Describe your goal → Atlas queries your skill index and designs a multi-agent pipeline |
| 🎮 **Real-Time Dashboard** | React + Phaser visual hub showing agent sprites working in real-time |
| 🔒 **Validation Gates** | Pre/post execution security checks block dangerous commands and validate outputs |
| 📝 **Human-Readable Logs** | `runs.md` + `memories.md` — fully transparent execution history |
| 🔍 **Checkpoints** | Human approval points at critical pipeline stages |
| 🧠 **Qdrant Memory** | All runs stored in Qdrant for cross-session intelligence |
| 🌐 **Multi-IDE** | Works with Antigravity, Claude Code, Cursor, Copilot, OpenCode, Codex |
| 🌍 **Multi-Language** | CLI in English, Portuguese, Spanish (more coming) |
| 📋 **Predefined Scenarios** | Ready-to-use team templates for common workflows |
| ⚡ **Dynamic Teams** | Agents created on-the-fly from the agi-agent-kit skill pool |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [agi-agent-kit](https://www.npmjs.com/package/@techwavedev/agi-agent-kit) installed
- Qdrant running locally (for memory features)
- Ollama with a model pulled (for local LLM execution)

### Install

```bash
git clone https://github.com/techwavedev/openminions.git
cd openminions
npm install
cd ui && npm install && cd ..
```

### Interactive Setup

```bash
node bin/cli.js init
```

This walks you through language, IDE, and scenario selection — then assembles your first team.

### Run a Squad

```bash
# Auto-design from intent
python3 bin/runner.py --intent "Research AI trends and write a report" --auto

# Run existing squad
python3 bin/runner.py --squad data/squads/blog-content-pipeline

# Dry run (preview without execution)
python3 bin/runner.py --squad data/squads/blog-content-pipeline --dry-run
```

### Start the Dashboard

```bash
npm run dev
# Open http://localhost:5173
```

---

## 🏛️ Architecture

openminions follows a **3-layer architecture**: Directives → Orchestration → Execution.

```
openminions (orchestrator)
├── bin/
│   ├── cli.js                 # Interactive CLI (init, scenarios, teams)
│   ├── architect_wizard.py    # Qdrant-backed squad designer (Atlas)
│   ├── runner.py              # Pipeline execution engine
│   └── security_gate.py       # Pre-push security scanner
├── ui/                        # React + Phaser real-time dashboard
├── scenarios/                 # Predefined team templates
│   └── catalog.json
├── src/
│   └── locales/               # i18n (en, pt-BR, es)
├── templates/
│   └── ide/                   # Multi-IDE integration templates
├── data/
│   └── squads/                # Squad configs + runtime state
└── package.json

         ↕ deep dependency

@techwavedev/agi-agent-kit (skills + execution engine)
├── execution/                 # Deterministic Python scripts
├── skills/                    # Modular capabilities
└── templates/                 # Agent scaffolding
```

### How It Works

1. **Intent** → Describe what you want in natural language
2. **Architect (Atlas)** → Queries Qdrant for relevant skills, designs a multi-agent pipeline
3. **Review** → You see the team lineup and approve
4. **Runner** → Executes each agent step, writing `state.json` for the dashboard
5. **Dashboard** → Phaser sprites animate in real-time as agents work
6. **Logs** → `runs.md` + `memories.md` + Qdrant storage for cross-session memory

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AGI_PATH` | `~/code/agi` | Path to agi-agent-kit installation |

---

## 🔒 Security

- **Pre-push gate**: `python3 bin/security_gate.py` scans for secrets before pushing
- **Validation gates**: Block dangerous patterns (`rm -rf`, `sudo`, `eval(`) 
- **Post-validation**: Output inspection for crash indicators
- **Checkpoints**: Human approval at critical pipeline stages
- **Local-first**: Sensitive tasks routed to local Ollama models via agi-agent-kit

---

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the full development plan.

---

## 📄 License

Apache-2.0 — see [LICENSE](LICENSE) for details.
