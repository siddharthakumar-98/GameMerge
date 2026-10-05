# GameMerge

**Burnout 3: Takedown, decompiled and rewritten in Rust, on the way to merging it with Midnight Club 3.**

> Full plan and progress: **[ROADMAP.md](ROADMAP.md)**

## Status

> **Done:** Burnout 3 matching build (byte-identical, from assembly) · **Currently:** verifying it in PCSX2 and
> decompiling to C · **Next:** Rust rewrite of Burnout 3

## Plan

1. **Decompile Burnout 3** (active, in [`Burnout3_decomp/`](Burnout3_decomp/README.md)). This produces C/C++ that
   the original CodeWarrior compiler builds into a byte-identical `SLUS_210.50`. The build pipeline already reproduces
   the original exactly from assembly. Next come verifying it in PCSX2 and converting its 8,948 functions to C.
2. **Rewrite Burnout 3 in Rust** (next, in [`Burnout3_rust/`](Burnout3_rust/README.md)). A native port of the finished
   decomp that plays the same, loads assets from your own disc, and is verified against the decomp function by
   function and frame by frame.

Midnight Club 3: DUB Edition Remix gets the same two steps (decomp, then Rust rewrite) once its game files are
available. That work is coming soon.

## Long-term goal: GameMerge

Once both games are done, GameMerge brings Burnout 3's gameplay into Midnight Club 3 as a passthrough mod for PCSX2.
Midnight Club 3 is the host: its city, cars, rendering and controls stay. Burnout 3 runs hidden alongside it and
supplies takedowns, boost, Impact Time slow-mo, the takedown cam, aftertouch, Road Rage and Crash mode. A Rust bridge
passes data between the two games in real time.

### How it works

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

### Planned features

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

- [PCSX2](https://pcsx2.net) 2.x (PINE enabled for GameMerge)
- A PS2 BIOS dumped from your own console
- Your own dumps of both games (by default in `~/Desktop/ps2_games/`)
- For the decomps: Docker, Python 3, and the original compiler, which you supply (see [Burnout3_decomp](Burnout3_decomp/README.md))
- Rust

## Repository layout

| Path | What it is |
|---|---|
| `Burnout3_decomp/` | Burnout 3 matching decomp (C/C++, CodeWarrior), phase 1 |
| `Burnout3_rust/` | Burnout 3 Rust rewrite, phase 2, plus the ISO extractor |
| `MC3DER_rust/` | Midnight Club 3 Rust rewrite (future) |

## Legal

This project publishes **decompiled C/C++ source, headers, symbol names, build configs, original Rust code and documentation**. It contains **no game executables, disassembly, assets, BIOS, disc images or compilers**, and never will. The build tools regenerate everything else locally from your own copy, after checking its hash. You need your own legally obtained copies of both games, your own BIOS dump, and your own copy of each game's original compiler.

Midnight Club is a trademark of Take-Two Interactive / Rockstar Games. Burnout is a trademark of Electronic Arts. This is an unofficial fan project with no affiliation to either.

## Credits

- [mc3-znx-tools](https://github.com/znxee/mc3-znx-tools): MC3 symbols, formats and tooling research
- The [Reburn 3](https://forum.mattkc.com/) community: Burnout 3 reverse engineering
- [PCSX2](https://github.com/PCSX2/pcsx2) and its PINE IPC
- chasm's [SkyCraft](https://github.com/chasmlol/SkyCraft) for the passthrough architecture

---

See **[ROADMAP.md](ROADMAP.md)** for the full plan, milestones and testing.
