# -*- coding: utf-8 -*-
"""
全 11 版 War3 Game.dll（1.0.17.5988 ~ 1.27.0.52240）批量逆向验证脚本：
一次读取每个版本的 Game.dll，验证并提取：
  1. CNetCommandUnitOrderBasic(0x10) / TargetPoint(0x11) / TargetImage(0x12) 虚表与客户端发包标志位打包器
  2. CAbilityChannel / CAbilityBlink / CAbilityItemTownPortal 的 GetTargetType() 返回值与虚槽
  3. CAgentTimer::GetTimeout (+0x10) / GetRemainingTime (+0x18) 内存偏移
  4. CAbilitySpell 冷却标志 (+0x20 & 0x200) 与 CAgentTimer 偏移 (+0xD0 / node +0xDC) 及 StartCooldown RVA
  5. CItem 冷却 CAgentTimer 偏移 (+0xE4 / node +0xF0) 与技能数组偏移 (+0x98 / +0x9C)
  6. CAbilityInventory 共享冷却表偏移 (count +0xBC / ids +0xC0 / timers +0xDC, stride 0x14)
"""
import os, sys, struct, json
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

VERSIONS_DIR = r"D:\Qt\workspace\War3Launcher\versions"
OUT_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown\all_11_versions_scan.json"
OUT_TXT  = r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown\all_11_versions_scan.txt"

def find_dll(ver_dir):
    for name in ("Game.dll", "game.dll"):
        p = os.path.join(ver_dir, name)
        if os.path.isfile(p):
            return p
    return None

def find_all_bytes(buf, pat, max_hits=50):
    hits = []
    pos = 0
    while len(hits) < max_hits:
        idx = buf.find(pat, pos)
        if idx == -1:
            break
        hits.append(idx)
        pos = idx + 1
    return hits

def find_rtti_exact(pe, exact_name):
    """按精确 RTTI 名（如 '.?AVCAbilitySpell@@'）查找主虚表 (offset == 0)"""
    raw = pe.data
    needle = exact_name.encode("ascii") + b"\x00"
    idx = raw.find(needle)
    if idx == -1:
        return None
    td_rva = pe.off_to_rva(idx - 8)
    if td_rva is None:
        return None
    td_bytes = struct.pack("<I", pe.image_base + td_rva)
    cpos = 0
    while True:
        cidx = raw.find(td_bytes, cpos)
        if cidx == -1:
            break
        cpos = cidx + 1
        col_off = cidx - 12
        if col_off < 0:
            continue
        sig, offset, cdOffset = struct.unpack_from("<III", raw, col_off)
        if sig == 0 and offset == 0 and cdOffset == 0:
            col_rva = pe.off_to_rva(col_off)
            if col_rva is None:
                continue
            col_bytes = struct.pack("<I", pe.image_base + col_rva)
            vidx = raw.find(col_bytes)
            if vidx != -1:
                return pe.off_to_rva(vidx + 4)
    return None

def find_func_start(text, off, max_back=0x40):
    """向前回退寻找 55 8B EC 或 CC 填充后的函数入口"""
    for back in range(0, min(off, max_back)):
        p = off - back
        if p >= 2 and text[p-1] in (0xCC, 0x90, 0xC3) and text[p] in (0x55, 0x56, 0x53, 0x51, 0x8B, 0x83):
            if text[p:p+3] == b"\x55\x8B\xEC":
                return p
            if p >= 2 and text[p-2:p] == b"\xCC\xCC":
                return p
    return off

def analyze_version(ver, dll_path):
    pe = SimplePE32(dll_path)
    tname, tva, tvs, tro, trs = pe.get_section(".text")
    text = pe.data[tro:tro+trs]
    ib = pe.image_base

    res = {"version": ver, "image_base": f"0x{ib:08X}"}

    # 1. RTTI 虚表
    rtti_map = {
        "vt_CAgentTimer": ".?AVCAgentTimer@@",
        "vt_CAbilitySpell": ".?AVCAbilitySpell@@",
        "vt_CAbilityChannel": ".?AVCAbilityChannel@@",
        "vt_CAbilityBlink": ".?AVCAbilityBlink@@",
        "vt_CAbilityItemTownPortal": ".?AVCAbilityItemTownPortal@@",
        "vt_CAbilityInventory": ".?AVCAbilityInventory@@",
        "vt_CItem": ".?AVCItem@@",
        "vt_NetCmdBasic": ".?AVCNetCommandUnitOrderBasic@@",
        "vt_NetCmdPoint": ".?AVCNetCommandUnitOrderTargetPoint@@",
        "vt_NetCmdTarget": ".?AVCNetCommandUnitOrderTargetImage@@",
    }
    vts = {}
    for k, cname in rtti_map.items():
        v = find_rtti_exact(pe, cname)
        vts[k] = v
        res[k] = f"0x{v:06X}" if v is not None else None

    # 2. 验证 CAgentTimer::GetTimeout (vt+0x10) 与 GetRemainingTime (vt+0x18) 偏移
    if vts["vt_CAgentTimer"]:
        vt = vts["vt_CAgentTimer"]
        fn_timeout = pe.read_u32(vt + 0x10) - ib
        fn_rem     = pe.read_u32(vt + 0x18) - ib
        res["CAgentTimer_GetTimeout"] = f"0x{fn_timeout:06X}"
        res["CAgentTimer_GetRemaining"] = f"0x{fn_rem:06X}"
        b_to = pe.read_bytes(fn_timeout, 0x40)
        b_rm = pe.read_bytes(fn_rem, 0x60)
        # 检查 +0x0C (node) / +0x08 (total) / +0x04 (expire) / +0x40 (gameClock)
        res["CAgentTimer_offsets_ok"] = (
            (b"\x0C" in b_to and b"\x08" in b_to) and
            (b"\x0C" in b_rm and b"\x40" in b_rm)
        )

    # 3. 定位客户端 abilityFlags 打包器 (0x10/0x11/0x12)
    # 特征：and eax, 100h (25 00 01 00 00) 且附近 32 字节内有 83 E? 20 和 83 E? 04
    pack_hits = []
    for idx in find_all_bytes(text, b"\x25\x00\x01\x00\x00", 40):
        win = text[max(0, idx-16):idx+36]
        if (b"\x83\xE0\x20" in win or b"\x83\xE1\x20" in win or b"\x83\xE2\x20" in win) and \
           (b"\x83\xE1\x04" in win or b"\x83\xE0\x04" in win or b"\x83\xE2\x04" in win):
            fstart = find_func_start(text, idx, 0x90)
            rva = tva + fstart
            if rva not in pack_hits:
                pack_hits.append(rva)
    res["client_flag_packers"] = [f"0x{x:06X}" for x in pack_hits[:6]]

    # 4. 定位 CAbilityBlink / CAbilityItemTownPortal / CAbilityChannel 的 GetTargetType()
    # 在 CAbilityBlink 虚表中扫描返回 mov eax, 0x100002; ret (B8 02 00 10 00 C3) 的虚槽
    target_slot = None
    if vts["vt_CAbilityBlink"]:
        vt_b = vts["vt_CAbilityBlink"]
        for off in range(0x280, 0x380, 4):
            fn_va = pe.read_u32(vt_b + off)
            if fn_va and ib <= fn_va < ib + tva + tvs:
                fb = pe.read_bytes(fn_va - ib, 8)
                if fb.startswith(b"\xB8\x02\x00\x10\x00\xC3"):
                    target_slot = off
                    res["GetTargetType_vslot"] = f"+0x{off:03X}"
                    res["Blink_GetTargetType"] = f"0x{fn_va - ib:06X} (0x100002)"
                    break
    if target_slot and vts["vt_CAbilityItemTownPortal"]:
        fn_va = pe.read_u32(vts["vt_CAbilityItemTownPortal"] + target_slot)
        fb = pe.read_bytes(fn_va - ib, 8)
        val = struct.unpack_from("<I", fb, 1)[0] if fb[:1] == b"\xB8" else None
        res["TP_GetTargetType"] = f"0x{fn_va - ib:06X} (0x{val:X})" if val is not None else f"0x{fn_va - ib:06X}"
    if target_slot and vts["vt_CAbilityChannel"]:
        fn_va = pe.read_u32(vts["vt_CAbilityChannel"] + target_slot)
        fb = pe.read_bytes(fn_va - ib, 0x90)
        has_6 = b"\xBE\x06\x00\x00\x00" in fb or b"\xB8\x06\x00\x00\x00" in fb or b"\xBF\x06\x00\x00\x00" in fb
        has_100k = b"\x00\x00\x10\x00" in fb
        res["Channel_GetTargetType"] = f"0x{fn_va - ib:06X} (has_6={has_6}, has_100k={has_100k})"

    # 5. 定位 CAbilitySpell::StartCooldown（特征：push 0x000D01BE + 附近 or [reg+20h], 200h + lea reg, [reg+XX]）
    spell_cd_hits = []
    item_cd_start = None
    item_cd_off = None
    for idx in find_all_bytes(text, b"\x68\xBE\x01\x0D\x00", 30):
        win_pre = text[max(0, idx-32):idx]
        win_post = text[idx:idx+24]
        # CAbilitySpell::StartCooldown: 前面有 or [reg+20h], 200h (81 4? 20 00 02 00 00)
        if b"\x20\x00\x02\x00\x00" in win_pre:
            # 找后面 lea ecx, [reg+disp32] (8D 8? disp32) 或 add ecx, disp32 (81 C1 disp32)
            disp = None
            for k in range(len(win_post) - 6):
                if win_post[k] == 0x8D and (win_post[k+1] & 0xC0) == 0x80:
                    disp = struct.unpack_from("<I", win_post, k+2)[0]
                    break
                if win_post[k:k+2] == b"\x81\xC1":
                    disp = struct.unpack_from("<I", win_post, k+2)[0]
                    break
            fstart = find_func_start(text, idx - 20, 0x30)
            spell_cd_hits.append((tva + fstart, disp))
        else:
            # 可能是 CItem::StartCooldown: 后面紧跟 add ecx, 0xE4 (81 C1 E4 00 00 00) 或 lea ecx, [reg+0xE4]
            # 且前面 16 字节内是函数入口 6A 00 6A 00 51 68 BE 01 0D 00
            if b"\x6A\x00\x6A\x00" in win_pre[-12:] and (b"\x81\xC1" in win_post or b"\x8D" in win_post):
                disp = None
                for k in range(len(win_post) - 6):
                    if win_post[k:k+2] == b"\x81\xC1":
                        disp = struct.unpack_from("<I", win_post, k+2)[0]
                        break
                    if win_post[k] == 0x8D and (win_post[k+1] & 0xC0) == 0x80:
                        disp = struct.unpack_from("<I", win_post, k+2)[0]
                        break
                if disp is not None and 0xB0 <= disp <= 0x120:
                    fstart = find_func_start(text, idx - 8, 0x20)
                    item_cd_start = tva + fstart
                    item_cd_off = disp

    if spell_cd_hits:
        rva, disp = spell_cd_hits[0]
        res["CAbilitySpell_StartCooldown"] = f"0x{rva:06X}"
        res["CAbilitySpell_timer_off"] = f"+0x{disp:X}" if disp is not None else "unknown"
    else:
        res["CAbilitySpell_StartCooldown"] = None
        res["CAbilitySpell_timer_off"] = None

    res["CItem_StartCooldown"] = f"0x{item_cd_start:06X}" if item_cd_start else None
    res["CItem_timer_off"] = f"+0x{item_cd_off:X}" if item_cd_off is not None else None

    # 6. 通过 CItem::StartCooldown 的调用者反推 CAbilityInventory 共享冷却表偏移！
    if item_cd_start:
        # 找调用 item_cd_start 的地方
        callers = []
        for i in range(len(text) - 5):
            if text[i] == 0xE8:
                rel = struct.unpack_from("<i", text, i + 1)[0]
                if tva + i + 5 + rel == item_cd_start:
                    callers.append(i)
        res["CItem_StartCD_callers"] = [f"0x{tva+c:06X}" for c in callers]
        if callers:
            # 在调用点往前 0x100 字节内搜索共享冷却数组特征：
            # add reg, 0Bh (83 C? 0B) + lea reg, [reg+reg*4] + lea reg, [edi+reg*4] -> 20 * 11 = 0xDC!
            # 以及前面的 count 偏移 [edi+disp32] 和 ids 偏移 [edi+disp32]
            c = callers[0]
            win = text[max(0, c - 0x110):c]
            # 找 83 C? 0B (add r, 0x0B -> 0xDC) 或任意 83 C? imm8 紧跟 8D ?? ?? (lea *, [r+r*4])
            shared_timer_off = None
            shared_ids_off = None
            shared_cnt_off = None
            for k in range(len(win) - 10):
                if win[k] == 0x83 and (win[k+1] & 0xF8) == 0xC0 and 0x06 <= win[k+2] <= 0x14:
                    # 看看后面 8 字节有没有 *4 (8D .. 8?)
                    if win[k+3] == 0x8D:
                        shared_timer_off = win[k+2] * 20
                        # 往前找 lea reg, [reg+disp32] (ids) 和 mov reg, [reg+disp32] (count)
                        pre = win[max(0, k-64):k]
                        # 找所有 disp32 在 [shared_timer_off - 0x30, shared_timer_off - 0x10] 范围的值
                        for m in range(len(pre) - 4):
                            d = struct.unpack_from("<I", pre, m)[0]
                            if d == shared_timer_off - 0x1C:
                                shared_ids_off = d
                            elif d == shared_timer_off - 0x20:
                                shared_cnt_off = d
                        break
            res["Inv_sharedCd_cnt_off"]   = f"+0x{shared_cnt_off:X}" if shared_cnt_off else None
            res["Inv_sharedCd_ids_off"]   = f"+0x{shared_ids_off:X}" if shared_ids_off else None
            res["Inv_sharedCd_timer_off"] = f"+0x{shared_timer_off:X}" if shared_timer_off else None

    # 7. 检查 CItem+0x98/+0x9C (item ability array): 在 CItem_StartCooldown 附近 0x2000 字节搜 0x200 + +0x98/+0x9C
    if item_cd_start:
        c_off = item_cd_start - tva
        win = text[max(0, c_off - 0x1000):min(len(text), c_off + 0x2500)]
        # 搜 cmp dword ptr [reg+98h], reg + lea reg, [reg+9Ch]
        found_98 = (b"\x98\x00\x00\x00" in win and b"\x9C\x00\x00\x00" in win)
        res["CItem_abil_array_98_9C"] = found_98

    return res

def main():
    versions = sorted([d for d in os.listdir(VERSIONS_DIR) if os.path.isdir(os.path.join(VERSIONS_DIR, d))])
    all_res = []
    for v in versions:
        dll = find_dll(os.path.join(VERSIONS_DIR, v))
        if not dll:
            print(f"[SKIP] {v}: no Game.dll")
            continue
        print(f"Scanning {v} ...")
        r = analyze_version(v, dll)
        all_res.append(r)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_res, f, indent=2, ensure_ascii=False)

    lines = []
    lines.append("=== 全 11 版 War3 Game.dll 批量逆向扫描结果 ===")
    for r in all_res:
        lines.append(f"\n[{r['version']}] (base={r['image_base']})")
        for k, val in r.items():
            if k not in ("version", "image_base"):
                lines.append(f"  {k:28s}: {val}")
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nDone! Scanned {len(all_res)} versions -> {OUT_TXT}")

if __name__ == "__main__":
    main()
