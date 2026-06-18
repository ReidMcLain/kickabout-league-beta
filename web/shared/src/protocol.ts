export type Team = "blue" | "red";

export type Vec2 = {
  x: number;
  y: number;
};

export type PlayerInput = {
  up: boolean;
  down: boolean;
  left: boolean;
  right: boolean;
  sprint: boolean;
  action: boolean;
  pointer: Vec2;
};

export type ClientMessage =
  | { type: "create_room" }
  | { type: "join_room"; code: string }
  | { type: "input"; sequence: number; input: PlayerInput }
  | { type: "leave_room" }
  | { type: "ping"; sentAt: number };

export type ServerMessage =
  | { type: "room_created"; code: string; playerId: string; side: Team }
  | { type: "joined"; code: string; playerId: string; side: Team }
  | { type: "room_error"; reason: string }
  | { type: "match_start"; seed: number; side: Team }
  | { type: "snapshot"; snapshot: GameSnapshot }
  | { type: "player_disconnected" }
  | { type: "pong"; sentAt: number };

export type PlayerState = {
  id: string;
  team: Team;
  slot: number;
  controlled: boolean;
  pos: Vec2;
  vel: Vec2;
  hasBall: boolean;
};

export type BallState = {
  pos: Vec2;
  vel: Vec2;
  ownerId: string | null;
};

export type GameSnapshot = {
  tick: number;
  players: PlayerState[];
  ball: BallState;
  score: Record<Team, number>;
  status: "waiting" | "playing";
};

export const emptyInput = (): PlayerInput => ({
  up: false,
  down: false,
  left: false,
  right: false,
  sprint: false,
  action: false,
  pointer: { x: 0, y: 0 }
});
