# Scan all War3 game.dll versions for D3D Release, GL ScenePresent, GL Reset.
# Usage: python scan_draw_hooks.py
import hashlib
import json
import os
import struct

import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

ROOT = r"D:\Qt\workspace\War3Launcher\versions"
OUT = r"D:\Qt\workspace\War3Analysis\artifacts\draw-hooks"
VERSIONS = [
    "1.0.17.5988", "1.0.20.6048", "1.20.4.6074", "1.21.0.6263",
    "1.22.0.6328", "1.23.0.6352", "1.24.1.6374", "1.24.4.6387",
    "1.25.1.6397", "1.26.0.6401", "1.27.0.52240",
]
OGL_END = {
    "1.0.17.5988": 0x0D5BD0, "1.0.20.6048": 0x0D5BD0, "1.20.4.6074": 0x0D5BD0,
    "1.21.0.6263": 0x0D5BD0, "1.22.0.6328": 0x5235E0, "1.23.0.6352": 0x525370,
    "1.24.1.6374": 0x533D00, "1.24.4.6387": 0x533D80, "1.25.1.6397": 0x533050,
    "1.26.0.6401": 0x533280, "1.27.0.52240": 0x0F0CC0,
}
OGL_RESET = {
    "1.0.17.5988": 0x0CBED0, "1.0.20.6048": 0x0CBED0, "1.20.4.6074": 0x0CBED0,
    "1.21.0.6263": 0x0CBED0, "1.22.0.6328": 0x51AC70, "1.23.0.6352": 0x51CA00,
    "1.24.1.6374": 0x52B390, "1.24.4.6387": 0x52B410, "1.25.1.6397": 0x52A6E0,
    "1.26.0.6401": 0x52A910, "1.27.0.52240": 0x0E7670,
}
RELEASE_127 = 0x0EC510
ERAS = {
    "pre122": ["1.0.17.5988", "1.0.20.6048", "1.20.4.6074", "1.21.0.6263"],
    "mid": ["1.22.0.6328", "1.23.0.6352", "1.24.1.6374", "1.24.4.6387", "1.25.1.6397", "1.26.0.6401"],
    "post127": ["1.27.0.52240"],
}

MD = Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = True


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def load_image(path):
    pe = pefile.PE(path, fast_load=False)
    pe.parse_data_directories(directories=[
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]
    ])
    base = pe.OPTIONAL_HEADER.ImageBase
    size = pe.OPTIONAL_HEADER.SizeOfImage
    img = bytearray(size)
    exec_ranges = []
    for s in pe.sections:
        va = s.VirtualAddress
        data = s.get_data()
        img[va:va + len(data)] = data
        if s.Characteristics & 0x20000000:
            exec_ranges.append((va, va + s.Misc_VirtualSize))
    iat = {}
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for e in pe.DIRECTORY_ENTRY_IMPORT:
            dll = e.dll.decode(errors="ignore").lower()
            for i in e.imports:
                if i.name:
                    iat[(dll, i.name.decode(errors="ignore"))] = i.address - base
    return {"base": base, "size": size, "img": img, "exec": exec_ranges, "iat": iat, "pe": pe}


def in_exec(info, rva):
    return any(a <= rva < b for a, b in info["exec"])


def disasm(info, rva, nbytes=256, max_ins=40):
    end = min(len(info["img"]), rva + nbytes)
    code = bytes(info["img"][rva:end])
    out = []
    for ins in MD.disasm(code, rva):
        out.append(ins)
        if len(out) >= max_ins:
            break
    return out


def fmt_ins(ins):
    return f"{ins.address:08X}  {ins.bytes.hex(' ').upper():<24} {ins.mnemonic} {ins.op_str}"


def func_start(info, rva):
    img = info["img"]
    for k in range(rva, max(1, rva - 0x3000), -1):
        if img[k - 1] == 0xCC and img[k] != 0xCC:
            return k
    return None


def six_ok(info, rva):
    insns = disasm(info, rva, 32, 8)
    total = 0
    parts = []
    for ins in insns:
        if ins.address != rva + total:
            return False, parts
        total += ins.size
        parts.append(f"{ins.mnemonic} {ins.op_str}")
        if total == 6:
            return True, parts
        if total > 6:
            return False, parts
    return False, parts


def parse_sig(sig):
    out = []
    for p in sig.split():
        out.append(None if p == "??" else int(p, 16))
    return out


def sig_to_str(masked):
    return " ".join("??" if b is None else f"{b:02X}" for b in masked)


def find_hits(img, masked, limit=8):
    n = len(masked)
    if n == 0 or n > len(img):
        return []
    # anchor on first concrete byte
    anchors = [i for i, b in enumerate(masked) if b is not None]
    if not anchors:
        return []
    a0 = anchors[0]
    needle = bytes([masked[a0]])
    hits = []
    start = 0
    size = len(img)
    while start <= size - n and len(hits) < limit:
        j = img.find(needle, start + a0)
        if j < 0:
            break
        pos = j - a0
        if pos < 0:
            start = j + 1 - a0
            continue
        ok = True
        for k, b in enumerate(masked):
            if b is not None and img[pos + k] != b:
                ok = False
                break
        if ok:
            hits.append(pos)
            start = pos + 1
        else:
            start = pos + 1
    return hits


def mask_insn(ins):
    raw = list(ins.bytes)
    if ins.bytes[0] in (0xE8, 0xE9) and len(raw) == 5:
        return [raw[0], None, None, None, None]
    if len(raw) >= 6 and raw[0] == 0xFF and raw[1] in (0x15, 0x25):
        return raw[:2] + [None, None, None, None]
    if raw[0] in (0xA1, 0xA3) and len(raw) == 5:
        return [raw[0], None, None, None, None]
    if len(raw) == 6 and raw[0] == 0x0F and 0x80 <= raw[1] <= 0x8F:
        return raw[:2] + [None, None, None, None]
    if len(raw) == 5 and raw[0] == 0x68:
        imm = int.from_bytes(ins.bytes[1:], "little")
        # wildcard absolute addresses; keep small immediates
        if imm > 0x10000:
            return [0x68, None, None, None, None]
    if len(raw) == 5 and 0xB8 <= raw[0] <= 0xBF:
        imm = int.from_bytes(ins.bytes[1:], "little")
        if imm > 0x10000:
            return [raw[0], None, None, None, None]
    if len(raw) == 2 and raw[0] in (0xEB, 0xE2) or (len(raw) == 2 and 0x70 <= raw[0] <= 0x7F):
        return [raw[0], None]
    return raw


def insn_stream(info, rva, max_ins=48):
    return disasm(info, rva, max_ins * 15, max_ins)


def build_era_sig(images, rvas, max_ins=36):
    streams = []
    for ver, info in images.items():
        if ver not in rvas:
            continue
        insns = insn_stream(info, rvas[ver], max_ins)
        streams.append((ver, [mask_insn(i) for i in insns], insns))
    if not streams:
        return None
    # longest instruction-aligned common prefix, wildcarding bytes that differ but share length
    prefix = []
    for idx in range(min(len(s[1]) for s in streams)):
        group = [s[1][idx] for s in streams]
        if any(len(g) != len(group[0]) for g in group):
            break
        merged = []
        for col in range(len(group[0])):
            vals = {g[col] for g in group}
            if len(vals) == 1:
                merged.append(group[0][col])
            else:
                merged.append(None)
        # stop if the whole instruction collapsed to wildcards (no anchor)
        if all(b is None for b in merged):
            break
        prefix.append(merged)
    # grow until first hit == target on every version
    chosen = None
    flat_so_far = []
    for n in range(1, len(prefix) + 1):
        flat = []
        for part in prefix[:n]:
            flat.extend(part)
        # need at least 8 concrete bytes to be distinctive
        concrete = sum(1 for b in flat if b is not None)
        if concrete < 8:
            continue
        sig = sig_to_str(flat)
        ok = True
        detail = {}
        for ver, info in images.items():
            if ver not in rvas:
                continue
            hits = find_hits(info["img"], flat, limit=6)
            detail[ver] = hits
            if not hits or hits[0] != rvas[ver]:
                ok = False
        if ok:
            counts = {v: len(h) for v, h in detail.items()}
            chosen = {
                "sig": sig,
                "insns": n,
                "concrete": concrete,
                "unique": all(c == 1 for c in counts.values()),
                "counts": counts,
                "hits": {v: [hex(x) for x in h] for v, h in detail.items()},
            }
            if chosen["unique"]:
                break
    return chosen


def calls_iat(info, rva, iat_rva, window=0x900):
    if iat_rva is None:
        return []
    target = struct.pack("<I", info["base"] + iat_rva)
    pat = b"\xFF\x15" + target
    img = info["img"]
    hits = []
    start = rva
    end = min(len(img), rva + window)
    blob = bytes(img[start:end])
    i = 0
    while True:
        j = blob.find(pat, i)
        if j < 0:
            break
        hits.append(start + j)
        i = j + 1
    return hits


def iat_of(info, names):
    for (dll, name), rva in info["iat"].items():
        if name in names:
            return rva, dll, name
    return None, None, None


def release_sites(info):
    img = info["img"]
    needle = b"\x84\x05\x00\x00"
    sites = []
    seen = set()
    pos = 0
    while True:
        i = img.find(needle, pos)
        if i < 0:
            break
        pos = i + 1
        if not in_exec(info, i):
            continue
        for start in range(max(0, i - 8), i + 1):
            insns = disasm(info, start, 80, 16)
            if not insns or insns[0].address != start:
                continue
            if "0x584" not in insns[0].op_str:
                continue
            # walk until we leave a tight window
            rel = None
            null = None
            base_reg = None
            text = []
            for ins in insns[:14]:
                text.append(fmt_ins(ins))
                op = ins.op_str
                if ins.mnemonic == "call" and "+ 8]" in op.replace(" ", " ") or (
                    ins.mnemonic == "call" and "+ 8]" in op
                ):
                    rel = ins.address
                if ins.mnemonic == "call" and ("+ 8]" in op or "+8]" in op):
                    rel = ins.address
                if ins.mnemonic == "mov" and "0x584" in op and ", 0" in op:
                    null = ins.address
                if ins.mnemonic.startswith("mov") and "0x584" in op and base_reg is None:
                    # [reg + 0x584]
                    if "[" in op:
                        base_reg = op[op.find("[") + 1:op.find("+")].strip()
            if rel is not None and null is not None and start not in seen:
                seen.add(start)
                sites.append({
                    "rva": start,
                    "base": base_reg,
                    "release_call": rel,
                    "null_store": null,
                    "window": text,
                    "bytes": bytes(img[start:start + 32]).hex(" ").upper(),
                })
            break
    return sites


def prologue(info, rva, n=12):
    return [fmt_ins(i) for i in disasm(info, rva, 96, n)]


def main():
    os.makedirs(OUT, exist_ok=True)
    images = {}
    meta = {}
    for ver in VERSIONS:
        path = os.path.join(ROOT, ver, "game.dll")
        print("load", ver, flush=True)
        info = load_image(path)
        images[ver] = info
        meta[ver] = {
            "sha256": sha256(path),
            "imagebase": hex(info["base"]),
            "size": hex(info["size"]),
            "path": path,
        }

    report = {"meta": meta, "release": {}, "ogl_end": {}, "ogl_reset": {}}

    for ver, info in images.items():
        print("release", ver, flush=True)
        sites = release_sites(info)
        known = None
        if ver == "1.27.0.52240":
            known = RELEASE_127
        report["release"][ver] = {
            "sites": [{**{k: (hex(v) if isinstance(v, int) else v) for k, v in s.items() if k != "window"},
                       "window": s["window"]} for s in sites],
            "known_present": known in [s["rva"] for s in sites] if known else None,
        }

    # signatures for release: per era, use the site whose window matches the 1.27 shape if multiple
    rel_rvas = {}
    for ver, info in images.items():
        sites = report["release"][ver]["sites"]
        # prefer the one that begins with mov r32, [esi+0x584] and test/jz/call [+8]/store 0
        pick = None
        for s in sites:
            win = "\n".join(s["window"])
            if "esi + 0x584" in win and "call" in win and "+ 8]" in win:
                pick = int(s["rva"], 16)
                break
        if pick is None and sites:
            pick = int(sites[0]["rva"], 16)
        rel_rvas[ver] = pick
        report["release"][ver]["picked"] = hex(pick) if pick is not None else None
        if pick is not None:
            ok, parts = six_ok(info, pick)
            report["release"][ver]["hook6"] = {"ok": ok, "parts": parts}
            report["release"][ver]["func"] = hex(func_start(info, pick) or 0)

    print("era sig release", flush=True)
    report["release_sigs"] = {}
    for era, vers in ERAS.items():
        rvas = {v: rel_rvas[v] for v in vers if rel_rvas.get(v)}
        report["release_sigs"][era] = build_era_sig({v: images[v] for v in vers}, rvas)

    # also test the existing 1.27 signature on every version
    existing = "8B 8E 84 05 00 00 85 C9 74 ?? 8B 01 51 FF 50 08 C7 86 84 05 00 00 00 00 00 00"
    masked = parse_sig(existing)
    report["release_existing_sig"] = {}
    for ver, info in images.items():
        hits = find_hits(info["img"], masked, 8)
        report["release_existing_sig"][ver] = [hex(h) for h in hits]

    swap_name = "wglSwapLayerBuffers"
    cds_names = ("ChangeDisplaySettingsExA", "ChangeDisplaySettingsA")

    for label, table, api_names in (
        ("ogl_end", OGL_END, (swap_name,)),
        ("ogl_reset", OGL_RESET, cds_names),
    ):
        print("check", label, flush=True)
        for ver, rva in table.items():
            info = images[ver]
            iat_rva, dll, name = iat_of(info, api_names)
            calls = calls_iat(info, rva, iat_rva)
            ok, parts = six_ok(info, rva)
            report[label][ver] = {
                "rva": hex(rva),
                "func": hex(func_start(info, rva) or 0),
                "prologue": prologue(info, rva, 16),
                "iat": None if iat_rva is None else {"dll": dll, "name": name, "rva": hex(iat_rva)},
                "api_calls_in_func_window": [hex(c) for c in calls],
                "hook6": {"ok": ok, "parts": parts},
                "head16": bytes(info["img"][rva:rva + 16]).hex(" ").upper(),
            }
        report[label + "_sigs"] = {}
        for era, vers in ERAS.items():
            rvas = {v: table[v] for v in vers}
            print(" sig", label, era, flush=True)
            report[label + "_sigs"][era] = build_era_sig({v: images[v] for v in vers}, rvas)

    out_path = os.path.join(OUT, "scan.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
