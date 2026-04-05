# 🗺️ openminions Roadmap

> Development plan organized by milestone. Each feature should be tracked as a GitHub Issue and delivered via PR with full security scans passing before merge.

---

## v0.1.0 — Foundation (Current)

**Status: ✅ Complete (pending E2E test from Copilot)**

- [x] Project scaffold and repository setup
- [x] Architect Wizard (Atlas) — Qdrant-backed squad designer
- [x] Runner — Pipeline execution engine with state.json output
- [x] Dashboard — React + Phaser real-time agent visualization
- [x] Validation Gates — Pre/post execution security checks
- [x] Human-readable logs — `runs.md` and `memories.md`
- [x] Predefined scenarios catalog (6 templates)
- [x] CLI interactive setup (`node bin/cli.js init`)
- [x] Multi-IDE template generation (6 IDEs supported)
- [x] i18n — English, Portuguese, Spanish
- [x] Pre-push security gate (`bin/security_gate.py`)
- [x] Comprehensive `.gitignore` for public repo safety
- [x] GitHub Actions — CI/CD, secret scanning, dependency review
- [x] Git pre-push hook auto-install
- [x] End-to-end dry-run test *(assigned to Copilot — Issue #5)*

---

## v0.2.0 — Intelligence Layer

**Status: 🟢 Completed**

- [x] Skill auto-discovery — query agi-agent-kit's full skill catalog via Qdrant
- [x] Dynamic role generation — Atlas creates custom agent roles from skill metadata
- [x] Skill dependency resolution — auto-install required skills per scenario
- [x] Agent memory persistence — carry context between squad runs
- [x] Squad templates export/import (shareable `.squad.yaml` files)
- [x] Scenario builder CLI — `openminions scenario create`

---

## v0.3.0 — Dashboard Evolution

**Status: 🟢 Completed**

- [x] Dashboard redesign — premium dark theme with glassmorphism *(assigned to Copilot — Issue #7)*
- [x] Agent activity log panel (real-time output streaming) *(completed by Copilot — Issue #25)*
- [x] Squad history viewer (past runs with replay) *(completed by Copilot — Issue #27)*
- [x] Pipeline visualization (flowchart view) *(completed by Copilot — Issue #26)*
- [x] Mobile-responsive layout *(completed by Copilot — Issue #29)*
- [x] Dashboard auth (optional PIN/password gate) *(completed by Copilot — Issue #30)*

---

## v0.4.0 — Multi-Agent Execution

**Status: 🔄 In Progress**

- [ ] Parallel agent execution (non-dependent steps run concurrently) *(assigned to Copilot — Issue #8)*
- [ ] Agent-to-agent communication channels *(assigned to Copilot — Issue #32)*
- [ ] Conditional pipeline branching (if/else logic in squad.yaml) *(assigned to Copilot — Issue #33)*
- [ ] Error recovery with automatic retry and fallback agents
- [ ] Resource pool management (token budget tracking per squad)
- [ ] Execution sandboxing (isolated environments per agent)

---

## v0.5.0 — Ecosystem & Distribution

**Status: 📋 Planned**

- [ ] `npx openminions init` — one-command project scaffolding
- [ ] Published to npm as `@techwavedev/openminions`
- [ ] Community scenario marketplace (submit/discover scenarios)
- [ ] Plugin system — third-party skill integration
- [ ] API server mode — REST/WebSocket API for external integrations
- [ ] Docker support — `docker-compose up` for full stack

---

## v1.0.0 — Production Release

**Status: 📋 Planned**

- [ ] Full test suite (unit + integration + e2e)
- [ ] Performance benchmarks (token usage, execution time per scenario)
- [ ] Documentation site (guides, API reference, tutorials)
- [ ] VS Code extension — visual squad builder
- [ ] Team collaboration — shared squads across users
- [ ] Cloud deployment option (managed service)
- [ ] Telemetry (opt-in usage analytics)

---

## Governance

- **Every feature** → GitHub Issue first, then PR
- **Every PR** → Must pass: secret scanning, dependency review, lint, security gate
- **Branch protection** → `main` requires PR review, no direct pushes
- **Versioning** → Semantic versioning with patch-until-99 policy
- **Releases** → Tagged releases with CHANGELOG updates

---

## Comparison with Alternatives

| Feature | openminions | Alternative A | Alternative B |
|---------|------------|---------------|---------------|
| Dynamic team creation | ✅ Qdrant-backed | ❌ Static templates | ❌ Manual config |
| Real-time dashboard | ✅ Phaser + React | ⚠️ Basic logs | ❌ CLI only |
| Skill auto-selection | ✅ Semantic search | ❌ Manual install | ❌ Hardcoded |
| Multi-IDE support | ✅ 6 IDEs | ⚠️ 1-2 IDEs | ❌ Single IDE |
| Validation gates | ✅ Pre + Post | ⚠️ Post only | ❌ None |
| Memory persistence | ✅ Qdrant + local | ⚠️ Local only | ❌ None |
| i18n | ✅ 3 languages | ⚠️ Limited | ❌ English only |
| 3-layer architecture | ✅ Deterministic | ❌ Probabilistic | ❌ Monolithic |
