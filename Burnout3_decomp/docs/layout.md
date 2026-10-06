# SLUS_210.50 memory layout

The executable is a CodeWarrior (`MW MIPS C Compiler (2.4.1.01)`) ELF with **one merged PT_LOAD**. The linker kept no
section headers, so the boundaries below were recovered by hand. They are encoded in
[`../assembly/splat/b3.yaml`](../assembly/splat/b3.yaml), and the build reproduces the original SHA-1 with them.
`tools/xref.py` (function/data cross-references, compiler fingerprints, strings) regenerates the evidence.

ELF: entry `0x100008`, load segment file offset `0x100`, vaddr `0x100000`, filesz `0x3E2680`, memsz `0x1DCEA00`.
`.reginfo` gives `_gp = 0x4E8670`.

## Sections

| VRAM | Rom offset | Section | Evidence |
|---|---|---|---|
| `0x100000`–`0x469E00` | `0x000000` | `.text` (8,946 functions) | Valid R5900 code throughout. The last `jr $ra` is at `0x469D88`, then zero padding to a 0x80 boundary. |
| `0x469E00`–`0x483F00` | `0x369E00` | VU microcode in DMA/VIF chains | 27 microprograms, [below](#vu-microcode). Data ends at `0x483EA0`, then zero padding. |
| `0x483F00`–`0x4B1500` | `0x383F00` | `.data` | Starts with Sony library version tags (`PsIIlibgraph2800`, …). Code writes here; no `__sinit` writes. |
| `0x4B1500`–`0x4D3E00` | `0x3B1500` | `.rodata` | Starts with the MW runtime's `std::exception` RTTI. Holds strings, `const` tables, RTTI, jump tables, and `const` objects that `__sinit` fills in. |
| `0x4D3E00`–`0x4DD820` | `0x3D3E00` | `.init`: C++ static initializers (`__sinit_*`) | Code placed after data; reached only through `.ctor`. A test compile shows CodeWarrior emits `__sinit_*` into `.init`. |
| `0x4DD820`–`0x4DDAA0` | `0x3DD820` | `.ctor`: 158 pointers into `.init`, a null terminator and padding | |
| `0x4DDAA0`–`0x4E0680` | `0x3DDAA0` | `.vtables` | Entries are `{RTTI*, 0, methods…}`; the first is `std::exception`'s. A test compile shows CodeWarrior emits vtables into `.vtables`. |
| `0x4E0680`–`0x4E2680` | `0x3E0680` | `.sdata` | `_gp - 0x7FF0`. The lowest `$gp`-relative access in the code is exactly `0x4E0680`. |
| `0x4E2680`–`0x1ECEA00` | — | `.sbss` + `.bss` (NOLOAD) | `$gp`-relative accesses continue past `0x4E8670`; the large remainder is static pools. The exact `.sbss`/`.bss` split is still open. |

How `.data` and `.rodata` were told apart: every unit's `.data` piece comes before every unit's `.rodata` piece, so
code references form two separate, increasing streams. Only the `.rodata` stream is written by `__sinit` (const
objects with constructors), and it holds the D2 jump table and RenderWare's `$Id` strings, which CodeWarrior and GCC
both put in `.rodata`. The game's string literals are in `.rodata` too, which needs `-str readonly`
([compiler.md](compiler.md)).

## `.text` by library

Library code was built with ee-gcc and game code with CodeWarrior, and the two are told apart by codegen
fingerprints that hold across the whole binary:

- **CodeWarrior** starts every function on a 16-byte boundary (all 6,197 game functions) and doesn't emit
  branch-likely instructions (`beql`, `bnel`, `bgezl`…; only 2 game functions contain any, see below).
- **ee-gcc** aligns functions to 8 bytes, so about half of them start at an address ending in 8, and it uses
  branch-likely freely.
- Edges were then settled function by function: libraries never call game code, library data and strings sit
  inside the library's stretch of `.data`/`.rodata`, and functions listed in `.vtables` are CodeWarrior C++.

`python3 tools/xref.py compilers` prints the fingerprint regions. Units in order:

| VRAM | Unit | Category | Evidence |
|---|---|---|---|
| `0x100000` | `runtime/crt0` | runtime | `_start` (clears GPRs with `padduw`), `_exit`, syscall stubs, static-init caller |
| `0x100270` | `runtime/mwrt` | runtime | Metrowerks C++ runtime: `__construct_array`, `std::exception`/`bad_exception`. CodeWarrior-built, but with 128-bit `sq`/`lq` saves (a different build from the game's compiler). |
| `0x102380` | `sce/libgraph` | sce | `sceGs*` strings; called from RenderWare sky2 |
| `0x103BC8` | `sce/libdma` | sce | `libdma: sync timeout` |
| `0x104410` | `sce/mpeg_ipu` | sce | libmpeg (`sceMpeg*` strings, macroblock decoder) followed by libipu (`PsIIlibipu` data); not yet split |
| `0x10BA00` | `sce/libkernl` | sce | 138 syscall stubs, then libkernl (`## internel error in libkernl.a!`, TTY, TLB setup) |
| `0x117078` | `runtime/libm` | runtime | fdlibm double-precision math (constant tables of 1/3, …) |
| `0x11E3A0` | `sce/libcdvd` | sce | `Libcdvd bind err …` |
| `0x11FD00` | `runtime/libc` | runtime | newlib (`bug in vfprintf: bad base`, `ctype` table, `Infinity`), then libgcc soft-float double routines |
| `0x12EB30` | `game/…` | game | `main` |
| `0x1D8260` | `rw/renderware` | rw | RenderWare 3.6: the first function uses `babinary.c`'s `.rodata`; 12 `$Id` strings run `babinary.c` … `p2heap.c`, then the PS2 sky2 driver |
| `0x211C30` | `game/…` | game | |
| `0x215660` | `sce/pad2_dbc` | sce | libpad2 then libdbc; ends with libdbc's no-op `printf` |
| `0x216E40` | `game/…` | game | includes online code (`GtComm`, UPnP port mapping) |
| `0x2372F0` | `sce/insck_mrpc` | sce | libinsck (`PsIIlibinsck` data) to about `0x23A740`, then libmrpc (`sceSifMCallRpc`) |
| `0x23AFD0` | `game/…` | game | |
| `0x241BC0` | `sce/mc2_netcnfif_scf` | sce | libmc2, netcnfif, libscf |
| `0x24B2A0` | `game/…` | game | |
| `0x2C28C0` | `lg/lgcodec` | lg | Logitech headset codec (`lgCodecUlawEncode`) |
| `0x2E2700` | `game/…` | game | |
| `0x304008` | `lg/lgkbm` | lg | Logitech USB keyboard/mouse (`LgKbM library version … May 18 2004`) |
| `0x306D90` | `game/…` | game | |
| `0x3D3158` | `sce/libnet` | sce | `insufficient buffer size in Libnet` |
| `0x3D46A0` | `game/…` | game | |
| `0x3FFE48` | `ea/dirtysock` | ea | EA DirtySock (`dirtyaddr`, `rpc-e:`, lobby API) |
| `0x41C900` | `game/…` | game | |
| `0x443860` | `lg/lgdev` | lg | Logitech wheels and force feedback (`liblgdev version 1.11.027, May 10 2004`) |
| `0x445300` | `game/…` | game | runs to the end of `.text` |

The game ranges are still one unit each (named `game/text_<VRAM>`), apart from the D2 units carved out of them.
Two single functions inside game ranges (`0x2174A0`, `0x2FC530`) use branch-likely but sit between CodeWarrior
functions and are called from game code; they are probably game functions with inline asm.

Libraries that CodeWarrior compiled as part of the game project (RenderWare Audio's EE side, for example) can't
be told apart by fingerprint and are still inside the game ranges.

## VU microcode

One splat piece per microprogram (`vu/rw_<VRAM>`, `vu/game_<VRAM>`, symbols `vu_rw_*`/`vu_game_*`). Each starts
with a DMA tag (`ret` or `end`) followed by VIF `MPG` uploads, and code passes its address to the DMA.

| VRAM | Owner | Referenced from |
|---|---|---|
| `0x469E00`, `0x46A000`, `0x46A270`, `0x46A3D0`, `0x46A560` | RenderWare sky2 | pipeline tables at `0x4B9474`–`0x4B9488` and `0x49AD80` |
| `0x46A590` … `0x4839E0` (22 programs) | game | one game function each |

## Data inside libkernl's `.data`

libkernl carries kernel patches as code stored in `.data` (linked to run at `0x8007xxxx` and installed through
syscalls `0x5A`/`0x5B`): about `0x484240`–`0x484500`, `0x4848C0`–`0x484F40` and `0x485080`–`0x485740`, with their
install tables at `0x485040` and `0x4857C8`. They stay data.

## Open items

- Carve the game ranges into translation units. Anchors: `.ctor`/`.init` order (158 units with static
  initializers), `.vtables` order (each vtable points into its unit's functions), and the order of each unit's
  `.data`, `.rodata` and `.sdata` pieces.
- Split the combined library units (`sce/mpeg_ipu`, `sce/pad2_dbc`, `sce/insck_mrpc`, `sce/mc2_netcnfif_scf`,
  `runtime/libc` from libgcc) and carve `.data`/`.rodata` per library.
- Confirm the `.sbss`/`.bss` split.
- 116 symbols still resolve to absolute addresses (`build/undefined_syms_auto.txt`), mostly references into the
  middle of functions or data objects. They must become real symbols before the shift build can pass.
