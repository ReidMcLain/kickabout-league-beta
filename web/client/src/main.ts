import Phaser from "phaser";
import { ClientMessage, GameSnapshot, PlayerInput, ServerMessage, Team, emptyInput } from "../../shared/src/protocol";
import { FIELD } from "../../shared/src/simulation";
import "./styles.css";

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Missing app root");

app.innerHTML = `
  <div id="hud">
    <div id="score">0 - 0</div>
    <div id="status">Offline</div>
  </div>
  <div id="menu" class="panel">
    <input id="display-name" maxlength="20" autocomplete="nickname" placeholder="Display name" />
    <button id="host" class="primary">Host Game</button>
    <button id="join" class="primary">Join Game</button>
    <form id="join-form" class="hidden">
      <input id="code" maxlength="6" autocomplete="off" placeholder="CODE" />
      <button type="submit">Connect</button>
    </form>
    <div id="room-code" class="code hidden"></div>
    <div id="error" class="error"></div>
  </div>
  <div id="game"></div>
`;

const statusEl = document.querySelector<HTMLDivElement>("#status")!;
const scoreEl = document.querySelector<HTMLDivElement>("#score")!;
const menuEl = document.querySelector<HTMLDivElement>("#menu")!;
const roomCodeEl = document.querySelector<HTMLDivElement>("#room-code")!;
const errorEl = document.querySelector<HTMLDivElement>("#error")!;
const joinForm = document.querySelector<HTMLFormElement>("#join-form")!;
const displayNameInput = document.querySelector<HTMLInputElement>("#display-name")!;
const codeInput = document.querySelector<HTMLInputElement>("#code")!;

let socket: WebSocket | null = null;
let side: Team | null = null;
let sequence = 0;
let currentSnapshot: GameSnapshot | null = null;

class MatchScene extends Phaser.Scene {
  private cursors?: Phaser.Types.Input.Keyboard.CursorKeys;
  private keys?: Record<string, Phaser.Input.Keyboard.Key>;
  private players = new Map<string, Phaser.GameObjects.Sprite>();
  private labels = new Map<string, Phaser.GameObjects.Text>();
  private ball?: Phaser.GameObjects.Sprite;
  private graphics?: Phaser.GameObjects.Graphics;
  private previousPointerDown = false;
  private actionUntil = 0;

  constructor() {
    super("match");
  }

  preload() {
    this.load.image("blue", "/assets/player-blue.png");
    this.load.image("red", "/assets/player-red.png");
    this.load.image("ball", "/assets/ball.png");
  }

  create() {
    this.cameras.main.setBounds(0, 0, FIELD.width, FIELD.height);
    this.cameras.main.setZoom(0.82);
    this.graphics = this.add.graphics();
    this.cursors = this.input.keyboard?.createCursorKeys();
    this.keys = this.input.keyboard?.addKeys("W,A,S,D,SPACE") as Record<string, Phaser.Input.Keyboard.Key>;
  }

  update() {
    if (currentSnapshot) this.renderSnapshot(currentSnapshot);
    this.sendInput();
  }

  private renderSnapshot(snapshot: GameSnapshot) {
    scoreEl.textContent = `${snapshot.score.blue} - ${snapshot.score.red}`;
    this.drawField();

    for (const p of snapshot.players) {
      let sprite = this.players.get(p.id);
      if (!sprite) {
        sprite = this.add.sprite(p.pos.x, p.pos.y, p.team).setDisplaySize(52, 52);
        this.players.set(p.id, sprite);
        const label = this.add.text(p.pos.x, p.pos.y + 35, p.controlled ? p.team.toUpperCase() : "AI", {
          color: "#f7fbff",
          fontFamily: "Arial",
          fontSize: "14px",
          fontStyle: "bold",
          stroke: "#10251d",
          strokeThickness: 4
        }).setOrigin(0.5);
        this.labels.set(p.id, label);
      }
      sprite.setPosition(p.pos.x, p.pos.y);
      sprite.setTint(p.controlled ? 0xffffff : 0xd6d6d6);
      sprite.setScale(p.hasBall ? 1.08 : 1);
      const label = this.labels.get(p.id);
      label?.setPosition(p.pos.x, p.pos.y + 35);
      label?.setText(p.controlled ? (p.displayName ?? p.team.toUpperCase()) : p.id.endsWith("keeper") ? "GK" : "AI");
    }

    this.ball ??= this.add.sprite(snapshot.ball.pos.x, snapshot.ball.pos.y, "ball").setDisplaySize(28, 28);
    this.ball.setPosition(snapshot.ball.pos.x, snapshot.ball.pos.y);
    const focus = snapshot.players.find((p) => p.team === side && p.controlled)?.pos ?? snapshot.ball.pos;
    this.cameras.main.centerOn(focus.x, focus.y);
  }

  private drawField() {
    const g = this.graphics;
    if (!g) return;
    g.clear();
    g.fillStyle(0x2f8a4a);
    g.fillRect(0, 0, FIELD.width, FIELD.height);
    for (let y = 0; y < FIELD.height; y += 120) {
      g.fillStyle(y % 240 === 0 ? 0x348f4f : 0x2b8045);
      g.fillRect(0, y, FIELD.width, 120);
    }
    g.lineStyle(4, 0xf4f0de);
    g.strokeRect(40, 40, FIELD.width - 80, FIELD.height - 80);
    g.lineBetween(40, FIELD.height / 2, FIELD.width - 40, FIELD.height / 2);
    g.strokeCircle(FIELD.width / 2, FIELD.height / 2, 95);
    g.strokeRect(FIELD.width / 2 - 210, 40, 420, 190);
    g.strokeRect(FIELD.width / 2 - 210, FIELD.height - 230, 420, 190);
    g.strokeRect(FIELD.width / 2 - FIELD.goalWidth / 2, 0, FIELD.goalWidth, 40);
    g.strokeRect(FIELD.width / 2 - FIELD.goalWidth / 2, FIELD.height - 40, FIELD.goalWidth, 40);

    const owned = currentSnapshot?.players.find((p) => p.hasBall);
    if (owned) {
      g.lineStyle(4, owned.team === "blue" ? 0x61a8ff : 0xff6969);
      g.strokeCircle(owned.pos.x, owned.pos.y, 36);
    }
  }

  private sendInput() {
    if (!socket || socket.readyState !== WebSocket.OPEN || !side) return;
    const pointer = this.input.activePointer.positionToCamera(this.cameras.main) as Phaser.Math.Vector2;
    const pointerDown = this.input.activePointer.isDown;
    if (pointerDown && !this.previousPointerDown) this.actionUntil = performance.now() + 120;
    const action = performance.now() < this.actionUntil;
    this.previousPointerDown = pointerDown;
    const input: PlayerInput = {
      up: Boolean(this.cursors?.up.isDown || this.keys?.W.isDown),
      down: Boolean(this.cursors?.down.isDown || this.keys?.S.isDown),
      left: Boolean(this.cursors?.left.isDown || this.keys?.A.isDown),
      right: Boolean(this.cursors?.right.isDown || this.keys?.D.isDown),
      sprint: Boolean(this.keys?.SPACE.isDown),
      action,
      pointer: { x: pointer.x, y: pointer.y }
    };
    send({ type: "input", sequence: sequence++, input });
  }
}

new Phaser.Game({
  type: Phaser.AUTO,
  parent: "game",
  width: window.innerWidth,
  height: window.innerHeight,
  backgroundColor: "#163b2b",
  scene: MatchScene,
  scale: {
    mode: Phaser.Scale.RESIZE,
    autoCenter: Phaser.Scale.CENTER_BOTH
  }
});

document.querySelector<HTMLButtonElement>("#host")!.addEventListener("click", () => {
  const displayName = requireDisplayName();
  if (!displayName) return;
  connect();
  send({ type: "create_room", displayName });
});

document.querySelector<HTMLButtonElement>("#join")!.addEventListener("click", () => {
  joinForm.classList.remove("hidden");
  codeInput.focus();
});

joinForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const displayName = requireDisplayName();
  if (!displayName) return;
  connect();
  send({ type: "join_room", code: codeInput.value, displayName });
});

const requireDisplayName = () => {
  const displayName = displayNameInput.value.trim();
  if (displayName) {
    errorEl.textContent = "";
    return displayName;
  }
  errorEl.textContent = "Enter a display name first";
  displayNameInput.focus();
  return null;
};

const connect = () => {
  if (socket && socket.readyState <= WebSocket.OPEN) return;
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const host = import.meta.env.VITE_WS_HOST || (location.port === "5173" ? `${location.hostname}:8787` : location.host);
  socket = new WebSocket(`${protocol}://${host}`);
  socket.addEventListener("open", () => {
    statusEl.textContent = "Connected";
    errorEl.textContent = "";
  });
  socket.addEventListener("message", (event) => handleServerMessage(JSON.parse(event.data) as ServerMessage));
  socket.addEventListener("close", () => {
    statusEl.textContent = "Disconnected";
    side = null;
  });
};

const send = (message: ClientMessage) => {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    setTimeout(() => send(message), 80);
    return;
  }
  socket.send(JSON.stringify(message));
};

const handleServerMessage = (message: ServerMessage) => {
  if (message.type === "room_created") {
    side = message.side;
    roomCodeEl.textContent = message.code;
    roomCodeEl.classList.remove("hidden");
    statusEl.textContent = "Waiting for player";
  } else if (message.type === "joined") {
    side = message.side;
    statusEl.textContent = "Joined";
  } else if (message.type === "match_start") {
    side = message.side;
    menuEl.classList.add("hidden");
    statusEl.textContent = `Playing ${side}`;
  } else if (message.type === "snapshot") {
    currentSnapshot = message.snapshot;
  } else if (message.type === "room_error") {
    errorEl.textContent = message.reason;
  } else if (message.type === "player_disconnected") {
    statusEl.textContent = "Other player disconnected";
  }
};

window.addEventListener("beforeunload", () => {
  socket?.send(JSON.stringify({ type: "leave_room" } satisfies ClientMessage));
});
