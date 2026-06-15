# Assets and Cache Research Track

## Current Launcher Metadata

The launcher source uses this remote config endpoint:

```text
https://static.alterorb.net/launcher/v3/config.json
```

Current Kickabout entry from that config:

```text
name: Kickabout League
internalName: kickabout
mainClass: Kickabout
gamepackHash: c6f693399f70424567ecce13e865674aba616ec0449739b54c1b2778e7ea10da
gamecrc: 613591652
server: https://mgg-server.alterorb.net
```

The local `analysis\kickabout\kickabout.jar` matches that SHA-256 exactly. The `classic-deob` bundled Kickabout jar does not.

## Launcher Cache Behavior

Launcher source:

```text
C:\Users\reidm\OneDrive\Desktop\codex\launcher
```

Important files:

- `Storage.java`: stores gamepacks under `%USERPROFILE%\.alterorb\gamepacks` and caches under `%USERPROFILE%\.alterorb\caches`.
- `Launcher.java`: downloads gamepacks from `https://static.alterorb.net/launcher/v3/jars/<internalName>.jar`.
- `Hook.java`: exposes `Hook.cacheRedirect(directory, file)` to patched clients.
- `AlterOrbAppletStub.java`: provides applet params and code/document base URLs.

The patched Kickabout client calls into the launcher hook:

```java
return Hook.cacheRedirect((String) string2, (String) string);
```

That call is visible in:

```text
C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout\decompiled\bj.java
```

The game client then opens Jagex cache-style files through that redirect:

```text
random.dat
main_file_cache.dat2
main_file_cache.idx255
main_file_cache.idx0
main_file_cache.idx1
...
```

Local status checked after running AlterOrb 3.1.1 and launching Kickabout:

- `C:\Users\reidm\.alterorb\gamepacks\kickabout.jar` exists and matches the launcher hash.
- `C:\Users\reidm\.alterorb\caches\Kickabout` exists.
- `main_file_cache.dat2` and `main_file_cache.idx0..18/255` exist, but all are still `0` bytes.
- The tutorial can be played even while those cache files remain empty.

Interpretation: the patched client creates the old Jagex cache file structure, but current tutorial play does not populate it on disk. Assets may be streamed through the JS5/update-server path and kept in memory, supplied by a different archive path, or bundled/packed in code rather than committed to the redirected cache files.

## Where The Assets Come From

The launcher is not the asset provider. It only downloads `kickabout.jar`, supplies applet params, and starts `Kickabout`.

The asset/data path is inside the Kickabout client:

```text
Launcher
  -> starts Kickabout applet
  -> codeBase/documentBase = https://mgg-server.alterorb.net
  -> applet params include gamecrc, gameport1, gameport2, servernum

Kickabout client
  -> ma reads getCodeBase().getHost(), gamecrc, gameport1, gameport2, servernum
  -> js.a(...) initializes the archive system
  -> gt.t = new tb()                  // JS5/update-server requester
  -> e.i = new eb(bu2)                // disk cache worker
  -> al.Ab = new n(gt.t, e.i)         // master archive manager
  -> uj.a(...) creates sj archives backed by wm
  -> sj.f.a("asset.png", "", id)      // named asset lookup
```

Working class roles:

- `ma`: applet startup; reads launcher-provided host/ports and `gamecrc`.
- `js`: initializes cache/archive globals.
- `tb extends bi`: network archive requester. It writes JS5-style request keys to a `bh` socket and fills `ui` byte buffers from the response stream.
- `n`: master archive manager. It requests archive `255/255`, parses the master table, and constructs per-index `wm` archives.
- `wm extends ow`: concrete archive provider used by `sj`. It first checks disk-backed cache stores, validates CRC/version, then requests missing groups through `tb`.
- `sj`: named/grouped archive API. Calls like `sj.f.a("background.png", "", 66)` resolve named assets from an archive.
- `qh`: old Jagex `main_file_cache.dat2` / `idx*` reader-writer wrapper.
- `eb`: asynchronous disk cache read/write worker.

Network setup:

- `ma` sets `this.z = getCodeBase().getHost()`.
- With the launcher, that host comes from config server `https://mgg-server.alterorb.net`.
- `ma` reads applet params `gameport1` and `gameport2`; AlterOrb's applet stub supplies both as `43594`.
- `fw.h(...)` opens a socket with `hf.e.a(true, tk.yb, nb.b)`, then wraps it in `bh`, handshakes, and calls `gt.t.a(je.e, 20, ac.f)`.
- After that handoff, `tb` owns the JS5/archive socket and serves archive requests for `n/wm/sj`.

So the practical answer is:

```text
Original assets are coming from the Kickabout client's JS5/archive network stream,
using host mgg-server.alterorb.net and the launcher-provided game port,
then being decoded into in-memory sj/wm archive objects.
```

They are not currently being saved as normal files, and the redirected disk cache remains empty.

## What the Jar Contains

The launcher-current jar:

```text
C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout\kickabout.jar
```

contains class files and signature metadata. It does not contain loose PNG/JPG/audio/data assets as ordinary jar resources.

Interpretation: original art/audio/model/level data is expected to live in cache/archive files fetched or generated during applet operation, not as simple jar entries.

## Named Asset Leads From Decompiled Client

Directly named graphics loaded through the archive provider include:

- `background_guy.png`
- `background.png`
- `splash.jpg`
- `botbar.png`
- `bank_top.png`
- `bank_mid.png`
- `bank_bot.png`
- `button_lrg.png`
- `button_sml.png`
- `cone_1.png`
- `cone_2.png`
- `button_left.png`
- `button_middle.png`
- `button_right.png`
- `stopwatch.png`
- `thin_button_endl.png`
- `thin_button_mid.png`
- `thin_button_endr.png`
- `small_button_L.png`
- `small_button_mid.png`
- `small_button_R.png`
- `top_bar_Seg.png`
- `top.png`
- `asphalt_corner.png`
- `asphalt_v.png`
- `asphalt_h.png`
- `arrow_on.png`
- `arrow_off.png`
- `achievements_large.png`
- `ka_logo.png`

Audio-related names found:

- `headers.packvorbis`
- `jagex logo2.packvorbis`

Loader categories found:

- graphics
- models
- sound effects
- music
- levels
- languages
- animations
- toolkit
- fonts
- instruments
- textures

Kickabout-specific loading labels:

- `loading_park`
- `loading_beach`
- `loading_street`
- `loading_pitch`
- `loading_hud`
- `loading_lobby`
- `loading_menu`

## Current Prototype Assets

The prototype uses local Kenney Sports Pack assets:

```text
C:\Users\reidm\OneDrive\Desktop\codex\kenney-assets\packs\kenney_sports-pack\PNG
```

Current Python asset use:

- `Equipment/ball_soccer1.png`
- `Blue/characterBlue (1).png`
- `Blue/characterBlue (11).png`
- `Red/characterRed (1).png`
- `Red/characterRed (11).png`
- `White/characterWhite (1).png`
- `White/characterWhite (11).png`
- `Special/characterSpecial (1).png`
- `Special/characterSpecial (11).png`

Kenney assets remain the safest shippable asset path because the local Kenney mirror notes CC0 licensing. The original Kickabout assets should be treated as reference/research unless separate redistribution rights are established.

## Best Next Asset Work

Most useful next steps:

1. Instrument or patch `tb`/`wm` in a copied jar to dump completed `ui`/archive byte buffers before they are decoded.
2. Trace `sj.f` initialization and the `sj.f.a("asset.png", "", id)` calls to map named graphics to archive indexes.
3. Check whether tutorial-only assets are generated procedurally or packed into classes rather than loaded from the cache files.
4. Build a read-only cache inventory script only if `main_file_cache.dat2` becomes nonzero in a later run.
5. Keep generated/Kenney replacements in the prototype, using original asset names only as visual target references.

Until nonzero cache files exist locally, asset research from `/launcher` is limited to current gamepack metadata, cache paths, applet launch params, and the patched `Hook.cacheRedirect` behavior.
