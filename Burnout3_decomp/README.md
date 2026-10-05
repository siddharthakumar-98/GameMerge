# Burnout3_decomp

**A matching decompilation of Burnout 3: Takedown (PS2, NTSC-U, SLUS-21050).**

The goal is C/C++ source that the original compiler (Metrowerks CodeWarrior for PS2, `MW MIPS C Compiler 2.4.1.01`)
builds into a byte-identical `SLUS_210.50`. The game is C++ on top of RenderWare 3.6 and Sony libsce. Game assets are
never in this repo. The rebuilt ELF runs in PCSX2 with your own disc providing them.

> **Status:** D1 done. The build reproduces the original SHA-1 entirely from generated assembly. No C yet. See
> [../ROADMAP.md](../ROADMAP.md) for milestones and [docs/layout.md](docs/layout.md) for the memory layout.

## Supported build

| Game | Region | Serial | ELF SHA-1 |
|---|---|---|---|
| Burnout 3: Takedown | NTSC-U | SLUS-21050 (`VER 1.00`) | `332be40d6081b8b5055a6ea01194ad6ff662a863` |

## Requirements

- Docker (the build runs in a linux/amd64 image, through Rosetta on Apple Silicon)
- Python 3, for the optional native venv with splat/spimdisasm
- Rust, to run the ISO extractor in `../Burnout3_rust`
- Your own dump of the game
- From D2 on: the CodeWarrior PS2 compiler, which you supply in `compilers/` (never committed)

## Building

1. Extract the ELF from your disc into `orig/`:

   ```bash
   cd ../Burnout3_rust && cargo run --release -p iso_extract -- extract ~/Desktop/ps2_games/"Burnout 3 - Takedown (USA).iso" ../Burnout3_decomp/orig --only SLUS_210
   ```

2. Build the image once:

   ```bash
   docker build --platform linux/amd64 -t b3-build -f docker/Dockerfile .
   ```

3. Configure. This checks your ELF's hash, splits it with splat and writes `build.ninja`:

   ```bash
   tools/dock python3 configure.py
   ```

4. Build:

   ```bash
   tools/dock ninja
   ```

The last step prints `build/SLUS_210.50: 332be40d… OK` when the output matches. Use `configure.py --no-split` to
regenerate `build.ninja` without re-running splat.

To boot the rebuilt ELF, load `build/SLUS_210.50` in PCSX2 ("Boot ELF") with your Burnout 3 ISO selected as the disc.

## Layout

| Path | What it is | Committed |
|---|---|---|
| `configure.py` | Writes `build.ninja` and `objdiff.json` | yes |
| `splat/b3.yaml` | Segment split of the load segment | yes |
| `config/symbol_addrs.txt` | Symbol names | yes |
| `config/linker_extra.ld` | Extra linker script | yes |
| `include/` | Asm macros and headers | yes |
| `src/` | Decompiled C/C++ (from D2) | yes |
| `tools/elf.py` | Extracts the load segment and rebuilds the exact ELF container | yes |
| `tools/dock` | Runs a command in the build container | yes |
| `docker/Dockerfile` | Build image: binutils-mips-linux-gnu, wibo, objdiff-cli, splat | yes |
| `docs/` | Layout and reverse-engineering notes | yes |
| `orig/` | Your ELF and its raw load segment | **no** |
| `asm/`, `assets/` | splat output, regenerated from your ELF | **no** |
| `build/` | Build output | **no** |
| `compilers/` | CodeWarrior binaries you supply | **no** |
| `tools/bin/` | Downloaded helper tools (objdiff GUI, m2c) | **no** |

## Tooling for decompiling

- **objdiff:** run `tools/bin/objdiff` (macOS GUI) in this directory. It reads `objdiff.json`.
- **Ghidra 12.1.4** with ghidra-emotionengine-reloaded, installed via Homebrew (`ghidraRun`).
- **m2c:** `tools/bin/m2c/m2c.py` for first-draft C from a function's asm.

## Legal

This directory publishes decompiled source, headers, symbol names and build configs only. It never includes the game
executable, disassembly, assets or compilers. You need your own legally obtained copy of the game. Burnout is a
trademark of Electronic Arts, and RenderWare is a trademark of Criterion Software. This is an unofficial fan project
with no affiliation to either.
