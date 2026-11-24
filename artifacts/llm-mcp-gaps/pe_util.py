# -*- coding: utf-8 -*-
"""
纯 Python 标准库 PE32 解析与 dumpbin 反汇编辅助工具。
不依赖 pefile 等第三方库，适配全部 11 个 War3 版本的 Game.dll。
"""
import os
import re
import struct
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx64\x64\dumpbin.exe"
VERSIONS_DIR = r"D:\Qt\workspace\War3Launcher\versions"

ALL_VERSIONS = [
    "1.0.17.5988",
    "1.0.20.6048",
    "1.20.4.6074",
    "1.21.0.6263",
    "1.22.0.6328",
    "1.23.0.6352",
    "1.24.1.6374",
    "1.24.4.6387",
    "1.25.1.6397",
    "1.26.0.6401",
    "1.27.0.52240",
]


@dataclass
class Section:
    name: str
    vaddr: int
    vsize: int
    raw_ptr: int
    raw_size: int


class PE32:
    """轻量级 PE32 解析器"""

    def __init__(self, path: str):
        self.path = path
        with open(path, "rb") as f:
            self.raw = f.read()
        e_lfanew = struct.unpack_from("<I", self.raw, 0x3C)[0]
        assert self.raw[e_lfanew : e_lfanew + 4] == b"PE\x00\x00"
        num_sec = struct.unpack_from("<H", self.raw, e_lfanew + 6)[0]
        opt_size = struct.unpack_from("<H", self.raw, e_lfanew + 20)[0]
        opt_off = e_lfanew + 24
        self.image_base = struct.unpack_from("<I", self.raw, opt_off + 28)[0]
        self.image_size = struct.unpack_from("<I", self.raw, opt_off + 56)[0]
        sec_off = opt_off + opt_size
        self.sections: List[Section] = []
        for i in range(num_sec):
            o = sec_off + i * 40
            name = self.raw[o : o + 8].rstrip(b"\x00").decode("ascii", "replace")
            vsize, vaddr, raw_size, raw_ptr = struct.unpack_from("<IIII", self.raw, o + 8)
            self.sections.append(Section(name, vaddr, vsize, raw_ptr, raw_size))

    def get_section(self, name: str) -> Optional[Section]:
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def rva_to_off(self, rva: int) -> Optional[int]:
        for s in self.sections:
            if s.vaddr <= rva < s.vaddr + max(s.vsize, s.raw_size):
                off = s.raw_ptr + (rva - s.vaddr)
                if off < len(self.raw):
                    return off
        return None

    def off_to_rva(self, off: int) -> Optional[int]:
        for s in self.sections:
            if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
                return s.vaddr + (off - s.raw_ptr)
        return None

    def read_u32_rva(self, rva: int) -> Optional[int]:
        off = self.rva_to_off(rva)
        if off is None or off + 4 > len(self.raw):
            return None
        return struct.unpack_from("<I", self.raw, off)[0]

    def read_cstr_rva(self, rva: int, max_len: int = 128) -> str:
        off = self.rva_to_off(rva)
        if off is None:
            return ""
        end = self.raw.find(b"\x00", off, off + max_len)
        if end < 0:
            end = off + max_len
        return self.raw[off:end].decode("ascii", "replace")

    def find_all_bytes(self, pat: bytes, sec_name: Optional[str] = None) -> List[int]:
        """返回所有匹配的 RVA 列表"""
        out: List[int] = []
        if sec_name:
            sec = self.get_section(sec_name)
            if not sec:
                return out
            start, end = sec.raw_ptr, sec.raw_ptr + sec.raw_size
        else:
            start, end = 0, len(self.raw)
        pos = start
        while True:
            idx = self.raw.find(pat, pos, end)
            if idx < 0:
                break
            rva = self.off_to_rva(idx)
            if rva is not None:
                out.append(rva)
            pos = idx + 1
        return out

    def find_string_rvas(self, text: str) -> List[int]:
        pat = b"\x00" + text.encode("ascii") + b"\x00"
        out = []
        pos = 0
        while True:
            idx = self.raw.find(pat, pos)
            if idx < 0:
                break
            rva = self.off_to_rva(idx + 1)
            if rva is not None:
                out.append(rva)
            pos = idx + 1
        return out

    def find_xrefs_to_va(self, target_va: int, sec_name: str = ".text") -> List[int]:
        return self.find_all_bytes(struct.pack("<I", target_va), sec_name=sec_name)

    def find_rtti_vtables(self, mangled_substr: str) -> List[int]:
        """通过 MSVC RTTI TypeDescriptor 名称查找所有对应类的虚表 RVA"""
        pat = mangled_substr.encode("ascii")
        vtables = []
        pos = 0
        while True:
            idx = self.raw.find(pat, pos)
            if idx < 0:
                break
            # TypeDescriptor.name 位于 TypeDescriptor + 0x08
            td_rva = self.off_to_rva(idx)
            if td_rva is not None:
                td_va = self.image_base + td_rva - 8
                # 在 .rdata 中找指向 td_va 的 CompleteObjectLocator (offset +0x0C)
                for col_td_rva in self.find_all_bytes(struct.pack("<I", td_va), ".rdata"):
                    col_va = self.image_base + col_td_rva - 0x0C
                    # vtable[-1] 指向 COL
                    for vt_meta_rva in self.find_all_bytes(struct.pack("<I", col_va), ".rdata"):
                        vt_rva = vt_meta_rva + 4
                        if vt_rva not in vtables:
                            vtables.append(vt_rva)
            pos = idx + 1
        return vtables


def disasm(dll_path: str, image_base: int, rva: int, size: int) -> List[str]:
    """调用 dumpbin 反汇编指定 RVA 范围"""
    va1 = image_base + rva
    va2 = image_base + rva + size
    res = subprocess.run(
        [DUMPBIN, "/nologo", "/disasm", f"/range:0x{va1:X},0x{va2:X}", dll_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return [ln.strip() for ln in res.stdout.splitlines() if re.match(r"^\s+[0-9A-F]{8}:", ln)]


def dll_path_for(ver: str) -> str:
    return os.path.join(VERSIONS_DIR, ver, "Game.dll")
