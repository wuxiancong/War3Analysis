#!/usr/bin/env python3
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from pathlib import Path

data = Path(r"C:\War3Analysis\samples\1.27.0.52240\game.dll").read_bytes()
TEXT_RAW=0x400; TEXT_VA=0x6F001000; TEXT_RSZ=0x94D000
tb=data[TEXT_RAW:TEXT_RAW+TEXT_RSZ]
md=Cs(CS_ARCH_X86, CS_MODE_32)

def off_to_va(o): return TEXT_VA+(o-TEXT_RAW)
def va_to_off(va): return va-TEXT_VA+TEXT_RAW
def cstr(va):
    o=va-0x6F000000-0xC00
    if o<0 or o>=len(data): return "?"
    return data[o:data.find(b"\0",o)].decode("latin1","replace")

print("=== settings type table key -> first dword @ 0x6F950DD0 + key*16 ===")
for key in range(0, 0x30):
    va=0x6F950DD0 + key*16
    o=va-0x6F000000-0xC00
    a,b,c,d=struct.unpack_from("<IIII", data, o)
    names=[]
    for x in (a,b,c,d):
        if 0x6F94E000<=x<=0x6FB00000:
            s=cstr(x)
            if s and all(32<=ord(ch)<127 for ch in s) and 1<len(s)<32:
                names.append(s)
    mark=""
    if "maxfps" in names or "lockfb" in names or "refreshrate" in names:
        mark=" <==="
    print(f"key 0x{key:02X} ({key:2d}) @{va:08X}: {a:08X} {b:08X} {c:08X} {d:08X} {names}{mark}")

def find_calls(target):
    hits=[]
    s=0
    while True:
        i=tb.find(b"\xE8", s)
        if i<0 or i+5>len(tb): break
        rel=struct.unpack_from("<i", tb, i+1)[0]
        dest=off_to_va(TEXT_RAW+i)+5+rel
        if dest==target:
            hits.append(off_to_va(TEXT_RAW+i))
        s=i+1
    return hits

for name,t in [("get_mgr/slot 6f023e00",0x6F023E00),("apply 6f023240",0x6F023240),
               ("set_val 6f025a70",0x6F025A70),("get_int? 6f023ed0",0x6F023ED0),
               ("setrs 6f0ef3a0",0x6F0EF3A0),("fill_pp  containing 6f0ec759",0x6F0EC680)]:
    print(f"\ncalls to {name}:")

print("\n=== calls to 0x6F023E00 ===")
hits=find_calls(0x6F023E00)
print("count", len(hits))
for va in hits:
    o=va_to_off(va)
    # look back 12 bytes for push 0x16
    ctx=data[o-12:o+5]
    flag=" KEY16" if b"\x6A\x16" in data[o-16:o] else ""
    print(f"  0x{va:08X}{flag}  prev={data[o-12:o].hex(' ')}")

print("\n=== 1000 imm (3E8) near idiv in .text, capped ===")
s=0; n=0
while n<40:
    i=tb.find(b"\xE8\x03\x00\x00", s)  # could be part of 00 E8 03 00 00 00 = mov r, 1000
    if i<0: break
    # require B8/B9/... or 68 push
    prev=tb[i-1] if i>0 else 0
    if prev in (0xB8,0xB9,0xBA,0xBB,0xBC,0xBD,0xBE,0xBF,0x68) or (i>=2 and tb[i-2]==0x81):
        va=off_to_va(TEXT_RAW+i-1 if prev in range(0xB8,0xC0) or prev==0x68 else TEXT_RAW+i)
        print(f"  0x{off_to_va(TEXT_RAW+max(0,i-1)):08X} {data[TEXT_RAW+i-6:TEXT_RAW+i+10].hex(' ')}")
        n+=1
    s=i+1

print("\n=== float 1000.0 (00 00 7A 44) in .text ===")
s=0; n=0
pat=struct.pack("<f", 1000.0)
while n<15:
    i=tb.find(pat,s)
    if i<0: break
    print(f"  0x{off_to_va(TEXT_RAW+i):08X} {data[TEXT_RAW+i-6:TEXT_RAW+i+8].hex(' ')}")
    n+=1; s=i+1

print("\n=== function containing PresentationInterval=0 ===")
# walk back to CC padding / push ebp
va=0x6F0EC759
o=va_to_off(va)
start=o
while start>TEXT_RAW+0x10:
    if data[start]==0x55 and data[start+1]==0x8B and data[start+2]==0xEC:
        # previous byte cc or c3
        if data[start-1] in (0xCC,0xC3,0x90) or data[start-2:start] in (b"\xcc\xcc", b"\xc3\xcc"):
            break
    start -= 1
print("candidate start", hex(off_to_va(start)))
code=data[start:o+40]
for i in md.disasm(code[:0x200], off_to_va(start)):
    print(f"  0x{i.address:08X}  {i.mnemonic:8} {i.op_str}")
    if i.address>0x6F0EC770:
        break

print("\n=== Present call function start ===")
va=0x6F0ED2D0
o=va_to_off(va)
start=o
while start>TEXT_RAW+0x10:
    if data[start]==0x55 and data[start+1]==0x8B and data[start+2]==0xEC:
        if data[start-1] in (0xCC,0xC3,0x90):
            break
    start -= 1
print("candidate start", hex(off_to_va(start)))
for i in md.disasm(data[start:start+0x80], off_to_va(start)):
    print(f"  0x{i.address:08X}  {i.mnemonic:8} {i.op_str}")
    if i.address>=0x6F0ED2D8:
        break

print("\n=== lockfb string nearby ascii ===")
o=0x95079C
print(data[o-80:o+80].split(b"\0"))
