/* D2 test: non-leaf function with a stack frame and a conditional call. */

typedef struct Unk0013B740 {
    char pad[0x8];
    char sub[1];
} Unk0013B740;

void func_002139A0(void *dest, int kind, void *value);

void func_0013B740(Unk0013B740 *obj, void *value)
{
    if (value != 0) {
        func_002139A0(obj->sub, 9, value);
    }
}
