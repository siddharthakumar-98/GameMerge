# Burnout3_rust

**A Rust rewrite of Burnout 3: Takedown (PS2, NTSC-U).**

This rewrite is ported from the byte-matching C/C++ decomp in [../Burnout3_decomp](../Burnout3_decomp) once that
decomp is complete. It keeps the original behavior exactly and uses idiomatic Rust wherever that doesn't change
gameplay. It is part of [Burnout3](../README.md), and its gameplay core (takedowns, boost, crash scoring) becomes the
`burnout3-core` crate that GameMerge builds on.

> **Status:** waiting on the decomp (Stage A1). The only working piece is the ISO extractor. See
> [../ROADMAP.md](../ROADMAP.md) for the plan and [PLAN.md](PLAN.md) for disc findings.

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
- Your own dump of the game, placed in `~/Desktop/ps2_games/`

Build and check the toolchain:

```bash
cargo run
```

List the files on the disc:

```bash
cargo run --release -p iso_extract -- list ~/Desktop/ps2_games/"Burnout 3 - Takedown (USA).iso"
```

Extract everything into `extracted/` (gitignored, about 2.9 GB):

```bash
cargo run --release -p iso_extract -- extract ~/Desktop/ps2_games/"Burnout 3 - Takedown (USA).iso" extracted
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
| `PLAN.md` | ISO findings and asset formats |

Planned (Stage B1): `formats`, `ee` (EE float semantics), `game` (no_std gameplay core), `rw` (RenderWare runtime
replacement) and `engine` (wgpu, audio, input).

## Legal

This directory contains **no game executables, assets, BIOS or disc images**, and never will. You need your own
legally obtained copy of the game, which is read at runtime. The decompiled C/C++ lives in `../Burnout3_decomp`
under the publish rule in [../ROADMAP.md](../ROADMAP.md).

Burnout is a trademark of Electronic Arts. RenderWare is a trademark of Criterion Software. This is an unofficial
fan project with no affiliation to either.
