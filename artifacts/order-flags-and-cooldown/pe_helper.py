# -*- coding: utf-8 -*-
"""
轻量级纯 Python PE32 解析辅助模块（免 pefile 依赖），供全 11 版 Game.dll 批量逆向使用。
"""
import struct

class SimplePE32:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()
        e_lfanew = struct.unpack_from("<I", self.data, 0x3C)[0]
        assert self.data[e_lfanew:e_lfanew+4] == b"PE\x00\x00"
        self.num_sections = struct.unpack_from("<H", self.data, e_lfanew + 6)[0]
        opt_size = struct.unpack_from("<H", self.data, e_lfanew + 20)[0]
        opt_off = e_lfanew + 24
        self.image_base = struct.unpack_from("<I", self.data, opt_off + 28)[0]
        sec_off = opt_off + opt_size
        self.sections = []
        for i in range(self.num_sections):
            off = sec_off + i * 40
            name = self.data[off:off+8].rstrip(b"\x00").decode("ascii", errors="ignore")
            vsize, va, rsize, roff = struct.unpack_from("<IIII", self.data, off + 8)
            self.sections.append((name, va, vsize, roff, rsize))

    def rva_to_off(self, rva):
        for name, va, vsize, roff, rsize in self.sections:
            span = max(vsize, rsize)
            if va <= rva < va + span:
                off = roff + (rva - va)
                if off < roff + rsize:
                    return off
        return None

    def off_to_rva(self, off):
        for name, va, vsize, roff, rsize in self.sections:
            if roff <= off < roff + rsize:
                return va + (off - roff)
        return None

    def read_u32(self, rva):
        off = self.rva_to_off(rva)
        if off is None or off + 4 > len(self.data):
            return None
        return struct.unpack_from("<I", self.data, off)[0]

    def read_bytes(self, rva, size):
        off = self.rva_to_off(rva)
        if off is None:
            return b""
        return self.data[off:off+size]

    def get_section(self, name):
        for s in self.sections:
            if s[0] == name:
                return s
        return None

    def find_rtti_vtables(self, name_substr):
        """通过 MSVC RTTI TypeDescriptor 反向定位虚表 RVA"""
        results = []
        needle = name_substr.encode("ascii")
        raw = self.data
        pos = 0
        seen_names = set()
        while True:
            idx = raw.find(needle, pos)
            if idx == -1:
                break
            pos = idx + 1
            start = raw.rfind(b".?AV", max(0, idx - 64), idx + 4)
            if start == -1:
                continue
            end = raw.find(b"\x00", start)
            if end == -1:
                continue
            tname = raw[start:end].decode("ascii", errors="ignore")
            if tname in seen_names:
                continue
            seen_names.add(tname)
            td_rva = self.off_to_rva(start - 8)
            if td_rva is None:
                continue
            td_va = self.image_base + td_rva
            td_bytes = struct.pack("<I", td_va)
            cpos = 0
            vtables = []
            while True:
                cidx = raw.find(td_bytes, cpos)
                if cidx == -1:
                    break
                cpos = cidx + 1
                col_off = cidx - 12
                if col_off < 0:
                    continue
                sig, offset, cdOffset = struct.unpack_from("<III", raw, col_off)
                if sig != 0 or offset > 0x400 or cdOffset != 0:
                    continue
                col_rva = self.off_to_rva(col_off)
                if col_rva is None:
                    continue
                col_va = self.image_base + col_rva
                col_bytes = struct.pack("<I", col_va)
                vpos = 0
                while True:
                    vidx = raw.find(col_bytes, vpos)
                    if vidx == -1:
                        break
                    vpos = vidx + 1
                    vt_rva = self.off_to_rva(vidx + 4)
                    if vt_rva is not None:
                        vtables.append((offset, vt_rva))
            results.append((tname, vtables))
        return results
