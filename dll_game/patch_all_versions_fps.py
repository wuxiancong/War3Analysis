#!/usr/bin/env python3
"""Build FPS-unlock game.dll (and war3.exe when needed) for every bundled version.

Does not modify War3Launcher/versions originals.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT_ROOT = Path(__file__).resolve().parent
STR_SWAP = b"wglSwapIntervalEXT\x00"
md = Cs(CS_ARCH_X86, CS_MODE_32)


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def rel32(src: int, dst: int) -> bytes:
    return struct.pack("<i", dst - (src + 5))


def parse_pe(blob: bytes):
    e = struct.unpack_from("<I", blob, 0x3C)[0]
    nsec = struct.unpack_from("<H", blob, e + 6)[0]
    optsz = struct.unpack_from("<H", blob, e + 20)[0]
    ib = struct.unpack_from("<I", blob, e + 24 + 28)[0]
    secs = []
    o = e + 24 + optsz
    for _ in range(nsec):
        name = blob[o : o + 8].split(b"\x00")[0].decode(errors="replace")
        vsz, va, rsz, raw = struct.unpack_from("<IIII", blob, o + 8)
        secs.append({"name": name, "va": va, "raw": raw, "vsz": vsz, "rsz": rsz})
        o += 40
    return ib, secs


def rva_to_off(secs, rva: int) -> int | None:
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsz"], s["rsz"]):
            return s["raw"] + (rva - s["va"])
    return None


def va_to_off(ib, secs, va: int) -> int | None:
    return rva_to_off(secs, va - ib)


def off_to_va(ib, secs, fo: int) -> int | None:
    for s in secs:
        if s["raw"] <= fo < s["raw"] + s["rsz"]:
            return ib + s["va"] + (fo - s["raw"])
    return None


def text_sec(secs):
    for s in secs:
        if s["name"] == ".text":
            return s
    raise RuntimeError("no .text")


def imports(blob, ib, secs) -> dict[str, int]:
    e = struct.unpack_from("<I", blob, 0x3C)[0]
    imp_rva = struct.unpack_from("<I", blob, e + 24 + 96 + 8)[0]
    off = rva_to_off(secs, imp_rva)
    out = {}
    if off is None:
        return out
    while True:
        ilt, _, _, name_rva, iat = struct.unpack_from("<IIIII", blob, off)
        if name_rva == 0 and iat == 0:
            break
        thunk = ilt or iat
        idx = 0
        while True:
            to = rva_to_off(secs, thunk + idx * 4)
            if to is None:
                break
            th = struct.unpack_from("<I", blob, to)[0]
            if th == 0:
                break
            if th & 0x80000000:
                nm = f"ord_{th & 0xFFFF}"
            else:
                ho = rva_to_off(secs, (th & 0x7FFFFFFF) + 2)
                nm = blob[ho:].split(b"\x00")[0].decode(errors="replace") if ho else "?"
            out[nm] = ib + iat + idx * 4
            idx += 1
        off += 20
    return out


def find_all(hay: bytes, needle: bytes) -> list[int]:
    out = []
    s = 0
    while True:
        i = hay.find(needle, s)
        if i < 0:
            break
        out.append(i)
        s = i + 1
    return out


def set_section_vsz(buf: bytearray, name: str, vsz: int) -> None:
    e = struct.unpack_from("<I", buf, 0x3C)[0]
    nsec = struct.unpack_from("<H", buf, e + 6)[0]
    optsz = struct.unpack_from("<H", buf, e + 20)[0]
    o = e + 24 + optsz
    want = name.encode()[:8]
    for _ in range(nsec):
        if bytes(buf[o : o + 8]).split(b"\x00")[0] == want:
            struct.pack_into("<I", buf, o + 8, vsz)
            return
        o += 40
    raise RuntimeError(f"section {name} not found")


class Patcher:
    def __init__(self, blob: bytes):
        self.orig = bytes(blob)
        self.buf = bytearray(blob)
        self.ib, self.secs = parse_pe(blob)
        self.ts = text_sec(self.secs)
        self.text_va = self.ib + self.ts["va"]
        self.traw = self.ts["raw"]
        self.tb = blob[self.traw : self.traw + self.ts["rsz"]]
        self.imps = imports(blob, self.ib, self.secs)
        self.applied: list[tuple[str, int, bytes, bytes]] = []
        self.notes: list[str] = []
        self.slack_off = self.traw + self.ts["vsz"]
        self.slack_va = self.text_va + self.ts["vsz"]
        self.slack_left = max(0, self.ts["rsz"] - self.ts["vsz"])
        self.slack_cursor = 0
        self.rs = next((s for s in self.secs if s["name"] == ".rdata"), None)
        self.rd_cursor = 0
        if self.rs:
            self.rd_off = self.rs["raw"] + self.rs["vsz"]
            self.rd_va = self.ib + self.rs["va"] + self.rs["vsz"]
            self.rd_left = max(0, self.rs["rsz"] - self.rs["vsz"])
        else:
            self.rd_off = self.rd_va = self.rd_left = 0

    def alloc_slack(self, n: int) -> tuple[int, int]:
        if self.slack_cursor + n > self.slack_left:
            raise RuntimeError(f"need {n} slack bytes, have {self.slack_left - self.slack_cursor}")
        off = self.slack_off + self.slack_cursor
        va = self.slack_va + self.slack_cursor
        self.slack_cursor += n
        return off, va

    def alloc_rdata(self, n: int) -> tuple[int, int]:
        if self.rs is None or self.rd_cursor + n > self.rd_left:
            raise RuntimeError("not enough .rdata slack")
        off = self.rd_off + self.rd_cursor
        va = self.rd_va + self.rd_cursor
        self.rd_cursor += n
        return off, va

    def patch(self, name: str, off: int, old: bytes, new: bytes) -> None:
        got = bytes(self.buf[off : off + len(old)])
        if got != old:
            raise RuntimeError(f"{name}: expected {old.hex()} at 0x{off:X}, found {got.hex()}")
        if len(new) != len(old):
            raise RuntimeError(f"{name}: size {len(old)} -> {len(new)}")
        self.buf[off : off + len(new)] = new
        self.applied.append((name, off, old, new))

    def find_soft64(self) -> int | None:
        """Return file offset of the FB byte in `and eax, ~4` before edx=0x11."""
        tb = self.tb
        text_va = self.text_va
        traw = self.traw
        hits = []
        for i in find_all(tb, b"\x83\xE0\xFB"):
            win = tb[i : i + 20]
            if b"\xBA\x11\x00\x00\x00" in win or b"\x8D\x53\x11" in win:
                # require preceding test al,4
                pre = tb[max(0, i - 8) : i]
                if b"\xA8\x04" in pre:
                    hits.append(traw + i + 2)
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            self.notes.append(f"multiple software-64 hits {[hex(h) for h in hits]}")
            return hits[0]
        return None

    def patch_d3d8(self) -> None:
        """Exclusive-fullscreen interval only.

        D3D8 windowed CreateDevice rejects IMMEDIATE on many drivers, and
        LOCKABLE_BACKBUFFER (Flags=eax=1 at join) is required for windowed.
        """
        pat = bytes.fromhex("89562cc7463000000000")
        hits = find_all(self.tb, pat)
        if len(hits) != 1:
            raise RuntimeError(f"D3D8 interval seq count={len(hits)}")
        i = hits[0]
        off = self.traw + i + 3
        self.patch(
            "d3d8-fullscreen-PresentationInterval-IMMEDIATE",
            off,
            bytes.fromhex("c7463000000000"),
            bytes.fromhex("c7463000000080"),
        )

    def patch_d3d9(self, windowed: bool = True) -> None:
        pat = bytes.fromhex("894630c7463400000000")
        hits = find_all(self.tb, pat)
        if len(hits) != 1:
            raise RuntimeError(f"D3D9 interval seq count={len(hits)}")
        i = hits[0]
        off = self.traw + i + 3
        self.patch(
            "d3d9-PresentationInterval-IMMEDIATE",
            off,
            bytes.fromhex("c7463400000000"),
            bytes.fromhex("c7463400000080"),
        )
        if self.tb[i + 10] != 0x5B:  # pop ebx in 1.27 then jmp
            # 1.27: 5B E9 / 5B EB?
            pass
        # find jmp to join: after interval 7 bytes at i+3, then pop ebx (1) jmp
        # bytes at i: 89 46 30 C7 46 34 00 00 00 00 5B EB/E9
        p = i + 10
        if self.tb[p] == 0x5B:
            p += 1
        if self.tb[p] == 0xEB:
            join_va = self.text_va + p + 2 + self.tb[p + 1]
        elif self.tb[p] == 0xE9:
            join_va = self.text_va + p + 5 + struct.unpack_from("<i", self.tb, p + 1)[0]
        else:
            raise RuntimeError(f"D3D9 no jmp after interval: {self.tb[p:p+6].hex()}")
        stolen = bytes.fromhex("c7461801000000894e08")
        win_va = join_va - 10
        win_off = va_to_off(self.ib, self.secs, win_va)
        if bytes(self.buf[win_off : win_off + 10]) != stolen:
            raise RuntimeError(
                f"D3D9 windowed stolen mismatch at 0x{win_va:X}: {self.buf[win_off:win_off+10].hex()}"
            )
        if not windowed:
            self.notes.append("D3D9 windowed interval skipped (not enough .text slack)")
        else:
            cave_body = (
                bytes.fromhex("c7461801000000")
                + bytes.fromhex("c7463400000080")
                + bytes.fromhex("894e08")
                + b"\xE9"
            )
            cave_len = len(cave_body) + 4
            coff, cva = self.alloc_slack(cave_len)
            cave = cave_body + rel32(cva + len(cave_body), join_va)
            old = bytes(self.buf[coff : coff + cave_len])
            if any(b not in (0x00, 0xCC, 0x90) for b in old):
                raise RuntimeError(f"D3D9 cave slack dirty {old.hex()}")
            self.patch("d3d9-windowed-interval-cave", coff, old, cave)
            hook = b"\xE9" + rel32(win_va, cva) + b"\x90" * 5
            self.patch("d3d9-windowed-hook-to-cave", win_off, stolen, hook)
        flags = bytes.fromhex("c7462c01000000")
        fh = find_all(self.tb, flags)
        # prefer one near join
        join_i = join_va - self.text_va
        near = [h for h in fh if abs(h - join_i) < 32]
        if len(near) != 1:
            raise RuntimeError(f"D3D9 flags near join count={len(near)} all={len(fh)}")
        self.patch(
            "d3d9-Flags-clear-LOCKABLE_BACKBUFFER",
            self.traw + near[0],
            flags,
            bytes.fromhex("c7462c00000000"),
        )

    def patch_maxfps(self) -> None:
        idx = self.orig.find(b"maxfps\x00")
        if idx < 0:
            self.notes.append("no maxfps string")
            return
        sva = off_to_va(self.ib, self.secs, idx)
        if sva is None:
            self.notes.append("maxfps string unmapped")
            return
        xrefs = find_all(self.tb, struct.pack("<I", sva))
        patched = False
        for xi in xrefs:
            win = self.tb[xi : xi + 48]
            for enc, name in (
                (bytes.fromhex("c745fcc8000000"), "ebp-4"),
                (bytes.fromhex("c7442414c8000000"), "esp+14"),
                (bytes.fromhex("c7442410c8000000"), "esp+10"),
                (bytes.fromhex("c744240cc8000000"), "esp+0c"),
            ):
                j = win.find(enc)
                if j >= 0:
                    off = self.traw + xi + j
                    new = enc[:-4] + struct.pack("<I", 10000)
                    self.patch("maxfps-default-200-to-10000", off, enc, new)
                    patched = True
                    break
            if patched:
                break
        if not patched:
            imm = bytes.fromhex("c745fcc8000000")
            hits = find_all(self.tb, imm)
            if len(hits) == 1:
                off = self.traw + hits[0]
                self.patch(
                    "maxfps-default-200-to-10000",
                    off,
                    imm,
                    bytes.fromhex("c745fc10270000"),
                )
                patched = True
        if not patched:
            self.notes.append("maxfps default 200 store not found")

    def patch_opengl(self) -> None:
        iat_mk = self.imps.get("wglMakeCurrent")
        iat_gp = self.imps.get("wglGetProcAddress")
        if not iat_mk or not iat_gp:
            self.notes.append("OpenGL IAT missing")
            return
        calls = find_all(self.tb, b"\xFF\x15" + struct.pack("<I", iat_mk))
        hooked = False
        for ci in calls:
            nxt = ci + 6
            if self.tb[nxt] != 0xE8:
                continue
            orig_rel = struct.unpack_from("<i", self.tb, nxt + 1)[0]
            call_va = self.text_va + nxt
            orig_va = call_va + 5 + orig_rel
            # PIC: no absolute ImageBase addresses. Game.dll almost always rebases.
            # Use EDX (caller-saved). EBX is callee-saved and still live across this
            # call on 1.26 and earlier: resolution changes keep a refcounted node in
            # EBX, then `add byte ptr [ecx], -1` writes the cave and AVs (RX .text).
            #   call orig; push eax; call $+5; pop edx
            #   lea eax,[edx+str]; push eax; mov eax,[edx+iat]; call eax
            #   test eax,eax; jz skip; push 0; call eax; skip: pop eax; ret
            soff, sva = self.alloc_rdata(len(STR_SWAP))
            sold = bytes(self.buf[soff : soff + len(STR_SWAP)])
            if any(b not in (0x00,) for b in sold):
                raise RuntimeError("GL string rdata slack dirty")
            self.patch("opengl-wglSwapIntervalEXT-name", soff, sold, STR_SWAP)
            cave_len = 37
            coff, cva = self.alloc_slack(cave_len)
            pic_va = cva + 11
            code = bytearray()
            code += b"\xE8" + rel32(cva, orig_va)
            code += b"\x50"
            code += b"\xE8\x00\x00\x00\x00"
            code += b"\x5A"  # pop edx
            code += b"\x8D\x82" + struct.pack("<i", sva - pic_va)
            code += b"\x50"
            code += b"\x8B\x82" + struct.pack("<i", iat_gp - pic_va)
            code += b"\xFF\xD0\x85\xC0\x74\x04\x6A\x00\xFF\xD0\x58\xC3"
            if len(code) != cave_len:
                raise RuntimeError(f"gl cave {len(code)}")
            old = bytes(self.buf[coff : coff + cave_len])
            if any(b not in (0x00, 0xCC, 0x90) for b in old):
                raise RuntimeError("GL cave slack dirty")
            self.patch("opengl-wglSwapIntervalEXT-cave", coff, old, bytes(code))
            new_call = b"\xE8" + rel32(call_va, cva)
            self.patch(
                "opengl-hook-after-wglMakeCurrent",
                self.traw + nxt,
                b"\xE8" + struct.pack("<i", orig_rel),
                new_call,
            )
            hooked = True
            break
        if not hooked:
            self.notes.append("no wglMakeCurrent+call site for OpenGL hook")

    def apply_game_dll(self) -> None:
        fb = self.find_soft64()
        if fb is not None:
            self.patch("software-64fps-keep-flag-bit2", fb, b"\xFB", b"\xFF")
        else:
            self.notes.append("software-64 not in game.dll")
        d3d9 = b"Direct3DCreate9" in self.orig
        d3d8 = b"Direct3DCreate8" in self.orig
        gl_need = 37
        if d3d9:
            do_windowed = self.slack_left >= 22 + gl_need
            self.patch_d3d9(windowed=do_windowed)
        elif d3d8:
            self.patch_d3d8()
        else:
            self.notes.append("no Direct3DCreate8/9 string")
        self.patch_maxfps()
        self.patch_opengl()
        if self.slack_cursor:
            set_section_vsz(self.buf, ".text", self.ts["vsz"] + self.slack_cursor)
        if self.rd_cursor:
            set_section_vsz(self.buf, ".rdata", self.rs["vsz"] + self.rd_cursor)


def patch_war3_exe(blob: bytes) -> tuple[bytearray, list]:
    ib, secs = parse_pe(blob)
    applied = []
    hits = []
    s = 0
    while True:
        i = blob.find(b"\x83\xE0\xFB", s)
        if i < 0:
            break
        win = blob[i : i + 16]
        pre = blob[max(0, i - 8) : i]
        if b"\xA8\x04" in pre and (b"\xBA\x11\x00\x00\x00" in win):
            hits.append(i + 2)
        s = i + 1
    buf = bytearray(blob)
    if len(hits) == 1:
        off = hits[0]
        if buf[off] != 0xFB:
            raise RuntimeError("war3.exe FB mismatch")
        buf[off] = 0xFF
        applied.append(("software-64fps-war3exe", off, b"\xFB", b"\xFF"))
    return buf, applied


def write_readme(out_dir: Path, ver: str, src_dll: Path, dst_dll: Path, applied, notes, extra_exe=None):
    lines = [
        f"# {ver} FPS unlock",
        "",
        "从官方样本复制后改字节。输出文件名保持 `game.dll`（若有 `war3.exe` 补丁则一并放本目录）。",
        "",
        "## 文件",
        "",
        f"- 源 DLL：`{src_dll}`",
        f"- 源 SHA-256：`{sha256(src_dll.read_bytes())}`",
        f"- 输出 DLL：`{dst_dll}`",
        f"- 输出 SHA-256：`{sha256(dst_dll.read_bytes())}`",
        "",
        "## 改动",
        "",
        "| 名称 | 文件偏移 | 原始 | 替换 |",
        "| --- | ---: | --- | --- |",
    ]
    for name, off, old, new in applied:
        lines.append(f"| {name} | `0x{off:X}` | `{old.hex(' ')}` | `{new.hex(' ')}` |")
    if extra_exe:
        path, app, src = extra_exe
        lines += [
            "",
            f"- 源 EXE：`{src}`",
            f"- 输出 EXE：`{path}`",
            f"- 输出 EXE SHA-256：`{sha256(path.read_bytes())}`",
            "",
        ]
        for name, off, old, new in app:
            lines.append(f"| {name} | `0x{off:X}` | `{old.hex(' ')}` | `{new.hex(' ')}` |")
    lines += [
        "",
        "## 验证",
        "",
        "1. 备份游戏目录对应文件。",
        "2. 把本目录文件覆盖到该版本游戏根目录。",
        "3. Direct3D 启动后输入 `/fps`；OpenGL 加 `-opengl` 再测。",
        "4. 启动器切版本会从 `versions\\` 还原原件，测完勿提交 DLL。",
        "",
    ]
    if notes:
        lines += ["## 备注", ""] + [f"- {n}" for n in notes] + [""]
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = []
    for d in sorted(VERSIONS.iterdir()):
        src = d / "game.dll"
        if not src.exists():
            continue
        ver = d.name
        print(f"=== {ver} ===")
        p = Patcher(src.read_bytes())
        p.apply_game_dll()
        out_dir = OUT_ROOT / f"{ver}-fps-unlock-dx-ogl"
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = out_dir / "game.dll"
        dst.write_bytes(p.buf)
        extra = None
        if ver.startswith("1.27"):
            legacy = OUT_ROOT / "1.27.0.52240-fps-unlock-d3d9-ogl"
            legacy.mkdir(parents=True, exist_ok=True)
            (legacy / "game.dll").write_bytes(p.buf)
            (legacy / "README.md").write_text(
                "# 已废弃：请改用 `1.27.0.52240-fps-unlock-dx-ogl`\n\n"
                "本目录 game.dll 已同步为 PIC OpenGL 版本，避免 `-opengl` 读 0x6F94E4EC 崩溃。\n",
                encoding="utf-8",
            )
        stale_exe = out_dir / "war3.exe"
        # 1.22+ has the 64-cap in Game.dll; only patch war3.exe when DLL lacks it.
        exe_src = d / "war3.exe"
        if p.find_soft64() is None and exe_src.exists():
            ebuf, eapp = patch_war3_exe(exe_src.read_bytes())
            if eapp:
                epath = out_dir / "war3.exe"
                epath.write_bytes(ebuf)
                extra = (epath, eapp, exe_src)
                p.applied.extend(eapp)
                print(f"  also patched war3.exe {eapp}")
        elif stale_exe.exists():
            stale_exe.unlink()
        write_readme(out_dir, ver, src, dst, p.applied, p.notes, extra)
        names = [a[0] for a in p.applied]
        print(" ", ", ".join(names))
        for n in p.notes:
            print("  note:", n)
        print("  sha", sha256(p.buf), "slack used", p.slack_cursor, "/", p.slack_left)
        rows.append((ver, names, p.notes, sha256(p.buf)))

    index = [
        "# 全版本 FPS 解锁补丁",
        "",
        "每个子目录一个版本，内含补丁后的 `game.dll`。",
        "**1.22+ 只覆盖 game.dll**（64 帧限制已在 DLL 内）。**1.21 及更早必须同时覆盖 war3.exe**。",
        "D3D8（1.26 及更早）只改全屏 PresentationInterval，不再改窗口模式 Flags，避免 CreateDevice 失败。",
        "OpenGL cave 用 PIC（相对 edx 读 IAT/字符串），不依赖 ImageBase，且不破坏 callee-saved 的 ebx。",
        "**1.27 请用本目录 `1.27.0.52240-fps-unlock-dx-ogl/game.dll`，不要用旧的 `...-d3d9-ogl`（INT3 cave 无 PIC）。**",
        "",
        "重新生成：`python dll_game/patch_all_versions_fps.py`",
        "",
        "| 版本 | 输出 | 补丁项 | 备注 |",
        "| --- | --- | --- | --- |",
    ]
    for ver, names, notes, digest in rows:
        index.append(
            f"| {ver} | `{ver}-fps-unlock-dx-ogl/` | {', '.join(names)} | {'; '.join(notes) or digest[:12]} |"
        )
    index.append("")
    (OUT_ROOT / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
