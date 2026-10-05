# Burnout3_rust

**A Rust rewrite of Burnout 3: Takedown (PS2, NTSC-U).**

This is a reference decomp: the original game's code and data formats are studied in Ghidra and PCSX2, written up as
specs, and then rebuilt in clean Rust from those specs. It is the Burnout half of
[GameMerge](../README.md), next to [MC3DER_rust](../MC3DER_rust), and its gameplay core (takedowns, boost, crash
scoring) is meant to be shared with GameMerge's `gm-core`.

> **Status:** early planning. The only working piece is the ISO extractor. See [PLAN.md](PLAN.md).

## Supported build

| Game | Region | Serial | ISO SHA-1 |
|---|---|---|---|
| Burnout 3: Takedown | NTSC-U | SLUS-21050 | `11a7f335a37d2f3f5c13b967f3072c84f8eded02` |

Other regions and revisions are not supported.

## What's on the disc

- **Engine:** Criterion's RenderWare 3.6 (PS2 `sky2` driver), with RenderWare Audio.
- **Code:** C/C++ built with Metrowerks CodeWarrior (`MW MIPS C Compiler 2.4.1.01`) for the EE (MIPS R5900).
  The ELF has no symbols, but it keeps the labels of Criterion's tuning menu, such as
  `Score/Boost/Near Miss` and `Takedown BP`.
- **Data:** tracks in `TRACKS/{US,EU,AS}`, cars in `PVEH/`, textures as `.TXD`, audio as `.RWS`/`.AWD`, video as
  `.M2V`, and tuning values in `DATA/VDB.XML` (binary, despite the name).

Full findings are in [PLAN.md](PLAN.md).

## Getting started

Requirements:
- Rust (stable is enough for now)
- Your own dump of the game, placed in `~/Desktop/ps2 games/`

Build and check the toolchain:

```bash
cargo run
```

List the files on the disc:

```bash
cargo run --release -p iso_extract -- list "../../ps2 games/Burnout 3 - Takedown (USA).iso"
```

Extract everything into `extracted/` (gitignored, about 2.9 GB):

```bash
cargo run --release -p iso_extract -- extract "../../ps2 games/Burnout 3 - Takedown (USA).iso" extracted
```

Use `--only <substring>` to extract part of the disc, for example `--only SLUS_210 --only DATA/`.

Run the tests:

```bash
cargo test --workspace
```

## Repository layout

| Path | What it is |
|---|---|
| `src/main.rs` | Placeholder binary for the rewrite |
| `tools/iso_extract` | ISO9660 lister and extractor (shared design with `MC3DER_rust`) |
| `PLAN.md` | ISO findings and the reverse-engineering and rewrite plan |

Planned: `formats` (asset parsers), `engine` (wgpu renderer, audio, input), `game` (gameplay logic) and
`docs/{formats,re}` (specs).

## Legal

This repo contains **no game code, assets, BIOS or disc images**, and never will. You need your own legally obtained
copy of the game. Only original Rust code and documentation are published here.

Burnout is a trademark of Electronic Arts. RenderWare is a trademark of Criterion Software. This is an unofficial
fan project with no affiliation to either.
