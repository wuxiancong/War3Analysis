#!/usr/bin/env python3
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

data = Path(r"C:\War3Analysis\samples\1.27.0.52240\game.dll").read_bytes()
TEXT_RAW = 0x400
TEXT_VA = 0x6F001000
tb = data[TEXT_RAW : TEXT_RAW + 0x94D000]
md = Cs(CS_ARCH_X86, CS_MODE_32)


def xrefs(va, name):
    pat = struct.pack("<I", va)
    print(f"\n### {name} 0x{va:08X}")
    s = 0
    n = 0
    while True:
        i = tb.find(pat, s)
        if i < 0:
            break
        a = TEXT_VA + i
        o = TEXT_RAW + i
        hx = data[o - 8 : o + 8].hex(" ")
        print(f"  0x{a:08X} {hx}")
        n += 1
        s = i + 1
    print(" count", n)


def find_calls(target):
    hits = []
    s = 0
    while True:
        i = tb.find(b"\xE8", s)
        if i < 0 or i + 5 > len(tb):
            break
        rel = struct.unpack_from("<i", tb, i + 1)[0]
        dest = TEXT_VA + i + 5 + rel
        if dest == target:
            hits.append(TEXT_VA + i)
        s = i + 1
    return hits


def dis(va, n=64):
    o = va - TEXT_VA + TEXT_RAW
    print(f"\n==== 0x{va:08X} ====")
    for ins in md.disasm(data[o : o + n], va):
        print(f"  0x{ins.address:08X}  {ins.mnemonic:8} {ins.op_str}")


xrefs(0x6F994009, "FPS fmt")
xrefs(0x6F98B840, "fps chat")
print("\ncalls FUN_6f023ed0", [hex(x) for x in find_calls(0x6F023ED0)[:40]], "n=", len(find_calls(0x6F023ED0)))
print("calls FUN_6f023310", [hex(x) for x in find_calls(0x6F023310)[:40]], "n=", len(find_calls(0x6F023310)))

# look at apply function 0x6F023310
dis(0x6F023300, 80)
dis(0x6F023310, 120)

# 6A 16 near get-int
print("\n### push 0x16 windows near 6f023ed0 calls")
for va in find_calls(0x6F023ED0):
    o = va - TEXT_VA + TEXT_RAW
    win = data[o - 24 : o]
    if 0x16 in win:
        print(hex(va), win.hex(" "))
