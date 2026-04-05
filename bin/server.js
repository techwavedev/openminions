#!/usr/bin/env node

/**
 * openminions Production API Server
 * Serves the dashboard UI statically, provides the REST API, and
 * manages the WebSocket connection for real-time state tracking.
 */

const http = require("node:http");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const { WebSocketServer, WebSocket } = require("ws");
const chokidar = require("chokidar");
const { parse: parseYaml } = require("yaml");

const PORT = process.env.PORT || 5173;

// Resolve directories
const ROOT_DIR = path.resolve(__dirname, "..");
const UI_DIST = path.join(ROOT_DIR, "ui", "dist");

function resolveSquadsDir() {
  const candidates = [
    path.resolve(process.cwd(), "data/squads"),
    path.resolve(ROOT_DIR, "data/squads"),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return path.resolve(ROOT_DIR, "data/squads");
}

const squadsDir = resolveSquadsDir();
console.log(`[API Server] Data dir: ${squadsDir}`);

// Utility functions copied from plugin
async function discoverSquads() {
  let entries;
  try {
    entries = await fsp.readdir(squadsDir, { withFileTypes: true });
  } catch {
    return [];
  }

  const squads = [];
  for (const entry of entries) {
    if (!entry.isDirectory() || entry.name.startsWith(".") || entry.name.startsWith("_")) continue;
    const jsonPath = path.join(squadsDir, entry.name, "squad.json");
    const yamlPath = path.join(squadsDir, entry.name, "squad.yaml");
    
    let s = null;
    try {
      if (fs.existsSync(jsonPath)) {
        s = JSON.parse(await fsp.readFile(jsonPath, "utf-8"))?.squad;
      } else if (fs.existsSync(yamlPath)) {
        s = parseYaml(await fsp.readFile(yamlPath, "utf-8"))?.squad;
      }
    } catch {}

    if (s) {
      squads.push({
        code: typeof s.squad_name === "string" ? s.squad_name : (typeof s.code === "string" ? s.code : entry.name),
        name: typeof s.name === "string" ? s.name : entry.name,
        description: typeof s.description === "string" ? s.description : "",
        icon: typeof s.icon === "string" ? s.icon : "📋",
        agents: Array.isArray(s.agents) ? s.agents : [],
      });
      continue;
    }

    squads.push({
      code: entry.name,
      name: entry.name,
      description: "",
      icon: "📋",
      agents: [],
    });
  }
  return squads;
}

function isValidState(data) {
  if (!data || typeof data !== "object") return false;
  return typeof data.status === "string" && data.step != null && typeof data.step === "object" && Array.isArray(data.agents);
}

async function readActiveStates() {
  const states = {};
  let entries;
  try {
    entries = await fsp.readdir(squadsDir, { withFileTypes: true });
  } catch {
    return states;
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const statePath = path.join(squadsDir, entry.name, "state.json");
    try {
      const parsed = JSON.parse(await fsp.readFile(statePath, "utf-8"));
      if (isValidState(parsed)) states[entry.name] = parsed;
    } catch {}
  }
  return states;
}

async function buildSnapshot() {
  return {
    type: "SNAPSHOT",
    squads: await discoverSquads(),
    activeStates: await readActiveStates(),
  };
}

// Ensure directory
fsp.mkdir(squadsDir, { recursive: true }).catch(() => {});

// HTTP Request Handler
const respond = (res, statusCode, body, contentType = "application/json") => {
  res.writeHead(statusCode, { "Content-Type": contentType, "Access-Control-Allow-Origin": "*" });
  res.end(typeof body === "string" ? body : JSON.stringify(body));
};

const mimeTypes = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".ttf": "font/ttf",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

const server = http.createServer(async (req, res) => {
  // --- API Routes ---
  if (req.url === "/api/snapshot") {
    try {
      respond(res, 200, await buildSnapshot());
    } catch {
      respond(res, 500, { error: "Internal Server Error" });
    }
    return;
  }

  if (req.url === "/api/create-squad" && req.method === "POST") {
    let body = "";
    req.on("data", chunk => { body += chunk.toString(); });
    req.on("end", () => {
      try {
        const { intent } = JSON.parse(body);
        if (!intent) return respond(res, 400, { error: "No intent provided" });

        const cp = require("node:child_process");
        cp.execFile("python3", ["bin/skill_discovery.py", "generate-team", "--intent", intent, "--output-dir", "data/squads"], { cwd: ROOT_DIR }, (error, stdout, stderr) => {
          if (error) return respond(res, 500, { error: stderr || stdout || error.message });
          respond(res, 200, { success: true, output: stdout });
        });
      } catch (e) {
        respond(res, 500, { error: e.message });
      }
    });
    return;
  }

  if (req.url && req.url.startsWith("/api/logs/") && req.method === "GET") {
    const squadName = req.url.split("/api/logs/")[1];
    const logPath = path.join(squadsDir, squadName, "runs.md");
    try {
      if (fs.existsSync(logPath)) {
        respond(res, 200, await fsp.readFile(logPath, "utf-8"), "text/plain");
      } else {
        respond(res, 200, "No run logs found for this squad yet.", "text/plain");
      }
    } catch {
      respond(res, 500, "Internal Server Error", "text/plain");
    }
    return;
  }

  if (req.url && req.url.startsWith("/api/history/") && req.method === "GET") {
    const squadName = req.url.split("/api/history/")[1];
    try {
      const cp = require("node:child_process");
      const agiPath = process.env.AGI_PATH || path.resolve(ROOT_DIR, "..", "agi");
      const mmPath = path.join(agiPath, "execution", "memory_manager.py");
      
      cp.execFile("python3", [mmPath, "retrieve", "--query", "", "--project", squadName, "--top-k", "20"], (error, stdout) => {
        let parsedJson = null;
        try {
          if (stdout) {
            const match = stdout.match(/[\{\[]/);
            if (match) parsedJson = JSON.parse(stdout.substring(match.index));
          }
        } catch {}

        if (parsedJson) return respond(res, 200, parsedJson);
        
        if (error) {
          const memPath = path.join(squadsDir, squadName, "memories.md");
          if (fs.existsSync(memPath)) {
             return respond(res, 200, { results: [{ id: "local", type: "fallback", content: fs.readFileSync(memPath, "utf-8"), created_at: new Date().toISOString() }] });
          }
          return respond(res, 200, { results: [] });
        }
        respond(res, 200, stdout);
      });
    } catch (err) {
       respond(res, 500, { error: "Server error" });
    }
    return;
  }

  // --- Static File Serving ---
  let filePath = path.join(UI_DIST, req.url === "/" ? "index.html" : req.url);
  // Handle SPA routing
  if (!fs.existsSync(filePath)) {
    filePath = path.join(UI_DIST, "index.html");
  }

  const extname = String(path.extname(filePath)).toLowerCase();
  const contentType = mimeTypes[extname] || "application/octet-stream";

  try {
    const content = await fsp.readFile(filePath);
    res.writeHead(200, { "Content-Type": contentType });
    res.end(content, "utf-8");
  } catch (error) {
    // If running in development and ui/dist isn't built yet
    if (!fs.existsSync(UI_DIST)) {
       respond(res, 500, "Dashboard static files not found. Please run 'npm run build' inside the 'ui' directory first.", "text/plain");
    } else {
       respond(res, 500, `Error serving static file: ${error.message}`, "text/plain");
    }
  }
});

// WebSocket Handling
const wss = new WebSocketServer({ noServer: true });
server.on("upgrade", (req, socket, head) => {
  if (req.url === "/__squads_ws") {
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit("connection", ws, req);
    });
  } else {
    socket.destroy();
  }
});

function broadcast(msg) {
  const data = JSON.stringify(msg);
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      try { client.send(data); } catch {}
    }
  }
}

wss.on("connection", async (ws) => {
  try { ws.send(JSON.stringify(await buildSnapshot())); } catch {}
});

// Watcher
const watcher = chokidar.watch(squadsDir, {
  ignoreInitial: true,
  awaitWriteFinish: { stabilityThreshold: 300, pollInterval: 50 },
  ignored: [/(^|[/\\])\./, /node_modules/, /output[/\\]/],
  depth: 2,
});

watcher.on("add", handleFileChange);
watcher.on("change", handleFileChange);
watcher.on("unlink", handleFileRemoval);

function handleFileChange(filePath) {
  const parts = path.relative(squadsDir, filePath).replace(/\\/g, "/").split("/");
  if (parts.length < 2) return;
  const [squadName, fileName] = parts;
  if (fileName === "state.json") {
    fsp.readFile(filePath, "utf-8").then(raw => {
      const parsed = JSON.parse(raw);
      if (isValidState(parsed)) broadcast({ type: "SQUAD_UPDATE", squad: squadName, state: parsed });
    }).catch(() => {});
  } else if (fileName === "squad.yaml") {
    buildSnapshot().then(snap => broadcast(snap));
  }
}

function handleFileRemoval(filePath) {
  const parts = path.relative(squadsDir, filePath).replace(/\\/g, "/").split("/");
  if (parts.length < 2) return;
  const [squadName, fileName] = parts;
  if (fileName === "state.json") broadcast({ type: "SQUAD_INACTIVE", squad: squadName });
  else if (fileName === "squad.yaml") buildSnapshot().then(snap => broadcast(snap));
}

server.listen(PORT, () => {
  console.log(`\n🚀 openminions Production API server running on http://localhost:${PORT}`);
  console.log(`[API Server] Serving static files from: ${UI_DIST}`);
});
