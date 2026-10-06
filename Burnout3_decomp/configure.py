#!/usr/bin/env python3
"""Generate build.ninja for the Burnout 3 matching decomp.

Run inside the build container (tools/dock python3 configure.py), then `tools/dock ninja`.

Steps:
  1. orig/SLUS_210.50 (your copy, hash-checked) -> orig/SLUS_210.50.rom (raw load segment)
  2. splat splits the rom into assembly/asm/ and assembly/assets/ and writes the linker script into build/
  3. build.ninja assembles every asm unit, compiles every C unit in c_cpp/src/ with CodeWarrior, links
     (C objects replace their asm counterparts once they match), objcopies the load segment and
     rebuilds the ELF container, failing unless the result has the original SHA-1
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASENAME = "SLUS_210.50"
ORIG_ELF = Path("orig") / BASENAME
ORIG_ROM = Path("orig") / f"{BASENAME}.rom"
SPLAT_YAML = Path("assembly/splat/b3.yaml")
ASM_DIR = Path("assembly/asm")
ASSET_DIR = Path("assembly/assets")
SRC_DIR = Path("c_cpp/src")
BUILD = Path("build")

CROSS = "mips-linux-gnu-"
AS_FLAGS = "-EL -march=r5900 -mabi=eabi -G 0 -no-pad-sections -I assembly/include"

# CodeWarrior for PS2 Version 3.0.3 (decomp.me mwcps2-3.0.3-020716). Four builds stamp the game's
# "MW MIPS C Compiler (2.4.1.01)" (2.4 EB0017, 3.0, 3.0.1, 3.0.3); 3.0.3 is the only one that
# matches every D2 test, including the inline cvt.w.s float-to-int. See docs/compiler.md.
MWCC = Path("compilers/3.0.3-020716/mwccps2.exe")
# -O3 and -O4 produce identical code for every function tested so far; -O4 is the working choice.
# -str readonly: the game's string literals sit in .rodata and are addressed with lui/addiu even when
#   short (the default puts them in .data, and short ones in .sdata via $gp).
# -Cpp_exceptions off: the binary has no .exceptix exception tables.
CFLAGS = "-O4 -str readonly -Cpp_exceptions off"

# C/C++ translation units, keyed by path under c_cpp/src/ (.c or .cpp) and assembly/asm/ (.s).
#   linked: link the C object instead of the asm. Set only once objdiff shows 100%; the SHA-1 check
#           then proves it in the full build.
#   data:   carved data pieces this unit owns (path under assembly/asm/, ending in .data or .rodata),
#           mapped to the C object's section that replaces them (e.g. a switch's jump table).
C_UNITS = {
    "d2/func_00131AA0": {"linked": True},
    "d2/func_00131CE0": {"linked": False},  # 98.75%: original computes a large offset in v0, not at
    "d2/func_00136E00": {"linked": True},
    "d2/func_0013AE70": {"linked": False},  # 90.38%: branch delay slot filled differently
    "d2/func_0013B670": {"linked": False},  # original uses inline asm (pmaxw/pminw); C is a draft
    "d2/func_0013B740": {"linked": True},
    "d2/func_0013C910": {"linked": True},
    "d2/func_0014DD80": {"linked": True},
    "d2/func_0014E7E0": {"linked": True},
    "d2/func_0014EC30": {"linked": True, "data": {"data/d2/func_0014EC30.rodata": ".rodata"}},
    "d2/func_0028B700": {"linked": True},
}

LD_SCRIPT_SPLAT = BUILD / f"{BASENAME}.ld"
LD_SCRIPT_FINAL = BUILD / f"{BASENAME}.final.ld"
LD_SCRIPTS = [
    LD_SCRIPT_FINAL,
    BUILD / "undefined_syms_auto.txt",
    BUILD / "undefined_funcs_auto.txt",
    Path("config/linker_extra.ld"),
]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def asm_obj(unit: str) -> Path:
    return BUILD / ASM_DIR / f"{unit}.o"


def c_src(unit: str) -> Path:
    cpp = SRC_DIR / f"{unit}.cpp"
    return cpp if (ROOT / cpp).exists() else SRC_DIR / f"{unit}.c"


def c_obj(unit: str) -> Path:
    return BUILD / SRC_DIR / f"{unit}.o"


# Progress category of each unit, by the first part of its path (see docs/layout.md for the map).
CATEGORIES = {
    "game": ("game", "Burnout 3 game code"),
    "d2": ("game", None),
    "sinit": ("game", None),
    "rw": ("rw", "RenderWare 3.6"),
    "sce": ("sce", "Sony libsce"),
    "runtime": ("runtime", "Runtime: crt0, Metrowerks C++ runtime, newlib libc/libm, libgcc"),
    "ea": ("ea", "EA DirtySock"),
    "lg": ("lg", "Logitech device libraries"),
}


def category(unit: str) -> str:
    top = unit.split("/")[0]
    if top not in CATEGORIES:
        sys.exit(f"{unit}: no progress category for '{top}/' (add it to CATEGORIES)")
    return CATEGORIES[top][0]


def start_alignment(asm: Path) -> int:
    """Alignment implied by the unit's original start address (16, 8 or 4).

    GNU as gives every section 16-byte alignment, but library objects (built with ee-gcc) start on
    8-byte boundaries; their asm objects get the smaller alignment so they land where they did."""
    with open(ROOT / asm) as f:
        for line in f:
            m = re.match(r"\s*/\* [0-9A-F]+ ([0-9A-F]{8})", line)
            if m:
                vram = int(m.group(1), 16)
                return 16 if vram % 16 == 0 else 8 if vram % 8 == 0 else 4
    return 16


def write_final_ld_script() -> None:
    """Copy splat's linker script, pointing each linked C unit at its C object instead of its asm.

    Every section line of the unit (.text, .data, .rodata, .bss) is redirected, so the asm object is
    not pulled into the link at all."""
    script = (ROOT / LD_SCRIPT_SPLAT).read_text()
    for unit, cfg in C_UNITS.items():
        if not cfg["linked"]:
            continue
        old = f"{asm_obj(unit).as_posix()}("
        if old not in script:
            sys.exit(f"{unit}: {old} not found in {LD_SCRIPT_SPLAT}; is it carved out in {SPLAT_YAML}?")
        script = script.replace(old, f"{c_obj(unit).as_posix()}(")
        for piece, section in cfg.get("data", {}).items():
            old = f"{(BUILD / ASM_DIR / piece).as_posix()}.o({Path(piece).suffix})"
            if old not in script:
                sys.exit(f"{unit}: data piece {old} not found in {LD_SCRIPT_SPLAT}")
            script = script.replace(old, f"{c_obj(unit).as_posix()}({section})")
    (ROOT / LD_SCRIPT_FINAL).write_text(script)


def write_ninja(asm_files: list[Path]) -> None:
    elf = BUILD / f"{BASENAME}.elf"
    rom = BUILD / f"{BASENAME}.rom"
    out = BUILD / BASENAME

    lines = [
        "# Generated by configure.py. Do not edit.",
        "ninja_required_version = 1.10",
        "",
        "rule as",
        f"  command = {CROSS}as {AS_FLAGS} -o $out $in",
        "  description = AS $in",
        "",
        "rule as_aligned",
        f"  command = {CROSS}as {AS_FLAGS} -o $out.tmp $in && {CROSS}objcopy "
        "--set-section-alignment .text=$align --set-section-alignment .data=$align "
        "--set-section-alignment .rodata=$align $out.tmp $out && rm $out.tmp",
        "  description = AS $in (align $align)",
        "",
        "rule cc",
        f"  command = MWCIncludes=c_cpp/include wibo {MWCC} {CFLAGS} -c $in -o $out",
        "  description = CC $in",
        "",
        "rule ld",
        f"  command = {CROSS}ld -EL {' '.join(f'-T {s}' for s in LD_SCRIPTS)} "
        f"-Map {BUILD}/{BASENAME}.map --no-check-sections -o $out",
        "  description = LD $out",
        "",
        "rule objcopy",
        f"  command = {CROSS}objcopy -O binary -j .main $in $out",
        "  description = OBJCOPY $out",
        "",
        "rule elf",
        "  command = python3 tools/elf.py rebuild $in $out --check",
        "  description = ELF $out",
        "",
    ]

    objs = []
    for s in asm_files:
        o = BUILD / s.with_suffix(".o")
        objs.append(o)
        align = start_alignment(s)
        if align == 16:
            lines.append(f"build {o}: as {s}")
        else:
            lines += [f"build {o}: as_aligned {s}", f"  align = {align}"]
    for unit in C_UNITS:
        o = c_obj(unit)
        objs.append(o)
        lines.append(f"build {o}: cc {c_src(unit)}")
    lines += [
        "",
        f"build {elf}: ld | {' '.join(str(o) for o in objs)} {' '.join(str(s) for s in LD_SCRIPTS)}",
        f"build {rom}: objcopy {elf}",
        f"build {out}: elf {rom}",
        "",
        f"default {out}",
        "",
    ]
    (ROOT / "build.ninja").write_text("\n".join(lines))


def write_objdiff(asm_files: list[Path]) -> None:
    """objdiff units: target objects come from splat asm; C units add a base object to diff against."""
    units = []
    for s in asm_files:
        if s.relative_to(ASM_DIR).parts[0] == "data":
            continue
        unit = s.relative_to(ASM_DIR).with_suffix("").as_posix()
        entry = {
            "name": unit,
            "target_path": (BUILD / s.with_suffix(".o")).as_posix(),
            "metadata": {"progress_categories": [category(unit)]},
        }
        if unit in C_UNITS:
            entry["base_path"] = c_obj(unit).as_posix()
            entry["metadata"]["source_path"] = c_src(unit).as_posix()
        units.append(entry)
    config = {
        "min_version": "2.0.0",
        "custom_make": "ninja",
        "build_target": False,
        "build_base": True,
        "watch_patterns": ["*.c", "*.cpp", "*.h", "*.hpp", "*.s", "*.inc"],
        "progress_categories": [{"id": cid, "name": name} for cid, name in CATEGORIES.values() if name],
        "units": units,
    }
    (ROOT / "objdiff.json").write_text(json.dumps(config, indent=2) + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-split", action="store_true", help="reuse existing assembly/asm/ instead of re-running splat")
    args = p.parse_args()

    if not (ROOT / ORIG_ELF).exists():
        sys.exit(f"missing {ORIG_ELF}: extract SLUS_210.50 from your disc first (see README.md)")
    if not (ROOT / ORIG_ROM).exists():
        run([sys.executable, "tools/elf.py", "extract", str(ORIG_ELF), str(ORIG_ROM)])
    if C_UNITS and not (ROOT / MWCC).exists():
        sys.exit(f"missing {MWCC}: C units need the CodeWarrior compiler (see README.md)")

    if not args.no_split:
        # splat neither deletes files of units that were renamed nor rewrites existing binary pieces, so the
        # generated folders start empty on every split.
        for generated in (ASM_DIR, ASSET_DIR):
            shutil.rmtree(ROOT / generated, ignore_errors=True)
        run([sys.executable, "-m", "splat", "split", str(SPLAT_YAML)])

    asm_files = sorted(p.relative_to(ROOT) for p in (ROOT / ASM_DIR).rglob("*.s"))
    if not asm_files:
        sys.exit(f"no asm files found in {ASM_DIR}; run without --no-split")
    for unit in C_UNITS:
        if not (ROOT / c_src(unit)).exists():
            sys.exit(f"C unit {unit}: missing {c_src(unit)}")
    write_final_ld_script()
    write_ninja(asm_files)
    write_objdiff(asm_files)
    print(f"wrote build.ninja and objdiff.json ({len(asm_files)} asm files, {len(C_UNITS)} C units)")


if __name__ == "__main__":
    main()
