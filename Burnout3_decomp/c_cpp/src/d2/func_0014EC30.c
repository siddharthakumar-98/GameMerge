/* D2 test: a switch compiled to a jump table (7 entries, cases 0-6). The table lives in the data
 * section at 0x4B60D0; configure.py places this object's copy of it there. */

typedef struct Unk0014EC30 {
    char pad[0x57C];
    int state;
    int param;
    char pad2[0x58B - 0x584];
    unsigned char flag;
} Unk0014EC30;

void func_0014EC30(Unk0014EC30 *obj, int mode, int param, unsigned char flag)
{
    obj->param = param;
    obj->flag = flag;
    switch (mode) {
    case 0:
        obj->state = 1;
        break;
    case 1:
        obj->state = 4;
        break;
    case 2:
        obj->state = 3;
        break;
    case 3:
        obj->state = 2;
        break;
    case 4:
        obj->state = 5;
        break;
    case 6:
    default:
        obj->state = 0;
        break;
    }
}
