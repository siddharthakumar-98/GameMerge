# Roadmap: Burnout 3: Takedown, decompiled and rewritten in Rust

This file is the single source of truth for the project's plan and status. Update it whenever a milestone completes or
the approach changes.

## Status

> **Done:** Burnout 3 matching build (byte-identical, from assembly) · **Currently:** verifying it in PCSX2 and
> decompiling to C · **Next:** Rust rewrite of Burnout 3

| Phase | Milestone | State | Updated | Notes |
|---|---|---|---|---|
| 1 Decomp | D0 Environment | done (boot test pending) | 2026-10-05 | Tools installed, build image works, ISO and ELF hashes verified. The PCSX2 boot test waits on a BIOS dump. |
| 1 Decomp | D1 Matching build | **done** | 2026-10-05 | `tools/dock ninja` rebuilds `SLUS_210.50` byte-identical from splat assembly (8,948 functions, symbolic relocations). |
| 1 Decomp | D2 Compiler and flags locked | blocked | | Needs the CodeWarrior PS2 compiler `mwccps2` 2.4.1.01 in `Burnout3_decomp/compilers/` |
| 1 Decomp | D3 Map the binary | ready to start | | Needs no compiler, so it can run while D2 is blocked |
| 1 Decomp | D4–D11 Decompile subsystems to C | not started | | 0 of 8,948 functions in C |
| 2 Rust rewrite | R1–R6 | not started | | Starts when the Phase 1 gate passes |

## Overview

| Phase | Goal | Where |
|---|---|---|
| **1. Decompile Burnout 3** (active) | C/C++ source that CodeWarrior compiles into a byte-identical `SLUS_210.50` | `Burnout3_decomp/` |
| **2. Rewrite Burnout 3 in Rust** (next) | A native Rust port of the finished decomp, with the same gameplay and assets from your disc | `Burnout3_rust/` |
| 3. Decompile Midnight Club 3 | Coming soon | — |
| 4. Rewrite Midnight Club 3 in Rust | Coming soon | — |

Phase 2 starts only after **all** of Phase 1 is done and verified. It ports from matched source, never from guesses.

### What we publish
- **Committed:** decompiled C/C++ source, headers, symbol names, build configs, Rust code and docs.
- **Never committed:** ISOs, BIOS, ELFs, splat-generated assembly and data, extracted assets, VU microcode, compilers,
  savestates and traces. Each user supplies their own disc, BIOS and compiler. The build tools regenerate everything
  else locally from the user's ELF after a hash check.
- Publishing decompiled code carries some legal risk. The project accepts it, follows the usual decomp-community
  practice above, keeps trademark and no-affiliation notices, and honors takedown requests.

### Machine state (2026-10-05)
| Item | State | Action needed |
|---|---|---|
| Burnout 3 ISO | `~/Desktop/ps2_games/Burnout 3 - Takedown (USA).iso`, hash verified | — |
| PCSX2 | `~/Downloads/PCSX2-v2.4.0.app` | Move to `/Applications` |
| BIOS | `~/Library/Application Support/PCSX2/bios/` is **empty** | Dump from your own PS2 console (needed for every runtime test) |
| PINE | Off (`EnablePINE = false`, slot 28011) | Enable for Phase 2 trace capture |
| Docker | Image `b3-build` (linux/amd64: binutils 2.42, wibo 1.2.0, objdiff-cli 3.8.2, splat 0.50.0) | — |
| Rust | rustc 1.99 stable via Homebrew `rustup`, keg-only at `/opt/homebrew/opt/rustup/bin` | Add that directory to `PATH` |
| Ghidra | 12.1.4 + OpenJDK 21 (Homebrew), ghidra-emotionengine-reloaded v2.1.38 installed | Enable the extension on first launch |
| Decomp helpers | Python venv at `Burnout3_decomp/.venv`, objdiff GUI and m2c in `Burnout3_decomp/tools/bin/` (gitignored) | — |
| Compiler | Not present | Supply `mwccps2` 2.4.1.01 for D2 |

---

## Phase 1: Decompile Burnout 3 (active)

**Goal:** every function in `SLUS_210.50` is C/C++ that the original compiler builds into the exact original bytes,
and the rebuilt executable boots and plays in PCSX2 with your disc providing the assets.

**Where it stands:** the build pipeline is complete and byte-identical, but every function is still splat-generated
assembly. Decompiling to C (D2–D11) is the remaining work. It starts with D3, which needs no compiler, and with D2
once the compiler is available.

### What the binary is
- Disc `SYSTEM.CNF`: `BOOT2 = cdrom0:\SLUS_210.50;1`, `VER = 1.00`, NTSC. ISO SHA-1 `11a7f335a37d2f3f5c13b967f3072c84f8eded02`.
- `SLUS_210.50` SHA-1 `332be40d6081b8b5055a6ea01194ad6ff662a863`. Stripped MIPS R5900 ELF, entry `0x100008`, with
  **one merged PT_LOAD** at `0x100000` (filesz `0x3E2680`, memsz `0x1DCEA00`) and `_gp = 0x4E8670` from `.reginfo`.
- **Compiler:** `MW MIPS C Compiler (2.4.1.01)`, which is Metrowerks CodeWarrior for PS2.
- **Language and libraries:** C++ (MW-style RTTI) on top of RenderWare 3.6 (including the PS2 `sky2` driver),
  RenderWare Audio and Sony libsce.
- **Recovered layout** (details in [Burnout3_decomp/docs/layout.md](Burnout3_decomp/docs/layout.md)):

  | VRAM | Region |
  |---|---|
  | `0x100000`–`0x469E00` | `.text` |
  | `0x469E00`–`0x483F00` | VU microcode |
  | `0x483F00`–`0x4D3E00` | `.data` |
  | `0x4D3E00`–`0x4DD820` | C++ static initializers |
  | `0x4DD820`–`0x4DDAA0` | `.ctor` |
  | `0x4DDAA0`–`0x4E0680` | `.data` |
  | `0x4E0680`–`0x4E2680` | `.sdata` |
  | up to `0x1ECEA00` | bss |

- Disc contents and asset formats: [Burnout3_rust/PLAN.md](Burnout3_rust/PLAN.md).

### Repository layout: `Burnout3_decomp/`
```
configure.py              extracts, splits, writes build.ninja and objdiff.json
splat/b3.yaml             segment split of the load segment
config/                   symbol names, extra linker script
include/                  asm macros, later headers and struct layouts
src/{game,rw,sce,msl}/    decompiled C/C++ (from D2)
tools/elf.py              hash-checked extraction and exact ELF container rebuild
tools/dock                runs a command in the build container
docker/Dockerfile         linux/amd64 build image
docs/                     layout and reverse-engineering notes
orig/ asm/ assets/ build/ compilers/   gitignored: your ELF, generated output, your compiler
```

### Tooling
| Purpose | Tool |
|---|---|
| Compiler | CodeWarrior PS2 `mwccps2` 2.4.1.01 (Windows), run through **wibo** in the linux/amd64 image. Wine is the fallback. Nearby versions get tested if the exact one can't be found. |
| Assemble and link | GNU binutils (`mips-linux-gnu-as -march=r5900`, `ld`, `objcopy`). `tools/elf.py rebuild` wraps the linked segment in the original ELF container. |
| Split and disassemble | splat (`platform: ps2`, `compiler: MWCCPS2`) and spimdisasm (R5900: MMI, `lq`/`sq`, VU0 macro ops) |
| Diff and progress | objdiff (macOS GUI and CLI reports), asm-differ, decomp-permuter, decomp.me scratches |
| First-draft C | Ghidra 12.1.x + ghidra-emotionengine-reloaded, m2c. A planned sync script keeps Ghidra and `symbol_addrs.txt` names consistent. |
| Runtime | PCSX2 2.x: boot the rebuilt ELF with your ISO as the disc. Debugger and PINE for spot checks. |
| Reference | `librw` (open RenderWare 3.x reimplementation), the Reburn 3 forum (forum.mattkc.com), CodeBreaker addresses, and the tuning-menu labels compiled into the ELF. No proprietary SDKs are copied. |

### Milestones
| ID | Milestone | Exit criterion | State |
|---|---|---|---|
| **D0** | Environment | Tools installed, image builds, ELF extracted and hashes verified, PCSX2 boots the ISO | done (boot pending) |
| **D1** | Matching build | Section boundaries recovered. `ninja` builds `build/SLUS_210.50` entirely from generated assembly with SHA-1 `332be40d…`. | **done** |
| D2 | Compiler and flags locked | At least 10 functions across at least 3 TUs byte-match: a leaf C function, float math, a C++ ctor/vtable, and a switch/jump table. Flags recorded in `configure.py`. | blocked on compiler |
| D3 | Map the binary | libsce, MW runtime/MSL, RenderWare 3.6 TUs (by `$Id`) and VU microcode labeled and fenced off. Game TU boundaries carved, `.data`/`.rodata` split. Progress reported per category (`game`/`rw`/`sce`/`msl`). | ready |
| D4 | Core infrastructure | Memory/heaps, math (vector/matrix, VU0 paths), file I/O and streaming, the tuning-variable system (`VDB.XML` key hash), strings/localization | |
| D5 | Main loop and game flow | Boot, main loop, game state machine, mode/stage loading, frontend flow | |
| D6 | Vehicle physics and handling | Physics step, suspension, steering, drift, transmission, boost kick | |
| D7 | Gameplay rules | Boost economy, scoring, takedown detection and types, crash state machine, Impact Time, aftertouch, crash cameras | |
| D8 | Game modes and progression | Race, Road Rage, Crash mode (pickups, multipliers, Crashbreaker), Eliminator, Burning Lap, Face-Off, World Tour, save data | |
| D9 | AI, traffic, camera | Racer AI and arbitration, traffic, follow/bumper/replay cameras | |
| D10 | Presentation and platform | Game-side rendering, deformation, particles, audio (RW Audio, EA Trax), frontend UI, video, memory card, network (DirtySock) | |
| D11 | Libraries | MW runtime, libsce, RenderWare 3.6. Hand-written asm and VU microcode stay as asm, as in the original source. | |
| **Gate** | Phase 1 complete | 100% of functions in C and matching, the build reproduces the SHA-1, and every check under [Testing Phase 1](#testing-phase-1) passes | |

Work runs infrastructure first, then gameplay, then presentation, then libraries. Headers and struct layouts grow
outward from core code. Within a milestone, work goes one translation unit at a time, smallest functions first.

### Risks and open questions
| Risk / question | Mitigation |
|---|---|
| Getting the exact `mwccps2` 2.4.1.01 (proprietary) | You source it yourself, and it stays gitignored. Test nearby versions against D2 functions, and document the outcome. |
| Section and TU boundaries had to be inferred from one merged segment | `_gp`, alignment padding, rodata/string clustering, RenderWare `$Id` strings, vtable/RTTI order. Refined in D3. |
| GNU ld standing in for the MW linker | Match the load segment, then rebuild the container in `tools/elf.py`. Already proven in D1. |
| R5900-specific code (MMI, VU0 macro, 128-bit loads/stores) | Keep it as inline asm where the original most likely was. Hand-decompile the rest. |
| C++ under CodeWarrior (mangling, vtables, inlining order) | Lock patterns in D2. Recover class layouts from RTTI strings. |
| Scale: about 3.9 MB of code and data | Order by value, track progress, use decomp.me and permuter |
| Whether public CI should verify matching | Open. Options: local-only, or a private runner holding your ELF. |

---

## Testing Phase 1

How we confirm the decomp builds, and behaves, exactly like the original. A byte-identical executable behaves
identically by construction, so most of these checks guard the build itself. The runtime checks then confirm the
boot path and catch anything the hash can't, such as a wrong load procedure.

### 1. The build reproduces the original
| Check | How | State |
|---|---|---|
| SHA-1 match | `tools/dock ninja` prints `build/SLUS_210.50: 332be40d… OK` and fails otherwise | **passing** |
| Clean rebuild | Delete `asm/ assets/ build/ build.ninja orig/SLUS_210.50.rom`, then `tools/dock python3 configure.py && tools/dock ninja` | **passing** |
| Byte comparison | `cmp build/SLUS_210.50 orig/SLUS_210.50` reports no differences | **passing** |
| Fresh-clone build | Follow [Burnout3_decomp/README.md](Burnout3_decomp/README.md) from a fresh clone with only the ISO present | to do |
| Nothing derived is tracked | `git status --ignored` shows `orig/`, `asm/`, `assets/`, `build/`, `compilers/` ignored, and `git ls-files` lists no binaries | **passing** |

### 2. The build is genuinely relinkable
| Check | How | State |
|---|---|---|
| Symbolic relocations | The generated assembly uses `jal`/`%hi`/`%lo`/`%gp_rel` symbol references, not hard-coded addresses (about 40k `jal`, 36k `%hi`, 11.7k `%gp_rel`) | **passing** |
| Shift build | Insert padding early in `.text`, rebuild with the hash check disabled, and boot it in PCSX2. It must still reach the menu and load a race, which proves no address is baked in as a plain number. | to do (needs BIOS) |

### 3. Each decompiled function matches
| Check | How | State |
|---|---|---|
| Per function | objdiff shows 100% for every function moved from assembly to C | from D2 |
| Progress | `objdiff-cli report` → `tools/progress.py` → `Burnout3_decomp/PROGRESS.md`, summarized in the Status table | from D2/D3 |
| No regressions | The SHA-1 check stays green after every function lands. A function that doesn't match stays in assembly. | from D2 |

### 4. It runs like the original
All of these run the rebuilt `build/SLUS_210.50` in PCSX2 ("Boot ELF") with your Burnout 3 ISO as the disc. They need
a BIOS dump.

| Check | Pass criterion | State |
|---|---|---|
| Boot | Reaches the title screen and main menu | to do |
| Race | Loads a track and finishes a race. Boost, takedowns and crashes work. | to do |
| Modes | Road Rage, Crash mode (pickups, Crashbreaker) and Eliminator each play through to their results screen | to do |
| Save data | A memory-card save from the original loads in the rebuilt build, and the reverse | to do |
| Side by side | The same savestate and input recording in the original and the rebuilt ELF give the same RAM at fixed frames (compared over PINE) | to do |

**Phase 1 is verified** when every check above passes with 100% of functions in C.

---

## Phase 2: Rewrite Burnout 3 in Rust (next)

**Goal:** a native Rust version of Burnout 3, in `Burnout3_rust/`, that plays the same as the original. It loads assets
from your ISO at runtime and is ported from the finished, verified decomp. It uses idiomatic Rust wherever that
doesn't change gameplay.

**Starts when:** the Phase 1 gate passes.

### Tooling and structure
| Crate / tool | Role |
|---|---|
| `formats` | RenderWare binary stream, TXD, BGV/BTV, tracks, VDB, strings, audio |
| `ee` | EE float semantics (no denormals/inf/NaN, EE rounding) and RNG |
| `game` | `no_std` gameplay core |
| `rw` | RenderWare runtime replacement, with librw as a reference |
| `engine` | wgpu renderer, cpal audio, gilrs input |
| `tools/iso_extract` | Already exists. Used as a library so assets stream straight from your ISO. |
| C oracle | The matched decomp compiled natively (clang via the `cc` crate, behind a platform shim) and called from Rust tests |
| PCSX2 + PINE | Golden per-frame state traces from the matched ELF, using savestates and input recordings |

### Port order
1. Formats and assets
2. Math and EE float types
3. Tuning system
4. Headless deterministic sim: physics → gameplay rules → modes → AI/traffic
5. Camera
6. Renderer (replacing the sky2/VU pipelines)
7. Audio
8. Frontend/UI and video
9. Save data

**Idiom policy:** use ownership instead of raw pointers, enums for state machines, `Result` for I/O, and traits instead
of vtables, wherever results don't change. **Float operation order, EE float semantics, RNG sequences and frame timing
are preserved exactly.**

### Milestones
| ID | Milestone |
|---|---|
| R1 | A track loads from the ISO and a fly-cam works |
| R2 | A drivable car with `VDB.XML` tuning |
| R3 | Boost, near misses and takedowns against AI and traffic |
| R4 | Crash mode at one junction |
| R5 | UI, Road Rage and World Tour |
| R6 | The full game is playable with all modes |

### Verification
- **Unit:** each ported function is differential-tested against the C oracle on fuzzed and recorded inputs. Results
  must be bit-identical.
- **System:** golden traces from PCSX2 (matched ELF, scripted input, savestates, read over PINE) are replayed into the
  headless Rust sim. The per-frame gameplay-state diff must be zero across the scenario suite.
- **Visual:** renderer output is compared by screenshot against PCSX2 for the same frame.
- `cargo test --workspace` runs format round-trips, oracle diffs and trace replays. Traces and extracted data stay local
  and gitignored, and tests that need them skip with a clear message.

### Risks
- **EE FPU vs IEEE** is the biggest fidelity risk. Use an `ee` soft-float type wherever trace diffs require it.
- The oracle needs a platform shim and 32-bit pointer assumptions, so scope it to pure logic TUs.
- Renderer parity (VU1 lighting, skinning, deformation) can only be judged by screenshot.
- Open: platforms beyond macOS (wgpu keeps Windows and Linux possible).

---

## Future plans

3. **Decompile Midnight Club 3: DUB Edition Remix** (SLUS-21355). *Coming soon.* No milestones until the game files
   are available.
4. **Rewrite Midnight Club 3 in Rust.** *Coming soon.*

The earlier GameMerge passthrough plan (Burnout 3 gameplay inside Midnight Club 3, milestones M1–M10) remains in git
history (commit `a53cf40`) for when both games are done.
