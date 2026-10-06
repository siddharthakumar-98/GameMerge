# assembly/

The assembly side of the Burnout 3 decomp: everything splat needs to turn your `SLUS_210.50` into assembly
the build can reassemble byte-for-byte.

| Path | What it is | Committed |
|---|---|---|
| `splat/b3.yaml` | How the load segment is split into code, data, VU microcode and carved-out units | yes |
| `include/` | Assembler macros used by the generated `.s` files | yes |
| `asm/` | Generated assembly, one file per unit | **no** (regenerated from your ELF) |
| `assets/` | Generated binary blobs (VU microcode) | **no** |

Symbol names and relocation overrides shared with the C side live in `../config/`.
`../configure.py` runs splat and builds everything. A function carved out here can be replaced by C from
`../c_cpp/src/` once it matches.
