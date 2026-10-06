/* D2 test: leaf function. Reads a field from the index-th 16-byte element of an array pointer. */

typedef struct Elem00131AA0 {
    int a;
    int b;
    int value;
    int d;
} Elem00131AA0;

typedef struct Unk00131AA0 {
    char pad[0xC];
    Elem00131AA0 *elems;
} Unk00131AA0;

int func_00131AA0(Unk00131AA0 *obj, int index)
{
    return obj->elems[index].value;
}
