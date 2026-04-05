# CLI Reference

The `openminions` CLI provides core lifecycle management for deploying and running intelligent agent squads.

## Commands

### `npx openminions init`
Starts an interactive terminal dialog initializing your squad config. You'll specify your programming languages, IDE integrations, and custom scenario intents to form the team.

### `npx openminions scenarios`
Lists all globally available squad templates present in the local `scenarios` and plugin directories.

### `npx openminions scenario create`
Provides an interactive builder to design your own custom multi-agent sequence.

### `npx openminions teams`
Lists all activated teams found in the `data/squads` configuration datastore, alongside their operational status (e.g. `Idle` / `Active`).

### `npx openminions team export <name> [dest]`
Exports your finely-tuned squad logic locally to a robust JSON metadata package that can be imported to another environment.

### `npx openminions marketplace`
Connects to the central `openminions-marketplace` remote repository to let you easily download complex logic flows built by the community.

### `npx openminions run <args>`
Triggers an immediate pipeline execution.

- `--intent "goal"`: Dynamically compile a squad right now and run it.
- `--squad data/squads/<folder>`: Mount a specific existing squad folder.

### `npx openminions dashboard`
Fires up the Vite / Node.js development server to project your running pipelines onto the Real-time Action UI.
