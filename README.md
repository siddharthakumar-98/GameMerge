# GameMerge

**Burnout 3: Takedown's gameplay inside Midnight Club 3: DUB Edition Remix.** Takedowns, boost, Impact Time,
aftertouch, Road Rage and Crash mode, in Midnight Club's city with Midnight Club's cars.

> Full plan and progress: **[ROADMAP.md](ROADMAP.md)**

## Status

> **Approach:** a **PCSX2 bridge**. Both original games run in PCSX2 and talk through its PINE interface. The Rust
> rewrite of the two games, and the native app that would have run them, are **shelved**
> ([why and what's kept](ROADMAP.md#shelved-the-rust-rewrite-and-the-native-track)).
>
> **Currently:** nothing built yet. **Next:** B0, two PCSX2 instances and a PINE client. Plumbing starts now; each
> gameplay feature waits only for the decomp milestones it needs ([gates](ROADMAP.md#feature-gates)).

| Project | What it provides | Status |
|---|---|---|
| [Burnout3](https://github.com/siddharthakumar-98/Burnout3) | Byte-matching decomp of the guest game: its symbols, structs and, later, its gameplay rules as C | Decomp in progress (D4) |
| [MC3DER](https://github.com/siddharthakumar-98/MC3DER) | Byte-matching decomp of the host game: its symbols and structs | Decomp starting (D0) |

## How it works

Midnight Club 3 is the **host**: its city, cars, rendering, physics and controls stay. Burnout 3 is the **guest**: it
runs hidden and supplies the gameplay rules.

```
 PCSX2 #1 (visible)                         PCSX2 #2 (hidden, null renderer)
 Midnight Club 3 + injected host mod        Burnout 3 + injected guest patch
   world, cars, physics, rendering            takedown rules, boost, scoring, modes
          ▲ PINE                                        ▲ PINE
          └──────────────── gm-bridge (Rust) ───────────┘
   MC3 car states → Burnout puppet cars → Burnout events → MC3 impulses / slow-mo / camera / HUD
```

- **Injected code** on each side is C, built with the ps2dev toolchain and loaded through PCSX2 patches. It publishes
  a small mailbox in game RAM every frame.
- **The bridge** runs on your computer, reads and writes both mailboxes over PINE once per Midnight Club frame, and
  maps one game onto the other: Midnight Club's cars become Burnout's puppet cars, and Burnout's takedowns, boost and
  slow-mo come back as commands for Midnight Club.
- **Addresses** start out hand-found and provisional, and are replaced by names from the decomps as those reach the
  matching milestones.

**End state:** as Burnout 3's gameplay rules become matched C in its decomp, they are compiled into the Midnight Club
host mod one system at a time, checked against the hidden Burnout game until they agree, and the second emulator is
finally dropped: one PCSX2 running Midnight Club with Burnout's rules inside it.

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

- Your own dumps of both games, and a PS2 BIOS dumped from your own console
- [PCSX2](https://pcsx2.net) 2.x with PINE enabled, able to run two instances at once
- Rust, for the bridge
- Docker, for the ps2dev toolchain that builds the injected code

## Repository layout

Planned. Nothing is built yet.

| Path | What it is |
|---|---|
| `bridge/` | Rust workspace: `gm-protocol`, `gm-rules`, `gm-pine`, `gm-bridge`, `gm-tools`, `xtask` |
| `payload/` | C for the PS2 side: the MC3 host mod, the Burnout 3 guest patch, the shared protocol header |
| `addresses/` | `mc3.toml` and `b3.toml`: every address with its source, provisional or verified |
| `external/` | The two game repos as submodules pinned to tags |

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
- [mc3-znx-tools](https://github.com/znxee/mc3-znx-tools): MC3 symbols, formats, mod-building and PINE telemetry
  research
- The [Reburn 3](https://forum.mattkc.com/) community: Burnout 3 reverse engineering
- [PCSX2](https://github.com/PCSX2/pcsx2) and its PINE IPC
- The [ps2dev](https://github.com/ps2dev) toolchain

## License

GPL-3.0. See [LICENSE](LICENSE).
