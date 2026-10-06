#!/usr/bin/env python3
"""Assign .data and .rodata to the .text units, giving every unit its own data slices.

Run after configure.py has generated assembly/asm/ (plain Python 3, no container needed):

    python3 tools/dataslice.py               summary
    python3 tools/dataslice.py --yaml        the .data/.rodata subsegment lines for b3.yaml

Both sections are laid out in link order, the same order as the units in .text (docs/layout.md). Each stream is
cut into consecutive slices, one per unit in .text order (a unit may get none), choosing the cut points that put
the most code references inside their own unit's slice. Only cuts at item starts (labels in the generated
assembly) are allowed, and they are snapped to 16-byte boundaries because the generated assembly aligns items
relative to the start of its file. An item no code references goes with the next unit when it starts on an
8-byte boundary after the previous unit's last referenced item, since every unit's data starts aligned; otherwise
it stays with the previous unit. Data slices that b3.yaml already carves for C units (d2/) are kept exactly.
"""

import argparse
import bisect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import xref  # noqa: E402

YAML = ROOT / "assembly/splat/b3.yaml"
STREAMS = {"data": (0x483F00, 0x4B1500), "rodata": (0x4B1500, 0x4D3E00)}
SUBSEG = re.compile(r"\s*- \[0x([0-9A-F]+), (\w+), (\S+)\]")


def text_units() -> list[tuple[int, str]]:
    """(VRAM start, name) of every .text asm unit in b3.yaml, in order."""
    out = []
    for line in YAML.read_text().splitlines():
        m = SUBSEG.match(line)
        if m and m.group(2) == "asm":
            out.append((int(m.group(1), 16) + xref.BASE, m.group(3)))
    return out


def fixed_slices() -> dict[str, list[tuple[int, int, str]]]:
    """Data slices of C units (d2/) already carved in b3.yaml: stream -> [(start, end, name)]."""
    lines = [m for m in map(SUBSEG.match, YAML.read_text().splitlines()) if m]
    out = {s: [] for s in STREAMS}
    for k, m in enumerate(lines):
        if m.group(2) in STREAMS and m.group(3).startswith("d2/"):
            start = int(m.group(1), 16) + xref.BASE
            end = int(lines[k + 1].group(1), 16) + xref.BASE
            out[m.group(2)].append((start, end, m.group(3)))
    return out


def version_tags() -> set[int]:
    """Items no code references but that start a library's data: Sony version tags ("PsIIlibgraph2800") at the
    start of each library's .data, and RenderWare "@@(#)$Id: ...$" strings at the start of a source file's
    .rodata. The disassembler often leaves them inside the previous item."""
    rom = (ROOT / xref.ROM).read_bytes()
    lo, hi = STREAMS["data"][0], STREAMS["rodata"][1]
    tags = {lo + m.start() for m in re.finditer(rb"PsIIlib", rom[lo - xref.BASE:hi - xref.BASE])}
    rcsid = {(lo + m.start()) & ~7 for m in re.finditer(rb"@@\(#\)\$Id", rom[lo - xref.BASE:hi - xref.BASE])}
    return tags | rcsid


def labels(lo: int, hi: int) -> list[int]:
    """Start addresses of the data items in [lo, hi), from the generated assembly, plus version tags."""
    out = {a for a in version_tags() if lo <= a < hi}
    for path in (ROOT / "assembly/asm/data").rglob("*.s"):
        for line in path.read_text().splitlines():
            m = re.match(r"dlabel \w*?([0-9A-F]{8})$", line)
            if m and lo <= int(m.group(1), 16) < hi:
                out.add(int(m.group(1), 16))
    return sorted(out | {lo})


def assign(items: list[int], users: dict[int, set[int]], nunits: int) -> list[int]:
    """Monotone assignment of items to units maximizing references that land in their own unit."""
    NEG = float("-inf")
    best = [0.0] * nunits
    back = []
    for a in items:
        us = users.get(a, set())
        # prefix maximum: the item may stay in the same unit as the previous one or move forward
        pm, arg, choice = NEG, 0, [0] * nunits
        nb = [0.0] * nunits
        for u in range(nunits):
            if best[u] > pm:
                pm, arg = best[u], u
            choice[u] = arg
            nb[u] = pm + (1.0 if u in us else 0.0)
        back.append(choice)
        best = nb
    u = max(range(nunits), key=lambda k: (best[k], -k))
    out = [0] * len(items)
    for i in range(len(items) - 1, -1, -1):
        out[i] = u
        u = back[i][u]
    return out


def slices(stream: str, units: list[tuple[int, str]], funcs) -> list[tuple[int, str]]:
    lo, hi = STREAMS[stream]
    starts = [a for a, _ in units]
    # C units (d2/) own only their carved slices, so their references count for the unit before them
    owners = [k for k, (_, name) in enumerate(units) if not name.startswith("d2/")]
    rank = {u: i for i, u in enumerate(owners)}
    unit_of = lambda addr: rank[max(u for u in owners if u <= bisect.bisect_right(starts, addr) - 1)]
    users: dict[int, set[int]] = {}
    for f in funcs:
        if f.addr < 0x469E00:  # code in .text only; .init code can't be placed in a unit
            for a in f.refs:
                if lo <= a < hi:
                    users.setdefault(a, set()).add(unit_of(f.addr))
    items = labels(lo, hi)
    # a reference into the middle of an item counts for the item
    for a in list(users):
        if a not in items:
            k = bisect.bisect_right(items, a) - 1
            users.setdefault(items[k], set()).update(users.pop(a))
    owner = [owners[u] for u in assign(items, users, len(owners))]
    referenced = [i for i, a in enumerate(items) if a in users]
    # cut points: where the owner of referenced items changes, moved back over unreferenced items to the first
    # 8-byte-aligned one after the previous unit's last referenced item
    cuts = {items[0]: owner[referenced[0]] if referenced else 0}
    for p, q in zip(referenced, referenced[1:]):
        if owner[p] != owner[q]:
            cut = items[q]
            for i in range(p + 1, q):
                if items[i] % 8 == 0:
                    cut = items[i]
                    break
            cuts[cut] = owner[q]
    # The generated assembly aligns items with .align directives relative to its own start, and some items need
    # 16-byte alignment, so every slice must start on a 16-byte boundary: snap each cut to the nearest 16-aligned
    # item start between its neighbours, or drop it if there is none.
    aligned = [a for a in items if a % 16 == 0]
    ordered = sorted(cuts)
    snapped = {}
    for k, c in enumerate(ordered):
        if c % 16 == 0 or k == 0:
            snapped[c] = cuts[c]
            continue
        lo_c = max(snapped) if snapped else items[0]
        hi_c = ordered[k + 1] if k + 1 < len(ordered) else hi
        cands = [a for a in aligned if lo_c < a < hi_c]
        if cands:
            snapped[min(cands, key=lambda a: (abs(a - c), a))] = cuts[c]
    cuts = snapped
    for start, end, name in fixed_slices()[stream]:
        prev = max((c for c in cuts if c < start), default=items[0])
        after = cuts[max(c for c in cuts if c <= end)] if any(c <= end for c in cuts) else cuts[prev]
        cuts = {c: u for c, u in cuts.items() if not start <= c <= end}
        cuts[start] = name
        cuts[end] = after
    out = []
    for c in sorted(cuts):
        u = cuts[c]
        name = u if isinstance(u, str) else units[u][1]
        if out and out[-1][1] == name:
            continue
        out.append((c, name))
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--yaml", action="store_true", help="print the .data/.rodata subsegment lines for b3.yaml")
    args = p.parse_args()
    funcs = xref.load()
    units = text_units()
    result = {s: slices(s, units, funcs) for s in STREAMS}
    if args.yaml:
        for stream, sl in result.items():
            for start, name in sl:
                print(f"      - [0x{start - xref.BASE:06X}, {stream}, {name}]")
        return
    for stream, sl in result.items():
        names = [n for _, n in sl]
        dup = len(names) - len(set(names))
        print(f".{stream}: {len(sl)} slices for {len(set(names))} units"
              + (f" ({dup} units have more than one slice)" if dup else ""))


if __name__ == "__main__":
    main()
