/* D2 test, NOT MATCHING (98.75%, not linked): offsets beyond 16 bits into a large object, pointer
 * comparison, bool return. The original computes the first large offset in v0; CodeWarrior 3.0.3 uses at.
 * See docs/compiler.md. */

typedef struct Owner00131CE0 {
    char pad[0x1B8];
    void *owner;
} Owner00131CE0;

typedef struct Unk00131CE0 {
    char pad[0x2D8E8];
    char sub[0x2DA48 - 0x2D8E8];
    Owner00131CE0 *current;
} Unk00131CE0;

int func_00131CE0(Unk00131CE0 *obj)
{
    if (obj->current != 0 && obj->current->owner == obj->sub) {
        return 1;
    }
    return 0;
}
