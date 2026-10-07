# Roadmap: GameMerge, Burnout 3's gameplay inside Midnight Club 3

This file is the single source of truth for GameMerge's plan and status. The two games' own progress lives in their
repos, and this file links to their milestones instead of copying them.

## Status

> **Done:** the split into three repos · **Currently:** waiting on the game repos (see [Dependencies](#dependencies))
> · **Next:** S1, protocol and rules design, which needs nothing from the game repos

| Track | Milestone | State | Updated | Notes |
|---|---|---|---|---|
| Shared | S1 Protocol and rules design | not started | | Can start any time |
| A: PCSX2 as linker | A0–A3 Setup and plumbing | not started | | Gated on both decomps (see [Dependencies](#dependencies)) |
| A: PCSX2 as linker | F1–F7 Features | not started | | |
| B: Native Rust | N0–N3 Setup and plumbing | not started | | Gated on both Rust rewrites |
| B: Native Rust | F1–F7 Features | not started | | |

### Upstream
A snapshot, for orientation only. Each repo's own `ROADMAP.md` is authoritative.

| Repo | Role | State (2026-10-07) |
|---|---|---|
| [Burnout3](https://github.com/siddharthakumar-98/Burnout3) | Guest game: decomp, then Rust rewrite | D0–D3 done (byte-identical build, CodeWarrior compiler, binary mapped). D4 core infrastructure in progress. |
| [MC3DER](https://github.com/siddharthakumar-98/MC3DER) | Host game: decomp, then Rust rewrite | D0 environment in progress: disc and ELF hashes and sections recorded, compiler not yet identified |

## The goal

Midnight Club 3: DUB Edition Remix is the **host**: its city, cars, rendering, driving physics, traffic and controls
stay. Burnout 3: Takedown is the **guest**: it supplies the gameplay rules for takedowns, boost, Impact Time slow-mo,
the takedown cam, aftertouch, Road Rage and Crash mode. All cars come from Midnight Club 3.

The idea comes from "game merging" (passthrough modding): chasm's
[SkyCraft](https://github.com/chasmlol/SkyCraft) and the video
[*The Next Generation of Modding*](https://youtu.be/zRT3MyFwgu0). The lessons it gives:
- The host draws everything. The guest runs hidden and owns its game logic.
- The two talk through one protocol definition. Collisions flow from host to guest, and gameplay results flow back.
- Neither game has a script extender. **The decomps replace one:** every address, struct and function signature comes
  from matched source.

## Two tracks, one destination

| | Track A: PCSX2 as linker | Track B: native Rust |
|---|---|---|
| Runs | Both original games in two PCSX2 instances, linked by a Rust bridge over PINE | Both Rust rewrites as libraries in one native app |
| Needs | Both **decomps** (symbols, structs, signatures) | Both **Rust rewrites** (`burnout3-core`, `mc3-core`) |
| Available | Earlier | Later |
| Fidelity | Exact, because the original code runs | Exact once each rewrite is verified against its decomp |
| Hard parts | Injecting code into MC3, Rust on the R5900, PINE throughput, two emulators on one Mac | Both cores' public APIs, a shared renderer |

**They aren't rivals.** Track A's last step ("graduation") replaces the hidden Burnout emulator with Burnout's Rust
core. Doing the same for Midnight Club is Track B. So the work runs:

```
Track A (two emulators) → hybrid (MC3 in PCSX2 + burnout3-core native in the bridge) → Track B (fully native)
```

The parts that carry across all three stages are the **protocol** (`gm-protocol`) and the **rules for mapping one
game onto the other** (`gm-rules`: puppets, event classification, ownership). Only the plumbing (PINE, code
injection, guest patches) is specific to Track A.

**Decision point:** when both decomps pass their Phase 1 gates, decide whether to build Track A or wait for Track B.
Inputs: how far away the Rust rewrites are, and whether the A0 spike shows Rust on the R5900 is workable. Record the
decision here.

## Dependencies

GameMerge depends on the game repos at **tagged** milestones and never on their `main` branches. The game repos never
depend on GameMerge. Each game repo lists the same needs in its "What other projects need from this repo" section.

| Needed | From | Unblocks |
|---|---|---|
| Burnout 3 gameplay-rule symbols, structs and signatures (boost, takedowns, crash state, Impact Time) | Burnout3 D7 | Track A |
| Burnout 3 car slots and race/mode state machine | Burnout3 D6, D8 | Track A |
| MC3 main loop, time step and game state | MC3DER D5 | Track A |
| MC3 vehicle struct, car table and collision callbacks | MC3DER D6 | Track A |
| MC3 race and mode state machine | MC3DER D7 | Track A |
| MC3 opponent and traffic managers, cameras | MC3DER D9 | Track A |
| MC3 HUD and pad input | MC3DER D10 | Track A |
| `burnout3-core` with the step API and puppet cars | Burnout3 R3 | Hybrid stage, Track B |
| Crash mode in `burnout3-core` | Burnout3 R4 | Track B (F6) |
| `mc3-core` with the step API, puppet vehicles, host hooks (impulses, time scale, camera override) and a drivable car | MC3DER R2 | Track B |
| Traffic and opponents in `mc3-core` | MC3DER R3 | Track B |
| Shared `platform` crate (renderer, audio, input, disc file system) | Its own repo, once both games' Rust work uses it | Track B |

**How they're consumed:**
- Track A: the game repos as git submodules in `external/`, pinned to tags. `cargo xtask gen-sys` generates the
  `b3-sys` and `mc3-sys` memory models from their headers and `config/symbol_addrs.txt`.
- Track B: Cargo git dependencies pinned to `core-v*` tags.
- Gaps in a game repo's API or symbols are raised as issues in that repo, never patched from here.

---

## Shared work (any time)

### S1: Protocol and rules
- **`gm-protocol`** (`no_std`, `#[repr(C)]`, layout asserts):
  - `HostFrame`: frame number, a car table of up to 16 entries, contacts, pad input.
  - `GuestEvents`: takedowns {attacker, victim, type}, boost, slow-mo/camera requests, crash $, pickups, Crashbreaker.
  - `HostCommands`: impulses, time scale, camera override, HUD values, sequence number.
- **`gm-rules`**: which game owns what, how host vehicles become guest puppets, and how world-dependent events (wall
  takedowns, traffic checks) are classified from host collisions and fed into the guest's scoring as synthetic events.
- **Ownership:** MC3 owns the world, rendering, vehicle models, base physics and traffic/AI pathing. Burnout owns
  takedown rules, boost, scoring, slow-mo/camera decisions and mode rules. MC3 is authoritative, and one frame of
  latency is tolerated.
- **Open question:** MC3 has motorcycles, Burnout 3 has none. Whether bikes take part in takedowns, and as what kind
  of Burnout vehicle, is decided in S1.

S1 is a design document plus the two crates with tests. It needs nothing from the game repos except the feature list.

---

## Feature milestones (both tracks)

Both tracks deliver the same features, so they're defined once. Each ends with a clip, a log and a passing scenario.

| ID | Feature |
|---|---|
| F1 | **Boost:** earned from MC3 driving (drafting, near misses, oncoming, drifts, air), shown in the MC3 HUD, applied as nitro or force |
| F2 | **Takedown detection:** ramming an MC3 opponent produces the correct takedown type (Slam, Grind, Shunt, Wall, Traffic Check) |
| F3 | **Takedown feel:** victim impulse, Impact Time slow-mo, takedown cam, a "TAKEDOWN!" popup and a respawn |
| F4 | **Player crash and aftertouch:** wreck steering in slow-mo, and aftertouch takedowns are scored |
| F5 | **Road Rage:** a mode state machine with a target, a timer and results |
| F6 | **Crash mode:** chosen MC3 intersections, scripted traffic waves, pickup trigger volumes, damage $ using Burnout's formula, a Crashbreaker radial blast, and a $ HUD |
| F7 | **Polish:** takedown cam variety, rivals and revenge takedowns, audio from MC3 banks, an options toggle |

**Stretch:** visual deformation on MC3 car meshes by vertex offset at render time.

---

## Track A: PCSX2 as linker

**Starts when:** both decomps pass their Phase 1 gates (the project rule is decomps first). Optionally, the A0 spike
can run earlier to reduce risk, since it needs no symbols.

### Architecture
```
 PCSX2 #1 (visible)  MC3 + gm-hostmod            PCSX2 #2 (Null GS, muted)  Burnout 3 + gm-guestpatch
   mailbox @ fixed RAM addr                         puppet car slots, AI/timers suppressed
   applies impulses/slow-mo/cam/HUD                 takedown/boost/score logic runs for real
          ▲ PINE 28011                                        ▲ PINE 28012
          └────────────────── gm-bridge (Rust, macOS) ────────┘
     read HostFrame → write puppets → read GuestEvents → write HostCommands
     (+ burnout3-core shadow, once available: compute the same events natively and diff against Burnout's)
```
- **Puppets:** MC3 vehicle states are written into Burnout's car slots every frame.
- **Sync:** one bridge tick per MC3 frame, batched PINE calls.
- **Shadow mode:** once `burnout3-core` exists, the bridge runs it alongside the real game and logs any disagreement.

### Crates
```
crates/
  gm-protocol/   no_std  shared (S1)
  gm-rules/      no_std  shared (S1)
  gm-pine/       std     PINE client (unix socket, batched read/write, typed reads)
  b3-sys/        no_std  Burnout 3 memory model, generated from external/Burnout3
  mc3-sys/       no_std  MC3 memory model, generated from external/MC3DER
  gm-bridge/     bin     host↔guest loop over two PINE connections
  gm-hostmod/    no_std  code injected into MC3 (R5900 target): mailbox, impulses, time scale, camera, HUD, input
  gm-guestpatch/ no_std  Burnout patches: null-render-friendly, AI/timers off, puppet slots
  gm-tools/      bins    address-table validator, savestate scenario runner, fake_host / fake_guest
xtask/                   cargo xtask gen-sys | build-mod | inject | launch | test-scenarios
```

### Milestones
| ID | Milestone |
|---|---|
| A0 | **R5900 spike:** a `no_std` Rust crate with a custom mipsel target and `-Zbuild-std=core`, linked at a fixed address in a code cave, calls one MC3 function through `extern "C"`. Fallback: a ~100-line C/asm shim built with the decomp toolchain. |
| A1 | **Setup:** PINE enabled, two PCSX2 profiles (MC3 on slot 28011 with the normal renderer; Burnout on 28012 with the Null renderer and muted audio), launched by `xtask launch` with separate data dirs. `b3-sys`/`mc3-sys` generated. |
| A2 | **Hello host:** injected Rust writes a magic value into the mailbox, and the bridge reads it. **Hello guest:** Burnout runs hidden, and the bridge reads its boost bar. |
| A3 | **Mirror:** the MC3 player's transform drives Burnout's player slot. Verified by briefly enabling Burnout's rendering. |
| F1–F7 | Features, as defined above |
| A-grad | **Graduation:** once a system's shadow diff is zero, the bridge uses `burnout3-core` for it instead of the hidden game. When every system has moved, the second emulator is dropped. This is the hybrid stage. |

Until `gm-hostmod` exists, PINE writes alone cover A2–A3 and F1.

### Testing
- `cargo test`: `gm-protocol` layout asserts, `gm-rules` unit tests, a bridge loop driven by `fake_host`/`fake_guest`.
- `cargo xtask test-scenarios`: savestate fixtures plus scripted pad input against both emulators. For example, "ram an
  opponent at 120 km/h at 30°" must produce `TAKEDOWN type=SLAM`.
- The address-table validator runs at bridge startup and aborts clearly on a build mismatch.
- Performance budget: bridge tick under 2 ms, and no MC3 frame drops with two PCSX2 instances on Apple Silicon.

### Risks
| Risk | Mitigation |
|---|---|
| Rust can't target the R5900 cleanly | A0 spike, thin C/asm shim fallback. PINE-only work covers A2–A3 and F1. |
| Burnout's takedown logic is tied to its own world | The guest handles car-vs-car only. World events come from MC3 collisions through `gm-rules`. |
| PINE throughput at 60 Hz | Batched calls, a compact mailbox, one frame of latency tolerated |
| Two emulators on one Mac | Null renderer for the guest, measured in A2. Graduation removes the guest anyway. |
| MC3's compiler is still unknown | Track A only needs MC3's symbols and structs, not matched C, but those come from its decomp, which can't pass D2 until the compiler is identified |
| Scope creep | F1–F6 is the target. F7 and deformation are stretch. |

---

## Track B: native Rust

**Starts when:** Burnout3 R3 and MC3DER R2 are tagged. Feature work beyond F3 needs Burnout3 R4 and MC3DER R3.

### Architecture
```
                       gamemerge (one native process)
 ┌──────────────────────────────────────────────────────────────────────┐
 │  mc3-core (host World)                    burnout3-core (guest World) │
 │    step(input + HostCommands) ──HostFrame──► step(puppets)            │
 │          ▲                                        │                   │
 │          └──────── HostCommands ◄── gm-rules ◄── GuestEvents          │
 │                                                                      │
 │  platform (shared): renders MC3's draw output + GameMerge HUD,       │
 │  plays audio, reads input, streams assets from both of your discs    │
 └──────────────────────────────────────────────────────────────────────┘
```
- Same protocol and rules as Track A, but function calls replace PINE and code injection.
- Only the host is rendered. The guest core runs headless.
- Deterministic: both cores step in lockstep, so a recorded input reproduces a session exactly.

### Crates
```
crates/
  gm-protocol/  gm-rules/   shared (S1)
  gm-native/    bin   the merged app: owns both Worlds, runs the frame loop, draws through `platform`
  gm-replay/    lib   input recording and deterministic replay for tests
```
External: `burnout3-core`, `mc3-core` and `platform`, pinned to tags.

### Milestones
| ID | Milestone |
|---|---|
| N0 | **API check:** confirm both cores expose what this track needs (Burnout: step API, puppet cars, events as data; MC3: step API, puppet vehicles, host hooks). Gaps are filed as issues in the game repos, not patched here. |
| N1 | **Two cores, one process:** both Worlds step headless in one binary, loading assets from both discs, deterministically |
| N2 | **Host app:** MC3 is drivable in `gm-native` through `platform`, with GameMerge's HUD layer on top |
| N3 | **Mirror:** MC3 vehicles drive Burnout puppets. A debug view shows Burnout's world. |
| F1–F7 | Features, as defined above |
| N-rel | **Release:** a single native app. Users supply both discs. |

### Testing
- Everything from Track A's `cargo test` (shared crates).
- Replay tests: recorded input sessions must reproduce the same `GuestEvents` stream exactly.
- If Track A ran first: its scenario suite is replayed here, and the events must match what the emulated games produced.

### Risks
| Risk | Mitigation |
|---|---|
| The cores' APIs don't fit merging | The API rules are written into both game roadmaps ("Crate boundaries"). N0 checks them. |
| Two games, one renderer | A shared `platform` crate from the start. Only the host draws. |
| MC3 streams its city continuously | `mc3-core` emits streaming requests as outputs, so the merged step stays deterministic (a rule in MC3DER's roadmap) |
| Long wait for the rewrites | The hybrid stage of Track A delivers native Burnout logic earlier |

---

## Supported builds

| Game | Region | Serial | ELF SHA-1 |
|---|---|---|---|
| Midnight Club 3: DUB Edition Remix | NTSC-U | SLUS-21355 | `c09bdbec05cf27f1d3ed2267c437b98be8c7b26f` |
| Burnout 3: Takedown | NTSC-U | SLUS-21050 | `332be40d6081b8b5055a6ea01194ad6ff662a863` |

Memory addresses differ between regions and revisions. Other builds are not supported.

## History

Until 2026-10-06 this repo also held the Burnout 3 decomp and Rust rewrite (D0–D3, commits up to `b5044e0`, moved
under `Burnout3/` in `aac605f`) and the first MC3 Rust workspace (`MC3DER_rust/`). Both now live in their own repos,
[Burnout3](https://github.com/siddharthakumar-98/Burnout3) and [MC3DER](https://github.com/siddharthakumar-98/MC3DER),
which started with fresh histories; their earlier history stays here. The original passthrough plan (Stage C,
milestones M1–M10, now Track A) is in commit `a53cf40`.
