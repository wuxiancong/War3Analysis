#!/usr/bin/env python3
"""Resolve ReviveHero via native-registration sites (mov edx,name; mov ecx,handler)."""
from __future__ import annotations

import json
import struct
from pathlib import Path

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\hero-death-buyback")


def pe(data: bytes):
    e = struct.unpack_from("<I", data, 0x3C)[0]
    opt = e + 24
    ib = struct.unpack_from("<I", data, opt + 28)[0]
    coff = e + 4
    nsec = struct.unpack_from("<H", data, coff + 2)[0]
    optsz = struct.unpack_from("<H", data, coff + 16)[0]
    sec0 = coff + 20 + optsz
    secs = []
    for i in range(nsec):
        off = sec0 + i * 40
        vsz, va, rsz, raw = struct.unpack_from("<IIII", data, off + 8)
        secs.append((va, vsz, raw, rsz))
    return ib, secs


def o2r(secs, o):
    for va, _vsz, raw, rsz in secs:
        if raw <= o < raw + rsz:
            return va + (o - raw)
    return None


def r2o(secs, r):
    for va, vsz, raw, rsz in secs:
        if va <= r < va + max(vsz, rsz):
            return raw + (r - va)
    return None


def findall(d, n):
    out = []
    i = 0
    while True:
        j = d.find(n, i)
        if j < 0:
            break
        out.append(j)
        i = j + 1
    return out


def cstr_at(data, secs, abs_addr, ib):
    r = abs_addr - ib
    o = r2o(secs, r)
    if o is None:
        return None
    end = data.find(b"\x00", o)
    return data[o:end]


def resolve_revive(data: bytes, ib: int, secs) -> tuple[int | None, int | None]:
    """Return (ReviveHero handler RVA, str RVA) using registration xrefs."""
    # Collect all offsets whose cstring is exactly ReviveHero
    candidates = []
    o = 0
    while True:
        j = data.find(b"ReviveHero", o)
        if j < 0:
            break
        end = data.find(b"\x00", j)
        name = data[j:end]
        if name == b"ReviveHero":
            sr = o2r(secs, j)
            if sr is not None:
                candidates.append(sr)
        o = j + 1

    all_hits: dict[int, list[int]] = {}
    for sr in candidates:
        absva = ib + sr
        pat = struct.pack("<I", absva)
        for xo in findall(data, pat):
            xr = o2r(secs, xo)
            if xr is None:
                continue
            win_off = r2o(secs, xr - 0x20)
            if win_off is None:
                continue
            win = data[win_off : win_off + 0x40]
            ba_rel = None
            for i in range(len(win) - 5):
                if win[i] == 0xBA and struct.unpack_from("<I", win, i + 1)[0] == absva:
                    ba_rel = i
                    break
            if ba_rel is None:
                continue
            # push sig; mov edx,name; mov ecx,handler — ecx AFTER edx only
            for j in range(ba_rel + 5, min(len(win) - 5, ba_rel + 0x14)):
                if win[j] != 0xB9:
                    continue
                himm = struct.unpack_from("<I", win, j + 1)[0]
                if ib < himm < ib + 0x900000 and himm != absva:
                    all_hits.setdefault(sr, []).append(himm - ib)
    if not all_hits:
        return None, (candidates[0] if candidates else None)
    best_sr = None
    best_h = None
    for sr, hs in all_hits.items():
        pick = min(set(hs))
        if best_h is None or pick < best_h:
            best_h = pick
            best_sr = sr
    return best_h, best_sr


def main():
    handlers = json.loads((OUT / "native_handlers.json").read_text(encoding="utf-8"))
    by_ver = {e["ver"]: e for e in handlers}
    for vd in sorted(VERSIONS.iterdir()):
        dll = vd / "game.dll"
        if not dll.exists():
            continue
        data = dll.read_bytes()
        ib, secs = pe(data)
        h, sr = resolve_revive(data, ib, secs)
        e = by_ver[vd.name]
        e["ReviveHero"] = {
            "strRVA": hex(sr) if sr is not None else None,
            "handler": hex(h) if h is not None else "未确认",
        }
        print(vd.name, e["ReviveHero"]["handler"], "str", e["ReviveHero"]["strRVA"])

    rows = [by_ver[v] for v in sorted(by_ver)]
    (OUT / "native_handlers.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    lines = [
        "| Version | UnitAlive | TimerGetRemaining | TimerGetElapsed | ReviveHero | GetWidgetLife |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for e in rows:
        def h(n):
            v = e.get(n, {})
            return (v.get("handler") if isinstance(v, dict) else None) or "未确认"

        lines.append(
            f"| {e['ver']} | `{h('UnitAlive')}` | `{h('TimerGetRemaining')}` | `{h('TimerGetElapsed')}` | `{h('ReviveHero')}` | `{h('GetWidgetLife')}` |"
        )
    (OUT / "native_rva_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote table")


if __name__ == "__main__":
    main()
