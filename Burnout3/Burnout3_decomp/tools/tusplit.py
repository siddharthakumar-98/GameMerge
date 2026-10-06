#!/usr/bin/env python3
"""Propose translation-unit (source file) boundaries inside the game's .text ranges.

Run after configure.py has generated assembly/asm/ (plain Python 3, no container needed):

    python3 tools/tusplit.py                 summary and the proposed units
    python3 tools/tusplit.py --yaml          the .text subsegment lines of b3.yaml, with game units regenerated

The binary has no symbols or file names, so boundaries are inferred (docs/layout.md explains the evidence):

  links    Two functions are linked, i.e. evidence says they are in the same file, when they
           - reference the same private item: a string, jump table or other .rodata/.data item, or a float
             literal (an .sdata word only ever loaded with lwc1; CodeWarrior keeps one literal pool per file);
           - reference .rodata/.data out of link order (an earlier function uses a later address than a later
             function), which can only happen inside one file because those sections are laid out in link order;
           - are both methods found in only one vtable;
           - call a helper that nothing else far away calls (the pattern of a file-local static function).
           Links longer than WINDOW functions are ignored as too likely to be shared globals.
  cuts     Every gap between two functions that no link crosses becomes a boundary, unless the piece it would
           create carries no evidence of its own (no private data reference and no vtable entry), in which
           case it stays with the piece before it.
  anchors  Each of the 158 C++ static initializers (__sinit_*, one per file, in link order) is located through
           the private items it shares with game functions. Two consecutive anchors are different files, so if
           no cut separates them one is forced at the weakest gap between them.

The result is a first pass: units may still hold more than one real file, or one file split in two.
"""

import argparse
import bisect
import collections
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import xref  # noqa: E402

# Game ranges of .text from docs/layout.md (start, end)
GAME = [(0x12EB30, 0x1D8260), (0x211C30, 0x215660), (0x216E40, 0x2372F0), (0x23AFD0, 0x241BC0),
        (0x24B2A0, 0x2C28C0), (0x2E2700, 0x304008), (0x306D90, 0x3D3158), (0x3D46A0, 0x3FFE48),
        (0x41C900, 0x443860), (0x445300, 0x469E00)]
# Libraries CodeWarrior compiled inside the game ranges, found as call-closed regions: nothing inside calls game
# code outside, while game code calls in (docs/layout.md). (start, end, unit prefix)
EMBEDDED_LIBS = [(0x290B10, 0x2B52C0, "rwa")]  # RenderWare Audio, EE side
RODATA, DATA, SDATA = (0x4B1500, 0x4D3E00), (0x483F00, 0x4B1500), (0x4E0680, 0x4E2680)
VTABLES, CTOR, INIT = (0x4DDAA0, 0x4E0680), (0x4DD820, 0x4DDAA0), (0x4D3E00, 0x4DD820)
WINDOW = 60          # functions; longer links are treated as shared globals
WEAK_WINDOW = 60     # shorter limit for data that may be global (.data, non-string .rodata)
ANCHOR_SPREAD = 40   # an initializer is a reliable anchor when its functions lie within this many


def game_range(addr: int) -> int | None:
    for k, (lo, hi) in enumerate(GAME):
        if lo <= addr < hi:
            return k
    return None


def lib_of(addr: int) -> str:
    for lo, hi, name in EMBEDDED_LIBS:
        if lo <= addr < hi:
            return name
    return "game"


def float_literals() -> set[int]:
    """.sdata words that are only ever loaded with lwc1: per-file float literal pools."""
    ops = collections.defaultdict(set)
    for path in (ROOT / "assembly/asm").rglob("*.s"):
        for line in path.read_text().splitlines():
            m = re.search(r"\*/\s+(\w+)\s+.*%gp_rel\(D_([0-9A-F]{8})", line)
            if m:
                ops[int(m.group(2), 16)].add(m.group(1))
    return {a for a, o in ops.items() if SDATA[0] <= a < SDATA[1] and o == {"lwc1"}}


def vtables() -> list[list[int]]:
    """Function entries of each vtable, in address (= link) order."""
    out = []
    for line in (ROOT / "assembly/asm/data/vtables.data.s").read_text().splitlines():
        if line.startswith("dlabel "):
            out.append([])
        m = re.search(r"\.word func_([0-9A-F]{8})", line)
        if m and out:
            out[-1].append(int(m.group(1), 16))
    return out


class Model:
    def __init__(self):
        funcs = xref.load()
        self.G = [f for f in funcs if game_range(f.addr) is not None]
        self.inits = [f for f in funcs if INIT[0] <= f.addr < INIT[1]]
        self.idx = {f.addr: i for i, f in enumerate(self.G)}
        self.lits = float_literals()
        self.rom = (ROOT / xref.ROM).read_bytes()
        self.users = collections.defaultdict(set)
        for i, f in enumerate(self.G):
            for a in f.refs:
                self.users[a].add(i)
        n = len(self.G)
        self.diff = [0] * (n + 1)
        self.evidence = [False] * n
        self._links()
        self.cohesion, run = [], 0
        for g in range(n - 1):
            run += self.diff[g]
            self.cohesion.append(run)

    def private(self, a: int) -> bool:
        """Data that is probably file-local: anything in .rodata/.data, or a float literal."""
        return RODATA[0] <= a < RODATA[1] or DATA[0] <= a < DATA[1] or a in self.lits

    def strictly_private(self, a: int) -> bool:
        """Data that is file-local for certain: a string literal or a float literal. Initialized globals in .data
        and extern const tables in .rodata can be shared between files."""
        if a in self.lits:
            return True
        if not RODATA[0] <= a < RODATA[1]:
            return False
        b = self.rom[a - xref.BASE:a - xref.BASE + 64].split(b"\0")[0]
        return len(b) >= 2 and all(32 <= c < 127 or c in (9, 10, 13) for c in b)

    def link(self, i: int, j: int) -> None:
        lo, hi = min(i, j), max(i, j)
        if lo == hi or hi - lo > WINDOW or game_range(self.G[lo].addr) != game_range(self.G[hi].addr):
            return
        self.diff[lo] += 1
        self.diff[hi] -= 1

    def _links(self) -> None:
        G, n = self.G, len(self.G)
        for a, us in self.users.items():
            if self.private(a):
                us = sorted(us)
                for u in us:
                    self.evidence[u] = True
                if not self.strictly_private(a) and us[-1] - us[0] > WEAK_WINDOW:
                    continue  # possibly a shared global or extern const table
                for u in us[1:]:
                    self.link(us[0], u)
        for lo_, hi_ in (RODATA, DATA):
            spans = []
            for f in G:
                xs = [a for a in f.refs if lo_ <= a < hi_ and max(self.users[a]) - min(self.users[a]) <= 150]
                spans.append((min(xs), max(xs)) if xs else None)
            for j in range(n):
                if spans[j]:
                    for i in range(max(0, j - WINDOW), j):
                        if spans[i] and spans[i][1] > spans[j][0]:
                            self.link(i, j)
        vts = vtables()
        count = collections.Counter(a for v in vts for a in v)
        for v in vts:
            own = sorted(self.idx[a] for a in v if a in self.idx and count[a] == 1)
            for u in own:
                self.evidence[u] = True
            for u in own[1:]:
                self.link(own[0], u)
        callers = collections.defaultdict(set)
        for i, f in enumerate(G):
            for t in f.calls:
                if t in self.idx:
                    callers[self.idx[t]].add(i)
        for t, cs in callers.items():
            if len(cs) <= 3 and max(cs | {t}) - min(cs | {t}) <= WINDOW:
                for c in cs:
                    self.link(c, t)

    def anchors(self) -> list[tuple[int, int, int]]:
        """(initializer index, first, last function index) for initializers that locate reliably, in .ctor order."""
        rom = (ROOT / xref.ROM).read_bytes()
        ctor = []
        for off in range(CTOR[0], CTOR[1], 4):
            p = struct.unpack_from("<I", rom, off - xref.BASE)[0]
            if not p:
                break
            ctor.append(p)
        by_addr = {f.addr: f for f in self.inits}
        out = []
        for k, p in enumerate(ctor):
            pos = []
            for a in by_addr[p].refs:
                us = self.users.get(a)
                if us and self.private(a) and max(us) - min(us) <= 150:
                    pos += us
            if pos and max(pos) - min(pos) <= ANCHOR_SPREAD:
                out.append((k, min(pos), max(pos)))
        return out

    def units(self) -> tuple[list[int], dict]:
        """Indices of the first function of every unit, plus statistics."""
        G, coh = self.G, self.cohesion
        starts = {0}
        for g in range(len(G) - 1):  # range and embedded-library edges are always boundaries
            if game_range(G[g].addr) != game_range(G[g + 1].addr) or lib_of(G[g].addr) != lib_of(G[g + 1].addr):
                starts.add(g + 1)
        edges = set(starts)
        cuts = [g + 1 for g in range(len(G) - 1) if coh[g] == 0]
        # keep a cut only if the piece it starts carries evidence before the next cut
        allcuts = sorted(set(cuts) | starts)
        for a, b in zip(allcuts, allcuts[1:] + [len(G)]):
            if a in starts or any(self.evidence[i] for i in range(a, b)):
                starts.add(a)
        forced, forced_cuts = 0, set()
        anchors = self.anchors()
        ordered = sorted(starts)
        for (_, _, hi_a), (_, lo_b, _) in zip(anchors, anchors[1:]):
            if lo_b <= hi_a:
                continue
            k = bisect.bisect_right(ordered, hi_a)
            if k < len(ordered) and ordered[k] <= lo_b:
                continue  # already separated
            g = min(range(hi_a, lo_b), key=lambda g: (coh[g], -g))
            starts.add(g + 1)
            forced_cuts.add(g + 1)
            ordered = sorted(starts)
            forced += 1
        protected = edges | forced_cuts
        merged = self._merge(sorted(starts), protected, anchors)
        stats = {"zero_gaps": len(cuts), "anchors": len(anchors), "forced": forced, "merged": merged}
        return sorted(self._starts), stats

    def _merge(self, starts: list[int], protected: set[int], anchors) -> int:
        """Remove boundaries that the evidence contradicts: a string or float literal used on both sides, an
        initializer anchor straddling it, or strings out of link order across it. Boundaries that separate two
        anchors (or range edges) are kept. Only strings and float literals count here, since other data can be
        shared between files."""
        G = self.G
        drop = set()
        for a, us in self.users.items():
            if self.strictly_private(a) and len(us) > 1:
                lo, hi = min(us), max(us)
                if hi - lo <= 4 * WINDOW:
                    drop.update(s for s in starts if lo < s <= hi)
        for _, lo, hi in anchors:
            drop.update(s for s in starts if lo < s <= hi)
        spans = []
        for k, st in enumerate(starts):
            end = starts[k + 1] if k + 1 < len(starts) else len(G)
            xs = [a for i in range(st, end) for a in G[i].refs
                  if a not in self.lits and self.strictly_private(a)
                  and max(self.users[a]) - min(self.users[a]) <= 150]
            spans.append((st, min(xs), max(xs)) if xs else None)
        seen = [x for x in spans if x]
        for k, (st, lo, hi) in enumerate(seen):
            for st2, lo2, hi2 in seen[k + 1:k + 4]:
                if lo2 < hi:  # a later unit uses strings placed before this unit's: same file
                    drop.update(s for s in starts if st < s <= st2)
        drop -= protected
        self._starts = set(starts) - drop
        return len(drop)


def yaml_lines(model: Model, starts: list[int], carved: dict[int, int]) -> list[str]:
    """Subsegment lines for the game ranges; carved maps a D2 unit's start to its end (both VRAM)."""
    G = model.G
    inside = lambda a: any(lo < a < hi for lo, hi in carved.items())
    bounds = sorted({G[i].addr for i in starts if not inside(G[i].addr)} | set(carved) | set(carved.values()))
    lines = []
    for a in bounds:
        if a in carved:
            lines.append(f"      - [0x{a - xref.BASE:06X}, asm, d2/func_{a:08X}]")
        elif game_range(a) is not None:
            lines.append(f"      - [0x{a - xref.BASE:06X}, asm, {lib_of(a)}/unit_{a:08X}]")
    return lines


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--yaml", action="store_true", help="print the .text subsegment lines for b3.yaml")
    args = p.parse_args()
    m = Model()
    starts, stats = m.units()
    sizes = [b - a for a, b in zip(starts, starts[1:] + [len(m.G)])]
    if args.yaml:
        # The .text block of the current b3.yaml: library lines are kept, game lines are replaced, and D2 units
        # stay as carved (each ends where the next .text subsegment starts).
        text = []
        for line in (ROOT / "assembly/splat/b3.yaml").read_text().splitlines():
            mm = re.match(r"\s*- \[0x([0-9A-F]+), asm, (\S+)\]", line)
            if mm:
                text.append((int(mm.group(1), 16) + xref.BASE, mm.group(2), line))
        carved = {a: text[k + 1][0] for k, (a, name, _) in enumerate(text) if name.startswith("d2/")}
        keep = [(a, line) for a, name, line in text if not name.startswith(("game/", "rwa/", "d2/"))]
        gen = [(int(line.split("[")[1].split(",")[0], 16) + xref.BASE, line)
               for line in yaml_lines(m, starts, carved)]
        print("\n".join(line for _, line in sorted(keep + gen)))
        return
    print(f"{len(m.G)} game functions -> {len(starts)} units "
          f"(gaps no link crosses: {stats['zero_gaps']}; initializer anchors: {stats['anchors']}, "
          f"cuts forced between anchors: {stats['forced']}; boundaries removed by contradicting evidence: "
          f"{stats['merged']})")
    print(f"functions per unit: median {sorted(sizes)[len(sizes) // 2]}, max {max(sizes)}, "
          f"single-function units {sum(1 for s in sizes if s == 1)}")


if __name__ == "__main__":
    main()
