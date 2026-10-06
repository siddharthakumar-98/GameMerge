/* D2 test: float conversion. Two neighbouring getters that copy three floats (at 0x3A0..0x3A8 of a
 * sub-object) out through pointers, first truncated to int, then as floats. */

typedef struct Vec0014E7E0 {
    char pad[0x3A0];
    float a;
    float b;
    float c;
} Vec0014E7E0;

typedef struct Unk0014E7E0 {
    char pad[0x564];
    Vec0014E7E0 *vec;
} Unk0014E7E0;

void func_0014E7E0(Unk0014E7E0 *obj, int *c, int *b, int *a)
{
    *c = (int)obj->vec->c;
    *b = (int)obj->vec->b;
    *a = (int)obj->vec->a;
}

void func_0014E830(Unk0014E7E0 *obj, float *c, float *b, float *a)
{
    *c = obj->vec->c;
    *b = obj->vec->b;
    *a = obj->vec->a;
}
