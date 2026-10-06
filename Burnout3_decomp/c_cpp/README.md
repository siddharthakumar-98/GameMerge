# c_cpp/

The C/C++ side of the Burnout 3 decomp: source that CodeWarrior (`../compilers/`) compiles into exactly the
original bytes.

| Path | What it is |
|---|---|
| `src/` | Decompiled C/C++. Each file replaces the assembly unit with the same path under `../assembly/asm/`. |
| `include/` | Shared headers (passed to the compiler as `MWCIncludes`) |

A unit is added to `C_UNITS` in `../configure.py`. Once objdiff shows 100% for it, it's marked `linked`, and the
full build then links the C object instead of the assembly. The build's SHA-1 check proves the result.

Current units:

| Unit | Status |
|---|---|
| `src/d2/func_0013C910.c` | 100% match, linked (first D2 test function) |
