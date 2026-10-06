/* D2 compiler/flags test: first function moved from assembly to C.
 * func_0013C910 adds a value to one entry of an int array at offset 0x1C0 of a game object.
 * The real struct and names are unknown until D3/D4; this layout covers only what the
 * function touches. */

typedef struct Unk0013C910 {
    char pad[0x1C0];
    int counts[1];
} Unk0013C910;

void func_0013C910(Unk0013C910 *obj, int index, int amount)
{
    obj->counts[index] += amount;
}
