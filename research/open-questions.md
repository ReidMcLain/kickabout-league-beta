# Open Questions / Next Steps

## Need Better Names

The current map is enough to reason about the engine, but not enough to comfortably reimplement it one-to-one. The next useful step is a local renamed copy of key classes:

- `tj` -> `AgentBall`
- `nl` -> `AgentFootballer`
- `nu` -> `MatchState`
- `lt` -> `PhysicsIntegrator`
- `la` -> `CollisionBox`
- `up` -> `PlayerStats`

Do this manually in notes or with a copied source tree, not by editing the original decompiled output.

## Still To Trace

- `gt` and `it`: player/controller metadata.
- `N.a(...)`: event/stat logger invoked on headers/kicks/tackles/goals.
- Exact user-facing distinction between cross, lob, pass, and shot in event logging.

## Physics Questions

- Remaining uses of effective `POW`; core `SPD` and `TCK` uses in movement/tackle/contact are mapped.
- Whether multiplayer server is authoritative for all collision results or only validates snapshots.
- How `high_friction` is triggered besides special low shots.
- Exact scoring ownership rules around deflections, own goals, and last-touch bookkeeping.
- Whether `ACTION_HEADER` also covers volleys, or whether volley is a ground/air contact variant without a separate action name.
- Exact physics impact of each special trinket/cheat-ball modifier beyond the class clones and stat bonuses.

## Updated / Partially Answered

- VN player test direction, movement-state, recolor, and keeper pose findings are captured in `player-movement-vn-and-keeper-animation.md`.

## Suggested Next Work Session

1. Rename a copied subset of `tj`, `nl`, `nu`, `lt`, `la`, `up`.
2. Build a call graph around:
   - `nu.a(byte, ki)`
   - `nu.b(byte, ki)`
   - `nu.b(int)`
   - `tj.a(byte, int, la[])`
   - `nl.a(int, la[], boolean, boolean)`
3. Decode the remaining special trinket and cheat-ball modifier branches.
4. Write a small standalone Python simulation of:
   - free ball friction/gravity/bounce
   - player movement
   - kick impulse
   - pickup/collision radius
   - header intercept prediction
   - goal detection
5. Compare those constants against the current `kickabout-2.5d/main.py` prototype.
