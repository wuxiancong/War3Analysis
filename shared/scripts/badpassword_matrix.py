#!/usr/bin/env python3
"""Cross-version matrix for ERROR_ID_BADPASSWORD hook points."""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")
NEEDLE = b"ERROR_ID_BADPASSWORD\x00"
md = Cs(CS_ARCH_X86, CS_MODE_32)


def find_func(pe: pefile.PE, raw: bytes, rva: int) -> int | None:
    off = pe.get_offset_from_rva(rva)
    for back in range(0x1400):
        o = off - back
        if raw[o] == 0x55 and raw[o + 1] == 0x8B and raw[o + 2] == 0xEC:
            prev = raw[o - 1]
            if prev in (0xCC, 0x90, 0xC3, 0x00) or (o >= 3 and raw[o - 3] == 0xC2):
                return pe.get_rva_from_offset(o)
    return None


def next_call_rva(pe: pefile.PE, raw: bytes, base: int, rva: int) -> int | None:
    off = pe.get_offset_from_rva(rva)
    for insn in md.disasm(raw[off : off + 0x60], base + rva):
        if insn.mnemonic == "call" and insn.op_str.startswith("0x"):
            return int(insn.op_str, 16) - base
        if insn.mnemonic == "jmp" and insn.op_str.startswith("0x"):
            j = int(insn.op_str, 16) - base
            joff = pe.get_offset_from_rva(j)
            for insn2 in md.disasm(raw[joff : joff + 0x30], base + j):
                if insn2.mnemonic == "call" and insn2.op_str.startswith("0x"):
                    return int(insn2.op_str, 16) - base
            return None
    return None


def analyze(ver: Path) -> dict:
    g = next(f for f in ver.iterdir() if f.name.lower() == "game.dll")
    pe = pefile.PE(str(g))
    raw = g.read_bytes()
    base = pe.OPTIONAL_HEADER.ImageBase
    foff = raw.find(NEEDLE)
    if foff < 0:
        raise RuntimeError("string missing")
    srva = pe.get_rva_from_offset(foff)
    sva = base + srva
    imm = struct.pack("<I", sva)
    xrefs: list[int] = []
    start = 0
    while True:
        i = raw.find(imm, start)
        if i < 0:
            break
        if i > 0 and raw[i - 1] == 0xB9:
            xr = pe.get_rva_from_offset(i)
            if xr < 0xA00000:
                xrefs.append(xr)
        start = i + 1

    sites = []
    for xr in xrefs:
        func = find_func(pe, raw, xr)
        resolve = next_call_rva(pe, raw, base, xr)
        sites.append(
            {
                "xref": xr,
                "func": func,
                "resolve_or_next": resolve,
            }
        )

    # Prefer account-login style site: mov ecx,key; call resolve (not jmp-cluster)
    account = None
    for xr in xrefs:
        off = pe.get_offset_from_rva(xr)
        # pattern: B9 <imm> E8  => direct call after mov ecx
        if raw[off - 1] == 0xB9 and raw[off + 4] == 0xE8:
            account = xr
            break
    if account is None and xrefs:
        account = xrefs[0]

    account_func = find_func(pe, raw, account) if account else None
    resolve = next_call_rva(pe, raw, base, account) if account else None

    # After resolve in account path, find call to dialog helper (push 0xC pattern nearby)
    dialog = None
    if account:
        off = pe.get_offset_from_rva(account)
        window = raw[off : off + 0x80]
        for insn in md.disasm(window, base + account):
            if insn.mnemonic == "call" and insn.op_str.startswith("0x"):
                tgt = int(insn.op_str, 16) - base
                if resolve and tgt == resolve:
                    continue
                # heuristic: dialog often called with ecx=1 and many pushes
                dialog = tgt
        # better: scan for push 0xC then call
        for i in range(len(window) - 6):
            if window[i] == 0x6A and window[i + 1] == 0x0C:
                for insn in md.disasm(window[i : i + 0x30], base + account + i):
                    if insn.mnemonic == "call" and insn.op_str.startswith("0x"):
                        dialog = int(insn.op_str, 16) - base
                        break
                if dialog:
                    break

    return {
        "ver": ver.name,
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "str_file": foff,
        "str_rva": srva,
        "account_xref": account,
        "account_func": account_func,
        "string_resolve": resolve,
        "dialog_show": dialog,
        "all_sites": sites,
    }


def main() -> int:
    rows = []
    for ver in sorted(ROOT.iterdir()):
        if not ver.is_dir():
            continue
        try:
            rows.append(analyze(ver))
        except Exception as exc:  # noqa: BLE001
            print(f"{ver.name}: ERROR {exc}", file=sys.stderr)
    print(
        "| Version | account_func | account_xref(BADPASSWORD) | StringResolve | DialogShow | strRVA |"
    )
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(
            f"| {r['ver']} | `{hex(r['account_func']) if r['account_func'] is not None else '-'}` "
            f"| `{hex(r['account_xref']) if r['account_xref'] is not None else '-'}` "
            f"| `{hex(r['string_resolve']) if r['string_resolve'] is not None else '-'}` "
            f"| `{hex(r['dialog_show']) if r['dialog_show'] is not None else '-'}` "
            f"| `{hex(r['str_rva'])}` |"
        )
    print()
    for r in rows:
        print(f"## {r['ver']}  SHA256={r['sha256']}")
        for s in r["all_sites"]:
            print(
                f"  - xref `{hex(s['xref'])}` func `{hex(s['func']) if s['func'] is not None else '?'}` "
                f"next_call `{hex(s['resolve_or_next']) if s['resolve_or_next'] is not None else '?'}`"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
