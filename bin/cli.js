#!/usr/bin/env node
/**
 * openminions CLI
 *
 * The first evolution from @techwavedev/agi-agent-kit.
 * Dynamic multi-agent team orchestration with Qdrant-backed intelligence.
 *
 * Usage:
 *   npx openminions init              Interactive setup (language, IDE, scenario)
 *   npx openminions run               Run a squad (--intent or --squad)
 *   npx openminions scenarios         List available scenarios
 *   npx openminions teams             List created teams
 *   npx openminions dashboard         Start the visual dashboard
 */

const fs = require("fs");
const path = require("path");
const readline = require("readline");
const { execSync, spawn } = require("child_process");

// ─── Colors ──────────────────────────────────────────────────────────────────
const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  cyan: "\x1b[36m",
  red: "\x1b[31m",
  magenta: "\x1b[35m",
};

const log = {
  info: (msg) => console.log(`${c.cyan}ℹ${c.reset} ${msg}`),
  ok: (msg) => console.log(`${c.green}✔${c.reset} ${msg}`),
  warn: (msg) => console.log(`${c.yellow}⚠${c.reset} ${msg}`),
  err: (msg) => console.log(`${c.red}✖${c.reset} ${msg}`),
  header: (msg) => console.log(`\n${c.bold}${c.blue}${msg}${c.reset}\n`),
  step: (n, msg) => console.log(`  ${c.dim}${n}.${c.reset} ${msg}`),
};

// ─── i18n ────────────────────────────────────────────────────────────────────
const LANG_MAP = {
  "English": "en",
  "Português (Brasil)": "pt-BR",
  "Español": "es",
};

let strings = {};

function loadLocale(langLabel) {
  const code = LANG_MAP[langLabel] || "en";
  const localePath = path.join(__dirname, "..", "src", "locales", `${code}.json`);
  const fallbackPath = path.join(__dirname, "..", "src", "locales", "en.json");

  try {
    strings = JSON.parse(fs.readFileSync(localePath, "utf-8"));
  } catch {
    strings = JSON.parse(fs.readFileSync(fallbackPath, "utf-8"));
  }
}

function t(key) {
  return strings[key] || key;
}

// ─── Interactive Prompts ─────────────────────────────────────────────────────
function createRL() {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
}

function ask(rl, question) {
  return new Promise((resolve) => rl.question(question, resolve));
}

async function choose(rl, question, options) {
  console.log(`\n  ${c.bold}${question}${c.reset}`);
  options.forEach((opt, i) => {
    const marker = opt.default ? `${c.cyan}→${c.reset}` : " ";
    console.log(`  ${marker} ${c.dim}${i + 1}.${c.reset} ${opt.icon || ""} ${opt.label}`);
  });

  const answer = await ask(rl, `\n  ${c.dim}Choice [1-${options.length}]:${c.reset} `);
  const idx = parseInt(answer, 10) - 1;
  if (idx >= 0 && idx < options.length) return options[idx];
  return options[0]; // default to first
}

async function multiChoose(rl, question, options) {
  console.log(`\n  ${c.bold}${question}${c.reset}`);
  options.forEach((opt, i) => {
    const check = opt.checked ? `${c.green}[x]${c.reset}` : "[ ]";
    console.log(`   ${check} ${c.dim}${i + 1}.${c.reset} ${opt.label}`);
  });

  const answer = await ask(rl, `\n  ${c.dim}Enter numbers separated by commas (e.g. 1,3,5):${c.reset} `);
  const indices = answer.split(",").map((s) => parseInt(s.trim(), 10) - 1);
  const selected = indices.filter((i) => i >= 0 && i < options.length).map((i) => options[i]);
  return selected.length > 0 ? selected : options.filter((o) => o.checked);
}

// ─── Constants ───────────────────────────────────────────────────────────────
const LANGUAGES = [
  { label: "English", value: "English", icon: "🇺🇸", default: true },
  { label: "Português (Brasil)", value: "Português (Brasil)", icon: "🇧🇷" },
  { label: "Español", value: "Español", icon: "🇪🇸" },
];

const IDES = [
  { label: "Antigravity (Gemini)", value: "antigravity", checked: true },
  { label: "Claude Code", value: "claude-code", checked: true },
  { label: "Cursor", value: "cursor" },
  { label: "VS Code + Copilot", value: "vscode-copilot" },
  { label: "OpenCode", value: "opencode" },
  { label: "Codex (OpenAI)", value: "codex" },
];

// ─── Scenarios ───────────────────────────────────────────────────────────────
function loadScenarios() {
  const catalogPath = path.join(__dirname, "..", "scenarios", "catalog.json");
  try {
    return JSON.parse(fs.readFileSync(catalogPath, "utf-8"));
  } catch {
    return {};
  }
}

// ─── IDE Template Generation ─────────────────────────────────────────────────
function generateIdeTemplates(targetDir, ides, preferences) {
  for (const ide of ides) {
    switch (ide.value || ide) {
      case "antigravity":
        writeIdeTemplate(targetDir, ".agent/workflows/openminions.md", `---
description: Run openminions squad from this workspace
---

1. Check squad status: \`python3 ${targetDir}/bin/runner.py --squad ${targetDir}/data/squads/<name>\`
2. Start dashboard: \`cd ${targetDir}/ui && npm run dev\`
3. Design new squad: \`python3 ${targetDir}/bin/architect_wizard.py --intent "your goal"\`
`);
        writeIdeTemplate(targetDir, ".agent/rules/openminions.md",
          `# openminions Rules\n\nThis workspace uses openminions for multi-agent orchestration.\n- Squads are defined in \`data/squads/\`\n- Skills come from @techwavedev/agi-agent-kit\n- Use the 3-layer architecture: Directives → Orchestration → Execution\n`);
        break;

      case "claude-code":
        writeIdeTemplate(targetDir, ".claude/skills/openminions/SKILL.md", `---
name: openminions
description: Multi-agent team orchestration powered by agi-agent-kit
---

# openminions Skill

## When to Use
- User wants to create a team of AI agents for a complex task
- User mentions "squad", "team", "pipeline", or "multi-agent"

## How to Use
1. Check scenarios: \`cat scenarios/catalog.json\`
2. Design team: \`python3 bin/architect_wizard.py --intent "user's goal"\`
3. Run team: \`python3 bin/runner.py --squad data/squads/<name>\`
4. Dashboard: \`cd ui && npm run dev\`
`);
        writeIdeTemplate(targetDir, "CLAUDE.md",
          `# openminions\n\nMulti-agent orchestrator. See .claude/skills/openminions/SKILL.md for usage.\n`);
        break;

      case "cursor":
        writeIdeTemplate(targetDir, ".cursor/rules/openminions.mdc",
          `# openminions Rules\n\nThis project uses openminions for multi-agent orchestration.\nSquads in data/squads/. Skills from @techwavedev/agi-agent-kit.\nRun: python3 bin/runner.py --intent "goal" --auto\n`);
        break;

      case "vscode-copilot":
        writeIdeTemplate(targetDir, ".github/prompts/openminions.prompt.md",
          `# openminions\n\nMulti-agent orchestrator powered by agi-agent-kit.\nDesign squads: python3 bin/architect_wizard.py --intent "goal"\nRun squads: python3 bin/runner.py --squad data/squads/<name>\n`);
        break;

      case "opencode":
        writeIdeTemplate(targetDir, ".opencode/commands/openminions.md",
          `# openminions\n\nDesign: python3 bin/architect_wizard.py --intent "goal"\nRun: python3 bin/runner.py --squad data/squads/<name>\nDashboard: cd ui && npm run dev\n`);
        writeIdeTemplate(targetDir, "AGENTS.md",
          `# openminions\n\nMulti-agent orchestrator. Use bin/runner.py for pipeline execution.\n`);
        break;

      case "codex":
        writeIdeTemplate(targetDir, ".agents/skills/openminions/SKILL.md", `---
name: openminions
description: Multi-agent team orchestration
---
Design: python3 bin/architect_wizard.py --intent "goal"
Run: python3 bin/runner.py --squad data/squads/<name>
`);
        break;
    }
  }
}

function writeIdeTemplate(baseDir, relativePath, content) {
  const fullPath = path.join(baseDir, relativePath);
  fs.mkdirSync(path.dirname(fullPath), { recursive: true });
  fs.writeFileSync(fullPath, content, "utf-8");
  log.ok(`  ${relativePath}`);
}

// ─── Squad Creation from Scenario ────────────────────────────────────────────
function createSquadFromScenario(targetDir, scenarioKey, scenario, userIntent) {
  const squadDir = path.join(targetDir, "data", "squads", scenarioKey);
  fs.mkdirSync(squadDir, { recursive: true });

  const config = {
    squad: {
      squad_name: scenarioKey,
      name: scenario.name,
      description: userIntent || scenario.description,
      icon: scenario.icon,
      code: scenarioKey,
      agents: scenario.roles.map((r) => r.name),
      roles: scenario.roles,
      pipeline_sequence: scenario.pipeline_sequence,
      checkpoints: scenario.checkpoints || [],
    },
  };

  // Write as JSON (no PyYAML dependency needed)
  const configPath = path.join(squadDir, "squad.json");
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2), "utf-8");

  // Also write a squad.yaml for the dashboard watcher
  const yamlContent = `squad:
  code: "${scenarioKey}"
  name: "${scenario.name}"
  description: "${userIntent || scenario.description}"
  icon: "${scenario.icon}"
  agents:
${scenario.roles.map((r) => `    - "${r.name}"`).join("\n")}
`;
  fs.writeFileSync(path.join(squadDir, "squad.yaml"), yamlContent, "utf-8");

  return squadDir;
}

// ─── Init Command ────────────────────────────────────────────────────────────
async function init(targetDir) {
  const rl = createRL();

  try {
    // 1. Language
    console.log(`\n  ${c.bold}${c.magenta}🤖 openminions${c.reset} ${c.dim}— AI teams that actually work${c.reset}\n`);

    const langChoice = await choose(rl, "What language do you prefer for outputs?", LANGUAGES);
    loadLocale(langChoice.value || langChoice.label);

    console.log(`\n  ${t("welcome")}\n`);

    // 2. Name
    const userName = await ask(rl, `  ${t("askName")} `);

    // 3. IDEs
    const selectedIdes = await multiChoose(rl, t("chooseIdes"), IDES);

    // 4. Scenario or Custom
    const scenarios = loadScenarios();
    const scenarioKeys = Object.keys(scenarios);

    const modeChoice = await choose(rl, t("scenarioOrCustom"), [
      { label: t("fromScenario"), value: "scenario", icon: "📋" },
      { label: t("custom"), value: "custom", icon: "✨" },
    ]);

    let squadDir = null;

    if (modeChoice.value === "scenario") {
      // Pick scenario
      const scenarioOptions = scenarioKeys.map((key) => ({
        label: `${scenarios[key].name} — ${scenarios[key].description}`,
        value: key,
        icon: scenarios[key].icon,
      }));

      const scenarioChoice = await choose(rl, t("chooseScenario"), scenarioOptions);
      const scenario = scenarios[scenarioChoice.value];

      // Optional: customize intent
      const intent = await ask(rl, `\n  ${t("describeIntent")} `);

      console.log(`\n  ${t("teamCreating")}`);
      squadDir = createSquadFromScenario(targetDir, scenarioChoice.value, scenario, intent.trim());

      // Show the team
      console.log(`\n  ${t("teamDesigned")}\n`);
      scenario.roles.forEach((role, i) => {
        const pos = scenario.pipeline_sequence.indexOf(role.name) + 1;
        console.log(`   ${c.cyan}${pos}.${c.reset} ${c.bold}${role.name}${c.reset} — ${role.role}`);
        console.log(`      ${c.dim}Tools: ${role.tools.join(", ")}${c.reset}`);
      });
    } else {
      // Custom: use architect wizard
      const intent = await ask(rl, `\n  ${t("describeIntent")} `);
      console.log(`\n  ${t("teamCreating")}`);

      try {
        execSync(
          `python3 "${path.join(targetDir, "bin", "architect_wizard.py")}" --intent "${intent.trim()}" --output-dir "${path.join(targetDir, "data", "squads")}"`,
          { stdio: "inherit" }
        );
      } catch (e) {
        log.err("Architect wizard failed. You can try again with: python3 bin/architect_wizard.py --intent 'your goal'");
      }
    }

    // 5. Generate IDE templates
    log.header("Setting up IDE integrations...");
    generateIdeTemplates(targetDir, selectedIdes, {
      language: langChoice.value || langChoice.label,
      userName,
    });

    // 6. Write preferences
    const prefsDir = path.join(targetDir, ".openminions");
    fs.mkdirSync(prefsDir, { recursive: true });
    const prefs = {
      userName,
      language: langChoice.value || langChoice.label,
      ides: selectedIdes.map((ide) => ide.value || ide),
      createdAt: new Date().toISOString(),
    };
    fs.writeFileSync(
      path.join(prefsDir, "preferences.json"),
      JSON.stringify(prefs, null, 2),
      "utf-8"
    );

    // 7. Ensure data/squads exists
    fs.mkdirSync(path.join(targetDir, "data", "squads"), { recursive: true });

    // 8. Done!
    console.log(`\n  ${t("success")}`);
    console.log(`  ${c.yellow}${t("tokenCostWarning")}${c.reset}`);
    console.log(`\n  ${t("nextSteps")}`);

    for (const ide of selectedIdes) {
      const ideValue = ide.value || ide;
      const stepKey = `step1${ideValue.charAt(0).toUpperCase() + ideValue.slice(1).replace(/-([a-z])/g, (_, l) => l.toUpperCase())}`;
      if (t(stepKey) !== stepKey) {
        console.log(`  ${t(stepKey)}`);
      }
    }

    console.log(`\n  ${c.dim}${t("dashboardHint")}${c.reset}`);

    if (squadDir) {
      console.log(`\n  ${c.bold}Quick run:${c.reset}`);
      console.log(`  ${c.cyan}python3 bin/runner.py --squad ${squadDir} --dry-run${c.reset}\n`);
    }
  } finally {
    rl.close();
  }
}

// ─── Scenario Command ─────────────────────────────────────────────────────────
function listScenarios() {
  const scenarios = loadScenarios();
  log.header("Available Scenarios");

  for (const [key, scenario] of Object.entries(scenarios)) {
    console.log(`  ${scenario.icon} ${c.bold}${scenario.name}${c.reset} ${c.dim}(${key})${c.reset}`);
    console.log(`    ${scenario.description}`);
    console.log(`    ${c.dim}Agents: ${scenario.pipeline_sequence.join(" → ")}${c.reset}`);
    console.log(`    ${c.dim}Tags: ${scenario.tags.join(", ")}${c.reset}\n`);
  }
}

async function createScenario(targetDir, intentArg) {
  const rl = createRL();
  try {
    let intent = intentArg;
    if (!intent) {
      console.log(`\n  ${c.bold}Create Custom Scenario${c.reset}`);
      intent = await ask(rl, `  ${t("describeIntent")} `);
    }
    
    console.log(`\n  ${t("teamCreating")}`);
    try {
      execSync(
        `python3 "${path.join(targetDir, "bin", "skill_discovery.py")}" generate-team --intent "${intent.trim()}" --output-dir "${path.join(targetDir, "data", "squads")}"`,
        { stdio: "inherit" }
      );
    } catch (e) {
      log.err("Failed to create scenario.");
    }
  } finally {
    rl.close();
  }
}


// ─── Teams Command ───────────────────────────────────────────────────────────
function listTeams(targetDir) {
  const squadsDir = path.join(targetDir, "data", "squads");
  log.header("Created Teams");

  if (!fs.existsSync(squadsDir)) {
    log.info("No teams yet. Run: npx openminions init");
    return;
  }

  const entries = fs.readdirSync(squadsDir, { withFileTypes: true });
  for (const entry of entries) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) continue;

    const configPath = path.join(squadsDir, entry.name, "squad.json");
    const yamlPath = path.join(squadsDir, entry.name, "squad.yaml");
    const statePath = path.join(squadsDir, entry.name, "state.json");

    let config = { squad: { name: entry.name, description: "" } };
    try {
      if (fs.existsSync(configPath)) {
        config = JSON.parse(fs.readFileSync(configPath, "utf-8"));
      }
    } catch {}

    const hasState = fs.existsSync(statePath);
    const status = hasState ? `${c.green}● active${c.reset}` : `${c.dim}○ idle${c.reset}`;
    const squad = config.squad || config;

    console.log(`  ${status} ${c.bold}${squad.name || entry.name}${c.reset}`);
    if (squad.description) console.log(`    ${squad.description}`);
    if (squad.pipeline_sequence) {
      console.log(`    ${c.dim}${squad.pipeline_sequence.join(" → ")}${c.reset}`);
    }
    console.log();
  }
}

function exportTeam(targetDir, teamName, destFile) {
  if (!teamName) {
    log.err("Please specify a team name to export. Usage: npx openminions team export <name> [dest]");
    return;
  }
  const squadPath = path.join(targetDir, "data", "squads", teamName, "squad.json");
  if (!fs.existsSync(squadPath)) {
    log.err(`Team '${teamName}' not found in data/squads/`);
    return;
  }
  
  const dest = destFile || `${teamName}.squad.json`;
  fs.copyFileSync(squadPath, dest);
  log.ok(`Exported team '${teamName}' to ${dest}`);
}

function importTeam(targetDir, sourceFile) {
  if (!sourceFile || !fs.existsSync(sourceFile)) {
    log.err("Please specify a valid source file to import. Usage: npx openminions team import <file>");
    return;
  }
  try {
    const content = fs.readFileSync(sourceFile, "utf-8");
    const data = JSON.parse(content);
    const squad = data.squad || data;
    
    if (!squad.squad_name || !squad.pipeline_sequence) {
      log.err("Invalid squad file format.");
      return;
    }
    
    const teamDir = path.join(targetDir, "data", "squads", squad.squad_name);
    fs.mkdirSync(teamDir, { recursive: true });
    
    fs.writeFileSync(path.join(teamDir, "squad.json"), JSON.stringify({ squad }, null, 2), "utf-8");
    
    log.ok(`Imported team '${squad.squad_name}' into data/squads/`);
  } catch (e) {
    log.err(`Failed to import team: ${e.message}`);
  }
}

// ─── Run Command ─────────────────────────────────────────────────────────────
function runSquad(targetDir, args) {
  const runnerPath = path.join(targetDir, "bin", "runner.py");
  const cmdArgs = ["python3", runnerPath, ...args];

  try {
    execSync(cmdArgs.join(" "), { stdio: "inherit", cwd: targetDir });
  } catch (e) {
    process.exitCode = 1;
  }
}

// ─── Dashboard Command ──────────────────────────────────────────────────────
function startDashboard(targetDir) {
  const uiDir = path.join(targetDir, "ui");
  log.info("Starting openminions dashboard...");
  log.info(`Dashboard: http://localhost:5173`);

  try {
    execSync("npm run dev", { stdio: "inherit", cwd: uiDir });
  } catch {
    log.err("Dashboard failed to start. Run 'npm install' in ui/ first.");
  }
}

// ─── Main ────────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const command = args[0];
const projectDir = process.cwd();

switch (command) {
  case "init":
    init(projectDir).catch((e) => {
      log.err(e.message);
      process.exitCode = 1;
    });
    break;

  case "scenarios":
    listScenarios();
    break;

  case "scenario":
    if (args[1] === "create") {
      let intent = null;
      const intentIdx = args.indexOf("--intent");
      if (intentIdx !== -1 && intentIdx + 1 < args.length) {
        intent = args[intentIdx + 1];
      }
      createScenario(projectDir, intent).catch((e) => {
        log.err(e.message);
        process.exitCode = 1;
      });
    } else {
      listScenarios();
    }
    break;

  case "teams":
  case "team":
    if (args[1] === "export") {
      exportTeam(projectDir, args[2], args[3]);
    } else if (args[1] === "import") {
      importTeam(projectDir, args[2]);
    } else {
      listTeams(projectDir);
    }
    break;

  case "run":
    runSquad(projectDir, args.slice(1));
    break;

  case "dashboard":
    startDashboard(projectDir);
    break;

  default:
    console.log(`
  ${c.bold}${c.magenta}🤖 openminions${c.reset} — AI teams that actually work
  ${c.dim}Powered by @techwavedev/agi-agent-kit${c.reset}

  ${c.bold}Usage:${c.reset}
    npx openminions init                       Interactive setup (language, IDE, scenario)
    npx openminions scenarios                  List available predefined scenarios
    npx openminions scenario create            Interactively build a custom scenario
    npx openminions teams                      List created teams
    npx openminions team export <name>         Export a team to a shareable JSON file
    npx openminions team import <file>         Import a team from a JSON file
    npx openminions run --intent "goal" --auto Design + execute a squad
    npx openminions run --squad data/squads/x  Execute existing squad
    npx openminions dashboard                  Start the visual dashboard

  ${c.bold}What makes openminions different:${c.reset}
    ${c.cyan}•${c.reset} Qdrant-backed intelligence — skills are auto-selected, not manually installed
    ${c.cyan}•${c.reset} Dynamic teams — agents created on-the-fly from your intent
    ${c.cyan}•${c.reset} 3-layer architecture — Directives → Orchestration → Execution
    ${c.cyan}•${c.reset} Real-time Phaser dashboard — watch your agents work
    ${c.cyan}•${c.reset} Validation gates — security checks before every execution
    ${c.cyan}•${c.reset} Multi-IDE — works with Claude, Cursor, Antigravity, Copilot, and more

  ${c.dim}Learn more: https://github.com/techwavedev/openminions${c.reset}
    `);
    if (command) process.exitCode = 1;
    break;
}
