/* D2 compiler/flags test: two neighbouring functions from one original source file.
 * They add to and read one entry of an int array at offset 0x1C0 of a game object.
 * The real struct and names are unknown until D3/D4; this layout covers only what they touch. */

typedef struct Unk0013C910 {
    char pad[0x1C0];
    int counts[1];
} Unk0013C910;

void func_0013C910(Unk0013C910 *obj, int index, int amount)
{
    obj->counts[index] += amount;
}

int func_0013C930(Unk0013C910 *obj, int index)
{
    return obj->counts[index];
}
