# Class Map

## `tj` - AgentBall

`tj.toString()` prints:

```text
AgentBall p=[t,p,v] v=[q,h,n] posessor=m/s uncatchable=r high_friction=A model_id=l
```

Working field names:

- `t`: ball X position, 16.16 fixed point.
- `p`: ball Y position, 16.16 fixed point.
- `v`: ball Z height, 16.16 fixed point.
- `q`: ball X velocity.
- `h`: ball Y velocity.
- `n`: ball Z velocity.
- `m`: possessing team index, `-1` when free.
- `s`: possessing footballer slot.
- `r`: uncatchable timer.
- `A`: high-friction timer.
- `l`: ball model/skin id.
- `i`, `j`, `o`: recent contact/scoring bookkeeping.

Important methods:

- `a(int x, int y, byte, int z)`: reset ball position and zero velocity.
- `a(byte, int surface, la[] bounds)`: free-ball physics tick.
- `g(int)`: whether the free ball can be caught/picked up.
- `e(int)`: horizontal speed squared using `vx >> 8`, `vy >> 8`.
- `a(ml, byte)` and `c(ml, int)`: full and delta network decode.

## `nl` - AgentFootballer

`nl.toString()` prints:

```text
AgentFootballer[Type]
  loc=[M,w,v,K,C]
  spd=[A,g,q,D]
  act=[L, action, ai_wait=I]
  direc=[G,h,j,n]
  kick=[z,x,P,O]
  tackle=[k,m,s,r,B]
```

Working field names:

- `M`: footballer X position, 16.16 fixed point.
- `w`: footballer Y position, 16.16 fixed point.
- `v`: footballer Z height.
- `K`: footballer Z velocity.
- `C`: cooldown/timer.
- `A`: base movement speed derived from class + stat.
- `g`: diagonal/sprint adjusted movement speed.
- `q`: action/tackle/kick speed or power baseline.
- `D`: diagonal/action adjusted speed.
- `u`: action state.
- `L`: action timer/duration.
- `G`: facing/input direction bitmask.
- `h`: kick direction.
- `j`, `n`: normalized movement direction components.
- `k`, `m`: tackle velocity components.
- `N`: `up` stats object.
- `J`: player class id.
- `y`: membership flag.
- `l`: mega mode flag.

Action states from `nl.c(true)`:

- `0`: `Idle`
- `1`: `ACTION_CHARGE_KICK`
- `2`: `ACTION_KICK`
- `3`: `ACTION_TACKLE`
- `4`: `ACTION_DASH`
- `5`: `ACTION_DIVE`
- `6`: `ACTION_DIVE_STAND`
- `7`: `ACTION_FALL_TACKLED`
- `8`: `ACTION_PAUSE_TACKLED`
- `9`: `ACTION_STAND_TACKLED`
- `10`: `ACTION_TACKLE_STAND`
- `11`: `ACTION_RUN_HOME`
- `12`: `ACTION_TACKLE_SUCCESS`
- `13`: `ACTION_HEADER`
- `14`: `ACTION_KEEPER_SHUFFLE`

Class ids from `nl.c(9)`:

- `0`: Tank
- `1`: Hotshot (`Htshot` in decompiled string)
- `2`: Elite
- `3`: Ranger
- `4`: Keeper

## `up` - Player Stats

`up.toString()` prints readable player stats:

- type/class
- display name
- `POW`
- `TCK`
- `SPD`
- `EXP`
- trinket slots
- appearance

It is used by `nl` to derive runtime speeds and abilities.

Working field names:

- `q`: class id.
- `n`: `POW`.
- `o`: `TCK`.
- `g`: `SPD`.
- `r`: `EXP`.
- `h[]`: equipped trinket ids.
- `e`, `l`, `j`: name/appearance metadata.
- `c`: dirty/changed flag.

Physics-facing methods:

- `d(member, byte)`: effective speed stat, `SPD + speedTrinketBonus`.
- `a(member, int)`: effective tackle stat, `TCK + tackleTrinketBonus`.
- `d(member, int)`: effective power stat, `POW + powerTrinketBonus`, with one class/trinket penalty case.
- `c(member, byte)`: true for Hotshot class or Hotshot Clone trinket.
- `c(member, int)`: true for Ranger class or Ranger Clone trinket.
- `a(byte, member)`: true for Tank class or Tank Clone trinket.
- `b(member, int)`: true when a trinket grants the `SLALOM`-style capability used by dash turning.

Known trinket ids/names from `rv.b`:

- `54`: `SAFE TACKLER`
- `55`: `IMMUNITY`
- `56`: `SHIN PADS`
- `57`: `STUDS UP`
- `58`: `KNOCK-OUT`
- `59`: `TANK CLONE`
- `60`: `HOTSHOT CLONE`
- `61`: `RANGER CLONE`
- `62`: `SLALOM`
- `63..72`: cheat/ball modifiers such as `MUSHROOM`, `MOONWALK`, `ATOMBALL`, `TORQUING`, `MOONBALL`, `ASTEROID`, `PUMPKINS`
- `73`: `COSTUME: HORROR`

## `nu` - Match State

Important fields:

- `V`: `tj`, the ball.
- `P[2][5]`: footballer grid, two teams, five slots each. Slot `0` is often keeper.
- `B`: collision/valid-area boxes used by the ball.
- `x`: collision/valid-area boxes used by footballers.
- `C`: formation state.
- `X`: goal/score state.
- `R`: connected/player controller state.
- `u`: match phase.

Important methods:

- `b(int)`: big per-tick match simulation/update method. CFR could not structure it cleanly, but most physics interactions are here.
- `a(byte, ki)`: input handling for kick/tackle actions.
- `b(byte, ki)`: input handling for selection/dash-like actions.
- `a(int power, boolean high, boolean special, int dx, byte, int dy)`: free ball kick/pass/shot impulse.
- `b(int receiverSlot, byte)`: pass/lob toward a teammate.

## `ua` - AgentGoalState

`ua.toString()` prints:

```text
AgentGoalState score=[j0,j1] goal_count=m goal_scorer=n
```

Working field names:

- `j[2]`: score by side.
- `m`: goal timer/countdown. `0` means no active goal sequence.
- `n`: scoring side, `0` or `1`.

Important methods:

- `a(tj ball, int)`: detects whether a free ball crossed a goal line.
- `a(ml, byte)`: network decode.
- `a(byte, mo)`: copy from another goal state.

## `ki` - Input Command

`ki` is the command object sent through the match/network input path.

Constructor:

```java
ki(int type, int controllerId, int value, byte xByte, byte yByte)
```

Working field names:

- `r`: command type.
- `u`: controller/player id.
- `v`: action/value.
- `o`: click/vector X byte.
- `p`: click/vector Y byte.
- `s`, `t`: lineup/team payload for some menu commands.

Command types from `toString()`:

- `r == 0`: `Keyheld`, value is held direction/control data.
- `r == 1`: `Keypress`.
- `r == 2`: `Mouse`, with `Click(o,p)`.
- `r == 3`: `formation`.
- `r == 4`: `Team`.
- `r == 5`: `LineUp`.
- `r == 6`: `meta`.
- `r == 7`: `Cheat`.

Keypress values:

- `0`: `DASH`
- `1`: `SELECT0`
- `2`: `SELECT1`
- `3`: `SELECT2`
- `4`: `SELECT3`
- `5`: `SELECT4`
- `6`: `CHARGE_KICK_LEFT`
- `7`: `CHARGE_KICK_RIGHT`

Factory methods:

- `ha.b(1, controllerId, action)`: keypress.
- `mg.a(heldValue, false, controllerId)`: held input.
- `hw.a(controllerId, action, ..., yByte, xByte)`: mouse/click-vector command.
- `mf.a(action, controllerId, byte)`: formation command.
- `mg.a(controllerId, byte, action)`: team-selection command.
- `wd.a(...)`: lineup command.
- `fu.a(controllerId, byte, action)`: cheat command.

## `ch` - Logged Shot / Goal Attempt

`ch.toString()` prints:

```text
LoggedGoal{ p=(x,y)/side/slot/lastTouch b=(vx,vy) kick/power/high g=(keeperX,keeperY)/keeperState time=t }
```

or variants for `cross` and `header`.

Working field names:

- `t`: attempt type: `1` kick, `2` cross, `3` header.
- `k`: shooter/team side.
- `g`: shooter slot.
- `q`, `r`: shooter position at attempt time.
- `h`, `j`: kick/contact vector, clamped into byte range by repeated halving.
- `i`: kick power/charge for normal kicks.
- `n`: high/alternate kick flag for normal kicks.
- `m`, `p`: opposing keeper position.
- `e`: opposing keeper state counter.
- `l`: match time.
- `s`: last-touch/player id from ball bookkeeping.

This object is used for goal/shot logging and probably post-goal presentation.

## `jc` - Logged Player Stats

`jc.toString()` prints:

```text
LoggedPlayer{... tackles=m.c.n.a kicks=i.f.q crosses=j headers=h tot_goals=s}
```

Working stat names:

- `m`, `c`, `n`, `a`: tackle-related counters.
- `i`, `f`, `q`: kick counters. The normal kick branch increments one based on high flag and charge threshold.
- `j`: crosses.
- `h`: headers.
- `s`: total goals.

## `lt` - Movement Integrator

`lt.a(vx, vy, la[] boxes, ..., z, y, x, vz)` returns an array:

```text
[x, y, z, vx, vy, vz]
```

It tests whether the object is currently inside a valid box. If so, it attempts:

1. Move X by `vx`; if invalid, revert X and flip `vx`.
2. Move Y by `vy`; if invalid, revert Y and flip `vy`.
3. Move Z by `vz`; if invalid, revert Z and flip `vz`.

This is the core wall/floor bounce helper.

## `la` - Collision/Valid-Area Box

Constructor stores bounds as fixed point:

```java
la(int minX, int minY, int maxX, int maxY, int minZ, int maxZ)
```

All values are shifted left by 16. `a(x, y, ..., z)` returns true when the point is inside the box and z range.
