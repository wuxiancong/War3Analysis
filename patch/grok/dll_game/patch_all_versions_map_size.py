"""NOP Warcraft III game.dll map-size rejects.

Same method as LoveBeforT/WarcraftHelper plugin/sizebypass.cpp:
overwrite `CMP EAX, imm32` plus the following `JA` with NOP.
Does not modify the source DLL in versions\\.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT_ROOT = Path(r"D:\Qt\workspace\War3Analysis\patch\grok\dll_game")
OLD_IMMS = {
    bytes.fromhex("00004000"): 0x400000,
    bytes.fromhex("00008000"): 0x800000,
    bytes.fromhex("000080FF"): 0xFF800000,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pe_file_to_rva(data: bytes, file_off: int) -> int:
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    num = struct.unpack_from("<H", data, e_lfanew + 6)[0]
    opt = struct.unpack_from("<H", data, e_lfanew + 20)[0]
    sec = e_lfanew + 24 + opt
    for index in range(num):
        off = sec + index * 40
        virtual_size, virtual_address, raw_size, raw_ptr = struct.unpack_from("<IIII", data, off + 8)
        if raw_ptr <= file_off < raw_ptr + raw_size:
            return virtual_address + (file_off - raw_ptr)
    raise RuntimeError(f"file offset {file_off:#x} is outside a section")


def find_sites(data: bytes) -> list[dict]:
    sites = []
    start = 0
    while True:
        index = data.find(b"\x3D", start)
        if index < 0 or index + 7 > len(data):
            break
        immediate = data[index + 1 : index + 5]
        near = data[index + 5 : index + 7] == b"\x0F\x87"
        short = data[index + 5] == 0x77
        if immediate in OLD_IMMS and (near or short):
            nbytes = 11 if near else 7
            sites.append(
                {
                    "file": index,
                    "rva": pe_file_to_rva(data, index),
                    "old_imm": OLD_IMMS[immediate],
                    "old_bytes": data[index : index + nbytes],
                    "branch": "ja-near" if near else "ja-short",
                    "nbytes": nbytes,
                }
            )
        start = index + 1
    return sites


def patch_version(version: str) -> str:
    source = VERSIONS / version / "game.dll"
    if not source.is_file():
        raise SystemExit(f"missing sample: {source}")
    original = source.read_bytes()
    sites = find_sites(original)
    if not sites:
        raise SystemExit(f"{version}: no map-size compares")
    patched = bytearray(original)
    for site in sites:
        patched[site["file"] : site["file"] + site["nbytes"]] = b"\x90" * site["nbytes"]
    if find_sites(bytes(patched)):
        raise SystemExit(f"{version}: old limit compare still present after patch")
    out_dir = OUT_ROOT / f"{version}-map-size-unlock"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dll = out_dir / "game.dll"
    out_dll.write_bytes(patched)
    source_hash = sha256(source)
    out_hash = sha256(out_dll)
    rows = []
    for number, site in enumerate(sites, start=1):
        rows.append(
            "| {num} | `{file}` | `{rva}` | `{branch}` | `{n}` | `{old}` | `{new}` |".format(
                num=number,
                file=f"0x{site['file']:X}",
                rva=f"0x{site['rva']:X}",
                branch=site["branch"],
                n=site["nbytes"],
                old=site["old_bytes"].hex(),
                new=("90" * site["nbytes"]),
            )
        )
    readme = f"""# {version} map size unlock

从 `versions\\{version}\\game.dll` 复制后，把地图大小检查 `CMP EAX, imm32` + `JA` 整段改成 NOP。
做法与 [WarcraftHelper sizebypass.cpp](https://github.com/LoveBeforT/WarcraftHelper/blob/master/WarcraftHelper/plugin/sizebypass.cpp) 相同。
长度为 0、以及文件大小高 32 位非 0 的拒绝仍然保留。

## 文件

- 源 DLL：`{source}`
- 源 SHA-256：`{source_hash}`
- 输出 DLL：`{out_dll}`
- 输出 SHA-256：`{out_hash}`

## 改动

近程 `JA`（`0F 87`）NOP 11 字节，短跳 `JA`（`77`）NOP 7 字节。1.20e / 1.27a 的 RVA 与 WarcraftHelper 一致。

| # | 指令文件偏移 | 比较指令 RVA | 跳转 | 字节 | 原始 | 替换 |
| --- | ---: | ---: | --- | ---: | --- | --- |
{chr(10).join(rows)}

## 验证

1. 备份该版本游戏目录里的 `game.dll`。
2. 用本目录的 `game.dll` 覆盖游戏根目录同名文件。
3. 启动器切换版本会从 `versions\\` 还原官方 DLL，覆盖之后再测。
4. 1.23 及更早旧阈值是 4 MiB，1.24 起是 8 MiB。低版本仍不能运行需要更高 common.j 的地图。
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    print(f"{version} sites={len(sites)} out={out_hash}")
    return out_hash


def main() -> None:
    versions = sorted(path.name for path in VERSIONS.iterdir() if (path / "game.dll").is_file())
    if len(versions) != 11:
        raise SystemExit(f"expected 11 versions, found {len(versions)}: {versions}")
    hashes = []
    for version in versions:
        hashes.append((version, patch_version(version)))
    print("---")
    for version, digest in hashes:
        print(f"{version} {digest[:12]}")


if __name__ == "__main__":
    main()
