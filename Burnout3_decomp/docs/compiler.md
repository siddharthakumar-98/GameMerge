# Compiler identification (D2)

**Result:** Metrowerks CodeWarrior for PS2 **Version 3.0.3** (decomp.me `mwcps2-3.0.3-020716`) at **`-O4`**. With
this compiler and no other options, 10 functions in 8 translation units compile to the original bytes and link
into a build with the original SHA-1.

## The version stamp narrows it to four builds

The game's `.comment` section reads `MW MIPS C Compiler (2.4.1.01)`. That is the code generator's version, and
several releases share it. Compiling the same file with every PS2 CodeWarrior build on decomp.me:

| Build | Stamp | Note |
|---|---|---|
| 2.3.3 (Sep 2000) | `2.3.1.01` | ruled out |
| **2.4 Engineering Build 0017** (Dec 2000) | `2.4.1.01` | candidate |
| **3.0** (Nov 2001) | `2.4.1.01` | candidate |
| **3.0.1** (Jan 2002) | `2.4.1.01` | candidate |
| **3.0.3** (Jul 2002) | `2.4.1.01` | candidate |
| 3.0 builds 38–52, 3.0.1 builds 44–210 (Mar 2003 – Mar 2006) | `3.0.0` | ruled out |

## Test functions decide between them

Each function was compiled at `-O3`, `-O4`, `-O4 -opt speed` and `-O4 -opt space` with `tools/funcmatch.py`. All
four flag sets gave the same result for every function, so the table shows one value per compiler.

| Function | What it tests | 2.4 EB0017 | 3.0 | 3.0.1 | 3.0.3 |
|---|---|---|---|---|---|
| `func_0013C910`, `func_0013C930` | leaf, two functions in one file | 100% | 100% | 100% | **100%** |
| `func_00131AA0` | leaf, array of structs | 100% | 100% | 100% | **100%** |
| `func_0014E830` | float loads and stores | 100% | 100% | 100% | **100%** |
| `func_0014E7E0` | float to int | 0% (calls `fptosi`) | 0% | 0% | **100%** (inline `cvt.w.s`) |
| `func_0014DD80` | float return with a branch | 100% | 100% | 100% | **100%** |
| `func_00136E00` | global through `$gp` | 100% | 100% | 100% | **100%** |
| `func_0013B740` | call with stack frame | 82% (`sq`/`lq` saves, `paddub` moves) | 100% | 100% | **100%** |
| `func_0014EC30` | switch with jump table | not tested | not tested | not tested | **100%** |
| `__ct__12CUnk0028B700Fv` | C++ constructor installing a vtable | not tested | not tested | not tested | **100%** |
| `func_00131CE0` | large struct offsets | 87.5% | 94.7% | 98.75% | 98.75% |
| `func_0013AE70` | call or return 0 | 70.8% | 90.4% | 90.4% | 90.4% |
| `func_0013B670` | clamp with `pmaxw`/`pminw` | 0% | 0% | 0% | 0% |

- **EB0017 is ruled out.** It keeps registers 128-bit, using `paddub` moves and `sq`/`lq` saves where the game
  uses `daddu` and `sd`/`ld`. `#pragma processor VR5000` fixes the moves but not the saves.
- **3.0 and 3.0.1 are ruled out.** They call the `fptosi` helper for float-to-int, where the game has an inline
  `cvt.w.s`.
- **3.0.3 matches everything that matches anywhere.**

## Open items

- **`-O3` vs `-O4`, speed vs space:** no test function separates them yet. `configure.py` uses `-O4`. Functions
  with loops should settle it.
- **`func_0013AE70` (90%):** the original leaves the conditional branch's delay slot empty and sets the return
  value in the next branch's slot. Every 3.0.x build fills the first slot instead. Notably, EB0017 reproduces the
  original's branch layout, so this may point to a build between EB0017 and 3.0 that isn't on decomp.me, or to a
  source form not found yet. Eight source variants tried.
- **`func_00131CE0` (98.75%):** a single register choice. The original computes a large field offset in `v0`; ours
  uses `at`. Five source variants tried.
- **`func_0013B670`:** CodeWarrior never emits `pmaxw`/`pminw` from C (`MIN`/`MAX` macros and
  `#pragma conditional_move` both produce branches), and the trailing `pextlw` looks hand-written. The original is
  almost certainly an inline-asm clamp helper. It stays in assembly until inline asm is worked out.

## Reproducing

All builds above can be fetched from https://github.com/decompme/compilers/releases into `compilers/<version>/`
(gitignored), then compared with:

```bash
tools/dock python3 tools/funcmatch.py func_0013B740 c_cpp/src/d2/func_0013B740.c -c compilers/3.0.3-020716 -f=-O4
```
