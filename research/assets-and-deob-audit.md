# Assets and Deobfuscator Audit

## Deobfuscator Legitimacy

Local project reviewed: `C:\Users\reidm\OneDrive\Desktop\codex\classic-deob`.

Assessment: the deobfuscator looks legitimate as a local bytecode cleanup tool for FunOrb and RuneScape Classic gamepack jars. The repository remote is `https://github.com/RuneStar/classic-deob.git`, the README says it targets final FunOrb/RSC revisions, and the code is a Kotlin/ASM transformer pipeline.

What it does:

- Walks `input/**/gamepack.jar`.
- Reads `.class` files from each jar.
- Applies bytecode transforms such as string decryption, field resolution, opaque predicate removal, counter removal, renaming, and shift masking.
- Writes transformed class files to `output/<same relative input path>/gamepack.jar`.

Safety notes:

- I did not find process execution, shell commands, HTTP client logic, socket creation, credential access, or broad filesystem scanning in the deobfuscator source.
- The only destructive operation in the main pipeline is `dir.toFile().deleteRecursively()` on the computed output directory before rewriting a deobfuscated jar.
- Optional CFR/Fernflower/Procyon decompiler calls exist in `Main.kt`, but the calls that unpack/decompile output are commented out.
- Maven dependencies are normal for this kind of tool: Kotlin stdlib, ASM, zt-zip, CFR, plus local Fernflower/Procyon jars in `libs/`.

Legal/provenance note: the tool itself is ISC licensed, but the bundled `input/**/gamepack.jar` files are game client artifacts. Treat extracted or decompiled game assets/code as research/reference material unless you have separate rights to redistribute them.

## Kickabout Jar Inventory

Local jar reviewed:

```text
C:\Users\reidm\OneDrive\Desktop\codex\classic-deob\input\funorb\kickabout\gamepack.jar
```

The jar is about 2.0 MB and contains Java class files plus signature metadata:

- `META-INF/MANIFEST.MF`
- `META-INF/JAGEXLTD.SF`
- `META-INF/JAGEXLTD.RSA`
- hundreds of obfuscated `.class` files
- `Kickabout.class`

I did not find loose asset files in the jar itself. A .NET zip listing filtered for non-class, non-`META-INF` entries returned no art/audio/data resources.

Interpretation: this jar is mostly the applet/client code. Kickabout's real art, model, level, sound, music, language, and animation data appears to be loaded from the Jagex cache/archive system rather than embedded as ordinary jar resources.

## Decompiled Asset Clues

The existing decompiled tree at:

```text
C:\Users\reidm\OneDrive\Desktop\codex\analysis\kickabout\decompiled
```

contains useful resource names.

Directly named graphics loaded through `sj.f.a(...)` in `eh.java`:

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

Other named file resources found in decompiled source:

- `button.gif`
- `final_frame.jpg`
- `headers.packvorbis`
- `jagex logo2.packvorbis`
- local cache/preferences names such as `random.dat`, `main_file_cache.dat2`, `main_file_cache.idx*`, and `jagex_*_preferences*.dat`

The loader text also names the archive categories:

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

Kickabout-specific loading labels include:

- `loading_park`
- `loading_beach`
- `loading_street`
- `loading_pitch`
- `loading_hud`
- `loading_lobby`
- `loading_menu`

These labels line up with the known surface ids in `physics.md`: park, beach, and street.

## Current Prototype Asset Use

The Python prototype at `C:\Users\reidm\OneDrive\Desktop\codex\kickabout-2.5d\main.py` uses the local Kenney Sports Pack:

```text
C:\Users\reidm\OneDrive\Desktop\codex\kenney-assets\packs\kenney_sports-pack\PNG
```

Current loaded assets:

- `Equipment/ball_soccer1.png`
- `Blue/characterBlue (1).png`
- `Blue/characterBlue (11).png`
- `Red/characterRed (1).png`
- `Red/characterRed (11).png`
- `White/characterWhite (1).png`
- `White/characterWhite (11).png`
- `Special/characterSpecial (1).png`
- `Special/characterSpecial (11).png`

The prototype currently draws the pitch and UI directly with Pygame shapes rather than using the original Kickabout PNGs.

## Practical Asset Direction

For implementation work, keep using Kenney/CC0 assets for anything shippable. The original Kickabout names are still useful as reference targets:

- `asphalt_*` suggests a street pitch visual set.
- `cone_1.png` and `cone_2.png` suggest tutorial/practice props.
- `ka_logo.png`, `top.png`, `botbar.png`, and `button_*` map to the original shell/menu UI.
- The archive categories confirm that original pitch, character, model, animation, sound, and music assets probably require cache/archive extraction rather than jar extraction.

Next useful research step: trace the `sj` archive provider and `ib.a(...)`/`ni.a(...)` string-data loaders to identify cache group names or indexes for graphics, models, and localized text.
