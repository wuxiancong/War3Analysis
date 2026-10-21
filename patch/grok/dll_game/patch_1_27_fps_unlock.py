#!/usr/bin/env python3
"""Build a 1.27.0.52240 Game.dll with software-64 + D3D9 + OpenGL FPS unlock patches.

Does not modify the source Game.dll. Output is always named game.dll.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

EXPECTED_SHA256 = "e04d1716603c075eb0c8e1e21cf1093a664adc5249efab396bfa08d7b09d0c3a"
IMAGE_BASE = 0x6F000000
TEXT_VA = 0x6F001000
TEXT_RAW = 0x400

# Software 64 FPS: and eax, ~4  -> and eax, -1  (keep flag bit 2)
# VA 0x6F05FCFB, same site as 1.26 Game.dll+0x62D7FB and WarcraftHelper 1.27a +0x5FCFB
OFF_SOFT_64 = 0x5F0FB

# D3D9 CGxDeviceD3d present-parameter fill (exclusive-fullscreen branch)
OFF_D3D_INTERVAL = 0xEBB59  # mov [esi+34h], 0  -> IMMEDIATE
OFF_D3D_FLAGS = 0xEBBA2  # mov [esi+2Ch], 1  -> 0

# Windowed/borderless branch never writes PresentationInterval (stays DEFAULT).
# Steal 10 bytes at VA 0x6F0EC794 and finish in INT3 padding.
VA_D3D_WIN_HOOK = 0x6F0EC794
OFF_D3D_WIN_HOOK = 0xEBB94
VA_D3D_WIN_REJOIN = 0x6F0EC79E
VA_D3D_WIN_CAVE = 0x6F19DFC2
OFF_D3D_WIN_CAVE = 0x19D3C2

# maxfps registration default 200
OFF_MAXFPS_DEFAULT = 0x35C6ED  # C7 45 FC C8 00 00 00 in FUN_6f35d2d0

# OpenGL: after wglMakeCurrent, call extension loader
VA_CALL_EXTLOADER = 0x6F0E78EB
OFF_CALL_EXTLOADER = 0xE6CEB
VA_EXTLOADER = 0x6F0EBB40
VA_CAVE = 0x6F87A98D
OFF_CAVE = 0x879D8D
IAT_WGL_GET_PROC = 0x6F94E4EC
STR_SWAP_INTERVAL = b"wglSwapIntervalEXT\x00"


def va_to_off(va: int) -> int:
    return va - TEXT_VA + TEXT_RAW


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def rel32(src_va: int, dst_va: int) -> bytes:
    return struct.pack("<i", dst_va - (src_va + 5))


def build_gl_cave() -> bytes:
    """call original loader; wglGetProcAddress('wglSwapIntervalEXT'); if found, call 0; ret."""
    code = bytearray()
    code += b"\xE8" + rel32(VA_CAVE, VA_EXTLOADER)
    code += b"\x50"  # push eax
    code += b"\x56"  # push esi
    str_va = VA_CAVE + 29
    code += b"\x68" + struct.pack("<I", str_va)
    code += b"\xFF\x15" + struct.pack("<I", IAT_WGL_GET_PROC)
    code += b"\x85\xC0"  # test eax, eax
    code += b"\x74\x04"  # jz skip
    code += b"\x6A\x00"  # push 0
    code += b"\xFF\xD0"  # call eax
    code += b"\x5E"  # pop esi
    code += b"\x58"  # pop eax
    code += b"\xC3"  # ret
    if len(code) != 29:
        raise RuntimeError(f"cave code length {len(code)}, expected 29")
    blob = bytes(code) + STR_SWAP_INTERVAL
    if len(blob) > 67:
        raise RuntimeError("cave does not fit in INT3 padding")
    return blob


def build_d3d_windowed_cave() -> bytes:
    """Restore stolen windowed-path stores and force IMMEDIATE interval."""
    code = bytearray()
    code += bytes.fromhex("c7461801000000")  # mov [esi+18h], 1  SwapEffect
    code += bytes.fromhex("c7463400000080")  # mov [esi+34h], IMMEDIATE
    code += bytes.fromhex("894e08")  # mov [esi+8], ecx  BackBufferFormat
    code += b"\xE9" + rel32(VA_D3D_WIN_CAVE + 17, VA_D3D_WIN_REJOIN)
    if len(code) != 22:
        raise RuntimeError(f"windowed cave length {len(code)}, expected 22")
    return bytes(code)


def apply(buf: bytearray) -> list[tuple[str, int, bytes, bytes]]:
    applied = []

    def patch(name: str, off: int, old: bytes, new: bytes) -> None:
        got = bytes(buf[off : off + len(old)])
        if got != old:
            raise RuntimeError(f"{name}: expected {old.hex()} at 0x{off:X}, found {got.hex()}")
        buf[off : off + len(new)] = new
        applied.append((name, off, old, new))

    patch(
        "software-64fps-keep-flag-bit2",
        OFF_SOFT_64,
        b"\xFB",
        b"\xFF",
    )
    patch(
        "d3d9-PresentationInterval-IMMEDIATE",
        OFF_D3D_INTERVAL,
        bytes.fromhex("c7463400000000"),
        bytes.fromhex("c7463400000080"),
    )
    patch(
        "d3d9-Flags-clear-LOCKABLE_BACKBUFFER",
        OFF_D3D_FLAGS,
        bytes.fromhex("c7462c01000000"),
        bytes.fromhex("c7462c00000000"),
    )

    win_cave = build_d3d_windowed_cave()
    patch(
        "d3d9-windowed-interval-cave",
        OFF_D3D_WIN_CAVE,
        b"\xCC" * len(win_cave),
        win_cave,
    )
    stolen = bytes.fromhex("c7461801000000894e08")
    hook = b"\xE9" + rel32(VA_D3D_WIN_HOOK, VA_D3D_WIN_CAVE) + b"\x90" * 5
    if len(hook) != len(stolen):
        raise RuntimeError("windowed hook size mismatch")
    patch("d3d9-windowed-hook-to-cave", OFF_D3D_WIN_HOOK, stolen, hook)
    patch(
        "maxfps-default-200-to-10000",
        OFF_MAXFPS_DEFAULT,
        bytes.fromhex("c745fcc8000000"),
        bytes.fromhex("c745fc10270000"),
    )

    cave = build_gl_cave()
    old_cc = b"\xCC" * len(cave)
    patch("opengl-wglSwapIntervalEXT-cave", OFF_CAVE, old_cc, cave)

    old_call = b"\xE8" + rel32(VA_CALL_EXTLOADER, VA_EXTLOADER)
    new_call = b"\xE8" + rel32(VA_CALL_EXTLOADER, VA_CAVE)
    patch("opengl-hook-after-wglMakeCurrent", OFF_CALL_EXTLOADER, old_call, new_call)
    return applied


def main() -> None:
    here = Path(__file__).resolve().parent
    src = Path(r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll")
    out_dir = here / "1.27.0.52240-fps-unlock-d3d9-ogl"
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / "game.dll"

    digest = sha256(src)
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"source hash mismatch: {digest}")

    buf = bytearray(src.read_bytes())
    applied = apply(buf)
    dst.write_bytes(buf)

    lines = [
        "# 1.27.0.52240 FPS unlock Game.dll",
        "",
        "从官方 `game.dll` 复制后改字节，**不是**从源码重新编译。输出文件名保持 `game.dll`，方便覆盖游戏目录。",
        "",
        "## 文件",
        "",
        f"- 源：`{src}`",
        f"- 源 SHA-256：`{EXPECTED_SHA256}`",
        f"- 输出：`{dst}`",
        f"- 输出 SHA-256：`{sha256(dst)}`",
        "",
        "## 改动",
        "",
        "| 名称 | 文件偏移 | 原始 | 替换 |",
        "| --- | ---: | --- | --- |",
    ]
    for name, off, old, new in applied:
        lines.append(f"| {name} | `0x{off:X}` | `{old.hex(' ')}` | `{new.hex(' ')}` |")
    lines += [
        "",
        "## 覆盖了什么",
        "",
        "- **软件 64 FPS：** `and eax, 0xFFFFFFFB` 改为 `and eax, 0xFFFFFFFF`（VA `0x6F05FCFB`）。与 1.26 `Game.dll+0x62D7FB`、WarcraftHelper 1.27a `+0x5FCFB` 同一点：不清除对象 `+0x44` 的 bit2，从而不走 `edx=0x11` 那次限帧调度。",
        "- **Direct3D9：** 独占全屏分支把 `PresentationInterval` 改为 `IMMEDIATE`；窗口化分支经 cave 同样写入 `IMMEDIATE`；去掉 `LOCKABLE_BACKBUFFER`。",
        "- **OpenGL：** 在首次 `wglMakeCurrent` 成功并加载扩展之后，调用 `wglSwapIntervalEXT(0)`（扩展不存在则跳过）。",
        "- **maxfps 默认值：** 200 → 10000，避免注册表未写时仍按 200 封顶。启动器若写入 `maxfps` 仍优先生效（`1000/maxfps` 毫秒间隔）。",
        "",
        "## 验证",
        "",
        "1. 备份游戏目录里的 `game.dll`。",
        "2. 把本目录 `game.dll` 复制到 1.27 游戏根目录（覆盖）。",
        "3. Direct3D：正常启动（不要加 `-opengl`），游戏内输入 `/fps`。",
        "4. OpenGL：用 `-opengl` 启动，再看 `/fps`。",
        "5. 建议同时把注册表 `HKCU\\Software\\Blizzard Entertainment\\Warcraft III\\Video\\lockfb` 设为 `0`，`maxfps` 设为显示器刷新率或更大。",
        "6. 测完用备份还原。不要把改过的 DLL 提交进 Git。",
        "",
        "静态分析见 `analyses/warcraft-iii-1.27-fps-unlock.md`。本补丁尚未在本机实机测帧。",
        "",
    ]
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {dst} ({len(buf)} bytes)")
    for name, off, old, new in applied:
        print(f"  {name:42} 0x{off:06X}  {old.hex()} -> {new.hex()}")
    print("sha256", sha256(dst))


if __name__ == "__main__":
    main()
