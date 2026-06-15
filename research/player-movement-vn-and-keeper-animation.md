# Player Movement, VN Models, and Keeper Animation

Sources checked:

- `vn_player_test.py`
- `C:\Users\reidm\OneDrive\Desktop\codex\deob\vn_player_test.py`
- `C:\Users\reidm\OneDrive\Desktop\codex\deob\vn_to_obj.py`
- `C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout\decompiled\nl.java`
- `C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout\decompiled\gm.java`
- `C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout\decompiled\hv.java`
- `C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout\decompiled\wt.java`
- `C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout\decompiled\uv.java`
- `C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout\decompiled\df.java`
- `C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout\decompiled\pu.java`

## `vn_player_test.py` Status

The current visual test is useful for viewing the decoded VN body/head meshes, but it is not an original movement or animation implementation.

Important limitations:

- It renders 16 yaw snapshots by rotating the static combined body/head mesh.
- It does not use the original model renderer's pose sequence table.
- It treats the keeper as just another static character with walk/sprint speeds.

The keeper appears more correctly colored because `Characters_keeper_body.bin` already has strong face colors in the raw VN mesh, including red/yellow/white/black material values. The outfield bodies are intended to be kit-recolored from indexed face-color swatches, not globally tinted after rendering.

Current color status: `vn_player_test.py` now applies the confirmed deob-style face-color replacement for outfield players instead of the older broad tint blend. It replaces the `0xDBBC` class-base placeholder and the generated kit placeholder grids while leaving all other face colors alone. `kit-color-contact-sheet.png` compares the raw placeholders with the deob recolor output. This is confirmed working in the viewer: the outfield players now have basic but meaningful kit colors.

## Direction Bitmask

Original footballer direction is stored in `nl.G`, a 4-bit mask.

`nl.a(int directionMask, int)` decodes it into movement components:

```text
+X: bit 1 -> n += 1
-X: bit 4 -> n -= 1
-Y: bit 2 -> j -= 1
+Y: bit 8 -> j += 1
```

So the screen-style movement mapping is:

```text
right: bit 1
left:  bit 4
up:    bit 2
down:  bit 8
```

If no bits survive after decode, the method defaults `n = 1`, which makes a zero/invalid direction face right.

`nl.d(int)` reverses `j,n` back into this same mask.

`uv.a(true, dy, dx)` converts a target vector into this 4-bit direction mask. It wraps `uv.b(...)`, which uses the game's 8192-step angle system, then `en.b(...)` quantizes that angle to a direction mask.

## Why Movement Can Look Wrong In The VN Test

`vn_player_test.py` uses Pygame vectors for motion:

```python
x = right - left
y = down - up
```

That matches the original bit meaning above.

The confusing part is the visual yaw:

```python
angle = atan2(vec.x, -vec.y)
frame = round(angle / tau * 16)
```

This assumes yaw frame `0` means "facing up/north". The original renderer does not use those 16 baked frames. It continuously turns a render heading `gm.R` toward a model angle, and the mesh's native forward axis has an offset in the renderer path.

Evidence from `gm`:

- `gm.R` is a 2048-step render angle, not the 8192-step physics angle.
- Each visual update rotates `R` toward the target by `64` units per tick.
- The model is rendered with `eg2.a(..., n6, ...)`, where `n6` is `R` plus state-specific flips/offsets.
- `eg.a(...)` rotates model X/Z with the same sin/cos sign as the Python VN projection.
- `gm.b(...)` adds `1700` before rebuilding the lit model, but that is a lighting/model-cache angle, not the visible yaw passed to `eg2.a(...)`.
- For dash in megamode, the visible yaw adds `L * (2048 / vf.I[4])`, producing a full 2048-step spin over the 30-tick dash duration.
- `gm.f(byte)` maps movement components to render headings directly:
  - right `0`
  - up-right `256`
  - up-left `512`
  - up `768`
  - left `1024`
  - down `1280`
  - down-left `1536`
  - down-right `1792`

Interpretation: movement direction in the test is probably not reversed, but the rendered body heading can appear offset or mirrored if the Python viewer treats the lighting angle as visible yaw or forgets that its simplified projection mirrors left/right relative to the Java camera basis. In `vn_player_test.py`, the current viewer-facing conversion is:

```python
angle = atan2(-screen_x, -screen_y)
heading = angle / tau * 2048
```

That makes W show the model back, S show the model front, D show the right-facing profile, and A show the left-facing profile in the Python contact sheet.

## Idle / Non-Possession Facing

The deob does not show an outfield idle rule that turns the player toward the ball just because the player does not possess it.

Relevant behavior:

- `gm.f(byte)` derives the target render heading from `nl.j` and `nl.n`.
- `nl.a(directionMask, ...)` decodes `G` into `j/n`.
- If `directionMask == 0`, `nl.a(...)` returns immediately and does not clear `j/n`.
- Therefore idle/no-input visual heading keeps the previous decoded movement/action direction, including diagonals.

`vn_player_test.py` now follows that approximation: when no movement keys are held and the player is not carrying the ball, the player remains oriented to the last WASD/diagonal direction instead of automatically facing the ball. The original `gm.f(...)` path has explicit diagonal visual headings for up-right, up-left, down-left, and down-right, so diagonal idle is a valid approximation.

## Original Movement Speeds

`nl.a(boolean member, up stats, int)` derives runtime speed fields:

```text
A = base movement speed from class + SPD
g = diagonal movement speed helper = 181 * (A >> 8)
q = tackle/action power speed from class + TCK
D = diagonal action helper = (q >> 8) * 181
```

The diagonal helper is used when both movement axes are active. This is why `nl.b(false)` checks whether the current mask is diagonal.

Movement action behavior in `nl.a(...)`:

- Idle, charge, run-home, and keeper-shuffle use `A` for cardinal movement and `g` for diagonal movement.
- If boosted/megamode (`l`), movement speed becomes `speed * 5 / 4`.
- If slowed, movement speed becomes `speed * 9 / 10`.
- Charge-kick movement is heavily reduced: Ranger or Ranger-clone gets half speed, others get quarter speed.
- `ACTION_KEEPER_SHUFFLE` uses a fixed speed of `73728`, about `1.125` world units/tick.
- `ACTION_RUN_HOME` uses `io.q[class] * 3`, with diagonal correction if needed.
- `ACTION_DASH` uses doubled movement speed and can update direction while dashing if the player has the slalom capability.
- Tackle/header/success actions use stored tackle/action velocity rather than fresh movement input.
- Keeper dive moves only on X toward stored target `t`, with range `327680 - (o << 14)`.

## Running, Walking, Sliding, and Heading

The decompiled game does not expose a simple "walk vs run" boolean like the current Pygame test.

Closest original concepts:

- Normal movement: idle/charge/run-home/shuffle using class/stat speed `A`/`g`.
- Dash: action `4`, a timed doubled-speed action, not a held sprint for every class.
- Ranger ability: Ranger can keep more movement while charging and has the tutorial-described sprint-with-ball/custom movement behavior.
- Tackle/slide: action `3`, using stored velocity `k,m` from the tackle angle and class/stat action power `q`/`D`.
- Header: action `13`, selected by the free-ball intercept planner when the predicted ball is above the player's head.

Tackle setup in `nl.b(int angle, int controllerId)`:

```text
action = ACTION_TACKLE
k = cos(angle) * (q >> 8)
m = sin(angle) * (q >> 8)
L += effectiveTackleStat / 5
F = controllerId
s = false
```

If the Tank/Tank-clone turning capability is present and `G != 0`, a tackling player can retarget the action velocity from current direction input during the tackle.

Header setup is described in `physics.md`, but the visual consequence is in `gm`: `ACTION_HEADER` maps to pose `8` and a slower animation rate (`d2 = 0.38`).

## Action Durations

`vf.I` holds base action timers:

```text
ACTION_KICK             2  -> 21 ticks
ACTION_TACKLE           3  -> 22 ticks
ACTION_DASH             4  -> 30 ticks
ACTION_DIVE             5  -> 40 ticks
ACTION_DIVE_STAND       6  -> 80 ticks
ACTION_FALL_TACKLED     7  -> 30 ticks
ACTION_PAUSE_TACKLED    8  -> 20 ticks
ACTION_STAND_TACKLED    9  -> 30 ticks
ACTION_TACKLE_STAND     10 -> 10 ticks
ACTION_RUN_HOME         11 -> 2 ticks
```

Action `1` charge-kick uses `nl.c(byte)` instead:

```text
chargeCycle = 80 + 120 * (100 - SPD) / 100
```

Keeper shuffle (`14`) has no `vf.I` initializer; it is used as an ongoing AI movement state rather than a fixed-duration action.

## Keeper AI and Save Movement

Keeper class id is `4`, slot `0`.

`hv.a(boolean, nu match, int team)` is the keeper AI entry point:

- Own goal line is `1344` for team `0`, `0` for team `1`.
- The keeper checks whether the ball is within 250 world units of `(448, ownGoalY)`.
- If the keeper is idle/shuffling and has no urgent ball possession path, it starts `ACTION_KEEPER_SHUFFLE`.
- If the ball is free and threatening, it calls `wt.a(ball, keeper, byte, team)` to predict a save.
- If the ball is close to the goal area, `gg.a(...)` picks a guarded target and `ue.a(...)` steers the keeper.
- If the keeper owns the ball, `lk.a(...)` clears/passes to a teammate.

Save prediction in `wt.a(...)`:

```text
requires free ball
requires ball.vy != 0
window = 20 - (keeper.o >> 1)
ticks = ((keeper.y - ball.y) / ball.vy) * 9 / 4
reject if ticks <= 2 or ticks >= window
predictedX = ball.x + ball.vx * ticks
reject/stop if predictedX outside about x=372..523
if close enough: face the predicted X
else: start ACTION_DIVE toward predictedX
```

Keeper dive setup in `nl.c(targetX, action)`:

```text
action = ACTION_DIVE
G = targetX > keeper.x ? 8 : 2
t = targetX
decode G into movement direction
L += o * 2
```

The `G = 8/2` assignment looks odd because those are Y direction bits, but keeper dive movement does not use `j,n` for actual X movement. `ACTION_DIVE` separately compares `targetX` with current X and pushes left/right by `327680 - (o << 14)`.

## Keeper Visual Pose Mapping

`gm` is the visual subclass of `nl`. It maps action state `u` to pose sequence id `ob` through `gm.b(byte, int)`.

Confirmed mappings from `gm`:

```text
default idle/standing: pose 3, rate 1.0
moving: pose 5
moving with eb flag: pose 16
ACTION_KEEPER_SHUFFLE (14): pose 15, rate 1.5
ACTION_KICK (2), once facing target: pose 4
ACTION_TACKLE (3): pose 0
ACTION_TACKLE_SUCCESS (12): pose 0
ACTION_HEADER (13): pose 8, rate 0.38
ACTION_TACKLE_STAND (10): pose 6, rate 2.0
ACTION_TACKLE_STAND early/recovery: pose 7
ACTION_DIVE (5): pose 12 or 14, chosen by dive side
ACTION_DIVE_STAND (6): pose 13 or 11, chosen by dive side
ACTION_STAND_TACKLED (9): pose 2
ACTION_FALL_TACKLED (7): pose 1
ACTION_PAUSE_TACKLED (8): pose 2, rate 0.0
ACTION_RUN_HOME (11), when moving: pose 9
```

Dive side is derived from current Y/side and direction bit `G & 2`. It is not just "left/right equals pose A/B"; the code flips it based on keeper side and field half.

The renderer advances the current pose sequence through `dd mb`, then calls:

```text
mb.a(pv.I[classId][poseId], ...)
```

So the real animation frames are not in the VN mesh files alone. The VN files provide body/head geometry and colors; `pv.I[class][pose]` provides the sequence/pose data used to deform or animate the model.

## Animation Registry

`rf.a(...)` initializes the player animation table:

```text
pv.I = new nm[5][17]
```

So there are 5 class rows and 17 pose slots (`0..16`). Each populated entry is an `nm` animation sequence loaded from the `characters` animation archive. Missing class/pose slots are filled by copying the same pose slot from earlier class rows:

```java
while (pv.I[class][pose] == null) {
    pv.I[class][pose] = pv.I[fallbackClass++][pose];
}
```

Named animation sequences from `rf.java`:

```text
Tank class 0:
  pose 0  ka_tank_aggressive_tackle
  pose 1  ka_tank_fall
  pose 2  ka_tank_fall_stand
  pose 3  ka_tank_idle
  pose 4  ka_striker_kick
  pose 5  ka_tank_run
  pose 6  ka_tank_tackle_stand
  pose 8  ka_tank_diving_header
  pose 9  ka_tank_celebrate_new
  pose 16 ka_tank_aeroplane

Hotshot class 1:
  pose 0  ka_striker_aggressive_tackle
  pose 1  ka_striker_fall
  pose 2  ka_striker_fall_stand
  pose 3  ka_striker_idle
  pose 5  ka_striker_run
  pose 6  ka_striker_tackle_stand
  pose 9  ka_striker_celebrate_new
  pose 16 ka_striker_aeroplane
  pose 4/8 are filled from Tank: striker_kick and tank_diving_header

Elite class 2:
  pose 0  ka_specialist_aggressive_tackle
  pose 1  ka_specialist_fall
  pose 2  ka_specialist_fall_stand
  pose 3  ka_specialist_idle
  pose 5  ka_specialist_run
  pose 6  ka_specialist_tackle_stand
  pose 9  ka_specialist_celebrate_new
  pose 16 ka_specialist_aeroplane
  pose 4/8 are filled from Tank: striker_kick and tank_diving_header

Ranger class 3:
  pose 0  ka_scout_aggressive_tackle
  pose 1  ka_scout_fall
  pose 2  ka_scout_fall_stand
  pose 3  ka_scout_idle
  pose 5  ka_scout_run
  pose 6  ka_scout_tackle_stand
  pose 7  ka_scout_tackle_delay
  pose 9  ka_scout_celebrate_new
  pose 16 ka_scout_aeroplane
  pose 4/8 are filled from Tank: striker_kick and tank_diving_header

Keeper class 4:
  pose 0  ka_keeper_aggressive_tackle
  pose 3  ka_keeper_idle
  pose 4  ka_keeper_kick
  pose 5  ka_keeper_run
  pose 6  ka_keeper_tackle_stand
  pose 10 ka_keeper_basic_catch
  pose 11 ka_keeper_l_dive_stand
  pose 12 ka_keeper_l_dive_static
  pose 13 ka_keeper_r_dive_stand
  pose 14 ka_keeper_r_dive_static
  pose 15 ka_keeper_l_shuffle
  other missing poses are filled from earlier class rows
```

Practical pose meanings by behavior:

```text
0  aggressive tackle / slide tackle
1  fall
2  fall stand / stand tackled
3  idle
4  kick
5  run
6  tackle stand
7  tackle delay / delayed recovery, only explicitly named for Ranger
8  diving header
9  celebrate / run-home celebration
10 keeper catch
11 keeper left dive stand
12 keeper left dive static
13 keeper right dive stand
14 keeper right dive static
15 keeper shuffle
16 aeroplane / speed-up style run flag
```

`dd` is the sequence player. `gm.b(byte, poseId)` calls:

```java
mb.a(pv.I[classId][poseId], ...)
```

`dd` advances through `nm.e` frame ids using `nm.c` frame durations and applies each frame to the model before rendering:

```java
qc3.a(se.C, currentFrameId, ...)
```

## Kit Color Recoloring

Outfield kit recoloring happens before rendering, by replacing specific face color ids in a copied `vn`.

Relevant methods:

- `df.a(...)`: recolors the shared torso model.
- `pu.a(...)`: recolors full character/head/body combinations.
- `ks.a(...)`: constructs the kit placeholder HSL16 ids.
- `ev.B`: original 32-entry kit color palette.
- `hk.K`: class-base replacement colors for non-keepers.

The recolor logic uses kit pattern boolean grids and replaces generated color ids from `ks.a(...)` with primary/secondary kit colors. There are two related base-color paths:

- `pu.a(...)` replaces class-specific base color `-9284` with `hk.K[class][0]` for non-keepers.
- `hs.a(...)`, used by `fp.a(...)` when assembling appearance-specific characters, replaces `-9284` through `gt.h[class][headStyle][skinSlot][0]` and then applies more appearance tables such as `hr.m[...]` and `ad.e[...]`.

Confirmed details:

- `ks.a(hue, lightRow, ..., sat)` is effectively:

```text
hue | (lightRow << 10) | (sat << 7)
```

- `-9284` as an unsigned 16-bit face color is `0xDBBC`. This is the large class-base placeholder present on outfield bodies.
- `pu.a(...)` replaces `0xDBBC` with class base color before kit pattern recoloring, but only when `class != 4`, so keepers are excluded.
- The simpler `hk.K` replacement is not enough for the current static viewer. It makes Hotshot look reasonable because `hk.K[1][0] = 0x15a6` is brown and close to the striker body/head tone, but `hk.K[3][0] = 0x71c9` is teal and `hk.K[0][0] = 0x5229` is green. Those do not match Ranger/Tank `head_01` skin colors.
- Confirmed working viewer approximation: map `0xDBBC` to the selected head variant's dominant skin color. This fixes Ranger/Tank arms and legs to match their heads while preserving the kit recolor pass. The in-viewer result was confirmed as working perfectly.
- The asset set has five numbered heads per character prefix: `head_01` through `head_05`. Halloween heads also exist but are not part of the normal skin cycle yet.
- Tank `head_04` has a large dark hair-color region and is the likely afro head.

Class-base replacements from `hk.K`:

```text
Tank    class 0 -> 0x5229 -> RGB (47, 129, 35)
Hotshot class 1 -> 0x15a6 -> RGB (109, 74, 44)
Elite   class 2 -> 0x14ec -> RGB (222, 217, 211)
Ranger  class 3 -> 0x71c9 -> RGB (100, 193, 158)
Keeper  class 4 -> excluded
```

Original kit palette from `ev.B`:

```text
0  0x038a RGB (40, 0, 0)       16 0x03b2 RGB (201, 0, 0)
1  0x138a RGB (40, 15, 0)      17 0x13b2 RGB (201, 75, 0)
2  0x238a RGB (40, 30, 0)      18 0x23b2 RGB (201, 151, 0)
3  0x338a RGB (35, 40, 0)      19 0x33b2 RGB (176, 201, 0)
4  0x438a RGB (20, 40, 0)      20 0x43b2 RGB (100, 201, 0)
5  0x538a RGB (5, 40, 0)       21 0x53b2 RGB (25, 201, 0)
6  0x638a RGB (0, 40, 10)      22 0x63b2 RGB (0, 201, 50)
7  0x738a RGB (0, 40, 25)      23 0x73b2 RGB (0, 201, 125)
8  0x838a RGB (0, 40, 40)      24 0x83b2 RGB (0, 201, 201)
9  0x938a RGB (0, 25, 40)      25 0x93b2 RGB (0, 125, 201)
10 0xa38a RGB (0, 10, 40)      26 0xa3b2 RGB (0, 50, 201)
11 0xb38a RGB (5, 0, 40)       27 0xb3b2 RGB (25, 0, 201)
12 0xc38a RGB (20, 0, 40)      28 0xc3b2 RGB (100, 0, 201)
13 0xd38a RGB (35, 0, 40)      29 0xd3b2 RGB (176, 0, 201)
14 0x0014 RGB (40, 40, 40)     30 0x0028 RGB (80, 80, 80)
15 0x0001 RGB (2, 2, 2)        31 0x007c RGB (249, 249, 249)
```

Suggested non-keeper viewer kits:

```text
Hotshot:
  - Burnt orange / white: primary 17, secondary 31
  - Red / charcoal: primary 16, secondary 14
  - Gold / black: primary 18, secondary 15

Ranger:
  - Cyan / white: primary 24, secondary 31
  - Teal / dark slate: primary 23, secondary 14
  - Green / white: primary 20, secondary 31

Tank:
  - Red / black: primary 16, secondary 15
  - Gold / charcoal: primary 18, secondary 14
  - Lime / black: primary 20, secondary 15
```

The previous `vn_player_test.py` global tint:

```python
rgb = rgb * 0.55 + tint * 0.45
```

did not match original recoloring. The current viewer follows the closer strategy:

1. Keep original face colors by default.
2. Replace `0xDBBC` with the class base color for Hotshot/Ranger/Tank.
3. Apply kit recolor only to generated pattern swatches from `ks.a(...)`.
4. Avoid tinting skin, hair, outlines, and keeper-specific colored panels.

This is confirmed in `vn_player_test.py` by `build_color_map(...)`:

- `0xDBBC` maps to a viewer body-base color for non-keepers. The viewer now cycles body-base values with the selected numbered head/skin variant until the full `gt.h/hr.m/ad.e` appearance recolor path is implemented.
- Saturation `7` placeholder ids map to the selected primary kit palette index.
- Saturation `6` placeholder ids map to the selected secondary kit palette index.
- Keeper uses the raw VN face colors and is excluded from this replacement path.

Current viewer head/skin cycling:

```text
Hotshot: head_01..head_05
Ranger:  head_01..head_05
Tank:    head_01..head_05, with head_04 labeled afro
Keeper:  head_01..head_05, raw body colors
```

## Practical Implementation Notes

For `vn_player_test.py`, the quickest fidelity improvements would be:

- Treat visual heading separately from velocity and rotate it gradually toward the target heading, 64 units per tick in a 2048-step visual circle.
- Add a heading offset/calibration for the VN mesh native forward axis instead of assuming yaw frame `0` faces north.
- Add explicit action states and pose ids for keeper dive/shuffle/stand instead of rotating the idle mesh.
- If the real `pv.I[class][pose]` sequence data can be isolated, use it for pose animation; until then, pose ids above are useful labels but not enough to deform limbs accurately.

## Animation Sequence Decode

This pass confirms the real player animation data is available and decodable.

Archive wiring:

```text
eh.java:
  nt.Bb = dh.a(..., 14)
  vu.Eb = dh.a(..., 15)
  gd.h  = dh.a(..., 16)

de.a(sj2, sj3, ...):
  gs.d = sj2
  gd.c = sj3

rf.a(..., vu.Eb, gd.h, nt.Bb):
  pv.I = new nm[5][17]
```

Meaning:

```text
archive 16 -> nm animation sequence group
archive 15 -> je skeleton transform groups
archive 14 -> db frame definitions
```

Decoded outputs are in `research/animation-decoded/`, generated by `tools/decode_kickabout_animations.py`.

Confirmed extraction:

```text
archive 16_0:
  container kind 1, raw bzip2 block
  packed length   0x112a
  unpacked length 0x3e5d
  split into 91 nm sequence files

archive 15_0:
  split into 2 skeleton files
  skeleton 0 has 63 transforms
  skeleton 1 has 64 transforms

archive 14_0:
  split into 2405 frame files
  all sequence frame refs resolve in range 0..2404
  frame usage: skeleton 1 has 2366 frames, skeleton 0 has 39 frames
```

The sequence CSV contains the per-sequence frame ids and durations:

```text
research/animation-decoded/characters_animation_sequences.csv
research/animation-decoded/skeletons.csv
research/animation-decoded/frames.csv
research/animation-decoded/skeleton_transforms.csv
research/animation-decoded/frame_entries.csv
```

`rf.java` maps named player actions into `pv.I[class][pose]`. Confirmed class ids:

```text
0 Tank
1 Hotshot / Striker
2 Elite / Specialist
3 Ranger / Scout
4 Keeper
```

Confirmed pose slots:

```text
Tank:
  0  ka_tank_aggressive_tackle
  1  ka_tank_fall
  2  ka_tank_fall_stand
  3  ka_tank_idle
  4  ka_striker_kick
  5  ka_tank_run
  6  ka_tank_tackle_stand
  8  ka_tank_diving_header
  9  ka_tank_celebrate_new
  16 ka_tank_aeroplane

Hotshot:
  0  ka_striker_aggressive_tackle
  1  ka_striker_fall
  2  ka_striker_fall_stand
  3  ka_striker_idle
  4  ka_striker_kick, filled from Tank slot 4
  5  ka_striker_run
  6  ka_striker_tackle_stand
  8  ka_tank_diving_header, filled from Tank slot 8
  9  ka_striker_celebrate_new
  16 ka_striker_aeroplane

Elite:
  0  ka_specialist_aggressive_tackle
  1  ka_specialist_fall
  2  ka_specialist_fall_stand
  3  ka_specialist_idle
  4  ka_striker_kick, filled from Tank slot 4
  5  ka_specialist_run
  6  ka_specialist_tackle_stand
  8  ka_tank_diving_header, filled from Tank slot 8
  9  ka_specialist_celebrate_new
  16 ka_specialist_aeroplane

Ranger:
  0  ka_scout_aggressive_tackle
  1  ka_scout_fall
  2  ka_scout_fall_stand
  3  ka_scout_idle
  4  ka_striker_kick, filled from Tank slot 4
  5  ka_scout_run
  6  ka_scout_tackle_stand
  7  ka_scout_tackle_delay
  8  ka_tank_diving_header, filled from Tank slot 8
  9  ka_scout_celebrate_new
  16 ka_scout_aeroplane

Keeper:
  0  ka_keeper_aggressive_tackle
  3  ka_keeper_idle
  4  ka_keeper_kick
  5  ka_keeper_run
  6  ka_keeper_tackle_stand
  10 ka_keeper_basic_catch
  11 ka_keeper_l_dive_stand
  12 ka_keeper_l_dive_static
  13 ka_keeper_r_dive_stand
  14 ka_keeper_r_dive_static
  15 ka_keeper_l_shuffle
```

`qc.java` and `eg.java` show how these frames affect a rendered model:

```text
type 0 -> compute pivot from vertex groups
type 1 -> translate vertex groups
type 2 -> rotate vertex groups around the pivot, using the 2048-step trig table
type 3 -> scale vertex groups around the pivot
type 5 -> adjust face alpha groups
type 7 -> adjust HSL face-color groups
```

Important implementation consequence: player animation is not an object-level spin. It is deformation of `eg.N/W/E` vertex arrays through `vn.s` vertex groups and `vn.v` face groups. The current `vn_player_test.py` loader reads static vertices, faces, and colors, but it does not retain:

```text
vn.C -> per-vertex group id, later converted to vn.s
vn.O -> per-face group id, later converted to vn.v
```

`vn_player_test.py` now preserves these raw group ids:

```text
VNMesh.vertex_groups <- vn.C / per-vertex group id
VNMesh.face_groups   <- vn.O / per-face group id
```

`combine_meshes(...)` carries those ids through when body and head meshes are joined. This matches the Java merge path, where group ids remain semantic skeleton group numbers instead of being offset per mesh.

Current body mesh group counts from the Python loader:

```text
striker    vertices 647, faces 1278, vertex groups 256, face groups 0
scout      vertices 644, faces 1274, vertex groups 104, face groups 0
tank       vertices 609, faces 1202, vertex groups 104, face groups 0
keeper     vertices 519, faces 1034, vertex groups 104, face groups 0
specialist vertices 630, faces 1244, vertex groups 104, face groups 0
```

The lack of face groups on these body meshes means the initial viewer animation path should focus on vertex transforms. Face alpha/HSL animation opcodes exist in the engine, but they are not the primary path for the player body meshes tested here.

Current `vn_player_test.py` animation preview implementation:

```text
F     toggles decoded animation preview
C/V   cycles decoded sequence index
HUD   shows current sequence id, sequence frame count, and decoded frame id
```

The viewer now loads `characters_animation_sequences.csv`, `skeleton_transforms.csv`, and `frame_entries.csv`, applies decoded frame entries to a copy of the selected VN mesh, and renders the deformed mesh at the current heading. Implemented transform types:

```text
0 pivot
1 translate
2 rotate
3 scale
```

The first smoke test loaded 91 sequences, applied frame `642` from sequence `0`, and rendered a `116x150` surface successfully.

The next deob step is name mapping: the dumped `16_0.bin` group payload does not include the archive name index, so the current viewer cycles sequences by numeric decoded index. To bind gameplay actions directly, recover or infer the mapping from `ka_*` names to decoded sequence indexes, then assign:

```text
idle -> pose 3
run -> pose 5
kick -> pose 4
tackle/slide -> pose 0/6/7
header -> pose 8
keeper catch/dive/shuffle -> pose 10..15
```

## Observed Sequence IDs

These are visual observations from `vn_player_test.py` animation preview. They should be treated as confirmed viewer mappings once seen in-game, not as archive-name proof.

```text
seq 00:
  observed: idle/rest animation with head look-around and intermittent head-wipe gesture
  likely action family: idle/rest
  frames: 102
  total duration: 513
  frame ids start: 642, 658, 645, 618, 681, 678, 633, 668, 665, 684, 634, 616
  transform profile: skeleton 1 only, 614 total transform entries, all type 2 rotations
```

Next sequence to test:

```text
seq 01:
  observed: kicking-the-ball motion with arms raised
  likely action family: kick / shot follow-through
  frames: 6
  total duration: 21
  frame ids: 376, 380, 375, 379, 378, 377
  frame durations: 2, 5, 4, 5, 2, 3
  transform profile: skeleton 1 only, 141 total transform entries
  transform types: 132 type 2 rotations, 9 type 1 translations
  per-frame transform entries: 23..24

seq 02:
  observed: being tackled
  likely action family: tackled / hit reaction
  frames: 31
  total duration: 46
  note: Hotshot showed an orange piece visually stuck behind during this sequence before orphan-group repair

seq 03:
  observed: very subtle small kick with left foot
  likely action family: left-foot light kick/touch
  frames: 24
  total duration: 29

seq 04:
  observed: very subtle small kick with right foot
  likely action family: right-foot light kick/touch
  frames: 24
  total duration: 29

seq 05:
  observed: sliding kick
  likely action family: slide kick / slide tackle
  frames: 27
  total duration: 32
  note: Hotshot showed the same orange-piece artifact as seq 02 before orphan-group repair

seq 06:
  observed: both hands cock back, then bat forward
  likely action family: two-hand bat/throw/push style action
  frames: 39
  total duration: 56

seq 07:
  observed: getting back up after getting tackled
  likely action family: fall stand / recovery
  frames: 23
  total duration: 50

seq 08:
  observed: process of getting tackled
  likely action family: tackle impact / falling into tackled state
  frames: 30
  total duration: 35
```

Hotshot animation artifact:

```text
Observed on seq 02 and seq 05:
  orange piece appears held/stuck behind the Hotshot mesh

Likely cause:
  striker body has one vertex in group 255
  decoded skeleton 1 references groups only up to 119
  vertex 319 at (0, -242, -29), color 0x93a3, participates in four faces
  connected neighbor groups: 68, 82, 65, 59, 53

Viewer repair:
  during animated preview only, vertices with group ids above the active skeleton's max referenced group are reassigned to the most common connected valid neighbor group
  static rendering and source VN data are not changed

Result:
  user confirmed the Hotshot stuck-orange-piece artifact is fixed
  user reviewed all 90/91 decoded sequence previews and they appear visually good overall
  header animation was not obvious in the current sequence scan and remains unmapped
```

## Deob: Gameplay State to Animation Pose

`nl.java` owns the gameplay action state:

```text
u = action state
L = action timer, initialized from vf.I[u]
j/n = direction vector components
z/x/P/O = kick fields shown in debug string
k/m/s/r/B = tackle fields shown in debug string
l = mega mode flag
N = player/class stats object
```

State names from `nl.c(true)`:

```text
0  Idle
1  ACTION_CHARGE_KICK
2  ACTION_KICK
3  ACTION_TACKLE
4  ACTION_DASH
5  ACTION_DIVE
6  ACTION_DIVE_STAND
7  ACTION_FALL_TACKLED
8  ACTION_PAUSE_TACKLED
9  ACTION_STAND_TACKLED
10 ACTION_TACKLE_STAND
11 ACTION_RUN_HOME
12 ACTION_TACKLE_SUCCESS
13 ACTION_HEADER
14 ACTION_KEEPER_SHUFFLE
```

`gm.a(...)` maps those gameplay states onto `pv.I[class][pose]` animation slots:

```text
default pose = 3 idle
moving/e(292603688) = 5 run
moving with eb flag = 16 aeroplane
u == 2 and current heading has aligned = 4 kick
u == 3 or u == 12 = 0 aggressive_tackle
u == 13 = 8 diving_header
u == 10 = 6 tackle_stand, then 7 after L > vf.I[10]
u == 5 = 12 or 14 keeper static dive, selected by side
u == 6 = 13 or 11 keeper dive stand, selected by side
u == 9 = 2 fall_stand
u == 7 = 1 fall / tackled
u == 8 = 2 stand/fall pause with d2 = 0
u == 11 with movement/e(...) = 9 celebrate_new
u == 14 = 15 keeper_l_shuffle
```

Additional renderer behavior from `gm`:

```text
visual heading turns by 64 units per update toward the desired 2048-step direction
for u == 4 dash, mega mode rotates heading over the action timer: L * (2048 / vf.I[4])
animation playback speed d2 defaults to 1.0 and is adjusted per state
mega mode halves animation playback speed, except dash doubles it back
```

This means the state-to-pose relationship is no longer just a visual guess. The remaining uncertainty is the exact numeric decoded sequence id for each named `ka_*` asset because the dumped `16_0.bin` payload does not include the archive name index.

## Main Game Static VN Integration

`main.py` now uses the VN-rendered static heading sprites for both teams' character classes and keepers while preserving the existing gameplay/physics code.

```text
Hotshot -> Characters_striker body/head static heading frames
Ranger  -> Characters_scout body/head static heading frames
Tank    -> Characters_tank body/head static heading frames
Keeper  -> Characters_keeper body/head static heading frames
```

Implementation status:

```text
main.py loads static 32-direction VN surfaces through the vn_player_test loader
Player.draw selects a VN heading frame from the player facing vector
slide/dive still reuse the static heading set until animation state binding is added
Kenney sprites remain as fallback if VN assets fail to load
head/skin and kit choices are currently fixed to known-good defaults
red outfield players use red/white VN kit variants and matching Hotshot/Ranger/Tank class stats
blue outfield players use blue/white VN kit variants
the match game does not expose head/skin cycling; each spawned player gets a random normal variant from the five decoded heads for its class
manual head/skin cycling remains only in vn_player_test.py for research/debugging
controlled blue player is marked with a yellow overhead triangle and ground ring
```

Smoke test result:

```text
main smoke ok 10 [32, 32, 32, 32, 32, 32, 32, 32, 32, 32]
```

## Deob: Movement vs Mouse Aim

The original game separates keyboard movement from mouse action aiming.

Confirmed evidence:

```text
u.java tutorial strings:
  without possession:
    "Left-click to tackle in the direction of the cursor."
    "Right-click to switch character."
  with possession:
    "Charge up a low kick with the left mouse button."
    "Hold right-click to charge up a high pass."

nl.a(int n2, int n3):
  decodes direction bitmask into j/n movement components
  bit 4 -> n--
  bit 1 -> n++
  bit 2 -> j--
  bit 8 -> j++
  if both end at zero, n becomes 1 as a fallback direction

nl.a(...):
  movement velocity comes from j/n and class movement speeds
  possession/dribble affects speed selection, not by itself mouse-facing

gm.f(...):
  visible heading is derived from j/n for ordinary movement
```

Current `main.py` correction:

```text
Before:
  update_hero_mouse_aim() turned the carrier toward the mouse every frame while the hero had the ball.
  This made WASD movement and mouse pointer compete for carry direction.

After:
  mouse aim updates facing only while charging a pass/shot/aerial action.
  normal carrying/dribbling uses WASD/arrow movement direction.
  left-click without possession still aims the tackle/low strike toward the cursor.
```

## Main Game Animation Bindings

The first decoded animations are now bound in `main.py`:

```text
seq 02 -> player is tackled / falling reaction
seq 05 -> active slide kick / tackle
seq 07 -> tackled player getting up near the end of stun
seq 18 -> player carrying / possessing the ball while moving
seq 18 -> player moving without the ball
seq 21 -> default idle, including possessing the ball while not moving
```

Implementation notes:

```text
each spawned player keeps its static 32-direction VN frames plus the VN mesh/color map
Player.draw renders a decoded deformed mesh only for active bound animation states
static heading frames remain the fallback for ordinary movement/idle
flatten_player(...) resets the victim animation timer so seq 02 starts at tackle impact
seq 07 is selected for the final get-up portion of stun
```

Smoke result:

```text
possess smoke 18 True
tackle smoke 2
getup smoke 7
```

Updated smoke result:

```text
idle (21, ..., True)
possess idle (21, ..., True)
possess move (18, ..., True)
move no ball (18, ..., True)
slide (5, 0, False)
victim tackled (2, 0, False)
```

Render-order note:

```text
when the ball is carried and the carrier faces upward, main.py draws the ball after the carrier so it stays visible in front of the 3D body
for other carried directions, the ball draws before the carrier
loose balls keep the normal draw fallback
```

Tackle-loop bug fix:

```text
Problem:
  seq 02 was selected for most of the stun duration, but sequence_frame() always wrapped with modulo.
  Result: tackled players could visually fall down twice while still stunned.

Fix:
  sequence_frame(..., loop=False) now clamps one-shot animations to their final frame.
  seq 02 and seq 07 are one-shot/clamped.
  seq 18 possession still loops.
  get-up timing uses seq 07's decoded duration; before that, seq 02 holds on its last frame once the fall finishes.
```

Performance note:

```text
After seq 21 idle and seq 18 movement were enabled for every player, Player.draw was deforming and rendering a VN mesh every frame.
That made the main game feel slower even though the player count had not changed.

Fix:
  Player.animated_image caches rendered animation surfaces by sequence id, decoded frame, and 32-way heading.
  Player.draw skips offscreen players before asking for animated meshes.
  class/skin/kickoff resets clear the per-player animation cache when needed.

If this still stutters on first viewing a sequence, the next optimization is to share pre-rendered animation caches per visual variant instead of per player.
```
