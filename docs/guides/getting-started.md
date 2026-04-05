# Getting Started

## Installation

Ensure you have Node.js and Python 3.10+ installed.

1. Clone the repository:
```bash
git clone https://github.com/techwavedev/openminions.git
cd openminions
```

2. Generate your first AI squad via the wizard:
```bash
npx openminions init
```

3. Open the real-time visualizer dashboard:
```bash
npx openminions dashboard
```

## Running a Pipeline

From any project directory integrated with Openminions, simply type:

```bash
npx openminions run --squad data/squads/<squad-name>
```

Your pipeline will execute inside an isolated sandbox, maintaining clean logs and caching to your central vector database.
