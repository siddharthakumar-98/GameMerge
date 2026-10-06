#!/usr/bin/env python3
"""Cross-reference index of the generated assembly, for mapping the binary (D3).

Run after configure.py has generated assembly/asm/ (no container needed, plain Python 3):

    python3 tools/xref.py funcs 0x102380 0x102700     one line per function: size, data refs, calls
    python3 tools/xref.py bins 0x100000 0x140000 0x2000   per-bin summary of .data/.rodata refs and calls
    python3 tools/xref.py refs 0x4B8145               functions that reference an address range (+/- 0x100)
    python3 tools/xref.py strings 0x4B1500 0x4B2200   printable strings in the original image
    python3 tools/xref.py compilers                   CodeWarrior vs GCC regions of .text

Data references are split by section as recovered in docs/layout.md, so translation-unit order can be read off
the .data and .rodata streams: every unit's pieces of each section are laid out in link order.
"""

import argparse
import re
import sys
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASM_DIR = ROOT / "assembly/asm"
ROM = ROOT / "orig/SLUS_210.50.rom"
BASE = 0x100000

# (start, end, name) of the regions in docs/layout.md that code references
SECTIONS = [
    (0x100000, 0x469E00, "text"),
    (0x469E00, 0x483F00, "vutext"),
    (0x483F00, 0x4B1500, "data"),
    (0x4B1500, 0x4D3E00, "rodata"),
    (0x4D3E00, 0x4DD820, "init"),
    (0x4DD820, 0x4DDAA0, "ctor"),
    (0x4DDAA0, 0x4E0680, "vtables"),
    (0x4E0680, 0x4E2680, "sdata"),
    (0x4E2680, 0x4E8680, "sbss"),
    (0x4E8680, 0x1ECEA00, "bss"),
]

INSN = re.compile(r"\s*/\* [0-9A-F]+ ([0-9A-F]{8}) [0-9A-F]{8} \*/\s+(\S+)\s*(.*)")
SYM_ADDR = re.compile(r"(?:D_|func_|jtbl_|ofs_|STR_)([0-9A-F]{8})")
STORES = {"sb", "sh", "sw", "sd", "sq", "swc1", "sqc2", "swl", "swr", "sdl", "sdr"}
BRANCH_LIKELY = {"beql", "bnel", "beqzl", "bnezl", "bgezl", "bltzl", "blezl", "bgtzl", "bc1tl", "bc1fl", "bgezall",
                 "bltzall"}


def section_of(addr: int) -> str | None:
    for lo, hi, name in SECTIONS:
        if lo <= addr < hi:
            return name
    return None


class Func:
    __slots__ = ("name", "addr", "size", "file", "refs", "writes", "calls", "syscalls", "cop2", "likely", "gap")

    def __init__(self, name: str, file: Path):
        self.name, self.file = name, file
        self.addr, self.size = None, 0
        self.refs, self.writes, self.calls = set(), set(), set()
        self.syscalls = self.cop2 = self.likely = 0
        self.gap = 0  # padding bytes between this function's end and the next function

    def compiler(self) -> str:
        """'gcc', 'mw' or '?' from codegen fingerprints that hold across the whole binary.

        CodeWarrior starts every function on a 16-byte boundary, pads to 16 with nops and never emits
        branch-likely instructions. ee-gcc (Sony libraries, RenderWare, DirtySock, Logitech) aligns
        functions to 8 and uses branch-likely freely."""
        if self.addr % 16 or self.likely:
            return "gcc"
        if self.gap >= 8:
            return "mw"
        return "?"


def sym_addr(sym: str, addrs: dict[str, int]) -> int | None:
    if sym in addrs:
        return addrs[sym]
    m = SYM_ADDR.match(sym)
    return int(m.group(1), 16) if m else None


def load() -> list[Func]:
    files = sorted(p for p in ASM_DIR.rglob("*.s") if "data" not in p.relative_to(ASM_DIR).parts[:1])
    if not files:
        sys.exit(f"no assembly in {ASM_DIR}; run configure.py first")
    funcs, addrs, pending = [], {}, []
    for path in files:
        cur = None
        for line in path.read_text().splitlines():
            if line.startswith("glabel "):
                cur = Func(line.split()[1], path)
                funcs.append(cur)
                continue
            if line.startswith("endlabel "):
                cur = None  # what follows is alignment padding, not part of the function
                continue
            if cur is None:
                continue
            m = INSN.match(line)
            if not m:
                continue
            addr = int(m.group(1), 16)
            if cur.addr is None:
                cur.addr = addr
                addrs[cur.name] = addr
            cur.size = addr + 4 - cur.addr
            op, args = m.group(2), m.group(3)
            if op in BRANCH_LIKELY:
                cur.likely += 1
            if op == "syscall":
                cur.syscalls += 1
            elif op.startswith(("vadd", "vsub", "vmul", "vmadd", "vmsub", "vopmula", "vopmsub", "vdiv", "vsqrt",
                                "vrsqrt", "qmtc2", "qmfc2", "lqc2", "sqc2", "vcallms", "vclip", "vmove")):
                cur.cop2 += 1
            if op in ("jal", "j") and not args.startswith("."):
                pending.append((cur, "call", args.strip()))
            for sym in re.findall(r"%(?:hi|lo|gp_rel)\(([^)+]+)", args):
                pending.append((cur, "store" if op in STORES and "%hi" not in args else "ref", sym))
    for f, kind, sym in pending:
        a = sym_addr(sym, addrs)
        if a is None:
            continue
        if kind == "call":
            f.calls.add(a)
        else:
            f.refs.add(a)
            if kind == "store":
                f.writes.add(a)
    funcs.sort(key=lambda f: f.addr)
    for f, nxt in zip(funcs, funcs[1:]):
        f.gap = nxt.addr - (f.addr + f.size)
    return funcs


def compiler_regions(funcs, lo=0x100000, hi=0x469E00):
    """Maximal runs of functions by compiler. A run of undecided functions takes the class of its
    neighbours when both agree; otherwise it is reported as '?' (the boundary lies somewhere inside)."""
    fs = [f for f in funcs if lo <= f.addr < hi]
    runs = []
    for f in fs:
        c = f.compiler()
        if runs and runs[-1][0] == c:
            runs[-1][2] = f
        else:
            runs.append([c, f, f])
    for i, r in enumerate(runs):
        if r[0] == "?" and 0 < i < len(runs) - 1 and runs[i - 1][0] == runs[i + 1][0]:
            r[0] = runs[i - 1][0]
    merged = []
    for r in runs:
        if merged and merged[-1][0] == r[0]:
            merged[-1][2] = r[2]
        else:
            merged.append(r)
    return [(c, a.addr, b.addr + b.size + b.gap, sum(1 for f in fs if a.addr <= f.addr <= b.addr))
            for c, a, b in merged]


def span(xs) -> str:
    return f"{min(xs):06X}-{max(xs):06X}" if xs else "-" * 13


def cmd_funcs(funcs, lo, hi):
    for f in funcs:
        if not lo <= f.addr < hi:
            continue
        by = {}
        for a in f.refs:
            by.setdefault(section_of(a), []).append(a)
        parts = [f"{s}:{' '.join(f'{a:06X}' for a in sorted(v)[:4])}{'…' if len(v) > 4 else ''}"
                 for s, v in sorted(by.items(), key=lambda kv: str(kv[0])) if s not in (None, "text")]
        calls = sorted(f.calls)
        cs = " ".join(f"{a:06X}" for a in calls[:5]) + (" …" if len(calls) > 5 else "")
        flags = (f" sc{f.syscalls}" if f.syscalls else "") + (f" vu{f.cop2}" if f.cop2 else "")
        align = 16 if f.addr % 16 == 0 else 8 if f.addr % 8 == 0 else 4
        print(f"{f.addr:06X} {f.size:5X} a{align:<2} {f.name[:30]:30}{flags} | {'  '.join(parts)} | C {cs}")


def cmd_bins(funcs, lo, hi, step):
    bins = {}
    for f in funcs:
        if lo <= f.addr < hi:
            b = bins.setdefault(f.addr // step * step, {"n": 0, "data": [], "rodata": [], "calls": [], "sc": 0})
            b["n"] += 1
            b["sc"] += f.syscalls
            for a in f.refs:
                s = section_of(a)
                if s in ("data", "rodata"):
                    b[s].append(a)
            b["calls"] += list(f.calls)
    for k in sorted(bins):
        b = bins[k]
        print(f"{k:06X} n{b['n']:<4} sc{b['sc']:<3} data {span(b['data'])}  rodata {span(b['rodata'])}  "
              f"calls {span(b['calls'])}")


def cmd_refs(funcs, lo, hi):
    for f in funcs:
        hits = sorted(a for a in f.refs if lo <= a < hi)
        if hits:
            print(f"{f.addr:06X} {f.name:30} {' '.join(f'{a:06X}' for a in hits[:8])}")


def cmd_compilers(funcs, lo, hi, minsize):
    for c, a, b, n in compiler_regions(funcs, lo, hi):
        if c != "mw" or b - a >= minsize:
            print(f"{c:3} {a:06X}-{b:06X} {n:5} functions")


def cmd_strings(lo, hi, minlen):
    rom = ROM.read_bytes()
    for m in re.finditer(rb"[\x20-\x7e\t\n\r]{%d,}" % minlen, rom[lo - BASE:hi - BASE]):
        print(f"{lo + m.start():06X} {m.group(0)[:100].decode('ascii', 'replace')!r}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    num = lambda s: int(s, 0)
    for name in ("funcs", "refs", "strings"):
        s = sub.add_parser(name)
        s.add_argument("lo", type=num)
        s.add_argument("hi", type=num, nargs="?")
        if name == "strings":
            s.add_argument("--min", type=int, default=4)
    s = sub.add_parser("compilers", help="CodeWarrior/GCC regions from codegen fingerprints")
    s.add_argument("lo", type=num, nargs="?", default=0x100000)
    s.add_argument("hi", type=num, nargs="?", default=0x469E00)
    s.add_argument("--min", type=num, default=0, help="hide CodeWarrior runs smaller than this")
    s = sub.add_parser("bins")
    s.add_argument("lo", type=num)
    s.add_argument("hi", type=num)
    s.add_argument("step", type=num, nargs="?", default=0x2000)
    a = p.parse_args()
    if a.cmd == "strings":
        return cmd_strings(a.lo, a.hi or a.lo + 0x1000, a.min)
    funcs = load()
    if a.cmd == "funcs":
        cmd_funcs(funcs, a.lo, a.hi or a.lo + 0x1000)
    elif a.cmd == "compilers":
        cmd_compilers(funcs, a.lo, a.hi, a.min)
    elif a.cmd == "bins":
        cmd_bins(funcs, a.lo, a.hi, a.step)
    elif a.cmd == "refs":
        cmd_refs(funcs, a.lo - 0x100 if a.hi is None else a.lo, a.lo + 0x100 if a.hi is None else a.hi)


if __name__ == "__main__":
    main()
