# Connecting to the Visual Dashboard

Openminions provides a highly detailed game-engine mapped visualization of your AI Teams.

## Setup

Inside the root directory, simply run:
```bash
npx openminions dashboard
```

Alternatively:
```bash
cd ui
npm run dev
```

Navigate to `http://localhost:5173`. 

If a lock prompt appears, enter the PIN specified in `ui/.env.local` (`VITE_DASHBOARD_PIN`). If no PIN is configured, you'll enter the workspace immediately.

## Tabs

- **Live Overview**: Uses WebSocket mapping over a Phaser canvas to visually chart which agent is actively calculating processing steps.
- **Squad Builder**: Visual drag-and-drop workflow configuration.
- **Process Map**: Architectural overview of tool connections.
- **History**: Historical review of pipeline metrics, token spend, and logs retrieved securely via Qdrant contexts.
