import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import { WebSocketServer, WebSocket } from "ws";
import { ClientMessage, ServerMessage, Team } from "../../shared/src/protocol";
import { Simulation, createSimulation, setPlaying, setSimulationInput, stepSimulation } from "../../shared/src/simulation";

type Client = {
  id: string;
  displayName: string | null;
  socket: WebSocket;
  roomCode: string | null;
  side: Team | null;
};

type Room = {
  code: string;
  clients: Map<Team, Client>;
  sim: Simulation;
  lastEmptyAt: number | null;
};

const PORT = Number(process.env.PORT ?? 8787);
const TICK_HZ = 30;
const rooms = new Map<string, Room>();
const clients = new Map<WebSocket, Client>();

const server = http.createServer((req, res) => {
  if (serveStatic(req, res)) return;
  res.writeHead(200, { "content-type": "text/plain" });
  res.end("Kickabout online server");
});

const wss = new WebSocketServer({ server });

wss.on("connection", (socket) => {
  const client: Client = { id: randomUUID(), displayName: null, socket, roomCode: null, side: null };
  clients.set(socket, client);

  socket.on("message", (raw) => {
    const message = parseMessage(raw.toString());
    if (!message) return send(client, { type: "room_error", reason: "Invalid message" });
    handleMessage(client, message);
  });

  socket.on("close", () => {
    removeClient(client);
    clients.delete(socket);
  });
});

setInterval(() => {
  for (const room of rooms.values()) {
    if (room.clients.size === 0) {
      room.lastEmptyAt ??= Date.now();
      if (Date.now() - room.lastEmptyAt > 30_000) rooms.delete(room.code);
      continue;
    }
    if (room.clients.size === 2) {
      stepSimulation(room.sim, 1 / TICK_HZ);
      const snapshot = {
        ...room.sim.snapshot,
        players: room.sim.snapshot.players.map((player) => ({
          ...player,
          displayName: player.controlled ? (room.clients.get(player.team)?.displayName ?? null) : null
        }))
      };
      broadcast(room, { type: "snapshot", snapshot });
    }
  }
}, 1000 / TICK_HZ);

server.listen(PORT, () => {
  console.log(`Kickabout online listening on http://localhost:${PORT}`);
});

const handleMessage = (client: Client, message: ClientMessage) => {
  if (message.type === "create_room") {
    const displayName = normalizeDisplayName(message.displayName);
    if (!displayName) return send(client, { type: "room_error", reason: "Display name required" });
    const code = createRoomCode();
    const room: Room = { code, clients: new Map(), sim: createSimulation(), lastEmptyAt: null };
    rooms.set(code, room);
    joinRoom(client, room, "blue", displayName);
    send(client, { type: "room_created", code, playerId: client.id, side: "blue" });
    return;
  }

  if (message.type === "join_room") {
    const displayName = normalizeDisplayName(message.displayName);
    if (!displayName) return send(client, { type: "room_error", reason: "Display name required" });
    const code = message.code.trim().toUpperCase();
    const room = rooms.get(code);
    if (!room) return send(client, { type: "room_error", reason: "Room not found" });
    if (room.clients.has("red")) return send(client, { type: "room_error", reason: "Room is full" });
    joinRoom(client, room, "red", displayName);
    send(client, { type: "joined", code, playerId: client.id, side: "red" });
    setPlaying(room.sim);
    broadcast(room, { type: "match_start", seed: Date.now(), side: "blue" }, "blue");
    broadcast(room, { type: "match_start", seed: Date.now(), side: "red" }, "red");
    return;
  }

  if (message.type === "input") {
    const room = client.roomCode ? rooms.get(client.roomCode) : null;
    if (room && client.side) setSimulationInput(room.sim, client.side, message.input);
    return;
  }

  if (message.type === "leave_room") {
    removeClient(client);
    return;
  }

  if (message.type === "ping") {
    send(client, { type: "pong", sentAt: message.sentAt });
  }
};

const joinRoom = (client: Client, room: Room, side: Team, displayName: string) => {
  removeClient(client);
  client.displayName = displayName;
  client.roomCode = room.code;
  client.side = side;
  room.clients.set(side, client);
  room.lastEmptyAt = null;
};

const removeClient = (client: Client) => {
  if (!client.roomCode || !client.side) return;
  const room = rooms.get(client.roomCode);
  if (room) {
    room.clients.delete(client.side);
    broadcast(room, { type: "player_disconnected" });
    if (room.clients.size === 0) room.lastEmptyAt = Date.now();
  }
  client.displayName = null;
  client.roomCode = null;
  client.side = null;
};

const send = (client: Client, message: ServerMessage) => {
  if (client.socket.readyState === WebSocket.OPEN) client.socket.send(JSON.stringify(message));
};

const broadcast = (room: Room, message: ServerMessage, side?: Team) => {
  const targets = side ? [room.clients.get(side)] : Array.from(room.clients.values());
  for (const client of targets) if (client) send(client, message);
};

const parseMessage = (raw: string): ClientMessage | null => {
  try {
    return JSON.parse(raw) as ClientMessage;
  } catch {
    return null;
  }
};

const createRoomCode = () => {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let code = "";
  do {
    code = Array.from({ length: 6 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  } while (rooms.has(code));
  return code;
};

const normalizeDisplayName = (value: unknown) => {
  if (typeof value !== "string") return null;
  const displayName = value.trim().replace(/\s+/g, " ").slice(0, 20);
  return displayName.length > 0 ? displayName : null;
};

function serveStatic(req: http.IncomingMessage, res: http.ServerResponse) {
  if (process.env.NODE_ENV !== "production") return false;
  const dirname = path.dirname(fileURLToPath(import.meta.url));
  const root = path.resolve(dirname, "../../dist/client");
  const urlPath = req.url?.split("?")[0] ?? "/";
  const filePath = path.join(root, urlPath === "/" ? "index.html" : urlPath);
  if (!filePath.startsWith(root)) return false;
  const target = fs.existsSync(filePath) ? filePath : path.join(root, "index.html");
  const contentType = target.endsWith(".js")
    ? "application/javascript"
    : target.endsWith(".css")
      ? "text/css"
      : target.endsWith(".png")
        ? "image/png"
        : "text/html";
  res.writeHead(200, { "content-type": contentType, "x-content-type-options": "nosniff" });
  fs.createReadStream(target).pipe(res);
  return true;
}
