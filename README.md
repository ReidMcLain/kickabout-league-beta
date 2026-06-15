# Kickabout 2.5D Prototype

A small Pygame arcade soccer prototype using the local Kenney Sports Pack.

## Run

```powershell
python main.py
```

## Build a Windows Beta

```powershell
python -m pip install -r requirements.txt
.\scripts\package_windows.ps1
```

The build writes `dist\KickaboutBeta-windows.zip`, containing `KickaboutBeta.exe`.

## Publish a GitHub Beta Release

1. Commit the project, including `assets\`, `.github\workflows\windows-beta-release.yml`, and `scripts\package_windows.ps1`.
2. Push a beta tag:

```powershell
git tag beta-0.1.0
git push origin beta-0.1.0
```

GitHub Actions will build the Windows `.exe` and attach `KickaboutBeta-windows.zip` to a prerelease. You can also run the workflow manually from the Actions tab.

## Controls

- At match start, press `1`-`5` to choose your formation.
- `WASD` / arrow keys - move the selected player
- `Space` / `Ctrl` - sprint; while carrying, only Ranger-style players sprint with the ball
- Left-click while possessing - hold/release a low pass or low shot
- Right-click while possessing - hold/release a high pass or shot, aka a lob
- Left-click without possession - tackle, or header when the ball is overhead
- Right-click without possession - switch to the blue player nearest your mouse
- `1`-`5` - choose formation: Diamond, Box, Wide, Y, Upside-down Y
- `R` - reset match
- `Esc` - quit

## Notes

The pitch is larger than the screen and the camera follows the ball. The ball uses a 2.5D model: `x/y` position on the pitch plus `z` height, with Kickabout-style 60 Hz friction, gravity, bounce damping, uncatchable timers, high-friction low shots, and separate contact windows for volleys and headers.

Goalkeepers are protected from tackles, can never be player-controlled, and use a predicted goal-line crossing check before diving or collecting. Tackled players stay down for 2 seconds before they can move or tackle again. CPU defenders keep their formation shape, but nearby defenders now pressure and slide tackle the ball carrier.
