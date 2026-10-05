# SLUS_210.50 memory layout

The executable is a CodeWarrior (`MW MIPS C Compiler (2.4.1.01)`) ELF with **one merged PT_LOAD**. The linker kept no
`.text`/`.data` section headers, so the boundaries below were recovered by hand. They are encoded in
[`../splat/b3.yaml`](../splat/b3.yaml), and the asm-only build reproduces the original SHA-1 with them.

ELF: entry `0x100008`, load segment file offset `0x100`, vaddr `0x100000`, filesz `0x3E2680`, memsz `0x1DCEA00`.
`.reginfo` gives `_gp = 0x4E8670`.

| VRAM | Rom offset | Region | Evidence |
|---|---|---|---|
| `0x100000`–`0x469E00` | `0x000000` | `.text`: crt0, game, RenderWare, libsce, MW runtime (8,948 functions) | Valid R5900 code throughout. The last `jr $ra` is at `0x469D88`, then zero padding to a 0x80 boundary. `_start` at `0x100008` clears GPRs with `padduw`. |
| `0x469E00`–`0x483F00` | `0x369E00` | VU microcode in DMA/VIF chains (`vutext`, kept as an opaque blob) | Starts with a DMA tag followed by VIF `MPG` packets. The region is dense with VU lower/upper NOPs (`0x8000033C`/`0x000002FF`). Data ends at `0x483EA0`, then zero padding. |
| `0x483F00`–`0x4D3E00` | `0x383F00` | `.data`/`.rodata` | Begins with Sony library version tags (`PsIIlibgraph2800`, `PsIIlibkernl…`). Contains libkernl's kernel-patch blob (code linked for about `0x80074000`, stored as data), strings, and switch jump tables pointing into the end of `.text`. |
| `0x4D3E00`–`0x4DD820` | `0x3D3E00` | C++ static initializers (`__sinit_*`) | Real code placed after data. Nothing calls it directly, and every function is reached through the `.ctor` table. |
| `0x4DD820`–`0x4DDAA0` | `0x3DD820` | `.ctor`: 158 pointers into the sinit block, a null terminator and padding | |
| `0x4DDAA0`–`0x4E0680` | `0x3DDAA0` | More `.data` | |
| `0x4E0680`–`0x4E2680` | `0x3E0680` | `.sdata` | `_gp - 0x7FF0`. The lowest `$gp`-relative access in the code is exactly `0x4E0680`. |
| `0x4E2680`–`0x1ECEA00` | — | `.sbss` + `.bss` (NOLOAD) | `$gp`-relative accesses continue to `0x4E8670`. The large remainder is static pools. The `.sbss`/`.bss` split is still to be confirmed (D3). |

## Open items (D3)
- Split `.data` from `.rodata`. This matters once C translation units own their own data.
- Carve translation units out of `text`. Anchors include RenderWare `$Id:` strings, libsce version tags, string and
  rodata clustering, and `.ctor`/vtable order.
- Label the libkernl blob and the VU microcode programs.
