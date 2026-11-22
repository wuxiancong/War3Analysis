import struct
from pathlib import Path
import pefile

ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward")
NAMES = ["IsUnitInvisible","IsUnitDetected","IsUnitVisible","IsUnitHidden","UnitShareVision"]

def file_rva(pe, off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return s.VirtualAddress + (off - s.PointerToRawData)
    return None

lines=[]
for ver in ["1.26.0.6401","1.27.0.52240","1.24.4.6387","1.25.1.6397","1.23.0.6352","1.22.0.6328"]:
    dll=ROOT/ver/"game.dll"
    if not dll.exists(): continue
    pe=pefile.PE(str(dll), fast_load=True)
    data=dll.read_bytes(); ib=pe.OPTIONAL_HEADER.ImageBase
    lines.append(f"## {ver}\n")
    for name in NAMES:
        needle=name.encode()+b"\x00"; hits=[]; start=0
        while True:
            i=data.find(needle,start)
            if i<0: break
            if i==0 or data[i-1]==0:
                rva=file_rva(pe,i)
                if rva is not None: hits.append(rva)
            start=i+1
        if not hits:
            lines.append(f"- {name}: missing\n"); continue
        for rva in hits[:2]:
            va=ib+rva
            pat=b"\xBA"+struct.pack("<I",va)+b"\xB9"
            funcs=[]; start=0
            while True:
                i=data.find(pat,start)
                if i<0: break
                funcs.append(struct.unpack_from("<I",data,i+6)[0]-ib); start=i+1
            stub=""
            if funcs:
                try:
                    off=pe.get_offset_from_rva(funcs[0])
                    stub=" ".join(f"{b:02X}" for b in data[off:off+64])
                except Exception as e:
                    stub=str(e)
            lines.append(f"- {name}: strRVA=0x{rva:X} native={[hex(f) for f in funcs[:3]]}\n")
            if stub: lines.append(f"  stub: {stub}\n")
    lines.append("\n")
(OUT/"visibility_natives.md").write_text("".join(lines), encoding="utf-8")
print("".join(lines))
