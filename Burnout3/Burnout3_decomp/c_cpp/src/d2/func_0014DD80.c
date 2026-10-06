/* D2 test: float return with a branch. */

typedef struct A0014DD80 {
    char pad[0x24];
    float value;
    char pad2[0x52 - 0x28];
    unsigned char active;
} A0014DD80;

typedef struct B0014DD80 {
    char pad[0x10CC];
    float value;
} B0014DD80;

float func_0014DD80(A0014DD80 *a, B0014DD80 *b)
{
    if (a->active) {
        return b->value - a->value;
    }
    return 0.0f;
}
