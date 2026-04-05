# Changelog

All notable changes to this project will be documented in this file.

## [v0.1.1] - 2026-04-05
### Added
- Dynamic team generation from natural language intents via Qdrant skill auto-discovery (`skill_discovery.py`).
- Skill dependency resolver ensuring safe pipeline execution and auto-prompting missing AGI-agent-kit skills (`runner.py`).
- Agent memory persistence enabling background intelligence and historical state-retrieval cross-runs (`runner.py`).
- Squad configuration export to shareable `.squad.json` format (`openminions team export`).
- Squad configuration import parsing JSON natively (`openminions team import`).
- "Dogfood" system templates: generated `docs-team` and `master-orchestrator` orchestrating squads securely.
- Dashboard Redesign Prep: `ui/` codebase upgraded with deep space aesthetic, Tailwind CSS config, glassmorphism UI traits, and smooth React animations.

### Changed
- Dashboard's `SquadCard.tsx`, `SquadSelector.tsx`, and `StatusBar.tsx` refactored for new UI aesthetics.
- Dropped `.yaml` requirement to circumvent pipeline sequence serialization bugs.
