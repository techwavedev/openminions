# Build Your First Squad

Deploy an automated, isolated AI pipeline simply via the terminal. Let's design a "Deep Researcher" team!

## 1. Setup the Intent

Run `npx openminions init` on your system.

When prompted for what you want to achieve, type:
`"I want a two-agent squad. The first agent finds 3 sources about global logistics issues. The second agent summarizes them into a Markdown report."`

## 2. Review the Blueprint

Openminions uses the AGI intelligence router to generate a strict, deterministic `squad.json` structure for you inside `data/squads/<your-team-name>`.

You can freely edit the `.yaml` or `.json` to adjust tools available to specific agents.

## 3. Run Pipeline 

Hit `npx openminions run --squad data/squads/<your-team-name>`.

You can now watch the console logs, or flip over to the Visual Dashboard to watch your agents handoff information autonomously!
