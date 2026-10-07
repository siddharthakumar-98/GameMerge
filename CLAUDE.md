# CLAUDE.md

GameMerge brings Burnout 3: Takedown's gameplay (takedowns, boost, Impact Time, aftertouch, Road Rage, Crash mode)
into Midnight Club 3: DUB Edition Remix. MC3 is the host, Burnout 3 the hidden guest. `ROADMAP.md` is the source of
truth for plan and status; keep its Status table current. No code exists yet: the next step is S1 (protocol and rules
design), which needs nothing from the game repos.

## Rules
- **Edit only this repo.** The game repos are references: read them, never change them from a GameMerge session.
  A gap in their symbols or APIs becomes an issue in that repo.
- Never commit game-derived or proprietary files: ISOs, ELFs, BIOS, disassembly, assets, VU microcode, savestates,
  traces, address tables copied out of a game. Addresses and structs come in generated from the game repos' pinned
  tags (`cargo xtask gen-sys`), not pasted.
- Commit or push only when asked, with the user's exact message, ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Dependencies point one way: GameMerge depends on Burnout3 and MC3DER at tagged milestones, never on `main`. The game
  repos never depend on GameMerge.
- Don't copy the game repos' status into this repo beyond the dated snapshot in ROADMAP's "Upstream" table; link to
  their milestones instead.
- State a fact about either game only when its repo or a cited source verifies it. MC3's compiler and engine are
  still unknown; don't name them.

## Layout
- `README.md`, `ROADMAP.md`, `LICENSE` (GPL-3.0): all that is tracked today.
- Planned (see ROADMAP): `crates/` (`gm-protocol` and `gm-rules` shared; Track A: `gm-pine`, `gm-bridge`,
  `gm-hostmod`, `gm-guestpatch`, `b3-sys`, `mc3-sys`, `gm-tools`; Track B: `gm-native`, `gm-replay`), `external/`
  (game repos as submodules pinned to tags), `xtask/`.
- `Burnout3/` and `repo-split/` may exist on disk as leftovers from the 2026-10-06 split. Both are gitignored and
  unused: the live code is in the game repos.

## Plan in one paragraph
Two tracks share `gm-protocol` (`HostFrame`, `GuestEvents`, `HostCommands`) and `gm-rules` (ownership, puppets,
event classification) and deliver the same features F1–F7. Track A (A0–A3): both original games in two PCSX2
instances linked over PINE, needing only the decomps; its graduation step swaps the hidden Burnout instance for
`burnout3-core`. Track B (N0–N3): both Rust cores (`burnout3-core`, `mc3-core`) in one native app on a shared
`platform` crate, needing the rewrites. A decision point at both decomps' Phase 1 gates picks which track leads.

## Related repos (reference only)
- Burnout3: `~/Desktop/Burnout3`, https://github.com/siddharthakumar-98/Burnout3. Guest game. Its ROADMAP's
  "Crate boundaries" and "What other projects need from this repo" define what GameMerge gets and when.
- MC3DER: `~/Desktop/MC3DER`, https://github.com/siddharthakumar-98/MC3DER. Host game. Same two sections, plus the
  host hooks `mc3-core` must expose (impulses, time scale, camera override, puppet vehicles).
- Their `CLAUDE.md` files describe how each decomp is built and worked on.
