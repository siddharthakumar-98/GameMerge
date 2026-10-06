#!/usr/bin/env python3
"""Compare one C/C++ function against the original under one or more compiler flag sets.

Run inside the build container after configure.py has generated assembly/asm/:

    tools/dock python3 tools/funcmatch.py func_0013C930 c_cpp/src/d2/foo.c -f=-O3 -f="-O4 -inline auto"

The function's assembly is pulled out of assembly/asm/ into its own object (the target), the source is
compiled with CodeWarrior once per flag set (the base), and objdiff reports how well they match. On a
mismatch the two disassemblies are printed side by side. Nothing outside build/funcmatch/ is touched.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from configure import AS_FLAGS, ASM_DIR, CFLAGS, CROSS, MWCC  # noqa: E402

WORK = Path("build/funcmatch")
ASM_HEADER = '.include "macro.inc"\n\n.set noat\n.set noreorder\n\n.section .text, "ax"\n\n'


def sh(cmd: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, **kw)


def extract_function(name: str) -> str:
    for path in sorted((ROOT / ASM_DIR).rglob("*.s")):
        text = path.read_text()
        m = re.search(rf"^glabel {re.escape(name)}\n.*?^endlabel {re.escape(name)}\n", text, re.S | re.M)
        if m:
            return m.group(0)
    sys.exit(f"{name}: not found in {ASM_DIR}; run configure.py first")


def build_target(name: str) -> Path:
    s = WORK / f"{name}.target.s"
    o = WORK / f"{name}.target.o"
    (ROOT / s).write_text(ASM_HEADER + extract_function(name))
    r = sh(f"{CROSS}as {AS_FLAGS} -o {o} {s}")
    if r.returncode:
        sys.exit(f"assembling {s} failed:\n{r.stderr}")
    return o


def compile_base(compiler: Path, src: Path, flags: str, tag: int) -> tuple[Path | None, str]:
    o = WORK / f"{src.stem}.{tag}.o"
    env = dict(os.environ, MWCIncludes="c_cpp/include")
    r = sh(f"wibo {compiler} {flags} -c {src} -o {o}", env=env)
    if r.returncode or not (ROOT / o).exists():
        return None, r.stdout + r.stderr
    return o, ""


def match_percent(target: Path, base: Path, name: str) -> float | None:
    r = sh(f"objdiff-cli diff -1 {target} -2 {base} -o - {name}")
    if r.returncode:
        return None
    data = json.loads(r.stdout)
    for sym in data.get("right", {}).get("symbols", []):
        if sym.get("name") == name:
            return sym.get("match_percent")
    return None


def disasm(obj: Path, name: str) -> list[str]:
    r = sh(f"{CROSS}objdump -dr --no-show-raw-insn -M no-aliases {obj} --disassemble={name}")
    out = []
    for line in r.stdout.splitlines():
        m = re.match(r"\s*[0-9a-f]+:\s+(.*)", line)
        if m:
            out.append(re.sub(r"\s+", " ", m.group(1)).strip())
        elif "R_MIPS" in line:
            out[-1] += "  [" + line.split()[-1] + "]"
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("function", help="symbol name in the generated assembly, e.g. func_0013C930")
    p.add_argument("source", type=Path, help="C or C++ file defining that symbol")
    p.add_argument("-f", "--flags", action="append", help=f"compiler flags to try, written -f=FLAGS (default: {CFLAGS!r})")
    p.add_argument("-q", "--quiet", action="store_true", help="don't print disassembly on mismatch")
    p.add_argument("-c", "--compiler", type=Path, default=MWCC,
                   help=f"compiler executable, or a folder under compilers/ (default: {MWCC})")
    args = p.parse_args()

    compiler = args.compiler
    if (ROOT / compiler).is_dir():
        compiler = compiler / "mwccps2.exe"
    (ROOT / WORK).mkdir(parents=True, exist_ok=True)
    target = build_target(args.function)
    best = 0.0
    for i, flags in enumerate(args.flags or [CFLAGS]):
        base, err = compile_base(compiler, args.source, flags, i)
        if base is None:
            print(f"{flags:16} compile failed\n{err}")
            continue
        pct = match_percent(target, base, args.function)
        shown = "symbol missing" if pct is None else f"{pct:6.2f}%"
        print(f"{flags:16} {shown}")
        best = max(best, pct or 0.0)
        if pct != 100.0 and not args.quiet:
            left, right = disasm(target, args.function), disasm(base, args.function)
            for n in range(max(len(left), len(right))):
                a = left[n] if n < len(left) else ""
                b = right[n] if n < len(right) else ""
                print(f"   {'  ' if a == b else '!='} {a:48} | {b}")
    sys.exit(0 if best == 100.0 else 1)


if __name__ == "__main__":
    main()
