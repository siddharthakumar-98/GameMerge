# c_cpp/

The C/C++ side of the Burnout 3 decomp: source that CodeWarrior (`../compilers/3.0.3-020716/`) compiles into exactly
the original bytes.

| Path | What it is |
|---|---|
| `src/` | Decompiled C/C++ (`.c` or `.cpp`). Each file replaces the assembly unit with the same path under `../assembly/asm/`. |
| `include/` | Shared headers (passed to the compiler as `MWCIncludes`) |

## Adding a unit

1. Carve the function(s) out of their `game/text_<VRAM>` range in `../assembly/splat/b3.yaml`, and name the
   remainder after them `game/text_<VRAM>`. CodeWarrior functions always start on 16-byte boundaries, so the
   unit's start and end are too.
2. Write the C/C++ in `src/` with the same path.
3. Iterate with `tools/dock python3 tools/funcmatch.py <function> c_cpp/src/<unit>.c` until it reports 100%.
4. Add the unit to `C_UNITS` in `../configure.py` with `linked: True`. If it owns data, such as a switch's jump
   table, also carve that data and map it under `data`.
5. Run `tools/dock python3 configure.py && tools/dock ninja`. The build must still print `332be40d… OK`.

## Current units (D2 compiler tests)

| Unit | Functions | Tests | Status |
|---|---|---|---|
| `src/d2/func_0013C910.c` | `func_0013C910`, `func_0013C930` | leaf, two functions in one file | 100%, linked |
| `src/d2/func_00131AA0.c` | `func_00131AA0` | leaf, array of structs | 100%, linked |
| `src/d2/func_0014E7E0.c` | `func_0014E7E0`, `func_0014E830` | float to int, float copies | 100%, linked |
| `src/d2/func_0014DD80.c` | `func_0014DD80` | float return with a branch | 100%, linked |
| `src/d2/func_00136E00.c` | `func_00136E00` | global through `$gp` | 100%, linked |
| `src/d2/func_0013B740.c` | `func_0013B740` | call with stack frame | 100%, linked |
| `src/d2/func_0014EC30.c` | `func_0014EC30` | switch, jump table placed in data | 100%, linked |
| `src/d2/func_0028B700.cpp` | `CUnk0028B700::CUnk0028B700()` | C++ constructor and vtable | 100%, linked |
| `src/d2/func_00131CE0.c` | `func_00131CE0` | large struct offsets | 98.75%, not linked |
| `src/d2/func_0013AE70.c` | `func_0013AE70` | call or return 0 | 90.38%, not linked |
| `src/d2/func_0013B670.c` | `func_0013B670` | min/max clamp | draft; the original is inline asm |

Class and struct names such as `CUnk0028B700` are placeholders until the real ones are known. Details of how the
compiler was identified are in [../docs/compiler.md](../docs/compiler.md).
