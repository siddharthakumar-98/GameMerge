# Roadmap: GameMerge: decompile Burnout 3 and Midnight Club 3, rewrite both in Rust, then merge them

This file is the single source of truth for the project's plan and status. Update it whenever a milestone completes or
the approach changes.

## Status
| Stage | Milestone | State | Updated | Notes |
|---|---|---|---|---|
| A1 Burnout 3 decomp | D0 Environment | done (boot test pending) | 2026-10-05 | Tools installed, image builds, ISO and ELF hashes verified. The PCSX2 boot test waits on your BIOS dump. |
| A1 Burnout 3 decomp | D1 Matching shell | **done** | 2026-10-05 | `tools/dock ninja` rebuilds `SLUS_210.50` byte-identical from splat asm (8,948 functions, symbolic relocations). Layout in `Burnout3_decomp/docs/layout.md`. |
| A1 Burnout 3 decomp | D2 Compiler and flags locked | next, blocked | | Needs `mwccps2` 2.4.1.01 (you supply it) |
| A1 Burnout 3 decomp | D3 Map the binary | can start now | | Library labeling and TU carving need no compiler, so this runs in parallel with sourcing it. |
| A1 Burnout 3 decomp | D4–D11 | not started | | Progress % will come from `Burnout3_decomp/PROGRESS.md` (0% C so far) |
| A2 MC3 decomp | — | blocked | | Needs the MC3 ISO dump |
| B1/B2 Rust rewrites | — | not started | | Gated on 100% of the matching game's decomp |
| C GameMerge passthrough | M1–M10 | not started | | Gated on A1 + A2 |

## Overview

The project runs in three stages:

```
Stage A  Phase 1: matching decomps (original language, original compiler, byte-identical ELF)
         A1 Burnout 3: Takedown (SLUS-21050)            ← current
         A2 Midnight Club 3: DUB Edition Remix (SLUS-21355)  (may overlap A1 once its ISO is dumped)
Stage B  Phase 2: Rust rewrites, each starting once its game's decomp is 100% (whole-game gate)
         B1 Burnout3_rust      B2 MC3DER_rust
Stage C  GameMerge passthrough (Burnout 3 gameplay inside MC3), starting after A1 + A2,
         running in parallel with Stage B
```

- **Phase 1 (decomp)** turns each game back into C/C++ that compiles, with the original compiler, to the exact bytes of the
  shipped executable. Game assets are always read from the user's own disc at runtime.
- **Phase 2 (Rust)** rewrites each game in Rust from its matched decomp. It keeps the original behavior exactly and uses
  idiomatic Rust wherever that doesn't change gameplay.
- **Stage C (GameMerge)** is the original passthrough-mod goal. It now builds on the decomps: struct layouts and
  addresses come from matched headers, and `gm-core` is the gameplay core of the Burnout 3 Rust rewrite.

### What we publish (legal)
- **Committed:** decompiled C/C++ source, headers, symbol names, build configs, Rust code and docs.
- **Never committed:** ISOs, BIOS, ELFs, splat-generated asm/data, extracted assets, VU microcode blobs, compilers,
  savestates and traces. Users supply their own disc, BIOS and compiler. Build tools regenerate everything else from
  the user's own ELF after a hash check.
- Publishing decompiled code carries some legal risk. The project accepts it, follows the usual decomp-community
  practice above, keeps trademark and no-affiliation notices, and honors takedown requests.

### Current machine state (verified read-only, 2026-10-05)
| Item | Found | Action needed |
|---|---|---|
| Workspace | `~/Desktop/GameMerge/`, git repo tracking `origin/main` | — |
| ISOs | `~/Desktop/ps2_games/Burnout 3 - Takedown (USA).iso` only. **No MC3 ISO.** | Dump MC3 before A2 |
| PCSX2 | `~/Downloads/PCSX2-v2.4.0.app`, config in `~/Library/Application Support/PCSX2/` | Move to `/Applications` |
| PINE | `EnablePINE = false`, `PINESlot = 28011` | Enable in Stage C |
| BIOS | `…/PCSX2/bios/` is **empty** | Dump from your own PS2 console (needed for boot tests) |
| Rust | rustc 1.99 stable via Homebrew `rustup` (keg-only: `/opt/homebrew/opt/rustup/bin`) | Add that directory to `PATH`. A pinned nightly comes in Stage C for the MIPS target. |
| Java / Ghidra | Ghidra 12.1.4 + OpenJDK 21 (Homebrew), ghidra-emotionengine-reloaded v2.1.38 in `~/Library/ghidra/ghidra_12.1.4_PUBLIC/Extensions` | Enable the extension on first launch. The Temurin pkg needed sudo, so it isn't used. |
| Docker | Running, image `b3-build` (linux/amd64: binutils 2.42, wibo 1.2.0, objdiff-cli 3.8.2, splat 0.50.0) | — |
| Python | miniconda Python 3, venv at `Burnout3_decomp/.venv` | — |
| Decomp helpers | objdiff 3.8.2 GUI and m2c in `Burnout3_decomp/tools/bin/` (gitignored) | — |

---

## Stage A, Phase 1: matching decomps

### A1: Burnout 3: Takedown

#### Confirmed from the binary
- Disc `SYSTEM.CNF`: `BOOT2 = cdrom0:\SLUS_210.50;1`, `VER = 1.00`, NTSC. ISO SHA-1 `11a7f335a37d2f3f5c13b967f3072c84f8eded02`.
- `SLUS_210.50` SHA-1 `332be40d6081b8b5055a6ea01194ad6ff662a863`. Stripped MIPS R5900 ELF, entry `0x100008`.
  It has **one merged RWX PT_LOAD** at `0x100000` (filesz `0x3E2680`, memsz `0x1DCEA00`), no `.text`/`.data`
  section headers, and only `.comment` and `.reginfo` (which gives `_gp`).
- **Compiler:** `.comment` reads `MW MIPS C Compiler (2.4.1.01)`. That is **Metrowerks CodeWarrior for PS2**, not GCC.
- **Language:** C++ (MW-style RTTI strings such as `!std::exception!!std::bad_exception!!`) on top of C libraries.
- **Engine:** RenderWare 3.6 (`$Id: //RenderWare/RW36Active/rwsdk/...`, including the PS2 `sky2` driver), RenderWare
  Audio, and Sony libsce (`sceCd*`, `sceDbc*`, `sceMpeg*`).
- Disc contents and asset formats are listed in [Burnout3_rust/PLAN.md](Burnout3_rust/PLAN.md).
- **Recovered layout** (details in [Burnout3_decomp/docs/layout.md](Burnout3_decomp/docs/layout.md)):
  - `.text` `0x100000`–`0x469E00`
  - VU microcode `0x469E00`–`0x483F00`
  - `.data` `0x483F00`–`0x4D3E00`
  - C++ static initializers `0x4D3E00`–`0x4DD820`
  - `.ctor` `0x4DD820`–`0x4DDAA0`
  - `.data` `0x4DDAA0`–`0x4E0680`
  - `.sdata` `0x4E0680`–`0x4E2680`
  - bss up to `0x1ECEA00`

#### Layout: `Burnout3_decomp/`
```
configure.py              generates build.ninja
splat/b3.yaml             segment/TU split of SLUS_210.50
config/symbol_addrs.txt   symbol names (published)
src/{game,rw,sce,msl}/    matched C/C++ (published)
include/                  headers and struct layouts (published)
tools/                    ELF rebuild, progress report, Ghidra sync
docker/Dockerfile         linux/amd64 build image: binutils-mips-linux-gnu, wibo, ninja, python
orig/                     (gitignored) your SLUS_210.50, hash-checked
asm/ assets/ build/       (gitignored) generated
compilers/                (gitignored) mwccps2 2.4.1.01, which you supply
```

#### Tooling
- **Compiler:** MWCC PS2 `2.4.1.01` (`mwccps2.exe`, Windows) runs through **wibo** in the linux/amd64 Docker image
  (Rosetta on Apple Silicon). Wine is the fallback. Nearby versions are tested if the exact one can't be found.
- **Assembler/linker:** GNU binutils (`mips-linux-gnu-as -march=r5900`, `ld`, `objcopy`). `tools/elf_rebuild.py`
  reproduces the original ELF container so the SHA-1 can match.
- **Splitting/disasm:** splat (`splat64`, `platform: ps2`, `compiler: MWCCPS2`) and spimdisasm (R5900, including MMI,
  `lq`/`sq` and VU0 macro ops). splat runs on the raw load segment, which `tools/elf.py extract` writes after a hash check.
- **Diffing/progress:** objdiff (macOS GUI, CLI for reports), asm-differ, decomp-permuter, decomp.me scratches.
- **First-pass decompilation:** Ghidra 12.1.x + ghidra-emotionengine-reloaded, and m2c for MIPS→C drafts. A sync script
  keeps Ghidra and `symbol_addrs.txt` names consistent.
- **Runtime:** PCSX2 2.x boots the rebuilt ELF with your ISO mounted as the disc, so assets come from your copy.
- **Reference knowledge:** `librw` (open RW 3.x reimplementation), the Reburn 3 forum (forum.mattkc.com), CodeBreaker
  addresses, and the tuning-menu label tree compiled into the ELF. No proprietary SDKs are copied.

#### Milestones
| ID | Milestone | Exit criterion |
|---|---|---|
| **D0** | Environment | Tools installed. Docker image builds. ELF extracted to `orig/`. ISO and ELF SHA-1s verified. PCSX2 boots the ISO once the BIOS is dumped. |
| **D1** | Matching shell | Section boundaries recovered (`.text`/`.rodata`/`.data`/`.sdata`/`.sbss`/`.bss`, `_gp`). `ninja` builds `build/SLUS_210.50` **entirely from generated asm**, and its SHA-1 matches `332be40d…`. |
| D2 | Compiler and flags locked | At least 10 functions across at least 3 TUs byte-match: a leaf C function, float math, a C++ ctor/vtable, and a switch/jump table. Flags recorded in `configure.py`. |
| D3 | Map the binary | libsce, MW runtime/MSL, RenderWare 3.6 TUs (by `$Id`) and sky2 VU microcode labeled and fenced off. Game TU boundaries carved. Progress reported per category (`game`/`rw`/`sce`/`msl`). |
| D4 | Core infrastructure | Memory/heaps, math (vector/matrix, VU0 paths), file I/O and streaming, tuning-variable system (`VDB.XML` key hash), strings/localization. |
| D5 | Main loop and game flow | Boot, main loop, game state machine, mode/stage loading, frontend flow skeleton. |
| D6 | Vehicle physics and handling | Physics step, suspension, steering, drift, transmission, boost kick. |
| D7 | Gameplay rules | Boost economy, scoring, takedown detection and types, crash state machine, Impact Time, aftertouch, crash cameras. |
| D8 | Game modes and progression | Race, Road Rage, Crash mode (pickups, multipliers, Crashbreaker), Eliminator, Burning Lap, Face-Off, World Tour, save data. |
| D9 | AI, traffic, camera | Racer AI and arbitration, traffic, follow/bumper/replay cameras. |
| D10 | Presentation and platform | Game-side rendering, deformation, particles, audio (RW Audio / EA Trax), frontend UI, video, memory card, network (DirtySock). |
| D11 | Libraries | MW runtime, libsce, RenderWare 3.6 TUs. Hand-written asm and VU microcode stay as asm/blobs, as in the original source. |
| **Gate** | A1 complete | 100% of functions matched, the full build reproduces the SHA-1, and the rebuilt ELF boots and plays in PCSX2. |

The order runs infrastructure first, then gameplay logic, then presentation, then libraries. Headers and struct
layouts flow outward from core code, the rules GameMerge needs (D6–D8) come early, and libraries come last because
Phase 2 replaces them. Within a milestone, work goes TU by TU, smallest functions first.

#### Verification
- **Every build:** `ninja` → `build/SLUS_210.50` must have SHA-1 `332be40d6081b8b5055a6ea01194ad6ff662a863`.
- **Per function:** objdiff shows 100% for every function marked matched. `tools/progress.py` writes matched
  bytes/functions per category to `Burnout3_decomp/PROGRESS.md`, and the Status table above shows the summary.
- **Runtime smoke:** the rebuilt ELF boots in PCSX2 with your ISO, reaches the menu and loads a race.
- **CI:** public CI can't hold the ELF, so it only checks that the source compiles. Matching is verified locally.

#### Risks and open questions
| Risk / question | Mitigation |
|---|---|
| Getting the exact `mwccps2 2.4.1.01` binary (proprietary) | You source it yourself, and it stays gitignored. Test nearby `mwcps2` versions against D2 functions, and document the outcome. |
| Merged single segment: section and TU boundaries must be inferred | `_gp` from `.reginfo`, alignment padding, rodata/string clustering, RW `$Id` strings, vtable/RTTI order. |
| Reproducing MW-linker output with GNU ld | Match the loaded segment first, then rebuild the ELF headers exactly in `elf_rebuild.py`. |
| R5900-specific code (MMI, VU0 macro, 128-bit loads/stores) | Keep it as inline asm or asm where the original most likely was. Hand-decompile the rest. |
| C++ under MWCC (mangling, vtables, inlining order) | Lock patterns in D2. Recover class layouts from RTTI strings. |
| Scale: about 3.9 MB of code+data takes years to fully match | Order by value, track progress metrics, use decomp.me/permuter. |
| Whether public CI should verify matching | Open. Options: local-only, or a private runner holding your ELF. |

### A2: Midnight Club 3: DUB Edition Remix
Same template as A1, in `MC3DER_decomp/`, once the MC3 ISO (SLUS-21355) is dumped.
1. **First, confirm the compiler** from `.comment` and strings before any toolchain setup.
2. Seed `symbol_addrs.txt` from the **znxee/mc3-znx-tools** symbol tables (from the Oct 2004 alpha's `MC.MAP`), which is
   a large head start. Mind GPL-3 if any code is ported.
3. Milestones follow the A1 pattern: environment, matching shell, compiler lock, map, then subsystems. Priorities:
   vehicle struct and physics, collision callbacks, opponent/traffic managers, camera, time step, HUD, and the race/mode
   state machine and pad input, since those are what Stage C needs.

---

## Stage B, Phase 2: Rust rewrites
Each rewrite starts once its game's decomp is 100% matched.

### B1: Burnout3_rust
- **Crates:**
  - `formats`: RW binary stream, TXD, BGV/BTV, tracks, VDB, strings, audio.
  - `ee`: EE float semantics (no denormals/inf/NaN, EE rounding) and RNG.
  - `game`: the `no_std` gameplay core, later shared as GameMerge's `gm-core`.
  - `rw`: the RenderWare runtime replacement, with librw as a reference.
  - `engine`: wgpu renderer, cpal audio, gilrs input.
  - `tools`: including `iso_extract`, used as a library so assets stream straight from your ISO.
- **Port order:**
  1. formats/assets
  2. math and EE float types
  3. tuning system
  4. headless deterministic sim: physics → gameplay rules → modes → AI/traffic
  5. camera
  6. renderer (replacing sky2/VU pipelines)
  7. audio
  8. frontend/UI and video
  9. save data
- **Idiom policy:** use ownership instead of raw pointers, enums for state machines, `Result` for I/O, and traits instead
  of vtables, wherever results don't change. Float operation order, EE float semantics, RNG sequences and frame timing are preserved exactly.
- **Milestones:**
  1. A track loads from the ISO and a fly-cam works.
  2. A drivable car with `VDB.XML` tuning.
  3. Boost, near misses and takedowns vs AI and traffic.
  4. Crash mode at one junction.
  5. UI, Road Rage and World Tour.
  6. The full game is playable with all modes.
- **Verification:**
  - **Unit:** each ported function is differential-tested against the matched C, compiled natively as an oracle (via the
    `cc` crate behind a platform shim), on fuzzed and recorded inputs. Results must be bit-identical.
  - **System:** golden per-frame state traces from PCSX2 (matched ELF, scripted input, savestates, read over PINE) are
    replayed into the headless Rust sim. The gameplay-state diff must be zero across the scenario suite.
  - Traces and extracted data stay local and gitignored. Tests that need them skip with a clear message.
- **Risks:**
  - **EE FPU vs IEEE** is the biggest fidelity risk. Use an `ee` soft-float type where trace diffs demand it.
  - The oracle needs a platform shim and 32-bit pointer assumptions, so scope it to pure logic TUs.
  - Renderer parity (VU1 lighting, skinning, deformation) is judged by screenshots against PCSX2.
  - Open: platforms beyond macOS.

### B2: MC3DER_rust
Same pattern as B1, starting from the A2 decomp.

---

## Stage C: GameMerge passthrough (after A1 + A2, parallel with Stage B)

### Context
"Game merging" (passthrough modding) was kicked off by chasm's video *"The Next Generation of Modding"*
(youtu.be/zRT3MyFwgu0) and his SkyCraft project (Skyrim + Minecraft). We apply it to two PS2 racers:
- **Host = Midnight Club 3: DUB Edition Remix.** Its open city, cars, rendering and controls stay.
- **Guest = Burnout 3: Takedown.** It supplies takedowns, boost, Impact Time slow-mo, takedown cam, aftertouch, Road
  Rage, and **Crash mode** (crash junctions scored in insurance-damage $, multiplier pickups, Crashbreaker).
- All cars come from MC3.

**What the SkyCraft architecture teaches:**
- The host draws everything. The guest runs **hidden** and owns its game logic.
- The two talk through **shared memory** with one protocol definition. Collision flows from host to guest, and
  gameplay results flow back.
- Our games have no script extender. **The decomps replace SKSE:** every address, struct and function signature comes
  from matched source.
- On PS2, shared memory means **PCSX2 PINE** plus **injected code** inside MC3.

**Resources to reuse:**
| Resource | Use |
|---|---|
| znxee/mc3-znx-tools (GPL-3, SLUS-21355) | MC3 symbols (also seeds A2), modloader injector, C++ mods (freecam, HUD, widescreen), PINE telemetry, format docs |
| forum.mattkc.com (Reburn 3) | Burnout 3 RE knowledge |
| PCSX2-Burnout mods / CodeBreaker codes | Known RAM addresses for cross-checks |
| PCSX2 2.x debugger | Breakpoints, memory view, extra symbol files generated from our `symbol_addrs.txt` |
| trevaintdead passthrough guide | Build order from small to large |

### Rust workspace design (GameMerge)
```
crates/
  gm-protocol/   no_std  #[repr(C)] HostFrame / GuestEvents / HostCommands + layout asserts
  gm-pine/       std     PINE client (unix socket, batched read/write, typed reads)
  mc3-sys/       no_std  MC3 memory model, generated from MC3DER_decomp headers + symbols
  b3-sys/        no_std  Burnout 3 memory model, generated from Burnout3_decomp headers + symbols
  gm-core/       no_std  re-exports Burnout3_rust's `game` core (takedowns, boost, crash, aftertouch, modes, crash $)
  gm-bridge/     bin     host↔guest loop over two PINE connections; runs gm-core in shadow mode
  gm-hostmod/    no_std  code injected into MC3 (MIPS EE target): mailbox, impulses, time scale, camera, HUD, input
  gm-guestpatch/ no_std  Burnout patches: null-render-friendly, AI/timers off, puppet slots
  gm-tools/      bins    address-table validator, savestate scenario runner, fake_host / fake_guest
xtask/                   `cargo xtask build-mod | inject | launch | test-scenarios`
```
**Rust-on-PS2 is the main technical unknown for Stage C.** The EE is a MIPS R5900 (no LL/SC, 128-bit MMI ops, EABI).
- **C0 spike (opens Stage C):** a `no_std` crate with a custom mipsel target JSON and `-Zbuild-std=core`, linked at a
  fixed address in a code cave, calling one MC3 function through `extern "C"`.
- **Fallback:** a ~100-line C/asm shim for the ABI boundary only. The decomp toolchain can build it.
- Until `gm-hostmod` exists, PINE writes alone cover M1–M4.

### C0: Setup
1. Enable PINE and create two PCSX2 profiles. MC3 uses slot 28011 and the normal renderer. Burnout uses slot 28012,
   the **Null renderer** and muted audio. Launch them through `xtask launch` with separate portable data dirs.
2. Pin the nightly and scaffold the workspace above. Generate `mc3-sys`/`b3-sys` from the decomp headers and symbols.
3. Run the R5900 spike.

### C1: Passthrough architecture
```
 PCSX2 #1 (visible)  MC3 + gm-hostmod            PCSX2 #2 (Null GS, muted)  Burnout 3 + gm-guestpatch
   mailbox @ fixed RAM addr                         puppet car slots, AI/timers suppressed
   applies impulses/slow-mo/cam/HUD                 takedown/boost/score logic runs for real
          ▲ PINE 28011                                        ▲ PINE 28012
          └────────────────── gm-bridge (Rust, macOS) ────────┘
     read HostFrame → write puppets → read GuestEvents → write HostCommands
     (+ gm-core shadow: compute the same events in Rust and diff against Burnout's)
```
- **`gm-protocol` messages:**
  - `HostFrame`: frame number, a car table of up to 16 entries, contacts, pad input.
  - `GuestEvents`: takedowns {attacker, victim, type}, boost, slow-mo/camera requests, crash $, pickups, Crashbreaker.
  - `HostCommands`: impulses, time scale, camera override, HUD values, sequence number.
- **Ownership:**
  - MC3 owns the world, rendering, car models, base physics and traffic/AI pathing.
  - Burnout owns takedown rules, boost, scoring, slow-mo/camera decisions and mode rules.
- **Puppets:** MC3 car states are written into Burnout's car slots every frame. World-dependent events (wall takedowns,
  traffic checks) are classified from MC3 collision callbacks and fed into Burnout's scoring path as synthetic events.
- **Sync:** MC3 is authoritative. One bridge tick per MC3 frame, batched PINE calls, one frame of latency tolerated.
- **Shadow mode:** `gm-core` runs from day one. The bridge logs any disagreement with real Burnout.

### Milestones. Each ends with a clip, a bridge log and a passing scenario.
1. **M1 Hello host:** the injected Rust writes a magic value into the mailbox, and the bridge reads it.
2. **M2 Hello guest:** Burnout runs hidden, and the bridge reads its boost bar.
3. **M3 Mirror:** the MC3 player's transform drives Burnout's player slot. Verify by briefly enabling Burnout rendering.
4. **M4 Boost:** boost is earned from MC3 driving, shown in the MC3 HUD, and applied as nitro or force.
5. **M5 Takedown detection:** ramming an MC3 opponent produces the correct takedown type in the log. Shadow `gm-core` agrees.
6. **M6 Takedown feel:** victim impulse, Impact Time slow-mo, takedown cam, a "TAKEDOWN!" popup, and a respawn.
7. **M7 Player crash + aftertouch:** wreck steering in slow-mo, and aftertouch takedowns are scored.
8. **M8 Road Rage mode:** a mode state machine with a target, a timer and results.
9. **M9 Crash mode:** chosen MC3 intersections, scripted traffic waves, pickup trigger volumes, damage $ using
   Burnout's formula, a Crashbreaker radial blast, and a $ HUD.
10. **M10 Polish:** takedown cam variety, rivals/revenge, a signature subset, audio from MC3 banks, an options toggle.

**Stretch:** visual deformation on MC3 car meshes by vertex offset at render time.

### Testing (continuous)
- `cargo test`:
  - `gm-protocol` layout asserts
  - `gm-core` unit tests
  - a bridge loop driven by `fake_host`/`fake_guest`
- `cargo xtask test-scenarios`: savestate fixtures plus scripted pad input against both emulators. For example, "ram
  opponent at 120 km/h at 30°" must produce `TAKEDOWN type=SLAM` from both Burnout and `gm-core`.
- The address-table validator runs at bridge startup and aborts clearly on a build mismatch.
- Performance budget: bridge tick under 2 ms, no MC3 frame drops with two PCSX2 instances on Apple Silicon.

### Graduate and release
- Once a system's shadow diff is zero, `gm-hostmod` links that part of `gm-core` directly and stops asking Burnout.
  When every system has moved over, drop the second emulator.
- Optional later: a native PC build combining B1/B2 Rust rewrites, without emulation.
- Release: a public repo, users supply their own ISOs, BIOS and compilers, `cargo xtask launch` as a one-click
  launcher, and a README with supported serials and hashes.

### Stage C risks
| Risk | Mitigation |
|---|---|
| Rust can't target the R5900 cleanly | C0 spike. Thin C/asm shim fallback. PINE-only work covers M1–M4. |
| Burnout takedown logic tied to its own world | Guest handles car-vs-car only. World events come from MC3 collisions. Native `gm-core` fallback. |
| PINE throughput at 60 Hz | Batched calls, a compact mailbox, one frame of latency tolerated. |
| Two emulators on one Mac | Null renderer for the guest. Measure in M2. Graduating removes the guest anyway. |
| Scope creep | M1–M9 is the target. Deformation and full signature takedowns are stretch. |

---

## End-to-end verification
1. **A1/A2:** `ninja` in each decomp reproduces the original ELF SHA-1, the progress reports reach 100%, and the
   rebuilt ELFs boot and play in PCSX2 with the user's discs.
2. **B1/B2:** `cargo test --workspace` passes, including oracle diffs and trace replays with zero gameplay-state
   diffs. Each game is playable natively, loading assets from the user's ISO.
3. **Stage C:** `cargo xtask launch` shows MC3 visible, Burnout hidden and both PINE ports connected. Boost,
   takedowns, aftertouch, Road Rage and Crash mode all work. `cargo xtask test-scenarios` passes, and after
   graduating it also passes with the guest emulator disabled.
