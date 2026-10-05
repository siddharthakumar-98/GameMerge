# GameMerge

**Burnout 3: Takedown's gameplay inside Midnight Club 3: DUB Edition Remix.**

GameMerge is a passthrough mod for PS2 games running in PCSX2. Midnight Club 3 is the host: its city, cars, rendering and controls stay. Burnout 3 runs hidden alongside it and supplies takedowns, boost, Impact Time slow-mo, the takedown cam, aftertouch, Road Rage and Crash mode. A Rust bridge passes data between the two games in real time. Each Burnout system is also being reverse engineered and rewritten in Rust, so the mod can eventually run with no second game at all.

> **Status:** early planning / reverse-engineering. Nothing is playable yet. See [ROADMAP.md](ROADMAP.md).

## How it works

```
 PCSX2 #1 (visible)                         PCSX2 #2 (hidden, null renderer)
 Midnight Club 3 + injected host mod        Burnout 3 + guest patches
   world, cars, physics, rendering            takedown rules, boost, scoring, modes
          ▲ PINE                                        ▲ PINE
          └──────────────── gm-bridge (Rust) ───────────┘
   MC3 car states → Burnout puppet cars → Burnout events → MC3 impulses / slow-mo / camera / HUD
```

- **Host (Midnight Club 3)** owns the world, car models, base driving physics, traffic and AI.
- **Guest (Burnout 3)** owns the gameplay rules: what counts as a takedown, how boost is earned, how crashes score.
- **gm-bridge** reads both games' memory over PCSX2's PINE IPC every frame. It mirrors Midnight Club cars into Burnout and sends Burnout's events back.
- **gm-core** is a Rust reimplementation of the Burnout systems. It runs in shadow mode against the real game until the two agree, then takes over.

Inspired by chasm's [SkyCraft](https://github.com/chasmlol/SkyCraft) and the video [*The Next Generation of Modding*](https://youtu.be/zRT3MyFwgu0).

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

- [PCSX2](https://pcsx2.net) 2.x with PINE enabled
- A PS2 BIOS dumped from your own console
- Your own dumps of both games
- Rust (pinned nightly, see `rust-toolchain.toml`)

## Repository layout (planned)

| Path | What it is |
|---|---|
| `crates/gm-protocol` | Shared `#[repr(C)]` data layout between host, guest and bridge |
| `crates/gm-pine` | PCSX2 PINE client |
| `crates/mc3-sys`, `crates/b3-sys` | Reverse-engineered memory layouts and addresses for each game |
| `crates/gm-core` | Rust rewrite of Burnout 3's gameplay systems |
| `crates/gm-bridge` | The passthrough bridge |
| `crates/gm-hostmod` | Code injected into Midnight Club 3 |
| `crates/gm-guestpatch` | Patches that run Burnout 3 headless as a guest |
| `crates/gm-tools` | Symbol import, address validation, test simulators |
| `docs/` | Reverse-engineering notes and system specs |

## Legal

This project contains **no game code, assets, BIOS or disc images**, and never will. You need your own legally obtained copies of both games and your own BIOS dump. Only original code, symbol names and documentation are published here.

Midnight Club is a trademark of Take-Two Interactive / Rockstar Games. Burnout is a trademark of Electronic Arts. This is an unofficial fan project with no affiliation to either.

## Credits

- [mc3-znx-tools](https://github.com/znxee/mc3-znx-tools): MC3 symbols, formats and tooling research
- The [Reburn 3](https://forum.mattkc.com/) community: Burnout 3 reverse engineering
- [PCSX2](https://github.com/PCSX2/pcsx2) and its PINE IPC
- chasm's [SkyCraft](https://github.com/chasmlol/SkyCraft) for the passthrough architecture
