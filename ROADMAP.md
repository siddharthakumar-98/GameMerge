# Roadmap: GameMerge, Burnout 3's gameplay inside Midnight Club 3

This file is the single source of truth for GameMerge's plan and status. The two games' own progress lives in their
repos, and this file links to their milestones instead of copying them.

## Status

> **Decided (2026-10-07):** the Rust rewrite is **shelved**. GameMerge is built as a **PCSX2 bridge**: both original
> games run in PCSX2 and talk through PINE. Plumbing starts now; each feature waits only for the decomp milestones
> it needs. · **Currently:** nothing built yet · **Next:** B0, two emulators and a PINE client

| Milestone | State | Updated | Notes |
|---|---|---|---|
| B0 Two emulators + PINE | not started | | No game knowledge needed |
| B1 Protocol | not started | | No game knowledge needed |
| B2 Hello host (MC3) | not started | | Hand-found addresses allowed (provisional) |
| B3 Hello guest (Burnout 3) | not started | | Hand-found addresses allowed (provisional) |
| B4 Mirror | not started | | |
| F1–F7 Features | not started | | Each gated on specific decomp milestones ([gates](#feature-gates)) |
| T C transplant | not started | | Needs Burnout 3's gameplay rules as matched C |
| R Release | not started | | |

### Upstream
A snapshot, for orientation only. Each repo's own `ROADMAP.md` is authoritative, and GameMerge never edits them.

| Repo | Role | State (2026-10-07) |
|---|---|---|
| [Burnout3](https://github.com/siddharthakumar-98/Burnout3) | Guest game: matching decomp | D0–D3 done (byte-identical build, CodeWarrior compiler, binary mapped). D4 core infrastructure in progress. |
| [MC3DER](https://github.com/siddharthakumar-98/MC3DER) | Host game: matching decomp | D0 environment in progress: disc and ELF hashes and sections recorded, compiler not yet identified |

## The goal

Midnight Club 3: DUB Edition Remix is the **host**: its city, cars, rendering, driving physics, traffic and controls
stay. Burnout 3: Takedown is the **guest**: it supplies the gameplay rules for takedowns, boost, Impact Time slow-mo,
the takedown cam, aftertouch, Road Rage and Crash mode. All cars come from Midnight Club 3.

The idea comes from "game merging" (passthrough modding): chasm's
[SkyCraft](https://github.com/chasmlol/SkyCraft) and the video
[*The Next Generation of Modding*](https://youtu.be/zRT3MyFwgu0). The lessons it gives:
- The host draws everything. The guest runs hidden and owns its game logic.
- The two talk through one protocol definition. Collisions flow from host to guest, and gameplay results flow back.
- Neither game has a script extender. **The decomps replace one:** every address, struct and function signature
  ends up coming from matched source.

## How the PCSX2 bridge works

```
 PCSX2 #1 (visible, slot 28011)                PCSX2 #2 (hidden: null renderer, muted, slot 28012)
 Midnight Club 3 + host mod (C, injected)      Burnout 3 + guest patch (C, injected)
   writes HostFrame to its mailbox               puppet car slots, AI and timers off
   applies HostCommands: impulses,               takedown, boost and scoring logic runs for real,
   slow-mo, camera, HUD                          writes GuestEvents to its mailbox
            ▲ PINE ($TMPDIR/pcsx2.sock)                      ▲ PINE ($TMPDIR/pcsx2.sock.28012)
            └──────────────────── gm-bridge (Rust, on the Mac) ────────────────────┘
       read HostFrame → write puppets → read GuestEvents → write HostCommands, once per MC3 frame
```

**PINE** is PCSX2's built-in IPC server (`pcsx2/PINE.cpp`). What it offers and what it doesn't decide the design:
- It reads and writes guest memory 8, 16, 32 or 64 bits per command, and batches many commands in one message
  (up to about 650 KB). It can also save and load states and report the title, serial, CRC, version and run status.
- On macOS it listens on a Unix socket, `$TMPDIR/pcsx2.sock` for the default slot 28011 and `pcsx2.sock.<slot>` for
  any other, so two instances can be told apart.
- **It has no frame synchronisation.** Reads and writes run on PINE's own thread against RAM while the game runs, and
  there is no pause or frame-step command. So each side publishes a **mailbox** in its own RAM: a magic number, a
  version, a sequence word written before and after each update (a reader retries if they differ), the game's frame
  counter, then the payload. MC3 is authoritative, the bridge ticks once per MC3 frame, and one frame of latency is
  accepted.

**Injected code** is C (C++ where useful), built with the ps2dev toolchain (`mips64r5900el-ps2-elf-gcc`) and loaded
through PCSX2 `.pnach` patches. Prior art for MC3 exists: [mc3-znx-tools](https://github.com/znxee/mc3-znx-tools)
(GPL-3) builds C++ mods this way through its companion loader `mc3boot`, and its telemetry mod already publishes a
sequence-guarded mailbox (at `0x0061C990`, magic `MC3T`) that a PINE client reads. Burnout 3 has no such loader, so
its guest patch is ours from the start.

**Addresses** live in `addresses/mc3.toml` and `addresses/b3.toml`. Each entry records its type, its source (a game
repo tag, Ghidra, the PCSX2 debugger, CodeBreaker, mc3-znx-tools' symbols) and whether it is **provisional** or
**verified**. Verified means it comes from a tagged release of the game repo that owns it. The bridge checks the
running games' serials and CRCs at startup and refuses to attach to anything else.

## End state: the C transplant

The Rust rewrite used to be how Burnout's logic would leave its emulator. Its replacement fits the decomp-first plan:
once a Burnout system (boost, takedown detection, scoring…) is matched C in the Burnout3 repo, that C is compiled with
the ps2dev toolchain into the MC3 host mod. It first runs in **shadow mode**: the transplanted code and the hidden
Burnout instance see the same inputs, and the bridge logs every disagreement. When the scenario suite shows zero
differences, the guest's copy of that system is switched off. When every system has moved, the second emulator is
dropped and GameMerge is one PCSX2 instance running MC3 with Burnout's rules inside it.

---

## Milestones and steps

### B0: Two emulators and a PINE client
No game knowledge needed.
1. Run two PCSX2 instances side by side on macOS, each with its own settings directory (PCSX2's `--portable` mode or
   a separate data folder; to verify on macOS): MC3 on slot 28011 with the normal renderer, Burnout 3 on slot 28012
   with the null renderer and audio muted. Both boot from the user's ISOs.
2. Write `gm-pine`, a Rust PINE client: connect to both sockets, batch reads and writes, read the title, serial and
   CRC, and refuse anything but SLUS-21355 and SLUS-21050.
3. Measure: the round trip of one batched mailbox-sized read (about 1 KB) per frame on both sockets at 60 Hz, and the
   Mac's CPU load with both games running.
4. Script the launch: `cargo xtask launch` starts both instances with the right profiles.

**Done when** both games run at full speed together and the bridge reads both serials, with the measurements recorded
here.

### B1: Protocol
No game knowledge needed.
1. Define the mailbox header (magic, version, sequence word, frame counter) and the three messages in `gm-protocol`
   (Rust, `#[repr(C)]`): `HostFrame` (frame number, up to 16 vehicles with position, orientation and velocity,
   contacts, pad input), `GuestEvents` (takedowns {attacker, victim, type}, boost, slow-mo and camera requests,
   crash $, pickups, Crashbreaker) and `HostCommands` (impulses, time scale, camera override, HUD values, sequence).
2. Mirror it in `payload/include/gm_protocol.h`, with size and offset asserts on both sides so a layout change can't
   go unnoticed.
3. Write the ownership rules in `gm-rules`: MC3 owns the world, vehicles, base physics, traffic and rendering;
   Burnout owns takedown rules, boost, scoring, slow-mo and camera decisions and mode rules.
4. Decide how MC3's motorcycles take part: as Burnout cars, or excluded from takedowns.

**Done when** the protocol builds on both sides with matching layout asserts and a `fake_host`/`fake_guest` pair
passes a round trip in `cargo test`.

### B2: Hello host (MC3)
1. Study mc3-znx-tools and `mc3boot`: how the payload is loaded, where it lives in memory, how it hooks the frame.
   Decide between using `mc3boot` (if its source and licence allow) and a minimal loader of our own.
2. Build a Docker image with the ps2dev toolchain, like the decomp repos' build images.
3. Write the host mod's first payload: each frame, update the frame counter and the player's position and
   orientation in the host mailbox, at an address that doesn't collide with mc3-znx-tools' own mailbox.
4. The bridge reads the host mailbox with the sequence check and prints the player's position live.

**Done when** driving in MC3 moves the numbers in the bridge, at one update per frame, with no torn reads.

### B3: Hello guest (Burnout 3)
1. Find the boost bar and the player car slot (Ghidra on the Burnout3 project, the PCSX2 debugger, CodeBreaker
   codes) and record them as provisional in `addresses/b3.toml`.
2. Read the boost bar over PINE from the hidden instance.
3. Write the guest patch: a `.pnach` payload that publishes the guest mailbox, turns off AI and race timers, and keeps
   the simulation stepping with nothing drawn.

**Done when** the hidden Burnout instance runs a race indefinitely with no AI, and the bridge reads its boost bar.

### B4: Mirror
1. Every bridge tick, write MC3's player position, orientation and velocity into Burnout's player car slot.
2. Check by turning Burnout's renderer on briefly: its car follows the MC3 car.
3. Measure the drift between the two frame counters over ten minutes, and how often a tick misses a frame.

**Done when** the mirror holds over ten minutes and the drift and miss rate are recorded here.

### F1–F7: Features
Each feature ends with a clip, a bridge log and a passing scenario. Work on one can start at any time with
provisional addresses; it is **done** only when every address it uses is verified ([gates](#feature-gates)).

| ID | Feature | Steps |
|---|---|---|
| F1 | **Boost** | Burnout scores boost from the mirrored driving (drafting, near misses, oncoming, drifts, air); the bridge sends the bar to MC3's HUD and applies boost as MC3's nitro or as a forward impulse. |
| F2 | **Takedown detection** | Mirror MC3 opponents and traffic into Burnout's car and traffic slots; contacts reported by MC3's collision callbacks reach Burnout; Burnout's takedown event (Slam, Grind, Shunt, Wall, Traffic Check) comes back in `GuestEvents`. World-dependent types (wall, traffic) are classified from MC3's collisions in `gm-rules`. |
| F3 | **Takedown feel** | The victim gets an impulse, MC3's time step slows for Impact Time, the camera cuts to a takedown cam, a "TAKEDOWN!" popup shows, and the victim respawns. |
| F4 | **Player crash and aftertouch** | When the player wrecks, slow-mo starts, the stick steers the wreck, and aftertouch takedowns are scored. |
| F5 | **Road Rage** | A mode with a takedown target, a timer and a results screen, driven by Burnout's mode rules. |
| F6 | **Crash mode** | Chosen MC3 intersections, scripted traffic waves, pickups as trigger volumes, damage $ by Burnout's formula, a Crashbreaker blast, and a $ HUD. |
| F7 | **Polish** | Takedown cam variety, rivals and revenge takedowns, sounds from MC3's banks, an options toggle. |

**Stretch:** visual deformation on MC3 car meshes by vertex offset at render time.

#### Feature gates
The game-repo milestones whose tagged releases verify each feature's addresses.

| Feature | Burnout3 | MC3DER |
|---|---|---|
| B2–B4 plumbing | D6 (car slots) to verify B3–B4 | D5 (main loop, time step), D6 (vehicle struct) to verify B2 and B4 |
| F1 Boost | D7 (boost economy) | D6 (vehicles), D10 (HUD) |
| F2 Takedown detection | D6, D7 (takedown types) | D6 (collision callbacks), D9 (opponents, traffic) |
| F3 Takedown feel | D7 (Impact Time, crash cameras) | D5 (time step), D9 (cameras), D10 (HUD) |
| F4 Crash and aftertouch | D7 | D6 |
| F5 Road Rage | D8 (modes) | D7 (race and mode state machine) |
| F6 Crash mode | D8 | D7, D9 (traffic) |
| F7 Polish | D7, D10 (audio) | D10 (audio, HUD) |
| T Transplant | The transplanted system's units as matched C | The host-mod hooks it replaces |

### T: C transplant (end state)
For each Burnout system, in the order boost → takedown detection → scoring → modes:
1. Take the system's matched C from a tagged Burnout3 release (through `external/Burnout3`).
2. Build it with the ps2dev toolchain into the host mod, with a small adapter from `HostFrame` to the structs it
   expects. Check struct layouts against CodeWarrior's with asserts: GCC and CodeWarrior may pack or align some
   types differently.
3. Run it in shadow mode against the hidden Burnout instance over the scenario suite; the bridge logs each
   disagreement.
4. At zero differences, switch the system off in the guest patch and let the host mod's copy drive the game.

**Done when** every system has moved and the scenario suite passes with the second PCSX2 instance not running.

### R: Release
1. `cargo xtask launch` as the one command: checks both ISOs' serials and CRCs, builds and installs the patches,
   starts PCSX2 and the bridge.
2. README with supported serials and hashes, setup steps and known limits.
3. Users supply their own discs and BIOS; nothing game-derived ships.

---

## Testing (continuous)
- `cargo test`: `gm-protocol` layout asserts, `gm-rules` unit tests, a bridge loop driven by `fake_host`/`fake_guest`.
- `cargo xtask test-scenarios`: savestate fixtures plus scripted input against both emulators. For example, "ram an
  opponent at 120 km/h at 30°" must produce `TAKEDOWN type=SLAM`. During T, the same scenarios compare the host mod's
  transplanted code with the hidden Burnout.
- The address checker runs at bridge startup: wrong serial, wrong CRC or a provisional address in a release build
  aborts with a clear message.
- Performance budget: a bridge tick under 2 ms, and no MC3 frame drops with two PCSX2 instances on Apple Silicon.

## Risks
| Risk | Mitigation |
|---|---|
| PINE has no frame sync | Sequence-guarded mailboxes, frame counters on both sides, MC3 authoritative, one frame of latency accepted; drift measured in B4 |
| Two PCSX2 instances on macOS | Verified first, in B0 (portable mode or separate data folders) |
| `mc3boot` may not be public or reusable | B2 decides; a minimal `.pnach` loader of our own is the fallback |
| No loader for Burnout 3 | The guest patch is ours from B3; Burnout3's symbols tell where code and data can go |
| Burnout's takedown logic is tied to its own world | The guest handles car-vs-car only; world events come from MC3 collisions through `gm-rules` |
| Two emulators on one Mac | Null renderer and muted audio for the guest, measured in B0; T removes the guest |
| Provisional addresses are wrong or move | Every address records its source; features count as done only with verified addresses |
| CodeWarrior vs GCC layout differences in T | Layout asserts at the adapter; shadow mode catches behaviour differences |
| MC3's compiler is still unknown | The bridge needs only MC3's addresses and structs, not its compiler; that matters only if MC3 code is ever transplanted |
| Scope creep | F1–F6 is the target. F7 and deformation are stretch. |

---

## Repository layout (planned)
```
bridge/                  Rust workspace (runs on the Mac)
  gm-protocol/           mailbox header and messages, #[repr(C)], layout asserts
  gm-rules/              ownership, puppets, event classification
  gm-pine/               PINE client: Unix sockets, batched reads and writes, serial and CRC check
  gm-bridge/             the host↔guest loop
  gm-tools/              address checker, savestate scenario runner, fake_host / fake_guest
  xtask/                 cargo xtask launch | build-payload | test-scenarios
payload/                 C for the PS2 side, built with the ps2dev toolchain in Docker
  include/gm_protocol.h  mirror of gm-protocol
  mc3-hostmod/           MC3 host mod
  b3-guestpatch/         Burnout 3 guest patch
addresses/               mc3.toml, b3.toml: address, type, source, provisional or verified
external/                Burnout3 and MC3DER as submodules pinned to tags
```

---

## Shelved: the Rust rewrite and the native track
Shelved on 2026-10-07, not deleted. GameMerge no longer plans around either game's Rust rewrite.

- **What it was:** Track B, a native app running both games' Rust cores (`burnout3-core`, `mc3-core`) on a shared
  `platform` crate (renderer, audio, input, disc file system), and a "graduation" step that swapped the hidden
  Burnout instance for `burnout3-core` inside the bridge. The T milestone replaces that step.
- **What stays useful:** the protocol and rules (`gm-protocol`, `gm-rules`) and the scenario suite would carry over
  unchanged to a native app.
- **What would bring it back:** both games' Rust rewrites active again in their own repos, with the core-library
  rules their roadmaps already describe (no global state, one deterministic `World::step`, events as data, puppet
  vehicles and host hooks).

## Supported builds

| Game | Region | Serial | ELF SHA-1 |
|---|---|---|---|
| Midnight Club 3: DUB Edition Remix | NTSC-U | SLUS-21355 | `c09bdbec05cf27f1d3ed2267c437b98be8c7b26f` |
| Burnout 3: Takedown | NTSC-U | SLUS-21050 | `332be40d6081b8b5055a6ea01194ad6ff662a863` |

Memory addresses differ between regions and revisions. Other builds are not supported.

## History

- **2026-10-07:** scope rethought. The Rust rewrite and the native track are shelved; the PCSX2 bridge (the former
  Track A) is the path, starting now with per-feature gates, and the C transplant replaces graduation to a Rust core.
- **Until 2026-10-06** this repo also held the Burnout 3 decomp and Rust rewrite (D0–D3, commits up to `b5044e0`,
  moved under `Burnout3/` in `aac605f`) and the first MC3 Rust workspace (`MC3DER_rust/`). Both now live in their own
  repos, [Burnout3](https://github.com/siddharthakumar-98/Burnout3) and
  [MC3DER](https://github.com/siddharthakumar-98/MC3DER), which started with fresh histories; their earlier history
  stays here. The original passthrough plan (Stage C, milestones M1–M10) is in commit `a53cf40`.
