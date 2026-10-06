# Burnout3_decomp

**A matching decompilation of Burnout 3: Takedown (PS2, NTSC-U, SLUS-21050).**

The goal is C/C++ source that the original compiler (Metrowerks CodeWarrior for PS2, `MW MIPS C Compiler 2.4.1.01`)
builds into a byte-identical `SLUS_210.50`. The game is C++ on top of RenderWare 3.6, Sony libsce, EA DirtySock and Logitech's device libraries. Game assets are
never in this repo. The rebuilt ELF runs in PCSX2 with your own disc providing them.

> **Status:** D2 done, D3 in progress. The compiler is identified (CodeWarrior 3.0.3,
> `-O4 -str readonly -Cpp_exceptions off`), and 10 functions in 8 C/C++ files compile to the original bytes and are
> linked in place of their assembly. The binary is mapped into game, RenderWare, libsce, runtime, DirtySock and
> Logitech ranges, with progress per category in [PROGRESS.md](PROGRESS.md). The full build still reproduces the
> original SHA-1, and the rebuilt ELF boots and runs in PCSX2. See [../ROADMAP.md](../ROADMAP.md) for milestones and
> [docs/layout.md](docs/layout.md) for the memory layout.

## Supported build

| Game | Region | Serial | ELF SHA-1 |
|---|---|---|---|
| Burnout 3: Takedown | NTSC-U | SLUS-21050 (`VER 1.00`) | `332be40d6081b8b5055a6ea01194ad6ff662a863` |

## Requirements

- Docker (the build runs in a linux/amd64 image, through Rosetta on Apple Silicon)
- Python 3, for the optional native venv with splat/spimdisasm
- Rust, to run the ISO extractor in `../Burnout3_rust`
- Your own dump of the game
- The CodeWarrior PS2 compiler, **Version 3.0.3**, which you supply in `compilers/3.0.3-020716/` (never committed). It
  is the decomp.me build `mwcps2-3.0.3-020716`. [docs/compiler.md](docs/compiler.md) explains why this build was
  chosen.

## Building

1. Extract the ELF from your disc into `orig/`:

   ```bash
   cd ../Burnout3_rust && cargo run --release -p iso_extract -- extract ~/Desktop/ps2_games/"Burnout 3 - Takedown (USA).iso" ../Burnout3_decomp/orig --only SLUS_210
   ```

2. Build the image once:

   ```bash
   docker build --platform linux/amd64 -t b3-build -f docker/Dockerfile .
   ```

3. Configure. This checks your ELF's hash, splits it with splat into `assembly/asm/` and writes `build.ninja`:

   ```bash
   tools/dock python3 configure.py
   ```

4. Build:

   ```bash
   tools/dock ninja
   ```

The last step prints `build/SLUS_210.50: 332be40d… OK` when the output matches. Use `configure.py --no-split` to
regenerate `build.ninja` without re-running splat.

C units need the compiler in `compilers/3.0.3-020716/` (see Requirements). `tools/dock ninja` compiles each
`c_cpp/src/**/*.c` listed in `C_UNITS` in `configure.py`, and links it in place of its assembly once it's marked as
matching. To compare a C unit against the original, run `tools/dock objdiff-cli report generate -o build/report.json`,
or open `tools/bin/objdiff` in this folder.

To boot the rebuilt game, start PCSX2 with your ISO inserted and the rebuilt ELF swapped in:

```bash
/Applications/PCSX2-v2.4.0.app/Contents/MacOS/PCSX2 -elf ~/Desktop/GameMerge/Burnout3_decomp/build/SLUS_210.50 -- ~/Desktop/ps2_games/"Burnout 3 - Takedown (USA).iso"
```

Use `build/SLUS_210.50` (no extension). `build/SLUS_210.50.elf` is an unfinished intermediate file. Starting an ELF
from PCSX2's menu boots without a disc, and the game stalls on a black screen because it loads its modules from the
disc at startup.

## Layout

The decomp has two sides plus shared files at the top level.

| Path | What it is | Committed |
|---|---|---|
| **`assembly/`** | The assembly side ([README](assembly/README.md)) | |
| `assembly/splat/b3.yaml` | Split of the load segment into code, data, VU microcode and carved-out units | yes |
| `assembly/include/` | Assembler macros | yes |
| `assembly/asm/`, `assembly/assets/` | splat output, regenerated from your ELF | **no** |
| **`c_cpp/`** | The C/C++ side ([README](c_cpp/README.md)) | |
| `c_cpp/src/` | Decompiled C/C++, each file replacing the assembly unit with the same path | yes |
| `c_cpp/include/` | Shared headers | yes |
| **Shared** | | |
| `configure.py` | One combined build: splits, assembles, compiles, links, checks the SHA-1. Lists C units and compiler flags. | yes |
| `config/symbol_addrs.txt` | Symbol names | yes |
| `config/reloc_addrs.txt` | Relocation overrides (offsets the disassembler mistook for labels) | yes |
| `config/linker_extra.ld` | Extra linker script, including the offsets used by `reloc_addrs.txt` | yes |
| `tools/elf.py` | Extracts the load segment and rebuilds the exact ELF container | yes |
| `tools/funcmatch.py` | Compares one C/C++ function with the original under chosen flags or compiler | yes |
| `tools/dock` | Runs a command in the build container | yes |
| `docker/Dockerfile` | Build image: binutils-mips-linux-gnu, wibo, objdiff-cli, splat | yes |
| `docs/` | Memory layout, compiler identification, reverse-engineering notes | yes |
| `orig/` | Your ELF and its raw load segment | **no** |
| `compilers/` | CodeWarrior binaries you supply | **no** |
| `build/` | Build output | **no** |
| `tools/bin/` | Downloaded helper tools (objdiff GUI, m2c) | **no** |

## Tooling for decompiling

- **objdiff:** run `tools/bin/objdiff` (macOS GUI) in this directory. It reads `objdiff.json`.
- **Ghidra 12.1.4** with ghidra-emotionengine-reloaded, installed via Homebrew (`ghidraRun`).
- **m2c:** `tools/bin/m2c/m2c.py` for first-draft C from a function's asm.
- **funcmatch:** `tools/dock python3 tools/funcmatch.py <function> <file.c> [-f=FLAGS ...] [-c compilers/<version>]`
  compiles one function, compares it with the original through objdiff, and shows an instruction diff when it
  doesn't match.

## Legal

This directory publishes decompiled source, headers, symbol names and build configs only. It never includes the game
executable, disassembly, assets or compilers. You need your own legally obtained copy of the game. Burnout is a
trademark of Electronic Arts, and RenderWare is a trademark of Criterion Software. This is an unofficial fan project
with no affiliation to either.
