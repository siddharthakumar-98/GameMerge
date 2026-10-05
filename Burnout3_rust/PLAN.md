# Burnout 3: Takedown: ISO findings and reference-decompilation plan

## Context
The goal is a Rust rewrite of Burnout 3: Takedown in `GameMerge/Burnout3_rust`. The source is
`~/Desktop/ps2 games/Burnout 3 - Takedown (USA).iso`, in the same folder as the Midnight Club 3 ISO. Like
`MC3DER_rust`, this is a **reference decomp**: understand the original code and data formats well enough to write
specs, then build the Rust version clean from those specs. It is not a byte-matching decomp.

This repo also feeds GameMerge. The Burnout systems that GameMerge needs (takedowns, boost, Impact Time, aftertouch,
Road Rage, Crash mode) are the same ones this rewrite has to rebuild, so they come first. See [../ROADMAP.md](../ROADMAP.md).

## What the ISO contains (verified read-only)
- **Disc:** SLUS-210.50 (NTSC-U), `VER = 1.00`, `VMODE = NTSC`. It is a **single-layer DVD-5** (2.87 GB), so unlike
  MC3 there is no layer 1. `tools/iso_extract` still works and lists 775 files, 2,865,038,650 bytes.
- **Hashes (SHA-1):**
  - ISO: `11a7f335a37d2f3f5c13b967f3072c84f8eded02`
  - `SLUS_210.50`: `332be40d6081b8b5055a6ea01194ad6ff662a863`
- **Top-level folders:**

  | Folder | Files | Size | What it holds |
  |---|---|---|---|
  | `TRACKS/` | 357 | 1.75 GB | Track data in `US/`, `EU/` and `AS/` (Asia). Each track is a code like `C1`, `M1` or `P1` with `_V1`/`_V2` variants, and holds `STATIC.DAT`, `STREAMED.DAT`, `ENVIRO.DAT`, `GAMEDATA.BGD`, `SOUND.AWD` and DJ/crash `.RWS` audio. Also the EA Trax music (`_EATRAX0/1.RWS`, about 155 MB each), `CRASH1..20.RWS`, and per-track loading videos (`*.M2V`). |
  | `OVID/` | 62 | 719 MB | Video: intro titles, credits, tutorials (`TRC_ENG`, `TRD_ENG`), 20 signature takedown clips (`SIGTKD01..20`), Crash headline clips (`CRSHHD01..10`), unlock clips and `MOVIE.RWS`. |
  | `NFSUNDER/` | 9 | 304 MB | A separate **Need for Speed Underground demo** (its own ELF and `ZZDATA*.BIN`). Out of scope. |
  | `PVEH/` | 242 | 53 MB | Player vehicles in classes `COMP`, `CUPE`, `HEVY`, `HSPC`, `MSCL`, `SPRT`, `SUPR`, `TSPC`. Each car has `CARn.BGV` (model) plus `CARn.HWD`/`CARn.LWD` (likely high/low engine sound banks). `TSPC` uses `.BTV`. `VLIST.BIN` is the vehicle list. |
  | `DATA/` | 13 | 18 MB | `VDB.XML` (despite the name, a **binary** tuning database), `FRONTEND.TXD`/`GLOBAL.TXD` textures, `GLOBALUS.BIN`/`HEADUS.BIN` (likely US strings; both share the same header), `STAGEHED.BIN`, `LOADSCRN.BIN`, `PRGDATA.BIN`, `INTRO.KFS`/`AFTER.KFS` (keyframe sequences). |
  | `SOUND/` | 22 | 5.5 MB | Mode and crash sound banks (`CRASH`, `CRASHMOD`, `ROADRAGE`, `ELIM`, `SINGLE`, `FE`, `IDENT0..9`). |
  | `IOP/`, `NETGUI/`, `CNF/` | | 11 MB | IOP modules: sound (`LIBSD`), memory card, pad, USB, Logitech headset (`LGAUD`), EA online (`DRTYSCKF` DirtySock, DNAS), and Sony's network setup GUI. |

- **Main ELF (`SLUS_210.50`):**
  - MIPS R5900 (EE), one merged load segment at `0x100000`. File size `0x3E2680` (about 4 MB), memory size up to `0x1ECEA00`.
  - **Stripped:** `.symtab` and `.strtab` exist but are empty. About 3,700 strings.
  - **Compiler:** `.comment` says `MW MIPS C Compiler (2.4.1.01)`. That is **Metrowerks CodeWarrior** for PS2, not GCC, so
    C++ name mangling and calling details follow CodeWarrior's rules.
- **Engine: RenderWare 3.6** by Criterion. The ELF has `//RenderWare/RW36Active/rwsdk/...` source paths, including the
  PS2 `sky2` driver (`basky.c`, `skyinst.c`, `texcache.c`). This helps a lot: RenderWare's binary stream format,
  plugin IDs and texture dictionaries are documented by the GTA/RenderWare modding community.
- **Audio: RenderWare Audio.** `.RWS`, `.AWD`, `.HWD` and `.LWD` all start with RenderWare chunk headers (`0x0809`,
  `0x080D`). Voice chat uses Speex.
- **A tuning-variable tree is compiled in.** The ELF keeps the labels of Criterion's debug tuning menu, grouped by path.
  This gives ready-made names and units for the Phase 3 specs. Examples:
  - `Score/Boost/{Air, Oncoming, Drift, Near Miss, Takedowns, Crash Escape, Aggressive, Props, Lap, Crashing}`,
    e.g. `Boost value per Near Miss (Boost units)` and `Ratio of Boost Lost After Crash`.
  - `Takedown BP`, `Revenge Takedown Bonus BP`, `Aftertouch Takedown BP`, `Road Rage Takedown BP`,
    `Time window for getting a double takedown(Seconds)`, `Minimum Collide Time to enable Takedown - No Slam (Seconds)`.
  - `Physics/{Vehicle, Steering, Drift, Suspension/Front, Suspension/Rear, Transmission/Engine, Transmission/Gear Ratios, Transmission/Boost Kick}`.
  - `AI/{Aggressive Driving/Slam, Arbitrator, Avoidance, Car, Driver, Target}`, `Camera/{Bumper, Follow, Look Back}`,
    `Crash/HandyCam`, `InGame/Effect/{Slam, Shunt, Shunted, Shake, Burnout}`.
  - Crash mode pickups: `pickup_boost`, `pickup_multiplierx2`, `pickup_multiplierx4`, `pickup_multiplier_skull`,
    `pickup_score01..03`, `pickup_stealer`, `pickup_gamebreaker` (the internal name for Crashbreaker).
  - The values themselves very likely live in `DATA/VDB.XML`, which is a table of hashed keys and floats.
- **Languages:**
  - **C/C++** compiled with CodeWarrior, on top of RenderWare 3.6 (C).
  - **MIPS R5900 machine code** for the game, most likely with **VU1 microcode** in RenderWare's `sky2` pipelines (the merged segment hides section boundaries).
  - **IOP modules** (`.irx`, MIPS R3000).
  - The US disc ships English text (`GLOBALUS.BIN`, `HEADUS.BIN`).

## Plan

### Phase 0: Toolchain (on the Mac)
- Ghidra 11.x plus the **ghidra-emotionengine-reloaded** extension (R5900, VU and IOP support).
- PCSX2 2.x (macOS build) for runtime tracing, with its debugger, memory search and breakpoints.
- Python 3 for one-off scripts. Durable tools go into Rust (see Phase 2).
- Keep the ISO and extracted files **outside git**. `.gitignore` covers `/extracted`, `*.iso`, `*.DAT` and `*.BIN`.

### Phase 1: Extraction tool (Rust, in repo)
- `tools/iso_extract` is copied from `MC3DER_rust`. It reads ISO9660 on both layers, and on this single-layer disc it
  simply finds no layer 1.
- Run: `cargo run --release -p iso_extract -- extract "../../ps2 games/Burnout 3 - Takedown (USA).iso" extracted`.
- Verify: 775 files and 2,865,038,650 bytes, matching the listing above, and the hashes above match.

### Phase 2: Asset formats (in parallel with Phase 3)
Create a `formats` crate. Each format gets a parser, a round-trip test and a short spec in `docs/formats/`:
1. **RenderWare binary stream:** the 12-byte chunk header (type, size, library version) and the nested chunk tree.
   Everything else builds on this.
2. **Textures (`.TXD`):** RenderWare PS2 texture dictionaries, with GS pixel formats, palettes and swizzling. Export to PNG.
3. **Vehicles (`.BGV`, `.BTV`, `VLIST.BIN`):** Criterion's vehicle model format, likely RenderWare geometry plus a
   Burnout header with damage and deformation data.
4. **Tracks (`STATIC.DAT`, `STREAMED.DAT`, `ENVIRO.DAT`, `GAMEDATA.BGD`, `STAGEHED.BIN`):** world geometry split into
   always-loaded and streamed sections, plus environment/lighting and gameplay data (racing lines, traffic, Crash
   junction setups, spawn points).
5. **Tuning (`VDB.XML`):** recover the key hash from the ELF, then map every hashed key to its label in the debug menu
   tree. Dump it as readable TOML.
6. **Strings (`GLOBALUS.BIN`, `HEADUS.BIN`):** most likely the US text table and its index.
7. **Audio (`.RWS`, `.AWD`, `.HWD`, `.LWD`):** RenderWare Audio wave dictionaries and streams (PS2 ADPCM).
   **Video (`.M2V`):** plain MPEG-2 elementary streams. Decode them with ffmpeg or an existing crate, so no reverse
   engineering is needed.
8. **Keyframes (`.KFS`):** camera or replay keyframe sequences (the ELF references `Data\Replay.kfs`).

### Phase 3: Code reference decomp (Ghidra)
1. Load `SLUS_210.50` with the EE plugin. Apply PS2SDK/libsce signatures so Sony library functions (sce*, libgraph,
   libpad, libsd) are named automatically.
2. **Name RenderWare first.** RenderWare 3.6 is public-ish middleware with a known API (`RwEngineInit`,
   `RpWorldCreate`, `RwTexDictionaryStreamRead`...). Match it with string anchors from the `$Id:` paths, error strings
   and plugin IDs. That leaves the Burnout game code as the unnamed remainder.
3. Anchor the game code with the tuning-menu labels. The code that registers each label most likely
   sits next to the variable it edits, so its cross-references should lead to the boost, scoring, takedown, physics, AI and camera code.
4. Map the subsystems in this order:
   - **File I/O and track/vehicle loading**
   - **Main loop and game state machine**
   - **Vehicle physics and tuning** (the core of the feel)
   - **Takedowns, boost and scoring** (`Score/*`, `AI/Aggressive Driving/*`)
   - **Crash, Impact Time, aftertouch and crash cameras** (`Crash/HandyCam`, `InGame/Effect/*`)
   - **Game modes:** Race, Road Rage, Crash (pickups, multipliers, Crashbreaker), Eliminator, Burning Lap, Face-Off
   - AI/traffic, camera, renderer and audio
5. Write findings into `docs/re/<subsystem>.md`: struct layouts, constants and pseudo-code. Rust is written from these
   docs, not from pasted decompiler output.
6. Check against PCSX2: breakpoints and memory watches confirm constants and struct fields. Cross-check known
   CodeBreaker/pnach addresses and Reburn community notes.

### Phase 4: Rust rewrite scaffold
Convert the root package into crates:
- `formats` (Phase 2)
- `engine` (renderer via `wgpu`, audio, input)
- `game` (logic ported from the RE docs). Its `no_std` core (takedowns, boost, crash scoring) is designed to be shared
  with GameMerge's `gm-core`.
- `tools/*`

Milestones:
1. Load a track from the original assets and fly a camera through it.
2. A drivable car with the original tuning values from `VDB.XML`.
3. Boost, near misses and takedowns against AI racers and traffic.
4. Crash mode at one junction, with pickups, multipliers and Crashbreaker.
5. UI, Road Rage and the World Tour career.

## Legal note
Ship only original Rust code. The game data is read at runtime from the user's own disc, and nothing from the ISO is
committed.

## Verification
- `cargo test` in the workspace: format parsers round-trip on the extracted files, and extraction counts and sizes
  match the ISO listing.
- Spot-check: extracted textures render to PNG correctly, `.M2V` files play, and `VDB.XML` dumps to readable values
  with labels from the ELF.
- Physics and scoring: the Rust car's acceleration, top speed and boost earned per near miss match PCSX2 measurements
  within tolerance.
