"""Python reference implementation of the demo simulation model.

Mirrors demo/src/*.js exactly. Used to generate golden vectors for the JS tests.
Run: python tools/reference.py > tools/golden.json
"""
import json

M32 = 0xFFFFFFFF


def _i32(x):
    x &= M32
    return x - 0x100000000 if x & 0x80000000 else x


def _imul(a, b):
    return _i32((_i32(a) * _i32(b)) & M32)


def mulberry32(seed):
    state = {"a": _i32(seed)}

    def nxt():
        state["a"] = _i32(state["a"] + 0x6D2B79F5)
        a = state["a"]
        t = _imul(a ^ ((a & M32) >> 15), 1 | a)
        t = _i32((t + _imul(t ^ ((t & M32) >> 7), 61 | t)) & M32) ^ t
        return ((t ^ ((t & M32) >> 14)) & M32) / 4294967296

    return nxt


if __name__ == "__main__":
    r = mulberry32(1337)
    print(json.dumps({"mulberry32_1337": [round(r(), 12) for _ in range(6)]}, indent=2))
