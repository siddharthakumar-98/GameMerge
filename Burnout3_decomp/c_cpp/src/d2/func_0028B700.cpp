/* D2 test: a C++ constructor. It only installs the class's vtable (at offset 0) and returns this.
 * The real class name and members are unknown until D3/D4; CUnk0028B700 is a placeholder. The
 * virtual functions are defined elsewhere, so the vtable (__vt__12CUnk0028B700, 0x4DE1A0) is
 * emitted by another translation unit. */

class CUnk0028B700 {
public:
    CUnk0028B700();
    virtual ~CUnk0028B700();
};

CUnk0028B700::CUnk0028B700()
{
}
