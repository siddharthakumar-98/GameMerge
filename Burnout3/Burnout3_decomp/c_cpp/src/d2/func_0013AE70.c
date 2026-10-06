/* D2 test, NOT MATCHING (90.38%, not linked): returns a call's result, or 0 for an invalid (-1) handle.
 * The original leaves the conditional branch's delay slot empty; CodeWarrior 3.0.3 fills it with the
 * return value. See docs/compiler.md. */

typedef struct Unk0013AE70 {
    char pad[0x330];
    int handle;
} Unk0013AE70;

int func_003EB020(int handle);

int func_0013AE70(Unk0013AE70 *obj)
{
    if (obj->handle == -1) {
        return 0;
    }
    return func_003EB020(obj->handle);
}
