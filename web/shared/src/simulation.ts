import { BallState, GameSnapshot, PlayerInput, PlayerState, Team, Vec2, emptyInput } from "./protocol";

export const FIELD = {
  width: 1100,
  height: 1500,
  goalWidth: 320
};

const PLAYER_RADIUS = 24;
const BALL_RADIUS = 12;
const BASE_SPEED = 300;
const SPRINT_SPEED = 390;
const AI_SPEED = 150;
const FRICTION = 0.978;
const KICK_SPEED = 930;
const PASS_SPEED = 650;
const PICKUP_COOLDOWN_TICKS = 10;

export type Simulation = {
  snapshot: GameSnapshot;
  inputs: Record<Team, PlayerInput>;
  pendingActions: Record<Team, boolean>;
  pickupCooldown: number;
};

export const createSimulation = (): Simulation => ({
  snapshot: {
    tick: 0,
    players: [
      player("blue-human", "blue", 0, true, FIELD.width / 2, FIELD.height * 0.68),
      player("blue-ai-1", "blue", 1, false, FIELD.width * 0.28, FIELD.height * 0.58),
      player("blue-ai-2", "blue", 2, false, FIELD.width * 0.72, FIELD.height * 0.58),
      player("blue-keeper", "blue", 3, false, FIELD.width / 2, FIELD.height - 80),
      player("red-human", "red", 0, true, FIELD.width / 2, FIELD.height * 0.32),
      player("red-ai-1", "red", 1, false, FIELD.width * 0.28, FIELD.height * 0.42),
      player("red-ai-2", "red", 2, false, FIELD.width * 0.72, FIELD.height * 0.42),
      player("red-keeper", "red", 3, false, FIELD.width / 2, 80)
    ],
    ball: {
      pos: { x: FIELD.width / 2, y: FIELD.height / 2 },
      vel: { x: 0, y: 0 },
      ownerId: null
    },
    score: { blue: 0, red: 0 },
    status: "waiting"
  },
  inputs: {
    blue: emptyInput(),
    red: emptyInput()
  },
  pendingActions: {
    blue: false,
    red: false
  },
  pickupCooldown: 0
});

export const giveKickoff = (sim: Simulation, team: Team = "blue") => {
  const playerId = `${team}-human`;
  sim.snapshot.ball.ownerId = playerId;
  for (const playerState of sim.snapshot.players) playerState.hasBall = playerState.id === playerId;
};

export const setSimulationInput = (sim: Simulation, team: Team, input: PlayerInput) => {
  sim.inputs[team] = input;
  if (input.action) sim.pendingActions[team] = true;
};

export const setPlaying = (sim: Simulation) => {
  sim.snapshot.status = "playing";
  giveKickoff(sim, "blue");
};

export const stepSimulation = (sim: Simulation, dt: number) => {
  const snap = sim.snapshot;
  snap.tick += 1;
  if (snap.status !== "playing") return;

  const ball = snap.ball;
  sim.pickupCooldown = Math.max(0, sim.pickupCooldown - 1);

  for (const p of snap.players) {
    if (p.controlled) {
      updateControlledPlayer(p, sim.inputs[p.team], dt);
    } else {
      updateAiPlayer(p, ball, dt);
    }
  }

  if (ball.ownerId) {
    const owner = snap.players.find((p) => p.id === ball.ownerId);
    if (owner) {
      const input = owner.controlled ? sim.inputs[owner.team] : emptyInput();
      const aim = normalize({ x: input.pointer.x - owner.pos.x, y: input.pointer.y - owner.pos.y }, owner.team === "blue" ? { x: 0, y: -1 } : { x: 0, y: 1 });
      ball.pos = {
        x: owner.pos.x + aim.x * 30,
        y: owner.pos.y + aim.y * 30
      };
      ball.vel = { x: 0, y: 0 };
      if (consumeAction(sim, owner.team)) {
        kickBall(owner, ball, input.pointer, input.sprint ? KICK_SPEED : PASS_SPEED);
        sim.pickupCooldown = PICKUP_COOLDOWN_TICKS;
      } else {
        resolveStealAttempts(snap.players, ball, owner, sim);
      }
    } else {
      ball.ownerId = null;
    }
  } else {
    ball.pos.x += ball.vel.x * dt;
    ball.pos.y += ball.vel.y * dt;
    ball.vel.x *= Math.pow(FRICTION, dt * 60);
    ball.vel.y *= Math.pow(FRICTION, dt * 60);
    bounceBall(ball);
    resolveLooseBallActions(snap.players, ball, sim);
    if (sim.pickupCooldown === 0) collectBall(snap.players, ball);
  }

  checkGoal(snap);
};

const player = (id: string, team: Team, slot: number, controlled: boolean, x: number, y: number): PlayerState => ({
  id,
  displayName: null,
  team,
  slot,
  controlled,
  pos: { x, y },
  vel: { x: 0, y: 0 },
  hasBall: false
});

const updateControlledPlayer = (p: PlayerState, input: PlayerInput, dt: number) => {
  const dir = normalize({
    x: Number(input.right) - Number(input.left),
    y: Number(input.down) - Number(input.up)
  });
  const speed = input.sprint ? SPRINT_SPEED : BASE_SPEED;
  p.vel = { x: dir.x * speed, y: dir.y * speed };
  movePlayer(p, dt);
};

const updateAiPlayer = (p: PlayerState, ball: BallState, dt: number) => {
  const keeper = p.id.endsWith("keeper");
  const ownedByTeam = ball.ownerId?.startsWith(p.team);
  const dangerous = p.team === "blue" ? ball.pos.y > FIELD.height * 0.68 : ball.pos.y < FIELD.height * 0.32;
  const pressure = !ownedByTeam && dangerous && distance(p.pos, ball.pos) < (keeper ? 260 : 220);
  const target = pressure ? ball.pos : aiHomeTarget(p);
  const delta = { x: target.x - p.pos.x, y: target.y - p.pos.y };
  if (Math.hypot(delta.x, delta.y) < 18) {
    p.vel = { x: 0, y: 0 };
    return;
  }
  const dir = normalize(delta);
  p.vel = { x: dir.x * (keeper ? AI_SPEED * 1.2 : AI_SPEED), y: dir.y * (keeper ? AI_SPEED * 1.2 : AI_SPEED) };
  movePlayer(p, dt);
  if (keeper) {
    const y = p.team === "blue" ? FIELD.height - 80 : 80;
    p.pos.y = y;
    p.pos.x = clamp(p.pos.x, FIELD.width / 2 - FIELD.goalWidth / 2, FIELD.width / 2 + FIELD.goalWidth / 2);
  }
};

const movePlayer = (p: PlayerState, dt: number) => {
  p.pos.x = clamp(p.pos.x + p.vel.x * dt, PLAYER_RADIUS, FIELD.width - PLAYER_RADIUS);
  p.pos.y = clamp(p.pos.y + p.vel.y * dt, PLAYER_RADIUS, FIELD.height - PLAYER_RADIUS);
};

const collectBall = (players: PlayerState[], ball: BallState) => {
  const sorted = [...players].sort((a, b) => distance(a.pos, ball.pos) - distance(b.pos, ball.pos));
  for (const p of sorted) {
    if (distance(p.pos, ball.pos) < PLAYER_RADIUS + BALL_RADIUS + 4) {
      ball.ownerId = p.id;
      for (const playerState of players) playerState.hasBall = playerState.id === p.id;
      return;
    }
  }
};

const resolveStealAttempts = (players: PlayerState[], ball: BallState, owner: PlayerState, sim: Simulation) => {
  for (const p of players) {
    if (p.team === owner.team || !p.controlled) continue;
    if (!sim.pendingActions[p.team] || distance(p.pos, owner.pos) > PLAYER_RADIUS * 2.65) continue;
    consumeAction(sim, p.team);
    ball.ownerId = p.id;
    for (const playerState of players) playerState.hasBall = playerState.id === p.id;
    return;
  }
};

const resolveLooseBallActions = (players: PlayerState[], ball: BallState, sim: Simulation) => {
  for (const p of players) {
    if (!p.controlled || !sim.pendingActions[p.team]) continue;
    if (distance(p.pos, ball.pos) > PLAYER_RADIUS + BALL_RADIUS + 22) continue;
    consumeAction(sim, p.team);
    kickBall(p, ball, sim.inputs[p.team].pointer, sim.inputs[p.team].sprint ? KICK_SPEED : PASS_SPEED);
    sim.pickupCooldown = PICKUP_COOLDOWN_TICKS;
    return;
  }
};

const kickBall = (owner: PlayerState, ball: BallState, pointer: Vec2, speed: number) => {
  const fallbackY = owner.team === "blue" ? -1 : 1;
  const dir = normalize({ x: pointer.x - owner.pos.x, y: pointer.y - owner.pos.y }, { x: 0, y: fallbackY });
  ball.ownerId = null;
  owner.hasBall = false;
  ball.vel = { x: dir.x * speed, y: dir.y * speed };
  ball.pos = { x: owner.pos.x + dir.x * 34, y: owner.pos.y + dir.y * 34 };
};

const bounceBall = (ball: BallState) => {
  if (ball.pos.x < BALL_RADIUS || ball.pos.x > FIELD.width - BALL_RADIUS) {
    ball.vel.x *= -0.72;
    ball.pos.x = clamp(ball.pos.x, BALL_RADIUS, FIELD.width - BALL_RADIUS);
  }
  const inGoalMouth = Math.abs(ball.pos.x - FIELD.width / 2) < FIELD.goalWidth / 2;
  if (!inGoalMouth && (ball.pos.y < BALL_RADIUS || ball.pos.y > FIELD.height - BALL_RADIUS)) {
    ball.vel.y *= -0.55;
    ball.pos.y = clamp(ball.pos.y, BALL_RADIUS, FIELD.height - BALL_RADIUS);
  }
};

const checkGoal = (snap: GameSnapshot) => {
  const ball = snap.ball;
  const inGoalMouth = Math.abs(ball.pos.x - FIELD.width / 2) < FIELD.goalWidth / 2;
  if (!inGoalMouth) return;

  if (ball.pos.y < -BALL_RADIUS) {
    snap.score.blue += 1;
    resetAfterGoal(snap);
  } else if (ball.pos.y > FIELD.height + BALL_RADIUS) {
    snap.score.red += 1;
    resetAfterGoal(snap);
  }
};

const resetAfterGoal = (snap: GameSnapshot) => {
  const score = { ...snap.score };
  const fresh = createSimulation().snapshot;
  snap.players = fresh.players;
  snap.ball = fresh.ball;
  snap.score = score;
  snap.status = "playing";
  snap.ball.ownerId = score.blue <= score.red ? "blue-human" : "red-human";
  for (const playerState of snap.players) playerState.hasBall = playerState.id === snap.ball.ownerId;
};

const homeX = (slot: number) => (slot === 1 ? FIELD.width * 0.3 : slot === 2 ? FIELD.width * 0.7 : FIELD.width / 2);
const homeFieldY = (team: Team, slot: number) => team === "blue" ? FIELD.height * (0.58 + slot * 0.05) : FIELD.height * (0.42 - slot * 0.05);
const aiHomeTarget = (p: PlayerState): Vec2 => p.id.endsWith("keeper")
  ? { x: FIELD.width / 2, y: p.team === "blue" ? FIELD.height - 80 : 80 }
  : { x: homeX(p.slot), y: homeFieldY(p.team, p.slot) };
const consumeAction = (sim: Simulation, team: Team) => {
  const active = sim.pendingActions[team];
  sim.pendingActions[team] = false;
  return active;
};
const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
const distance = (a: Vec2, b: Vec2) => Math.hypot(a.x - b.x, a.y - b.y);
const normalize = (v: Vec2, fallback: Vec2 = { x: 0, y: 0 }): Vec2 => {
  const length = Math.hypot(v.x, v.y);
  return length > 0.0001 ? { x: v.x / length, y: v.y / length } : fallback;
};
