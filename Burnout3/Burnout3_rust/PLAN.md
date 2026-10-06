# Burnout 3: Takedown: ISO findings and asset formats

## Context
This file records what is on the Burnout 3: Takedown disc and the asset formats the Rust rewrite has to read. The
plan and status live in [../ROADMAP.md](../ROADMAP.md): first a byte-matching C/C++ decomp in
[../Burnout3_decomp](../Burnout3_decomp) (Stage A1), then this Rust rewrite from the finished decomp (Stage B1).

The source disc is `~/Desktop/ps2_games/Burnout 3 - Takedown (USA).iso`. Nothing from it is committed.

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

## Extracting the disc
`tools/iso_extract` reads ISO9660 on both layers, and on this single-layer disc it simply finds no layer 1.

```bash
cargo run --release -p iso_extract -- extract ~/Desktop/ps2_games/"Burnout 3 - Takedown (USA).iso" extracted
```

Expect 775 files and 2,865,038,650 bytes, and the hashes above.

## Asset formats (for the Stage B `formats` crate)
Each format gets a parser, a round-trip test and a short spec in `docs/formats/`:
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

Format knowledge is confirmed against the matched decomp's loaders as Stage A progresses.

## Legal note
Game data is read at runtime from the user's own disc, and nothing from the ISO is committed. See the publish rule in
[../ROADMAP.md](../ROADMAP.md).
