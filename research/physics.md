# Physics Reconstruction

## Coordinate System

World coordinates use 16.16 fixed point.

Evidence:

- `la` constructor shifts all box coordinates by 16.
- `tj.a(true)`, `tj.c(...)`, `nl.f(...)`, and `nl.a(true)` return position fields shifted right by 16.
- Pitch constants are `896 x 1344` world units.

Examples:

- Initial ball reset: `x = 0x1C00000`, `y = 0x2A00000`, `z = 0`.
- These decode as:
  - `0x1C00000 >> 16 = 448`
  - `0x2A00000 >> 16 = 672`
- So the ball starts at center pitch: `(448, 672)`.

## Math Helpers

Angles use an 8192-step circle. `0`, `2048`, `4096`, and `6144` are the main quadrant points.

Trig helpers:

- `we.a(angle, false)`: cosine-like lookup, scaled by `65536`.
- `ei.a(angle, byte)`: sine-like lookup, scaled by `65536`.
- `uv.b(dy, dx, byte)`: angle from a vector in the same 8192-step convention.
- `uv.a(true, dy, dx)`: converts a vector to the game's direction bitmask.
- `pc.a(n, -524289)`: approximate integer square root scaled by `256`.
- `de.a(n, byte)`: `pc.a(n) >> 8`, so effectively unscaled integer square root.

The kick and tackle code uses this pattern:

```java
vx = (we.a(angle) >> 8) * (speed >> 8)
vy = (ei.a(angle) >> 8) * (speed >> 8)
```

That keeps almost all simulation math deterministic integer math.

## Pitch / Bounds

The full pitch is `896 x 1344`.

Collision boxes are `la` rectangles. They are not obstacles in the usual sense; they are valid movement regions. `pe.a(la[], point)` returns true if the point is inside any valid box.

`p.a(boolean)` sets `nu.x` and `nu.B` to different `la[]` layouts. These likely represent match modes, tutorial segments, goal areas, or practice layouts. Examples:

```java
new la(0, 0, 896, 1344)
new la(368, 240, 528, 770)
new la(320, 0, 660, 1344)
```

## Pitch Surfaces

Surface ids map to the surviving pitch key array:

- `0`: park
- `1`: beach
- `2`: street

Ball friction tables:

- Ground/rolling: `sg.d = [64356, 64749, 64749]`
- Airborne: `en.q = [64356, 63569, 64749]`

Normalized:

- Park: ground `0.98199`, air `0.98199`
- Beach: ground `0.98799`, air `0.97000`
- Street: ground `0.98799`, air `0.98799`

User-facing pitch text says the ball bounces much faster on street than on sand. The code path we have confirms street preserves more airborne horizontal speed than beach. Bounce damping itself still appears to use the shared `0.90` wall/impact factor.

## Shared Integrator

Both free ball and footballers use:

```java
lt.a(vx, vy, boxes, ..., z, y, x, vz)
```

Reconstructed behavior:

```python
def integrate(x, y, z, vx, vy, vz, valid_boxes):
    if not inside_any(valid_boxes, x, y, z):
        return x, y, z, vx, vy, vz

    x2 = x + vx
    if inside_any(valid_boxes, x2, y, z):
        x = x2
    else:
        vx = -vx

    y2 = y + vy
    if inside_any(valid_boxes, x, y2, z):
        y = y2
    else:
        vy = -vy

    z2 = z + vz
    if inside_any(valid_boxes, x, y, z2):
        z = z2
    else:
        vz = -vz

    return x, y, z, vx, vy, vz
```

This means wall/floor bounces are axis-separated and perfectly sign-flipped first, then damping/friction is applied by the caller.

## Free Ball Tick

`tj.a(byte, int surface, la[] bounds)` handles free-ball physics when `ball.m == -1`.

Important behavior:

- Decrements `uncatchable` (`r`) and `high_friction` (`A`) timers.
- Calls the shared integrator.
- If X/Y velocity changed due to collision, applies damping with a stronger wall-bounce factor.
- If Z velocity changed due to collision, applies damping and snaps height to zero when needed.
- Applies horizontal friction every tick.
- Applies gravity when the ball is above ground.
- Stops tiny horizontal velocities.

Constants:

- Wall/impact damping when ball is out of vertical bounds or wall collision: `58982 / 65536 = 0.89999`.
- Surface friction arrays:
  - `sg.d = [64356, 64749, 64749]`
  - `en.q = [64356, 63569, 64749]`
- As normalized multipliers:
  - `64356 / 65536 = 0.98199`
  - `64749 / 65536 = 0.98799`
  - `63569 / 65536 = 0.97000`
- High-friction override: `60293 / 65536 = 0.92000`.
- Gravity while airborne: `vz -= 16384`, which is `0.25` world units/tick in 16.16 fixed point.
- Horizontal stop threshold: if `(vx >> 8)^2 + (vy >> 8)^2 < 4096`, set `vx = vy = 0`.

Ground/air friction selection:

```java
long friction = ball.A <= 10
    ? (ball.z >= 65536 ? en.q[surface] : sg.d[surface])
    : 60293L;
ball.vx = friction * ball.vx >> 16;
ball.vy = friction * ball.vy >> 16;
```

Interpretation:

- Ball friction depends on pitch surface and whether the ball is airborne.
- The `high_friction` timer makes the ball slow much faster for a short window.
- The ball uses deterministic integer math rather than floating point.

## Footballer Movement

`nl.a(int, la[] boxes, boolean isBoosted, boolean isSlowed)` updates a footballer.

Working behavior:

- Decrements action timers.
- Chooses movement velocity based on action state.
- Calls the same `lt.a(...)` integrator.
- Applies gravity: if airborne, `zVelocity -= 26214`, about `0.4` world units/tick.
- If Z collision crosses floor, it zeros `z` and `zVelocity`.

Movement/action details:

- Idle/run/dash use direction bitmask `G` converted to `j,n`.
- Tackle-like actions use stored tackle velocity `k,m`.
- `ACTION_DASH` uses a doubled scale from a speed field.
- `ACTION_DIVE` moves toward a keeper target.
- `ACTION_RUN_HOME` speed is based on class speed table `io.q[class] * 3`.

Runtime speed derivation in `nl.a(boolean member, up stats, int)`:

```java
baseMove = ea.j[class] + (io.q[class] - ea.j[class]) * statSpeed / 100
actionPower = g.b[class] + (pv.J[class] - g.b[class]) * statPower / 100
diagMove = 181 * (baseMove >> 8)
diagAction = (actionPower >> 8) * 181
```

Stat accessors:

- Movement speed uses `up.d(member, byte)`, effective `SPD`.
- Action/tackle/contact power uses `up.a(member, int)`, effective `TCK`, in the current naming from the class.
- Kick charge timing uses `up.d(member, byte)`, effective `SPD`.
- The special low-shot flag uses `up.c(member, byte)`, which is true for Hotshot or Hotshot Clone.

Class clone trinkets can make runtime movement/action derivation use another class table:

- Ranger/Ranger Clone can force movement table class `3`.
- Tank/Tank Clone can force action-power table class `0`.
- Hotshot/Hotshot Clone enables the special low-shot branch.

Class movement tables:

- `ea.j`:
  - Tank: `147456` = `2.25`
  - Hotshot: `163840` = `2.50`
  - Elite: `163840` = `2.50`
  - Ranger: `180224` = `2.75`
  - Keeper: `163840` = `2.50`
- `io.q`:
  - Tank: `204800` = `3.125`
  - Hotshot: `221184` = `3.375`
  - Elite: `204800` = `3.125`
  - Ranger: `245760` = `3.75`
  - Keeper: `204800` = `3.125`

Power/action tables:

- `g.b`:
  - Tank: `286720` = `4.375`
  - Hotshot: `163840` = `2.50`
  - Elite: `163840` = `2.50`
  - Ranger: `163840` = `2.50`
  - Keeper: `327680` = `5.00`
- `pv.J`:
  - Tank: `409600` = `6.25`
  - Hotshot: `204800` = `3.125`
  - Elite: `204800` = `3.125`
  - Ranger: `180224` = `2.75`
  - Keeper: `655360` = `10.00`

## Possession and Pickup

The ball stores possession as:

- `ball.m`: team index, `-1` if free.
- `ball.s`: footballer slot.

When possessed, the match tick snaps the ball to the footballer:

```java
ball.x = footballer.x
ball.y = footballer.y
ball.z = footballer.z
```

Free-ball pickup checks:

- `ball.g(...)` must be true:
  - `uncatchable == 0`
  - ball height `< 30`
  - ball Y is within broad pitch bounds
- Candidate footballers are skipped if they are tackling, heading, diving, falling, or tackled.
- Distance threshold for pickup/contact is usually `distanceSquared < 1600`, i.e. within about `40` world units.
- Keepers use a different radius tied to keeper state: `(20 - keeper.o)^2`.

## Ball/Footballer Contact

When a free ball contacts a footballer:

```java
dx = footballer.x - ball.x
dy = footballer.y - ball.y
distanceSquared = dx*dx + dy*dy
if distanceSquared < 1600:
    ball.copyPosition(footballer)
    ball.m = team
    ball.s = slot
```

For some contacts the ball is kicked/deflected instead of possessed:

```java
impulse = (4 * footballer.tackleStat << 16) / 100 + 524288
speed = impulse + max(footballer.actionPower, ballHorizontalSpeed)
ball.uncatchable = 5
ball.vy = footballer.tackleVy * speed / footballer.actionPower
ball.vx = footballer.tackleVx * speed / footballer.actionPower
```

The `524288` base is `8.0` in 16.16 units.

## Kicks / Passes / Shots

Clean method:

```java
nu.a(int power, boolean high, boolean special, int dx, byte, int dy)
```

Reconstructed formula:

```java
kickScale = ((393216 * power) >> 8) + 786432
angle = high ? 700 : 227
horizontalMagnitude = (kickScale >> 8) * cosTable(angle) >> 8
verticalVelocity = (kickScale >> 8) * sinTable(angle) >> 8

if special && !high && power > 32:
    horizontalMagnitude += (horizontalMagnitude * 3 >> 1) + (1280 * power)
    ball.high_friction = 25

length = sqrt(dx*dx + dy*dy)
ball.vz = verticalVelocity
ball.vx = dx * horizontalMagnitude / length
ball.vy = dy * horizontalMagnitude / length
ball.possessor = -1
ball.uncatchable = high ? 35 : 20
```

Interpretation:

- Low kicks use angle index `227`.
- High kicks/lobs use angle index `700`.
- Once charge timing is converted to `power`, velocity increases linearly with that `power`.
- Special low shots above power 32 get a large horizontal boost and high-friction timer.
- After a kick, the ball cannot be immediately caught for 20 or 35 ticks.

Pass-to-teammate helper:

```java
nu.b(int receiverSlot, byte)
```

It computes a target vector from ball to teammate, estimates accumulated friction over 70 ticks, and sets:

```java
ball.vx = scaledTargetX
ball.vy = scaledTargetY
ball.vz = 573440   // 8.75 in 16.16
ball.uncatchable = 10
ball.possessor = -1
```

This is likely the high pass / teammate lob behavior.

## Kick / Tackle Input Path

`nu.a(byte, ki)` handles active-play kick/tackle input.

Observed behavior:

- It only accepts input while match phase is `Playing`.
- If there is an active goal sequence or lockout, it ignores input.
- `ki.u` selects the controller/player.
- `ki.o` and `ki.p` are the command vector bytes. If no vector is supplied, it falls back to the footballer's current movement direction.
- If the selected footballer has possession and is charging a kick, command release stores:
  - `nl.P = yVector`
  - `nl.x = xVector`
  - `nl.z = ki.v` charge/action value
  - `nl.h = directionBitmask`
  - action becomes `ACTION_KICK`
- If the footballer does not have possession and can act, the same vector becomes a tackle angle. The player enters `ACTION_TACKLE`.
- If the ball is free, the code also calls the header/volley intercept planner.

This means shooting, tackling, and aerial attempts share the same directional command path.

Charge start is handled by keypress commands in `nu.b(byte, ki)`:

- Keypress `6` starts `ACTION_CHARGE_KICK` with `O = false`.
- Keypress `7` starts `ACTION_CHARGE_KICK` with `O = true`.
- `O` is passed into the kick formula as the high/alternate kick flag.
- The charge action timer is set to `nl.c(byte)`.

`nl.c(byte)` returns the charge cycle length:

```java
chargeCycle = 80 + 120 * (100 - chargeStat) / 100
```

The exact stat accessor is still obfuscated, but stronger charge-related stats shorten the cycle toward `80` ticks; weaker stats push it toward `200` ticks.

Mouse/click release in `va.c(dx, dy, -1)`:

- Repeatedly halves the vector until both components fit in signed byte range.
- Sends a `Mouse` command with those bytes.
- If the selected player is currently charging, `ki.v` is set to that player's current `L` timer.

Charge-to-power curve:

```java
statWindow = chargeStat * 14 / 100
deadZone = 14 - statWindow
cycle = nl.c(byte)
phase = (deadZone + chargeTimer) % cycle
half = cycle / 2
distanceFromPeak = phase > half ? cycle - phase : phase

if distanceFromPeak < deadZone:
    power = 0
elif distanceFromPeak > half - statWindow:
    power = 256
else:
    power = ((distanceFromPeak - deadZone) << 8) / (half - deadZone - statWindow)
```

So kick power is a timing curve, not a simple "hold longer is stronger" ramp. The best window is centered around the middle of the cycle, with stat-dependent forgiveness.

## Shot / Pass Branching

When a footballer is in `ACTION_KICK`, the main match tick waits until `L == 20` and confirms that this player still owns the ball.

Then:

- If `nl.z < 0`, it calls `nu.b(-nl.z, byte)`, the teammate lob/pass helper.
- Otherwise it converts `nl.z` through `nl.a(nl.z, byte)` into `0..256` power.
- It calls `nu.a(power, nl.O, specialLowShotFlag, nl.x, byte, nl.P)`.
- It copies ball position from the kicker after applying the impulse.
- It logs a `ch` shot attempt with type `kick`.

The `specialLowShotFlag` comes from a player-stat/class capability check: `nl.N.c(nl.y, byte)`. When true and the kick is low with power above `32`, the kick formula adds the special low-shot boost and sets high friction.

That check resolves to Hotshot class or Hotshot Clone trinket.

Stat counters after a normal kick:

- If `O == true`, increment one kick bucket.
- Else if power `< 128`, increment the low/weak kick bucket.
- Else increment the stronger kick bucket.

Tutorial text confirms the player-facing mapping:

- Left mouse button: kick/tackle/pass direction.
- Holding left mouse button: charged pass/shot.
- Right mouse button: lob to a teammate, or change player when not in possession.

## Headers / Volleys

The helper `nu.a(nl footballer, byte)` predicts whether a tackling/actioning footballer can meet a free ball.

Reconstructed behavior:

1. Copy the current ball into a temporary `tj`.
2. Simulate the footballer's tackle/action movement for up to `nl.L` ticks.
3. Simulate the temporary ball with normal free-ball physics over the same ticks.
4. After the first 10 ticks, track the closest predicted distance.
5. If the closest distance is within `10000` distance-squared and happens after tick 1, retarget the footballer's action velocity to intercept that predicted ball position.
6. If the predicted ball is above the player's head by more than `5` world units and the player is grounded, set vertical velocity and switch to `ACTION_HEADER`.

Header jump details:

```java
neededZ = predictedBallZ - playerZ - (5 << 16)
playerZVelocity = (neededZ + tick*tick*26214) / tick
playerZVelocity = min(playerZVelocity, 458752)
action = ACTION_HEADER
actionTimer = (playerZVelocity << 1) / 26214
```

The same later contact block treats `ACTION_HEADER` as a special ball strike. It sets `ball.uncatchable = 5`, copies the ball to the player, and applies a velocity based on the player's action velocity plus current ball speed.

## Tackles

`nl.b(int angle, int controllerId)` starts a tackle:

```java
action = ACTION_TACKLE
tackleVx = cos(angle) * (actionPower >> 8)
tackleVy = sin(angle) * (actionPower >> 8)
actionTimer += tackleStat / 5
F = controllerId
s = false
```

Tackle collision in `nu.b(...)`:

- If an `ACTION_TACKLE` footballer is within `40` units of another non-keeper footballer:
  - victim action becomes `ACTION_FALL_TACKLED`.
  - victim timer increases by tackler tackle stat.
  - victim position is copied from tackler.
  - tackler may enter `ACTION_TACKLE_SUCCESS`.
  - possession can transfer to the tackler if the victim had the ball.

## Goal Detection

`ua.a(tj ball, int)` detects goals.

Requirements:

- No goal sequence is already active (`goal_count <= 0`).
- Ball is free (`ball.m == -1`).
- Ball X is inside the goal mouth: `371 <= x <= 525`.
- Ball Y has crossed a pitch end:
  - `ball.y < 0`: side `0` scored.
  - `ball.y > 1344 << 16`: side `1` scored.

When a goal is detected:

```java
goal_count = 1
goal_scorer = side
```

The main match tick then increments the scorer's score, sets `ball.uncatchable = 205`, resets the opposing keeper's keeper-state counter, and after `goal_count >= 245` resets for kickoff.

Scoring attribution:

- `tj.o`, `tj.i`, and `tj.j` are last-touch / shot-type bookkeeping fields.
- `ch` logs the shot/cross/header attempt, shooter, opposing keeper, keeper state, kick vector, and power.
- The client has localized own-goal display text, so own goals are handled somewhere in the presentation/stat path.
- The exact rule that turns ball last-touch into displayed scorer or own-goal text is not fully isolated yet.

## Keeper Behavior

Keepers are class id `4` and slot `0`. Their `toString()` includes:

```text
keeperstate=[o,t]
```

Working interpretation:

- `o`: keeper extension/deflection state. It grows up to `15` during repeated keeper-ball contacts.
- `t`: keeper dive/target X position.

Keeper dive setup:

```java
nl.c(targetX, actionState)
```

This sets facing left/right based on `targetX`, stores `t = targetX`, and increases action time by `o * 2`.

`ACTION_DIVE` movement uses:

```java
range = 327680 - (o << 14)
```

That is `5.0 - o * 0.25` world units per tick in 16.16 scale, so the keeper's movement/extension changes as `o` grows.

Keeper ball deflection in the match tick:

- Checks each keeper when the ball is free.
- If the ball is close enough, copies the ball position to the keeper.
- Computes an outgoing angle from ball-to-keeper direction, adjusted by keeper facing and team side.
- Preserves current ball speed magnitude, then rewrites `ball.vx` and `ball.vy` from the adjusted angle.
- Runs one ball physics tick.
- Increments keeper `o` up to `15`.

This is not fully named yet, but it is enough to recreate the broad keeper touch/deflection feel.

Keeper AI entry point:

```java
hv.a(boolean, nu match, int team)
```

Important behavior:

- Keeper is `P[team][0]`.
- Own goal line Y is `1344` for team `0`, `0` for team `1`.
- `bl5` means the ball is within `250` world units of `(448, ownGoalY)`.
- If idle and not already moving, the keeper enters `ACTION_KEEPER_SHUFFLE`.
- If the ball is threatening and free, it tries `wt.a(ball, keeper, byte, team)` for a save prediction.
- If the ball is near the goal center, `gg.a(...)` computes a guarded target near the goal mouth, then `ue.a(...)` steers the keeper toward that target.
- If the keeper owns the ball, `lk.a(...)` turns possession into a pass/clear to the deepest teammate.
- If the keeper is tackling/diving and the ball is no longer free, it transitions back toward idle/run-home states.

Save prediction in `wt.a(ball, keeper, byte, team)`:

```java
if ball.possessor != -1 or ball.vy == 0:
    return false

window = 20 - (keeper.o >> 1)
ticks = (keeper.y - ball.y) / ball.vy
ticks = 9 * ticks / 4

if ticks <= 2 or ticks >= window:
    return false

predictedX = ball.x + ball.vx * ticks

if predictedX outside roughly 372..523:
    keeper.G = 0
    return false

if abs(predictedX - keeper.x) is close enough:
    keeper faces toward predictedX
else:
    keeper.c(predictedX, ACTION_DIVE)
```

The save window shrinks as `keeper.o` grows, which makes repeated/extended keeper contact less forgiving.

## Initial Formation / Reset

`nu.a(int, int)` resets player positions and the ball:

```java
ball.reset(448 << 16, 672 << 16, 0)
ball.possessor = -1
```

Footballers are placed using helper functions (`ts.a`, `cp.a`, etc.) based on slot, team, and formation/pitch mode.
