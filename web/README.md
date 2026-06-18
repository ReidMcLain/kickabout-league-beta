# Kickabout Online

Browser multiplayer version added beside the existing Python/Pygame prototype.

## Run locally

```powershell
cd web
npm install
npm run dev
```

Open two browser tabs at `http://localhost:5173`.

1. In the first tab, click `Host Game`.
2. Copy the displayed room code.
3. In the second tab, click `Join Game` and enter the code.

The host controls blue and the joiner controls red. Extra teammates and keepers are AI-controlled in this first online slice.

## Controls

- `WASD` or arrow keys: move
- `Space`: sprint
- Hold left mouse button or touch: shoot toward pointer

## Deployment note

This app uses a persistent WebSocket server. Deploy the web folder to a host that supports long-running Node processes, such as Render, Fly.io, or Railway.
