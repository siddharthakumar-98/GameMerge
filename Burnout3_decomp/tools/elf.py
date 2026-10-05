#!/usr/bin/env python3
"""Split SLUS_210.50 into its load segment, and rebuild the exact ELF container around one.

The shipped executable is a CodeWarrior-linked ELF with a single merged PT_LOAD holding all
code and data, plus a short trailer (.shstrtab, .comment, .reginfo, section headers). splat and
the build work on the raw load segment (the "rom"); `rebuild` wraps a segment back into a
byte-identical container. Only structural parameters live here, never game bytes.

    elf.py extract orig/SLUS_210.50 orig/SLUS_210.50.rom
    elf.py rebuild build/SLUS_210.50.rom build/SLUS_210.50
"""

import argparse
import hashlib
import struct
import sys
from pathlib import Path

TARGET_SHA1 = "332be40d6081b8b5055a6ea01194ad6ff662a863"

ENTRY = 0x00100008
E_FLAGS = 0x20924000  # EF_MIPS_NOREORDER | R5900 arch/mach bits as written by mwld

LOAD_VADDR = 0x00100000
LOAD_OFFSET = 0x100
LOAD_FILESZ = 0x003E2680
LOAD_MEMSZ = 0x01DCEA00
LOAD_ALIGN = 0x80

# mwld emits two empty PT_LOADs after the real one: one at 0 (R) and one at the end of
# memory (RW), each backed by an empty unnamed section.
EMPTY_SEGMENTS = [(0x00000000, 0x4), (0x01ECEA00, 0x6)]

SHSTRTAB = b"\0.shstrtab\0.strtab\0.symtab\0.comment\0.reginfo\0"
COMMENT = b"MW MIPS C Compiler (2.4.1.01)\0PlayStation2\0"
REGINFO_GPRMASK = 0xF7FFFFFE
REGINFO_CPRMASK = (0x00000000, 0xFFFFFFFF, 0x00000000, 0x00000000)
GP_VALUE = 0x004E8670

SHT_PROGBITS, SHT_SYMTAB, SHT_STRTAB, SHT_MIPS_REGINFO = 1, 2, 3, 0x70000006


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def build_elf(segment: bytes) -> bytes:
    if len(segment) != LOAD_FILESZ:
        sys.exit(f"segment is {len(segment):#x} bytes, expected {LOAD_FILESZ:#x}")

    shstrtab_off = LOAD_OFFSET + LOAD_FILESZ
    comment_off = shstrtab_off + len(SHSTRTAB)
    reginfo_off = comment_off + len(COMMENT)
    reginfo = struct.pack("<6I", REGINFO_GPRMASK, *REGINFO_CPRMASK, GP_VALUE)
    shoff = reginfo_off + len(reginfo)
    trailer_off = shstrtab_off  # empty sections/segments point here

    def name(s: str) -> int:
        return SHSTRTAB.index(s.encode() + b"\0") if s else 0

    # (name, type, flags, addr, offset, size, link, info, addralign, entsize)
    sections = [
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (name(".shstrtab"), SHT_STRTAB, 0, 0, shstrtab_off, len(SHSTRTAB), 0, 0, 1, 1),
        (name(".strtab"), SHT_STRTAB, 0, 0, 0, 0, 0, 0, 1, 1),
        (name(".symtab"), SHT_SYMTAB, 0, 0, 0, 0, 2, 0, 1, 0x10),
        (0, SHT_PROGBITS, 0x7, LOAD_VADDR, LOAD_OFFSET, LOAD_FILESZ, 0, 0, LOAD_ALIGN, 1),
    ]
    for vaddr, pflags in EMPTY_SEGMENTS:
        # section flags: R -> ALLOC (0x2), RW -> ALLOC|WRITE (0x3)
        sflags = 0x3 if pflags & 0x2 else 0x2
        sections.append((0, SHT_PROGBITS, sflags, vaddr, trailer_off, 0, 0, 0, 0x10, 1))
    sections += [
        (name(".comment"), SHT_PROGBITS, 0, 0, comment_off, len(COMMENT), 0, 0, 1, 1),
        (name(".reginfo"), SHT_MIPS_REGINFO, 0, 0, reginfo_off, len(reginfo), 0, 0, 4, 1),
    ]

    phdrs = [(1, LOAD_OFFSET, LOAD_VADDR, LOAD_VADDR, LOAD_FILESZ, LOAD_MEMSZ, 0x7, LOAD_ALIGN)]
    phdrs += [(1, trailer_off, v, v, 0, 0, f, 0x10) for v, f in EMPTY_SEGMENTS]

    ident = b"\x7fELF" + bytes([1, 1, 1]) + bytes(9)
    ehdr = ident + struct.pack(
        "<HHIIIIIHHHHHH",
        2, 8, 1, ENTRY, 0x34, shoff, E_FLAGS,
        0x34, 0x20, len(phdrs), 0x28, len(sections), 1,
    )
    out = bytearray(ehdr)
    for ph in phdrs:
        out += struct.pack("<8I", *ph)
    out += bytes(LOAD_OFFSET - len(out))
    out += segment
    out += SHSTRTAB + COMMENT + reginfo
    for sh in sections:
        out += struct.pack("<10I", *sh)
    return bytes(out)


def cmd_extract(args: argparse.Namespace) -> None:
    data = Path(args.elf).read_bytes()
    if sha1(data) != TARGET_SHA1:
        sys.exit(f"{args.elf}: SHA-1 {sha1(data)} does not match the supported build {TARGET_SHA1}")
    segment = data[LOAD_OFFSET:LOAD_OFFSET + LOAD_FILESZ]
    if build_elf(segment) != data:
        sys.exit("container layout in elf.py does not reproduce the original; fix the parameters")
    Path(args.rom).write_bytes(segment)
    print(f"wrote {args.rom} ({len(segment):#x} bytes)")


def cmd_rebuild(args: argparse.Namespace) -> None:
    elf = build_elf(Path(args.rom).read_bytes())
    Path(args.elf).write_bytes(elf)
    digest = sha1(elf)
    status = "OK" if digest == TARGET_SHA1 else "MISMATCH"
    print(f"{args.elf}: {digest} {status}")
    if args.check and digest != TARGET_SHA1:
        sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)
    e = sub.add_parser("extract", help="verify the original ELF and write its load segment")
    e.add_argument("elf")
    e.add_argument("rom")
    e.set_defaults(func=cmd_extract)
    r = sub.add_parser("rebuild", help="wrap a load segment into the original ELF container")
    r.add_argument("rom")
    r.add_argument("elf")
    r.add_argument("--check", action="store_true", help="exit non-zero unless the SHA-1 matches")
    r.set_defaults(func=cmd_rebuild)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
