"""Minimal minidump reader (no debugger needed): exception code/address, registers,
module+offset of the crash, and module return-address candidates on the faulting stack.
Usage: python -I mdump.py <file.dmp>
"""
import struct, sys

data = open(sys.argv[1], 'rb').read()
sig, ver, nstreams, rva_dir = struct.unpack_from('<IIII', data, 0)
streams = {}
for i in range(nstreams):
    t, size, rva = struct.unpack_from('<III', data, rva_dir + i * 12)
    streams.setdefault(t, []).append((size, rva))

def mdstr(rva):
    n = struct.unpack_from('<I', data, rva)[0]
    return data[rva + 4: rva + 4 + n].decode('utf-16-le', 'replace')

mods = []
if 4 in streams:
    size, rva = streams[4][0]
    n = struct.unpack_from('<I', data, rva)[0]
    for i in range(n):
        off = rva + 4 + i * 108
        base, msize, _, _, name_rva = struct.unpack_from('<QIIII', data, off)
        mods.append((base, msize, mdstr(name_rva)))

def where(addr):
    for b, s, name in mods:
        if b <= addr < b + s:
            return '%s+0x%X' % (name.split('\\')[-1], addr - b)
    return '?'

if 6 not in streams:
    print('no exception stream'); sys.exit()
size, rva = streams[6][0]
tid, _ = struct.unpack_from('<II', data, rva)
code, eflags, erec, eaddr, nparams = struct.unpack_from('<IIQQI', data, rva + 8)
params = struct.unpack_from('<15Q', data, rva + 8 + 32)
print('thread 0x%X code 0x%08X addr 0x%X (%s) params %s' % (tid, code, eaddr, where(eaddr), [hex(p) for p in params[:nparams]]))
ctx_size, ctx_rva = struct.unpack_from('<II', data, rva + 8 + 152)
ctx = data[ctx_rva: ctx_rva + ctx_size]
if len(ctx) >= 0xCC:
    names = ['edi', 'esi', 'ebx', 'edx', 'ecx', 'eax', 'ebp', 'eip', 'cs', 'eflags', 'esp']
    regs = struct.unpack_from('<11I', ctx, 0x9C)
    print(' '.join('%s=%08X' % (n, v) for n, v in zip(names, regs)))
    esp = regs[10]
    if 5 in streams:
        size, rva = streams[5][0]
        n = struct.unpack_from('<I', data, rva)[0]
        for i in range(n):
            start, msz, mrva = struct.unpack_from('<QII', data, rva + 4 + i * 16)
            if start <= esp < start + msz:
                off = esp - start
                print('stack return-address candidates:')
                cnt = 0
                for j in range(off, min(msz, off + 0x1000), 4):
                    v = struct.unpack_from('<I', data, mrva + j)[0]
                    w = where(v)
                    if w != '?' and not w.lower().startswith(('ntdll', 'kernel', 'ucrtbase', 'msvcr', 'user32', 'win32u')):
                        print('  [esp+0x%X] %08X %s' % (j - off, v, w))
                        cnt += 1
                        if cnt > 25: break
for b, s, n in mods:
    if n.split('\\')[-1].lower() in ('war3.exe', 'game.dll', 'hook.dll', 'load.dll', 'storm.dll'):
        print('  %08X %08X %s' % (b, s, n))
