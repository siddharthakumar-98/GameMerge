# Roadmap: GameMerge: Burnout 3 systems inside Midnight Club 3 DUB Edition Remix (passthrough mod, Rust rewrite)

## Context

"Game merging" (passthrough modding) is popular right now, kicked off by chasm's video *"The Next Generation of Modding"* (youtu.be/zRT3MyFwgu0) and his SkyCraft project (Skyrim + Minecraft). The goal is to apply that approach to two PS2 racers:

- **Host = Midnight Club 3: DUB Edition Remix.** Its open city, cars, rendering and controls stay.
- **Guest = Burnout 3: Takedown.** It supplies takedowns, boost, Impact Time slow-mo, takedown cam, aftertouch, Road Rage, and **Crash mode** ("insurance boom": crash junctions scored in insurance-damage $, multiplier pickups, Crashbreaker).
- All cars come from MC3.

**What's new in this revision:**
- Everything we write is **Rust**.
- Every reverse-engineered subsystem is **rewritten in Rust** as a clean reimplementation, so the Rust workspace effectively *is* the decomp of the parts we touch.
- The passthrough workflow stays as proposed. The Rust rewrite grows alongside it and finally replaces the hidden Burnout instance.

### Current machine state (verified read-only)
| Item | Found | Action needed |
|---|---|---|
| Workspace | `~/Desktop/GameMerge/`, empty, not a git repo | `git init` + Cargo workspace (Phase 0) |
| PCSX2 | `~/Desktop/PCSX2-v2.5.206.app`, config in `~/Library/Application Support/PCSX2/` | OK |
| PINE | `EnablePINE = false`, `PINESlot = 28011` in `inis/PCSX2.ini` | Enable it. The second instance gets slot 28012. |
| BIOS | `…/PCSX2/bios/` is **empty** | Dump from your own PS2 console (required before anything runs) |
| ISOs | `~/Desktop/ps2 games/Midnight Club 3 - DUB Edition Remix (USA).iso`, `…/Burnout 3 - Takedown (USA).iso` | Verify serials SLUS-21355 / SLUS-21050 from `SYSTEM.CNF`, then record SHA-1 hashes |
| Host CPU | Apple Silicon (arm64) | The bridge builds natively. Check whether this PCSX2 build is native or Rosetta (affects perf with two instances). |
| Rust | rustc 1.76 (Feb 2024) via `~/.cargo` | `rustup update`. Add a pinned **nightly** for `-Zbuild-std` (needed for the PS2 MIPS target). |

### What the video/SkyCraft architecture teaches
- SkyCraft does not rewrite either game. The host (Skyrim) draws everything. The guest (Minecraft) runs **hidden** and owns its game logic.
- The two talk through **shared memory** using one protocol definition. Collision flows from host to guest, and gameplay results flow from guest to host.
- SkyCraft relied on SKSE/Fabric. **Our games have no script extender, so reverse engineering replaces SKSE.**
- On PS2, "shared memory" becomes **PCSX2 PINE** (an outside process reads and writes emulated RAM), plus **injected code** inside MC3 for in-engine work.

### Existing resources to reuse (don't rebuild)
| Resource | Use |
|---|---|
| **znxee/mc3-znx-tools** (GPL-3, targets SLUS-21355) | Symbol `.tsv` files from the Oct 2004 alpha's `MC.MAP`, a modloader injector (`mc3_inject.py`), C++ mods (freecam, HUD, widescreen), PINE telemetry, `.pck`/vehicle/city/collision format docs. Use it as a **reference and bootstrap**. Its injector stays the loader until our Rust loader replaces it. Mind GPL-3 if code is ported. |
| Hidden Palace MC3 Oct 2004 prototype | Debug symbols. Use your own copy only if you legitimately have it. Otherwise rely on the znx symbol tables. |
| forum.mattkc.com (Reburn 3) | Burnout 3 RE knowledge and documented offsets. |
| PCSX2-Burnout mods / CodeBreaker codes | Known RAM addresses (boost, crash $, etc.) as Ghidra starting points. |
| PCSX2 2.x built-in debugger | Breakpoints, memory view, and loading symbol files (`Debugger/Analysis/ExtraSymbolFiles`). We feed it our generated symbol files. |
| Ghidra + `ghidra-emotionengine-reloaded` | The R5900 decompiler for both ELFs. |
| trevaintdead passthrough guide | Build order from small to large. Agent iteration driven by logs. |

---

## Rust workspace design (the "decomp in Rust")
```
GameMerge/
  Cargo.toml                 workspace
  rust-toolchain.toml        pinned nightly (build-std for MIPS)
  crates/
    gm-protocol/   no_std  #[repr(C)] HostFrame / GuestEvents / HostCommands + layout asserts
                           (single source of truth, like skycraft_protocol.h)
    gm-pine/       std     PINE client (unix socket, batched read/write, typed reads)
    mc3-sys/       no_std  MC3 memory model: #[repr(C)] structs (Vehicle, Physics, Camera, TrafficMgr…),
                           per-serial address table, extern fn signatures of game functions
    b3-sys/        no_std  same for Burnout 3 (Car, BoostState, TakedownEvent, CrashJunction…)
    gm-core/       no_std  RUST REWRITE of Burnout systems from the Phase 2 specs:
                           takedown classifier, boost economy, crash state machine, aftertouch,
                           Road Rage + Crash mode rules, crash $ scoring
    gm-bridge/     bin     host↔guest loop over two PINE connections; also runs gm-core in
                           "shadow" mode for differential testing against real Burnout
    gm-hostmod/    no_std  code injected into MC3 (MIPS EE target): mailbox, impulses,
                           time scale, camera, HUD, input; later links gm-core directly
    gm-guestpatch/ no_std  small Burnout patches: null-render-friendly, AI/timers off, puppet slots
    gm-tools/      bins    ghidra symbol import/export, address-table validator, ISO/ELF extract,
                           savestate scenario runner, fake_host / fake_guest simulators
  xtask/                   `cargo xtask build-mod | inject | launch | test-scenarios`
  docs/{mc3,b3}/           reverse-engineering specs (inputs → state → outputs, constants, timings)
  symbols/                 mc3_slus21355.tsv, b3_slus21050.tsv (names only; publishable)
  .gitignore               ISOs, ELFs, extracted assets, savestates, BIOS
```
**Rust-on-PS2 is the main technical unknown.** The EE is a MIPS R5900, and its quirks matter: no LL/SC, nonstandard 128-bit and multimedia ops, an EABI calling convention.
- Phase 0 includes a **spike**: a `no_std` crate built with a custom target JSON (mipsel, conservative MIPS-II/III instruction set, soft or hard float matching the EE's single-precision FPU) and `-Zbuild-std=core`. It is linked at a fixed address inside a code cave, and it calls one MC3 function through an `extern "C"` declaration.
- **Fallback if the spike fails:** keep a ~100-line C/asm shim (ps2dev toolchain via Docker) for the ABI boundary only. All logic stays in Rust.
- Until `gm-hostmod` exists, the bridge can do work purely by PINE writes, which is enough for M1–M4.

---

## Phase 0: Setup (week 1)
1. **Legal hygiene:** use only discs and BIOS you own and dumped yourself. Never commit ISOs, BIOS, ELFs, extracted assets or decompiled game code. Publish Rust code, symbol names, docs and patches only.
2. Dump the BIOS from your PS2 console into `…/PCSX2/bios/`. Boot both ISOs once to confirm they run.
3. Enable PINE. Create **two PCSX2 config profiles**:
   - MC3: slot 28011, normal renderer.
   - Burnout: slot 28012, **Null renderer, muted audio**. This is the "hidden guest".
   - Launch them through `xtask launch` using separate portable data dirs, so the settings don't collide.
4. `git init`. Update Rust, pin the nightly, and scaffold the workspace above.
5. Extract `SLUS_213.55` and `SLUS_210.50` from the ISOs (`gm-tools iso-extract`). Record hashes in `docs/builds.md`.
6. Clone mc3-znx-tools beside the repo (not vendored) as a reference.
7. **Spike:** build Rust for the PS2 target, inject it, and write a magic word to RAM. Check it in the PCSX2 debugger.

## Phase 1: Reverse engineer MC3 (targeted) + Rust bindings (weeks 2–5)
1. Import the MC3 ELF into Ghidra. Write a `gm-tools ghidra-import` script that applies the znx symbol layers, then auto-analyze.
2. Reverse and document the following in `docs/mc3/`, and mirror each one as `#[repr(C)]` structs plus an address table in `mc3-sys`:
   - **Vehicle struct:** position, orientation, linear/angular velocity, speed, nitro, damage, player/AI/traffic kind.
   - **Physics step:** the per-frame entry point and the impulse/force application function.
   - **Collision callbacks:** car-car, car-world, car-traffic. We need the contact point, normal, relative velocity and the other body.
   - **Opponent/traffic manager:** the active list, plus spawn and despawn.
   - **Camera:** modes and how to take over. Reference the znx freecam.
   - **Global time scale / main-loop `dt`:** for slow-mo.
   - **HUD/Flash UI:** for the boost bar, popups and the $ counter. Reference the znx HUD mod.
   - **Race/mode state machine** and **pad input**.
3. Use `gm-pine` plus `mc3-sys` for live validation. `cargo run -p gm-tools -- mc3-watch` prints every car's state at 60 Hz and logs collisions.
4. Every struct in `mc3-sys` gets a compile-time `size_of`/`offset_of` assertion and a runtime signature check against the live game. That check is the decomp's "test suite".

**Exit:** `mc3-watch` shows correct live data, and the collisions are logged with their impulses.

## Phase 2: Reverse engineer Burnout 3 + specs (weeks 3–8, overlaps Phase 1)
1. Anchors: CodeBreaker/pnach addresses, Reburn forum offsets, and strings such as "TAKEDOWN", "AFTERTOUCH", "CRASHBREAKER" and "IMPACT TIME", plus HUD message IDs. Follow cross-references outward in Ghidra.
2. Spec each system in `docs/b3/` as **inputs → state → outputs, with exact constants**:
   - **Takedown detection and types:** Slam, Grind, Shunt, Wall/Traffic Check, Psyche-out, Signature, Aftertouch, Revenge.
   - **Boost economy:** drafting, near miss, oncoming, drift, air, takedowns, bar extensions.
   - **Crash state machine** with Impact Time slow-mo and takedown cam timings and parameters.
   - **Aftertouch:** force and duration.
   - **Crash mode:** junction setup, traffic waves, damage-$ formula, multipliers/pickups, Crashbreaker threshold, radius and impulse.
   - **Road Rage rules** and **rivals/revenge**.
3. Mirror the memory layouts in `b3-sys`. `gm-tools b3-watch` live-verifies the boost bar, last takedown type and crash $ while you play Burnout normally.

**Exit:** a spec plus verified addresses for every system. These specs are the input for `gm-core`.

## Phase 3: Passthrough architecture (week 6)
```
 PCSX2 #1 (visible)  MC3 + gm-hostmod            PCSX2 #2 (Null GS, muted)  Burnout 3 + gm-guestpatch
   mailbox @ fixed RAM addr                         puppet car slots, AI/timers suppressed
   applies impulses/slow-mo/cam/HUD                 takedown/boost/score logic runs for real
          ▲ PINE 28011                                        ▲ PINE 28012
          └────────────────── gm-bridge (Rust, macOS) ────────┘
     read HostFrame → write puppets → read GuestEvents → write HostCommands
     (+ gm-core shadow: compute the same events in Rust and diff against Burnout's)
```
- **`gm-protocol`:**
  - `HostFrame`: frame number, a car table of up to 16 entries, this frame's contacts, pad input.
  - `GuestEvents`: takedowns {attacker, victim, type}, boost, slow-mo/camera requests, crash $, pickups, Crashbreaker.
  - `HostCommands`: impulses, time scale, camera override, HUD values, sequence number.
- **Who owns what:**
  - MC3 owns the world, rendering, car models, base physics and traffic/AI pathing.
  - Burnout owns takedown rules, boost, scoring, slow-mo/camera decisions and mode rules.
- **Puppets:** MC3 car states are written into Burnout's car slots every frame. Burnout's world geometry ≠ MC3's city, so world-dependent events (wall takedowns, traffic checks) are classified from MC3 collision callbacks and fed into Burnout's scoring path as synthetic events. This mirrors SkyCraft feeding host collision into the guest.
- **Sync:** MC3 is authoritative. One bridge tick per MC3 frame, batched PINE calls, one frame of event latency tolerated. Teleporting puppets every frame makes emulator speed drift harmless.
- **The Rust rewrite path is built in:** `gm-core` runs in **shadow mode** from day one, and the bridge logs any disagreement with real Burnout. When a system's diff is zero across the scenario suite, that system is "decompiled": its Rust version is trusted and the guest is no longer needed for it.

## Phase 4: Milestones (weeks 7–16). Each ends with a clip, a bridge log and a passing scenario.
1. **M1 Hello host:** the injected Rust writes a magic value into the mailbox, and the bridge reads it.
2. **M2 Hello guest:** Burnout runs hidden, and the bridge reads its boost bar.
3. **M3 Mirror:** the MC3 player's transform drives Burnout's player slot. Verify by briefly enabling Burnout rendering.
4. **M4 Boost:** boost is earned from MC3 driving, shown in the MC3 HUD, and applied as nitro or force.
5. **M5 Takedown detection:** ramming an MC3 opponent produces the correct takedown type in the log. Shadow `gm-core` agrees.
6. **M6 Takedown feel:** the victim gets an impulse, then Impact Time slow-mo, the takedown cam, a "TAKEDOWN!" popup, and a respawn.
7. **M7 Player crash + aftertouch:** wreck steering in slow-mo, and aftertouch takedowns are scored.
8. **M8 Road Rage mode:** a mode state machine in `gm-hostmod`/`gm-core` with a target, a timer and results.
9. **M9 Crash mode ("insurance boom"):** chosen MC3 intersections, scripted traffic waves through the MC3 traffic manager, pickup trigger volumes, damage $ from impulses using Burnout's formula, and a Crashbreaker radial blast. Show the $ HUD.
10. **M10 Polish:** takedown cam variety, rivals/revenge, a signature subset, audio from MC3 banks, an options toggle.

**Stretch:** visual deformation on MC3 car meshes, done natively by vertex offset at render time. It is not on the critical path.

## Phase 5: Testing (continuous)
- `cargo test` runs:
  - `gm-protocol` layout asserts
  - `gm-core` unit tests built from the spec constants
  - a bridge loop driven by `fake_host`/`fake_guest`, with no emulators
- `cargo xtask test-scenarios` runs savestate fixtures plus scripted pad input against both emulators. For example, "ram opponent at 120 km/h at 30°" must produce `TAKEDOWN type=SLAM` from both Burnout and `gm-core`.
- The address-table validator runs at bridge startup and aborts clearly if a build doesn't match.
- Performance budget: bridge tick under 2 ms, no MC3 frame drops with two PCSX2 instances on Apple Silicon.

## Phase 6: Graduate, where the Rust rewrite replaces the guest
- Once a system's shadow diff is zero, `gm-hostmod` links that part of `gm-core` directly and the bridge stops asking Burnout.
- When every system has moved over, drop the second emulator. The result is **MC3 + a Rust reimplementation of Burnout 3's gameplay systems**, a single-game mod.
- Optional later: retarget `gm-core` and `mc3-sys` toward a PS2Recomp-based native PC build when that project matures.

## Phase 7: Release
- Public repo with Rust code, protocol, symbol names and docs only. Users supply their own ISOs and BIOS.
- `cargo xtask launch` is the one-click launcher: two PCSX2 profiles, inject, guest patches, bridge.
- README covering supported serials and hashes, plus a showcase video.

## Key risks
| Risk | Mitigation |
|---|---|
| Rust can't target the R5900 cleanly | Phase 0 spike. Thin C/asm shim fallback. PINE-only work covers early milestones. |
| Burnout takedown logic tied to its own world | Guest handles car-vs-car only. World events come from MC3 collisions. Native `gm-core` fallback. |
| PINE throughput at 60 Hz | Batched calls, a compact mailbox, one frame of latency tolerated. |
| Two emulators on one Mac (Rosetta?) | Null renderer for the guest. Measure early in M2. Graduating (Phase 6) removes the guest anyway. |
| Scope creep | M1–M9 is the target. Deformation and full signature takedowns are stretch. |

## Verification (end to end)
1. `cargo test` passes (layouts, gm-core, fake bridge).
2. `cargo xtask launch`: MC3 is visible and Burnout is hidden, and both PINE ports show as connected in the bridge log.
3. Free-roam: near misses and drifting fill the boost bar in the MC3 HUD, and boost works.
4. Ram an opponent: popup, slow-mo, takedown cam, respawn. The log has the correct type, and the shadow diff is 0.
5. Crash the player: aftertouch steers the wreck and can score a takedown.
6. Road Rage and Crash mode play through to their results screens with correct scoring, pickups and Crashbreaker.
7. `cargo xtask test-scenarios` passes. After Phase 6, the same scenarios pass with the guest emulator disabled.
