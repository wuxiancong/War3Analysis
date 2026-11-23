# -*- coding: utf-8 -*-
"""
全 11 版 War3 Game.dll（1.0.17.5988 ~ 1.27.0.52240）第二轮精确扫描（不依赖 RTTI）：
补齐 1.0.17 ~ 1.21.0（无 RTTI）以及 1.22 ~ 1.26 的：
  1. CNetCommandUnitOrderBasic(0x10) / Point(0x11) / Target(0x12) 的 0xA0010/11/12 构造点 & 客户端 flags 打包器
  2. CAbilitySpell::StartCooldown (RVA + timer 偏移 +0xD0)
  3. CItem::StartCooldown (RVA + timer 偏移 +0xE4)
  4. CAbilityInventory 共享冷却表 (count +0xBC / ids +0xC0 / timers +0xDC, stride 0x14)
  5. CAgentTimer::GetRemainingTime (node+0x04 - *(node+0x0C)+0x40)
  6. CAbilityBlink (0x100002) & CAbilityItemTownPortal (0x100006) 的 GetTargetType
"""
import os, sys, struct, json
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

VERSIONS_DIR = r"D:\Qt\workspace\War3Launcher\versions"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown\all_11_versions_v2.txt"
OUT_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown\all_11_versions_v2.json"

def find_dll(ver_dir):
    for name in ("Game.dll", "game.dll"):
        p = os.path.join(ver_dir, name)
        if os.path.isfile(p):
            return p
    return None

def find_all(buf, pat, limit=60):
    res, pos = [], 0
    while len(res) < limit:
        i = buf.find(pat, pos)
        if i == -1: break
        res.append(i)
        pos = i + 1
    return res

def find_func_boundary(text, off, max_back=0x30):
    """回退找到紧接在 CC / 90 / C3 / C2 xx 00 之后的函数入口"""
    for back in range(1, min(off, max_back) + 1):
        p = off - back
        if p >= 1 and text[p-1] == 0xCC:
            return p
        if p >= 2 and text[p-2:p] == b"\x90\x90":
            return p
        if p >= 3 and text[p-3] == 0xC2 and text[p-1] == 0x00 and text[p] in (0x55, 0x56, 0x53, 0x51, 0x8B, 0x83, 0x6A, 0x64):
            return p
        if p >= 1 and text[p-1] == 0xC3 and text[p] in (0x55, 0x56, 0x53, 0x51, 0x8B, 0x83, 0x6A, 0x64):
            return p
    return off

def find_calls_to(text, tva, target_rva):
    hits = []
    for i in range(len(text) - 5):
        if text[i] == 0xE8:
            rel = struct.unpack_from("<i", text, i + 1)[0]
            if tva + i + 5 + rel == target_rva:
                hits.append(i)
    return hits

def analyze(ver, dll_path):
    pe = SimplePE32(dll_path)
    _, tva, tvs, tro, trs = pe.get_section(".text")
    text = pe.data[tro:tro+trs]
    ib = pe.image_base
    res = {"version": ver}

    # 1. CNetCommandUnitOrderBasic(0xA0010) / Point(0xA0011) / Target(0xA0012)
    for tag, val in (("netcmd_0x10", 0x000A0010), ("netcmd_0x11", 0x000A0011), ("netcmd_0x12", 0x000A0012)):
        hits = [f"0x{tva+i:06X}" for i in find_all(text, struct.pack("<I", val), 10)]
        res[tag] = hits

    # 2. 客户端 abilityFlags 打包器：搜索 (abilFlags >> 3) & 0x100 (或 shl/shr 组合 + 0x100 + 0x20 + 0x04)
    # 兼容所有寄存器：特征是 00 01 00 00 (0x100) 且附近 48 字节内有 C1 E? 10 (shr 16) 和 C1 E? 12 (shr 18)
    packers = []
    for idx in find_all(text, b"\x00\x01\x00\x00", 500):
        # 确认是 and reg, 100h (25 00 01 00 00 或 81 E? 00 01 00 00)
        if not ((idx >= 1 and text[idx-1] == 0x25) or (idx >= 2 and text[idx-2] == 0x81 and (text[idx-1] & 0xF8) == 0xE0)):
            continue
        win = text[max(0, idx-12):idx+40]
        has_shr16 = any(win[k] == 0xC1 and (win[k+1] & 0xF8) == 0xE8 and win[k+2] == 0x10 for k in range(len(win)-3))
        has_shr18 = any(win[k] == 0xC1 and (win[k+1] & 0xF8) == 0xE8 and win[k+2] == 0x12 for k in range(len(win)-3))
        if has_shr16 and has_shr18:
            f = find_func_boundary(text, idx, 0x90)
            rva = tva + f
            if rva not in packers:
                packers.append(rva)
    res["flag_packers"] = [f"0x{x:06X}" for x in packers[:6]]

    # 3. 扫描所有 push 0x000D01BE，区分 CAbilitySpell::StartCooldown 与 CItem::StartCooldown
    spell_start = None
    spell_off = None
    item_start = None
    item_off = None
    for idx in find_all(text, b"\x68\xBE\x01\x0D\x00", 40):
        pre = text[max(0, idx-40):idx]
        post = text[idx:idx+28]
        # 提取 post 中 lea reg, [reg+disp32] 或 add ecx, disp32
        disp = None
        for k in range(len(post) - 6):
            if post[k] == 0x8D and (post[k+1] & 0xC0) == 0x80:
                d = struct.unpack_from("<I", post, k+2)[0]
                if 0x80 <= d <= 0x140:
                    disp = d; break
            if post[k:k+2] == b"\x81\xC1":
                d = struct.unpack_from("<I", post, k+2)[0]
                if 0x80 <= d <= 0x140:
                    disp = d; break
        if disp is None:
            continue
        # 若 pre 中含 or [reg+20h], 200h (20 00 02 00 00) -> CAbilitySpell::StartCooldown
        if b"\x20\x00\x02\x00\x00" in pre:
            if spell_start is None:
                spell_start = tva + find_func_boundary(text, idx - 16, 0x30)
                spell_off = disp
        # 若 pre 中极短 (6A 00 6A 00 51) 且无 0x200 -> 可能是 CItem::StartCooldown 或 CAbilitySpell
        elif b"\x6A\x00\x6A\x00" in pre[-12:]:
            fstart = tva + find_func_boundary(text, idx - 4, 0x20)
            # CItem::StartCooldown 是短函数 (<= 0x24 字节) 且结尾 ret 8 (C2 08 00)
            fbytes = pe.read_bytes(fstart, 0x28)
            if b"\xC2\x08\x00" in fbytes:
                item_start = fstart
                item_off = disp
            elif spell_start is None and disp == 0xD0:
                spell_start = fstart
                spell_off = disp

    res["CAbilitySpell_StartCD"] = f"0x{spell_start:06X}" if spell_start else None
    res["CAbilitySpell_timer_off"] = f"+0x{spell_off:X}" if spell_off is not None else None
    res["CItem_StartCD"] = f"0x{item_start:06X}" if item_start else None
    res["CItem_timer_off"] = f"+0x{item_off:X}" if item_off is not None else None

    # 4. 通过 CItem::StartCooldown 的调用者反查 CAbilityInventory 共享冷却表偏移
    if item_start:
        callers = find_calls_to(text, tva, item_start)
        res["CItem_StartCD_callers"] = [f"0x{tva+c:06X}" for c in callers]
        for c in callers:
            win = text[max(0, c - 0x140):c]
            # 找 20 字节步长: lea r, [r+r*4] (8D ?? ??) 紧跟 [base + r*4] 或 imul r, r, 14h (6B ?? 14)
            # 在 1.22~1.27 中都是 add r, 0Bh; lea r, [r+r*4]; lea r, [base+r*4] -> 0x0B * 20 = 0xDC
            st_off, id_off, cnt_off = None, None, None
            for k in range(len(win) - 10):
                # Pattern A: 83 C? imm8 (add reg, imm8) + 8D (lea)
                if win[k] == 0x83 and (win[k+1] & 0xF8) == 0xC0 and 0x06 <= win[k+2] <= 0x18 and win[k+3] == 0x8D:
                    st_off = win[k+2] * 20
                    pre = win[max(0, k-80):k]
                    for m in range(len(pre) - 4):
                        d = struct.unpack_from("<I", pre, m)[0]
                        if d == st_off - 0x1C: id_off = d
                        elif d == st_off - 0x20: cnt_off = d
                    break
                # Pattern B: imul reg, reg, 14h (6B ?? 14) + disp32
                if win[k] == 0x6B and win[k+2] == 0x14:
                    post2 = win[k+3:k+16]
                    for m in range(len(post2) - 4):
                        d = struct.unpack_from("<I", post2, m)[0]
                        if 0xA0 <= d <= 0x140:
                            st_off = d; break
                    if st_off:
                        pre = win[max(0, k-80):k]
                        for m in range(len(pre) - 4):
                            d = struct.unpack_from("<I", pre, m)[0]
                            if d == st_off - 0x1C: id_off = d
                            elif d == st_off - 0x20: cnt_off = d
                        break
            if st_off:
                res["Inv_sharedCd_cnt"]   = f"+0x{cnt_off:X}" if cnt_off else None
                res["Inv_sharedCd_ids"]   = f"+0x{id_off:X}" if id_off else None
                res["Inv_sharedCd_timer"] = f"+0x{st_off:X}"
                break

    # 5. 检查 mov eax, 0x100002; ret (Blink) 和 mov eax, 0x100006; ret (TP)
    b_hits = [f"0x{tva+i:06X}" for i in find_all(text, b"\xB8\x02\x00\x10\x00\xC3", 5)]
    tp_hits = [f"0x{tva+i:06X}" for i in find_all(text, b"\xB8\x06\x00\x10\x00\xC3", 5)]
    res["Blink_0x100002"] = b_hits
    res["TP_0x100006"]    = tp_hits

    # 6. 验证 CAgentTimer::GetRemainingTime 模式: +0x0C (node) -> +0x0C (mgr) -> +0x40 (gameClock) & +0x04 (expire)
    # 特征: add reg, 40h (83 C? 40) 附近 16 字节有 add reg, 4 (83 C? 04) 且前面有 mov reg, [reg+0Ch]
    timer_rem_hits = []
    for idx in find_all(text, b"\x40", 0):
        pass
    # 更精确搜索 83 C? 40 (add reg, 40h) 且前 16 字节内有 83 C? 04 和 8B ?? 0C
    for r in range(8):
        pat = bytes([0x83, 0xC0 + r, 0x40])
        for idx in find_all(text, pat, 80):
            win = text[max(0, idx-24):idx+8]
            has_add4 = any(win[k] == 0x83 and (win[k+1] & 0xF8) == 0xC0 and win[k+2] == 0x04 for k in range(len(win)-3))
            has_mov0c = any(win[k] == 0x8B and (win[k+1] & 0xC0) == 0x40 and win[k+2] == 0x0C for k in range(len(win)-3))
            if has_add4 and has_mov0c:
                f = tva + find_func_boundary(text, idx - 12, 0x40)
                if f not in timer_rem_hits:
                    timer_rem_hits.append(f)
    res["CAgentTimer_GetRem_candidates"] = [f"0x{x:06X}" for x in timer_rem_hits[:4]]

    return res

def main():
    versions = sorted([d for d in os.listdir(VERSIONS_DIR) if os.path.isdir(os.path.join(VERSIONS_DIR, d))])
    all_res = []
    for v in versions:
        dll = find_dll(os.path.join(VERSIONS_DIR, v))
        if not dll: continue
        print(f"Scanning v2 {v} ...")
        all_res.append(analyze(v, dll))

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_res, f, indent=2, ensure_ascii=False)

    lines = ["=== 全 11 版 War3 Game.dll 第二轮扫描（免 RTTI） ==="]
    for r in all_res:
        lines.append(f"\n[{r['version']}]")
        for k, val in r.items():
            if k != "version":
                lines.append(f"  {k:30s}: {val}")
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Done! -> {OUT_TXT}")

if __name__ == "__main__":
    main()
