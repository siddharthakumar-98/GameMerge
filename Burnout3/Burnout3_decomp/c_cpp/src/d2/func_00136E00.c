/* D2 test: store to a small global (reached through $gp) plus a self-pointer. */

typedef struct Unk00136E00 {
    char pad[0x49C];
    struct Unk00136E00 *self;
} Unk00136E00;

extern int D_004E26A4;

void func_00136E00(Unk00136E00 *obj)
{
    D_004E26A4 = 0;
    obj->self = obj;
}
