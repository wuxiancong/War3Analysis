import struct, sys, re
data = open(sys.argv[1], 'rb').read()
pe = struct.unpack_from('<I', data, 0x3C)[0]
nsec = struct.unpack_from('<H', data, pe+6)[0]
opt = pe+24
imagebase = struct.unpack_from('<I', data, opt+28)[0]
secoff = opt + struct.unpack_from('<H', data, pe+20)[0]
secs = []
for i in range(nsec):
    o = secoff + i*40
    name = data[o:o+8].rstrip(b'\0').decode()
    vsize, va, rsize, raw = struct.unpack_from('<IIII', data, o+8)
    secs.append((name, va, vsize, raw, rsize))
def off2va(off):
    for n,va,vs,raw,rs in secs:
        if raw <= off < raw+rs: return imagebase + va + (off-raw)
for name in [b'blink', b'thunderbolt', b'stomp']:
    for m in re.finditer(b'\x00' + name + b'\x00', data):
        sva = off2va(m.start()+1)
        refs = [r.start() for r in re.finditer(re.escape(b'\x68' + struct.pack('<I', sva)), data)]
        print(name, hex(sva), 'refs', len(refs))
        for r in refs[:3]:
            print('  ', data[r-12:r+12].hex(' '))

def va2off(va):
    rva = va - imagebase
    for n,v,vs,raw,rs in secs:
        if v <= rva < v+max(vs,rs): return raw + (rva - v)
pairs = {}
for m in re.finditer(rb'\x68(.{4})\x68(.{4})\x8b\xce\xe8', data, re.S):
    sva = struct.unpack('<I', m.group(1))[0]; oid = struct.unpack('<I', m.group(2))[0]
    if not (0xD0000 <= oid <= 0xD0FFF): continue
    so = va2off(sva)
    if so is None: continue
    e = data.index(b'\0', so); s = data[so:e]
    if not re.fullmatch(rb'[a-z0-9]+', s): continue
    pairs[s.decode()] = oid
import json
out = sys.argv[2]
json.dump(dict(sorted(pairs.items(), key=lambda kv: kv[1])), open(out,'w'), indent=0)
print('pairs', len(pairs), 'blink', hex(pairs.get('blink',0)), 'attack', hex(pairs.get('attack',0)), 'stop', hex(pairs.get('stop',0)), 'move', hex(pairs.get('move',0)), 'channel', hex(pairs.get('channel',0)))
