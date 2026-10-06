/* D2 test, NOT MATCHING (not linked): add then clamp to [0, 1999999999].
 * The original uses EE min/max instructions (pmaxw/pminw, then pextlw), which CodeWarrior never emits from
 * C, so the original is almost certainly an inline-asm clamp helper. This C is a functional draft only;
 * see docs/compiler.md. */

typedef struct Unk0013B670 {
    char pad[0x40];
    int score;
} Unk0013B670;

void func_0013B670(Unk0013B670 *obj, int amount)
{
    obj->score += amount;
    if (obj->score < 0) {
        obj->score = 0;
    }
    if (obj->score > 1999999999) {
        obj->score = 1999999999;
    }
}
