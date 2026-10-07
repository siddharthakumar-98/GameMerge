# GameMerge

**Burnout 3: Takedown's gameplay inside Midnight Club 3: DUB Edition Remix.** Takedowns, boost, Impact Time,
aftertouch, Road Rage and Crash mode, in Midnight Club's city with Midnight Club's cars.

> Full plan and progress: **[ROADMAP.md](ROADMAP.md)**

## Status

> **Currently:** waiting on the two game projects below. GameMerge builds on their decomps and Rust rewrites, so its
> own work starts as they reach the milestones listed in [ROADMAP.md](ROADMAP.md#dependencies).

| Project | What it provides | Status |
|---|---|---|
| [Burnout3](https://github.com/siddharthakumar-98/Burnout3) | Byte-matching decomp, then Rust rewrite, of the guest game | Decomp in progress (D4) |
| [MC3DER](https://github.com/siddharthakumar-98/MC3DER) | Byte-matching decomp, then Rust rewrite, of the host game | Decomp starting (D0) |

## How it works

Midnight Club 3 is the **host**: its city, cars, rendering, physics and controls stay. Burnout 3 is the **guest**: it
runs hidden and supplies the gameplay rules. One protocol carries vehicle states from the host to the guest and
gameplay events back. GameMerge gets there in two ways, which share that protocol and the rules for mapping one game
onto the other.

### Track A: PCSX2 as linker

The original games run in two PCSX2 instances. A Rust bridge links them over PCSX2's PINE interface, using the
addresses and structs the decomps recover.

```
 PCSX2 #1 (visible)                         PCSX2 #2 (hidden, null renderer)
 Midnight Club 3 + injected host mod        Burnout 3 + guest patches
   world, cars, physics, rendering            takedown rules, boost, scoring, modes
          ▲ PINE                                        ▲ PINE
          └──────────────── gm-bridge (Rust) ───────────┘
   MC3 car states → Burnout puppet cars → Burnout events → MC3 impulses / slow-mo / camera / HUD
```

It needs only the decomps, so it can arrive first. Its last step replaces the hidden Burnout instance with Burnout's
Rust core running inside the bridge.

### Track B: native Rust

Both Rust rewrites run as libraries in one native app. Midnight Club's core is the host world, Burnout's core runs
headless beside it, and a shared platform layer draws, plays audio and reads input. No emulator is involved, and
assets stream from your own discs.

```
 gamemerge (native)
   mc3-core ──HostFrame──► burnout3-core
      ▲                          │
      └── HostCommands ◄── GuestEvents
   platform: renderer, audio, input, disc file system
```

It needs both rewrites, so it arrives later. It's also where Track A ends up.

## Planned features

- [ ] Boost bar earned from driving (drafting, near misses, oncoming, drifts, air)
- [ ] Takedowns on Midnight Club opponents and traffic: Slam, Grind, Shunt, Wall and Traffic Check
- [ ] Impact Time slow-mo, takedown cam and "TAKEDOWN!" popups
- [ ] Aftertouch and aftertouch takedowns
- [ ] Road Rage mode
- [ ] Crash mode at Midnight Club intersections: damage $, multiplier pickups, Crashbreaker
- [ ] Rivals and revenge takedowns

## Supported builds

| Game | Region | Serial |
|---|---|---|
| Midnight Club 3: DUB Edition Remix | NTSC-U | SLUS-21355 |
| Burnout 3: Takedown | NTSC-U | SLUS-21050 |

Memory addresses differ between regions and revisions. Other builds are not supported.

## Requirements

- Your own dumps of both games
- Rust
- Track A: [PCSX2](https://pcsx2.net) 2.x with PINE enabled, and a PS2 BIOS dumped from your own console
- Building either game's decomp: see its repo

## Repository layout

Planned. Nothing is built yet.

| Path | What it is |
|---|---|
| `crates/gm-protocol`, `crates/gm-rules` | Shared by both tracks: the host↔guest protocol and the mapping rules |
| `crates/gm-pine`, `gm-bridge`, `gm-hostmod`, `gm-guestpatch`, `b3-sys`, `mc3-sys`, `gm-tools` | Track A |
| `crates/gm-native`, `gm-replay` | Track B |
| `external/` | The two game repos as submodules pinned to tags (Track A reads their headers and symbols) |
| `xtask/` | `cargo xtask gen-sys`, `launch`, `test-scenarios` and friends |

Until 2026-10-06 this repo also held the Burnout 3 decomp and the first MC3 Rust workspace; see
[ROADMAP.md](ROADMAP.md#history).

## Legal

This repo contains **no game executables, disassembly, assets, BIOS or disc images**, and never will. You need your
own legally obtained copies of both games and your own BIOS dump.

Midnight Club is a trademark of Take-Two Interactive / Rockstar Games. Burnout is a trademark of Electronic Arts. This
is an unofficial fan project with no affiliation to any of them.

## Credits

- chasm's [SkyCraft](https://github.com/chasmlol/SkyCraft) and the video
  [*The Next Generation of Modding*](https://youtu.be/zRT3MyFwgu0), for the passthrough architecture
- [mc3-znx-tools](https://github.com/znxee/mc3-znx-tools): MC3 symbols, formats and tooling research
- The [Reburn 3](https://forum.mattkc.com/) community: Burnout 3 reverse engineering
- [PCSX2](https://github.com/PCSX2/pcsx2) and its PINE IPC

## License

GPL-3.0. See [LICENSE](LICENSE).
