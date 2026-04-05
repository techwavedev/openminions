import type { Plugin, ViteDevServer } from "vite";
import { WebSocketServer, WebSocket } from "ws";
import type { Server, IncomingMessage } from "node:http";
import type { Duplex } from "node:stream";
import fs from "node:fs";
import fsp from "node:fs/promises";
import { watch as chokidarWatch } from "chokidar";
import path from "node:path";
import { parse as parseYaml } from "yaml";
import type { SquadInfo, SquadState, WsMessage } from "../types/state";

function resolveSquadsDir(): string {
  const candidates = [
    path.resolve(process.cwd(), "../data/squads"),  // started from ui/
    path.resolve(process.cwd(), "data/squads"),     // started from project root
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  // Default: create at project root level
  const defaultDir = path.resolve(process.cwd(), "../data/squads");
  return defaultDir;
}

async function discoverSquads(squadsDir: string): Promise<SquadInfo[]> {
  let entries;
  try {
    entries = await fsp.readdir(squadsDir, { withFileTypes: true });
  } catch {
    return [];
  }

  const squads: SquadInfo[] = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    if (entry.name.startsWith(".") || entry.name.startsWith("_")) continue;

    const jsonPath = path.join(squadsDir, entry.name, "squad.json");
    const yamlPath = path.join(squadsDir, entry.name, "squad.yaml");
    
    let s: any = null;
    try {
      if (fs.existsSync(jsonPath)) {
        const raw = await fsp.readFile(jsonPath, "utf-8");
        s = JSON.parse(raw)?.squad;
      } else if (fs.existsSync(yamlPath)) {
        const raw = await fsp.readFile(yamlPath, "utf-8");
        s = parseYaml(raw)?.squad;
      }
    } catch {
      // invalid JSON/YAML - fall through
    }

    if (s) {
      squads.push({
        code: typeof s.squad_name === "string" ? s.squad_name : (typeof s.code === "string" ? s.code : entry.name),
        name: typeof s.name === "string" ? s.name : entry.name,
        description: typeof s.description === "string" ? s.description : "",
        icon: typeof s.icon === "string" ? s.icon : "\u{1F4CB}",
        agents: Array.isArray(s.agents) ? (s.agents as unknown[]).filter((a): a is string => typeof a === "string") : [],
      });
      continue;
    }

    squads.push({
      code: entry.name,
      name: entry.name,
      description: "",
      icon: "\u{1F4CB}",
      agents: [],
    });
  }

  return squads;
}

function isValidState(data: unknown): data is SquadState {
  if (!data || typeof data !== "object") return false;
  const d = data as Record<string, unknown>;
  return (
    typeof d.status === "string" &&
    d.step != null && typeof d.step === "object" &&
    Array.isArray(d.agents)
  );
}

async function readActiveStates(squadsDir: string): Promise<Record<string, SquadState>> {
  const states: Record<string, SquadState> = {};

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
      const raw = await fsp.readFile(statePath, "utf-8");
      const parsed = JSON.parse(raw);
      if (isValidState(parsed)) {
        states[entry.name] = parsed;
      }
    } catch {
      // Skip missing or invalid JSON
    }
  }

  return states;
}

async function buildSnapshot(squadsDir: string): Promise<WsMessage> {
  return {
    type: "SNAPSHOT",
    squads: await discoverSquads(squadsDir),
    activeStates: await readActiveStates(squadsDir),
  };
}

function broadcast(wss: WebSocketServer, msg: WsMessage) {
  const data = JSON.stringify(msg);
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      try {
        client.send(data);
      } catch {
        // Client connection dying — ws library will clean it up
      }
    }
  }
}

export function squadWatcherPlugin(): Plugin {
  return {
    name: "squad-watcher",
    configureServer(server: ViteDevServer) {
      if (!server.httpServer) {
        server.config.logger.warn("[squad-watcher] no httpServer — skipping");
        return;
      }

      const squadsDir = resolveSquadsDir();
      server.config.logger.info(`[squad-watcher] squads dir: ${squadsDir}`);

      // Create WebSocket server with noServer to avoid intercepting Vite's HMR
      const wss = new WebSocketServer({ noServer: true });
      (server.httpServer as Server).on("upgrade", (req: IncomingMessage, socket: Duplex, head: Buffer) => {
        if (req.url === "/__squads_ws") {
          wss.handleUpgrade(req, socket, head, (ws) => {
            wss.emit("connection", ws, req);
          });
        }
        // Let Vite handle all other upgrade requests (HMR)
      });

      // Send snapshot on new connection
      wss.on("connection", async (ws) => {
        try {
          const snap = await buildSnapshot(squadsDir);
          ws.send(JSON.stringify(snap));
        } catch {
          // Connection may have closed before snapshot was ready
        }
      });

      // Ensure squads directory exists
      fsp.mkdir(squadsDir, { recursive: true }).catch((err) => {
        server.config.logger.error(`[squad-watcher] failed to create squads dir: ${err.message}`);
      });

      // REST API fallback for polling and other actions
      server.middlewares.use(async (req, res, next) => {
        if (req.url === "/api/snapshot") {
          try {
            const snapshot = await buildSnapshot(squadsDir);
            res.setHeader("Content-Type", "application/json");
            res.setHeader("Cache-Control", "no-cache");
            res.end(JSON.stringify(snapshot));
          } catch {
            res.writeHead(500);
            res.end("Internal Server Error");
          }
          return;
        }

        if (req.url === "/api/create-squad" && req.method === "POST") {
          let body = "";
          req.on("data", chunk => { body += chunk.toString(); });
          req.on("end", () => {
            try {
              const { intent } = JSON.parse(body);
              if (!intent) {
                res.writeHead(400);
                res.end(JSON.stringify({ error: "No intent provided" }));
                return;
              }

              const cp = require("node:child_process");
              const openminionsRoot = path.resolve(process.cwd(), "..");
              
              // lgtm [js/incomplete-sanitization]
              cp.execFile("python3", ["bin/skill_discovery.py", "generate-team", "--intent", intent, "--output-dir", "data/squads"], { cwd: openminionsRoot }, (error: any, stdout: string, stderr: string) => {
                if (error) {
                  res.writeHead(500);
                  res.end(JSON.stringify({ error: stderr || stdout || error.message }));
                  return;
                }
                res.setHeader("Content-Type", "application/json");
                res.end(JSON.stringify({ success: true, output: stdout }));
              });
            } catch (e: any) {
              res.writeHead(500);
              res.end(JSON.stringify({ error: e.message }));
            }
          });
          return;
        }

        if (req.url && req.url.startsWith("/api/logs/") && req.method === "GET") {
          const squadName = req.url.split("/api/logs/")[1];
          const logPath = path.join(squadsDir, squadName, "runs.md");
          try {
            if (fs.existsSync(logPath)) {
              const content = await fsp.readFile(logPath, "utf-8");
              res.setHeader("Content-Type", "text/plain");
              res.end(content);
            } else {
              res.setHeader("Content-Type", "text/plain");
              res.end("No run logs found for this squad yet.");
            }
          } catch {
            res.writeHead(500);
            res.end("Internal Server Error reading logs");
          }
          return;
        }

        if (req.url && req.url.startsWith("/api/history/") && req.method === "GET") {
          const squadName = req.url.split("/api/history/")[1];
          try {
            const cp = require("node:child_process");
            const agiPath = process.env.AGI_PATH || path.resolve(process.cwd(), "..", "..", "agi");
            const mmPath = path.join(agiPath, "execution", "memory_manager.py");
            
            cp.execFile("python3", [mmPath, "retrieve", "--query", "", "--project", squadName, "--limit", "20"], (error: any, stdout: string, stderr: string) => {
              // Extract valid JSON from stdout even if process exited with non-zero
              let parsedJson = null;
              try {
                if (stdout) {
                  // The python script might output warnings before JSON. Find the first '{' or '['
                  const match = stdout.match(/[\{\[]/);
                  if (match) {
                     const jsonStr = stdout.substring(match.index!);
                     parsedJson = JSON.parse(jsonStr);
                  }
                }
              } catch (e) {}

              if (parsedJson) {
                res.setHeader("Content-Type", "application/json");
                res.end(JSON.stringify(parsedJson));
                return;
              }

              if (error) {
                console.error("[history api error]", stderr || error);
                
                // Fallback to local memories.md if Qdrant isn't ready or no results
                const memPath = path.join(squadsDir, squadName, "memories.md");
                if (fs.existsSync(memPath)) {
                   const content = fs.readFileSync(memPath, "utf-8");
                   res.setHeader("Content-Type", "application/json");
                   res.end(JSON.stringify({
                     results: [{ id: "local", type: "fallback", content: content, created_at: new Date().toISOString() }]
                   }));
                   return;
                }

                res.setHeader("Content-Type", "application/json");
                res.end(JSON.stringify({ results: [] }));
                return;
              }
              res.setHeader("Content-Type", "application/json");
              res.end(stdout);
            });
          } catch (err: any) {
             res.writeHead(500);
             res.end(JSON.stringify({ error: "Server error" }));
          }
          return;
        }

        next();
      });

      // File watcher using chokidar — reliable cross-platform, handles partial writes
      const watcher = chokidarWatch(squadsDir, {
        ignoreInitial: true,
        awaitWriteFinish: { stabilityThreshold: 300, pollInterval: 50 },
        ignored: [/(^|[/\\])\./, /node_modules/, /output[/\\]/],
        depth: 2,
      });

      function handleFileChange(filePath: string) {
        const relative = path.relative(squadsDir, filePath).replace(/\\/g, "/");
        const parts = relative.split("/");
        if (parts.length < 2) return;

        const squadName = parts[0];
        const fileName = parts[1];

        if (fileName === "state.json") {
          fsp.readFile(filePath, "utf-8").then((raw) => {
            const parsed = JSON.parse(raw);
            if (!isValidState(parsed)) return;
            broadcast(wss, { type: "SQUAD_UPDATE", squad: squadName, state: parsed });
          }).catch(() => {
            // Invalid JSON — next change event will retry
          });
        } else if (fileName === "squad.yaml") {
          buildSnapshot(squadsDir).then((snap) => broadcast(wss, snap));
        }
      }

      function handleFileRemoval(filePath: string) {
        const relative = path.relative(squadsDir, filePath).replace(/\\/g, "/");
        const parts = relative.split("/");
        if (parts.length < 2) return;

        const squadName = parts[0];
        const fileName = parts[1];

        if (fileName === "state.json") {
          broadcast(wss, { type: "SQUAD_INACTIVE", squad: squadName });
        } else if (fileName === "squad.yaml") {
          buildSnapshot(squadsDir).then((snap) => broadcast(wss, snap));
        }
      }

      watcher.on("add", handleFileChange);
      watcher.on("change", handleFileChange);
      watcher.on("unlink", handleFileRemoval);

      server.httpServer.on("close", () => {
        watcher.close();
      });
    },
  };
}

