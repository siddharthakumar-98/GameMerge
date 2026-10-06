# Burnout 3: Takedown, decompiled and rewritten in Rust

**A byte-matching decompilation of Burnout 3: Takedown (PS2, NTSC-U), followed by a native Rust rewrite ported from
it.**

> Full plan and progress: **[ROADMAP.md](ROADMAP.md)** · Per-category decomp progress: **[Burnout3_decomp/PROGRESS.md](Burnout3_decomp/PROGRESS.md)**

## Status

> **Done:** matching build (byte-identical, from assembly), compiler identified · **Currently:** mapping the binary
> (D3) and decompiling to C · **Next:** decompiling subsystems (D4–D11), then the Rust rewrite

| Phase | State |
|---|---|
| 1. Decompile to byte-matching C/C++ | D0–D2 done, D3 in progress. 10 functions in C and linked; the full build still matches the original SHA-1 and boots in PCSX2. |
| 2. Rewrite in Rust | Not started. Starts when Phase 1 is 100%. Only the ISO extractor exists. |

## The two phases

1. **Decompile** ([`Burnout3_decomp/`](Burnout3_decomp/README.md)). C/C++ that the original compiler (Metrowerks CodeWarrior for PS2,
   identified as Version 3.0.3) builds into a byte-identical `SLUS_210.50`. The build already reproduces the
   original exactly from assembly. Functions move from assembly to C one at a time, and each one must match before it
   is linked.
2. **Rewrite in Rust** ([`Burnout3_rust/`](Burnout3_rust/README.md)). A native port of the finished decomp that plays the same, loads
   assets from your own disc, and is verified against the decomp function by function and frame by frame.

Phase 2 ports from matched source, never from guesses, so it starts only after Phase 1 is complete.

## Supported build

| Game | Region | Serial | ISO SHA-1 | ELF SHA-1 |
|---|---|---|---|---|
| Burnout 3: Takedown | NTSC-U | SLUS-21050 (`VER 1.00`) | `11a7f335a37d2f3f5c13b967f3072c84f8eded02` | `332be40d6081b8b5055a6ea01194ad6ff662a863` |

Other regions and revisions are not supported.

## Quick start

Requirements:
- Docker (the build runs in a linux/amd64 image, through Rosetta on Apple Silicon)
- Python 3 and Rust
- Your own dump of the game
- The CodeWarrior PS2 compiler, Version 3.0.3 (decomp.me build `mwcps2-3.0.3-020716`), which you supply in
  `Burnout3_decomp/compilers/3.0.3-020716/`
- [PCSX2](https://pcsx2.net) 2.x and a BIOS dumped from your own console, to run the rebuilt game

```bash
# 1. Extract the ELF from your disc
cd Burnout3_rust && cargo run --release -p iso_extract -- extract /path/to/"Burnout 3 - Takedown (USA).iso" ../Burnout3_decomp/orig --only SLUS_210 && cd ..

# 2. Build the image, configure and build
cd Burnout3_decomp
docker build --platform linux/amd64 -t b3-build -f docker/Dockerfile .
tools/dock python3 configure.py
tools/dock ninja        # prints: build/SLUS_210.50: 332be40d… OK
```

Full instructions, including how to boot the rebuilt ELF in PCSX2, are in [Burnout3_decomp/README.md](Burnout3_decomp/README.md).

## Repository layout

| Path | What it is |
|---|---|
| [`Burnout3_decomp/`](Burnout3_decomp/README.md) | Phase 1: `assembly/` (the byte-identical assembly build), `c_cpp/` (decompiled C/C++), `configure.py`, `config/` (symbols), `tools/`, `docs/` |
| [`Burnout3_rust/`](Burnout3_rust/README.md) | Phase 2: the Rust workspace, currently the ISO extractor |
| [`ROADMAP.md`](ROADMAP.md) | Plan, milestones, testing and machine state |

## Related projects

- **MC3DER (planned):** the same decomp and Rust rewrite for Midnight Club 3: DUB Edition Remix, once its ISO is
  dumped.
- **[GameMerge](https://github.com/siddharthakumar-98/GameMerge):** brings Burnout 3's gameplay (takedowns, boost,
  Crash mode) into Midnight Club 3, using this repo's symbols and, later, its Rust core.

## Contributing

Pick an unmatched function in a unit, get it to 100% in objdiff (`tools/funcmatch.py` helps), and add it to `C_UNITS`
in `Burnout3_decomp/configure.py`. The build must still print the matching SHA-1. Never commit anything derived from the game:
see Legal.

## Legal

This repo publishes **decompiled C/C++ source, headers, symbol names, build configs, original Rust code and
documentation**. It contains **no game executables, disassembly, assets, VU microcode, BIOS, disc images or
compilers**, and never will. The build tools regenerate everything else locally from your own copy, after checking its
hash. You need your own legally obtained copy of the game, your own BIOS dump and your own copy of the compiler.

Burnout is a trademark of Electronic Arts. RenderWare is a trademark of Criterion Software. This is an unofficial fan
project with no affiliation to either. Takedown requests are honored.

## Credits

- The [Reburn 3](https://forum.mattkc.com/) community: Burnout 3 reverse engineering
- [splat](https://github.com/ethteck/splat), [spimdisasm](https://github.com/Decompollaborate/spimdisasm),
  [objdiff](https://github.com/encounter/objdiff), [m2c](https://github.com/matt-kempster/m2c),
  [decomp.me](https://decomp.me) and [wibo](https://github.com/decompals/wibo)
- [librw](https://github.com/aap/librw), an open RenderWare reimplementation used as a reference
- [PCSX2](https://github.com/PCSX2/pcsx2)

## License

GPL-3.0. See [LICENSE](LICENSE).
