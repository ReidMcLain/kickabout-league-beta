# Kickabout League Physics RE Notes

These notes are from static analysis of `analysis/kickabout/kickabout.jar`, decompiled with CFR 0.152.

The code is not encrypted, but it is obfuscated. Several `toString()` methods survived and give strong anchors:

- `tj` = `AgentBall`
- `nl` = `AgentFootballer`
- `nu` = active match/state container
- `up` = player stats/loadout (`POW`, `TCK`, `SPD`, `EXP`, trinkets)
- `la` = axis-aligned collision/valid-area box
- `lt` = shared movement integrator
- `p` = possession logger / pitch-region setup helper
- `wr` = formation selection state
- `ua` = goal/score state
- `ki` = network/input command

The original client is an old Java Applet/AWT game. It uses fixed-point integer math, a server-synchronized match state, and local client prediction/interpolation. The physics are not one monolithic engine class; they are spread mainly across `nu`, `nl`, `tj`, `lt`, and `la`.

## Current Confidence

High confidence:

- Ball and footballer class identities.
- Coordinate scale and pitch dimensions.
- The general movement/collision integrator.
- Action state names for footballers.
- Basic possession, pickup radius, and ball/player contact behavior.
- Ground/air friction values for the ball.
- Trig table scale and angle convention.
- Goal line detection bounds and goal reset timing.
- Input command structure for kick/tackle/dash/selection actions.
- Charge timing curve for kick power.
- Broad keeper AI/save trigger logic.
- Core player stat fields and physics-facing stat accessors.
- Pitch surface index mapping.

Medium confidence:

- Exact meaning of every `nl` speed field.
- Exact shot/pass charge mapping.
- Keeper deflection logic.
- Header/volley intercept setup.
- Shot/pass/cross stat logging.
- Trinket/class capability checks that affect physics.

Low confidence:

- Network/server authority boundaries.
- Every edge case for tackles, headers, trinket modifiers, and multiplayer correction.

## Files

- `class-map.md`: working class/field map.
- `physics.md`: reconstructed physics behavior.
- `player-movement-vn-and-keeper-animation.md`: VN test limits, movement heading, kit recoloring, and keeper pose notes.
- `physics-interactions-research.md`: source ranking and next work for physics/interactions using deob + launcher evidence.
- `assets-cache-research.md`: current launcher/gamepack/cache asset research.
- `assets-and-deob-audit.md`: deobfuscator legitimacy check and asset/cache findings.
- `open-questions.md`: what still needs tracing.
