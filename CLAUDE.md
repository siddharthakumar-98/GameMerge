# CLAUDE.md

GameMerge brings Burnout 3: Takedown's gameplay (takedowns, boost, Impact Time, aftertouch, Road Rage, Crash mode)
into Midnight Club 3: DUB Edition Remix. MC3 is the host, Burnout 3 the hidden guest. `ROADMAP.md` is the source of
truth for plan and status; keep its Status table current.

**Approach (2026-10-07):** a PCSX2 bridge. Both original games run in PCSX2; injected C on each side publishes a
mailbox in game RAM; a Rust bridge on the Mac links them over PINE. The Rust rewrite and the native track are
shelved (ROADMAP, "Shelved"). The end state is the C transplant: Burnout's matched C compiled into the MC3 host mod,
one system at a time, until the second emulator can go. No code exists yet; the next milestone is B0.

## Rules
- **Edit only this repo.** Burnout3 and MC3DER are references: read them, never change them from a GameMerge
  session, not even generated files. A gap in their symbols becomes an issue in that repo.
- Never commit game-derived or proprietary files: ISOs, ELFs, BIOS, disassembly, assets, VU microcode, savestates,
  traces. Addresses, names and struct layouts are fine.
- Every address lives in `addresses/mc3.toml` or `addresses/b3.toml` with its type, its source (game repo tag,
  Ghidra, PCSX2 debugger, CodeBreaker, mc3-znx-tools) and `provisional` or `verified`. Verified means it comes from a
  tagged release of the game repo that owns it. A feature is done only when all its addresses are verified.
- Commit or push only when asked, with the user's exact message, ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Dependencies point one way: GameMerge pins the game repos at tags, never `main`; they never depend on GameMerge.
- Don't copy the game repos' status beyond the dated "Upstream" snapshot in ROADMAP; link to their milestones.
- State a fact about either game only when its repo or a cited source verifies it. MC3's compiler and engine are
  still unknown; don't name them.

## Key facts
- PINE (PCSX2's IPC, `pcsx2/PINE.cpp`): 8/16/32/64-bit reads and writes, batched up to ~650 KB per message, plus
  save/load state, title, serial, CRC, version, status. macOS socket `$TMPDIR/pcsx2.sock` (slot 28011),
  `pcsx2.sock.<slot>` otherwise. **No frame sync, no pause or frame step**: hence sequence-guarded mailboxes with frame
  counters, MC3 authoritative, one frame of latency.
- Injected code: C/C++ via the ps2dev toolchain (`mips64r5900el-ps2-elf-gcc`) in Docker, loaded through `.pnach`
  patches. Prior art: mc3-znx-tools (GPL-3) and its loader `mc3boot`; its telemetry mailbox sits at `0x0061C990`
  (magic `MC3T`), so ours must not collide with it.
- Supported: MC3 SLUS-21355 (ELF SHA-1 `c09bdbec…`), Burnout 3 SLUS-21050 (ELF SHA-1 `332be40d…`). The bridge refuses
  anything else.

## Layout
- Tracked today: `README.md`, `ROADMAP.md`, `CLAUDE.md`, `LICENSE` (GPL-3.0), `.gitignore`.
- Planned (ROADMAP, "Repository layout"): `bridge/` (Rust: `gm-protocol`, `gm-rules`, `gm-pine`, `gm-bridge`,
  `gm-tools`, `xtask`), `payload/` (C: `mc3-hostmod`, `b3-guestpatch`, `include/gm_protocol.h`), `addresses/`,
  `external/` (game repos as submodules pinned to tags).
- `Burnout3/` and `repo-split/` may exist on disk as leftovers from the 2026-10-06 split. Both are gitignored and
  unused.

## Plugins
Two Claude Code plugins are installed for this project; use them.
- **superpowers:** process skills. `brainstorming` before any new feature or design change (classify spike, bounded
  or architectural; get approval before implementing), `writing-plans` and `executing-plans` for multi-step work,
  `test-driven-development` for bridge and payload code, `systematic-debugging` for failures, and
  `verification-before-completion` before claiming anything works. Specs go in `docs/superpowers/specs/`.
- **claude-mem:** persistent memory across sessions. Search it (`mem-search`, or the `claude-mem` MCP search tools)
  before re-deriving past decisions, findings or addresses; it records observations from each session automatically.

## Related repos (reference only)
- Burnout3: `~/Desktop/Burnout3`, https://github.com/siddharthakumar-98/Burnout3. Guest game. Its ROADMAP's "What
  other projects need from this repo" lists the milestones GameMerge's features wait on; its Ghidra project
  (`~/Desktop/Ghidra/Burnout3_decomp`) helps find provisional addresses.
- MC3DER: `~/Desktop/MC3DER`, https://github.com/siddharthakumar-98/MC3DER. Host game, D0 in progress.
- mc3-znx-tools: https://github.com/znxee/mc3-znx-tools. MC3 symbols (from an alpha's `MC.MAP`, provisional on
  retail), mods and PINE telemetry.
