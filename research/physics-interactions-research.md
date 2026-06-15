# Physics and Interactions Research Track

## Source Ranking

Primary source for physics/interactions:

```text
C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout
```

This is the best current source because `analysis\kickabout\kickabout.jar` matches the current AlterOrb launcher config exactly:

```text
SHA-256: c6f693399f70424567ecce13e865674aba616ec0449739b54c1b2778e7ea10da
Launcher game: Kickabout League
internalName: kickabout
mainClass: Kickabout
gamecrc: 613591652
```

The live launcher config endpoint used by `launcher` is:

```text
https://static.alterorb.net/launcher/v3/config.json
```

Secondary source:

```text
C:\Users\reidm\OneDrive\Desktop\codex\classic-deob
```

This is useful for the deobfuscator pipeline and for comparison, but its bundled Kickabout input jar is not the same jar as the current launcher-matching analysis jar:

```text
classic-deob\input\funorb\kickabout\gamepack.jar
SHA-256: 83f914e90ee3923c178d21b82fd7f1c48b4bda70d8771d3e5ed56e124d09846b
size: 2,012,730 bytes
```

The current `deob` folder is empty, so it is not a useful source until a jar or project is placed there.

Launcher source role:

```text
C:\Users\reidm\OneDrive\Desktop\codex\launcher
```

The launcher is not itself a physics source. It is useful because it proves which Kickabout jar is current, how the patched client is launched, which applet params are supplied, and where cache files are redirected.

## Confidence

Current physics/interactions confidence: about 80/100.

High-confidence systems already mapped in `physics.md`:

- Ball class: `tj`.
- Footballer class: `nl`.
- Match state: `nu`.
- Movement integrator: `lt`.
- Collision/valid-area boxes: `la`.
- Player stats/loadout: `up`.
- Fixed-point coordinate system and pitch size.
- Ball friction, gravity, bounce damping, uncatchable timers, and high-friction timer.
- Player movement/action states.
- Tackles, headers, possession pickup, shot/pass impulses, charge timing, goal bounds, keeper save trigger.

What keeps this from 100/100:

- Some central match code in `nu.b(int)` is hard for CFR to structure cleanly.
- Event/stat logging still has ambiguous branches.
- Some trinket and cheat-ball modifiers are only partially named.
- Network/server authority boundaries are not fully separated from local prediction.
- The launcher proves the current jar identity, but it does not add physics names or code by itself.

## Deob + Launcher Workflow

Best workflow for physics:

1. Use launcher metadata to identify the current target jar.
2. Prefer the jar whose SHA-256 matches the launcher config.
3. Decompile that jar and preserve a stable decompiled tree under `analysis/kickabout`.
4. Use `classic-deob` as a transformer reference and to generate cleaned jars when useful.
5. Keep physics notes tied to the launcher-matching jar unless a newer gamepack is deliberately downloaded and hashed.

Do not use `/launcher` as the main deob target for physics. It is a Java launcher, not the game simulation.

Do not use `classic-deob/input/funorb/kickabout/gamepack.jar` as the main physics truth without checking why it differs from the launcher jar. It may be an original/unpatched artifact, a different revision, or a differently packaged gamepack.

## Interaction Areas Worth Continuing

Highest-value next traces:

- `nu.b(int)`: central match tick, especially contact order and edge cases.
- `nu.a(byte, ki)`: kick/tackle/header command release path.
- `nu.b(byte, ki)`: selection, dash, and charge-start path.
- `tj.a(byte, int, la[])`: free-ball physics.
- `nl.a(int, la[], boolean, boolean)`: footballer movement/action tick.
- `wt.a(...)`: keeper save prediction.
- `hv.a(...)`: keeper AI.
- `up`: trinket/class modifier accessors.
- `rv`: trinket id/name table.
- `ch` and `jc`: goal/shot/player stat logging.

## Prototype Alignment Notes

The current Python prototype already mirrors many constants from the launcher-matching decompilation:

- 60 Hz tick model.
- 896 x 1344 source pitch scale.
- Park/beach/street friction arrays.
- Ball gravity, player gravity, bounce damping, high-friction timer.
- Low/high kick uncatchable windows.
- Header prediction radius.
- Charge timing curve.

Most useful future implementation work is not more broad decompilation. It is targeted comparison between `main.py` and specific decompiled methods, especially the central match tick and trinket modifiers.
