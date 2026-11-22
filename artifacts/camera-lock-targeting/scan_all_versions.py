# -*- coding: utf-8 -*-
r"""
War3 全 11 个版本 game.dll 完整偏移与 RVA 补齐核验脚本 (v3)
通过：
1. CWorldFrameWar3::OnMouseDown (含 push 0x1A0068) 内紧跟读取 m_targetMode 后的 `call CGameUI::IsCurrentMode`
   直接反汇编 IsCurrentMode 第一条指令拿到 100% 精确的 `CGameUI -> m_currentMode`！
2. SetTargetController 内 `dec dword ptr [reg+4]` 之前加载的 `[this + off]` 拿到 100% 精确的 `CCameraWar3 -> m_targetUnit`！
3. 精确匹配 `CCameraWar3::HasTargetController` (以 `mov ecx, [ecx + m_targetUnit]` 开头且含 `0x2B61676C`)，并统计其全部 Xrefs（含 CMinimap::OnMouseDown）及提取 `CGameUI::SetMode` / `CGameUI::PopMode`！
"""
import os
import re
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

VER_ROOT = r"D:\Qt\workspace\War3Launcher\versions"
OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\camera-lock-targeting\all_versions_offsets.txt"

KNOWN_NATIVES = {
    "1.0.17.5988":  {"SetCamTgt": 0x2DD570, "SetCamPos": 0x2DD0D0, "ResetCam": 0x2DD300},
    "1.0.20.6048":  {"SetCamTgt": 0x2DD570, "SetCamPos": 0x2DD0D0, "ResetCam": 0x2DD300},
    "1.20.4.6074":  {"SetCamTgt": 0x2DD690, "SetCamPos": 0x2DD1F0, "ResetCam": 0x2DD420},
    "1.21.0.6263":  {"SetCamTgt": 0x2E0C60, "SetCamPos": 0x2E07C0, "ResetCam": 0x2E09F0},
    "1.22.0.6328":  {"SetCamTgt": 0x3C5DF0, "SetCamPos": 0x3AED90, "ResetCam": 0x3AEE70},
    "1.23.0.6352":  {"SetCamTgt": 0x3C7B10, "SetCamPos": 0x3B0A90, "ResetCam": 0x3B0B70},
    "1.24.1.6374":  {"SetCamTgt": 0x3CE1E0, "SetCamPos": 0x3B5050, "ResetCam": 0x3B5130},
    "1.24.4.6387":  {"SetCamTgt": 0x3CE2A0, "SetCamPos": 0x3B5110, "ResetCam": 0x3B51F0},
    "1.25.1.6397":  {"SetCamTgt": 0x3CD530, "SetCamPos": 0x3B43A0, "ResetCam": 0x3B4480},
    "1.26.0.6401":  {"SetCamTgt": 0x3CD760, "SetCamPos": 0x3B45D0, "ResetCam": 0x3B46B0},
    "1.27.0.52240": {"SetCamTgt": 0x1F42F0, "SetCamPos": 0x1F4200, "ResetCam": 0x1F3110},
}

def find_dll(ver_dir):
    for name in ("game.dll", "Game.dll"):
        p = os.path.join(ver_dir, name)
        if os.path.exists(p):
            return p
    return None

def disasm_bytes(md, pe, rva, nbytes=0x200):
    img = pe.OPTIONAL_HEADER.ImageBase
    off = pe.get_offset_from_rva(rva)
    return list(md.disasm(pe.__data__[off:off + nbytes], img + rva))

def disasm_fn(md, pe, rva, nbytes=0x260):
    img = pe.OPTIONAL_HEADER.ImageBase
    res = []
    for ins in disasm_bytes(md, pe, rva, nbytes):
        res.append(ins)
        if ins.mnemonic.startswith("ret") and len(res) > 1:
            nxt_off = pe.get_offset_from_rva(ins.address - img) + ins.size
            if nxt_off < len(pe.__data__) and pe.__data__[nxt_off] in (0xCC, 0x90):
                break
            if len(res) > 6:
                break
    return res

def extract_calls(insns, img, sz_img):
    out = []
    for ins in insns:
        if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
            try:
                t = int(ins.op_str, 16) - img
                if 0x1000 <= t < sz_img:
                    out.append((ins.address - img, t, ins.mnemonic))
            except Exception:
                pass
    return out

def analyze_version(ver, dll_path):
    pe = pefile.PE(dll_path, fast_load=True)
    data = pe.__data__
    img = pe.OPTIONAL_HEADER.ImageBase
    sz_img = pe.OPTIONAL_HEADER.SizeOfImage
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    kn = KNOWN_NATIVES[ver]
    info = {"ver": ver}

    # 1. SetCameraPosition -> GetCGameUI, GetCamera, SetPosition, SetTargetController, m_worldFrame, m_camDirty
    ins_pos = disasm_fn(md, pe, kn["SetCamPos"], 0x90)
    calls_pos = [t for _, t, m in extract_calls(ins_pos, img, sz_img) if m == "call"]
    info["GetCGameUI"] = calls_pos[0]
    info["GetCamera"] = calls_pos[1] if len(calls_pos) >= 3 else None
    info["SetPosition"] = calls_pos[-1]

    ins_tgt = disasm_fn(md, pe, kn["SetCamTgt"], 0xB0)
    calls_tgt = [t for _, t, m in extract_calls(ins_tgt, img, sz_img) if m == "call"]
    if info["GetCamera"] is None and len(calls_tgt) >= 2:
        info["GetCamera"] = calls_tgt[1]
    info["SetTargetController"] = calls_tgt[-1]

    # g_pGameUI
    ins_ui = disasm_fn(md, pe, info["GetCGameUI"], 0x100)
    cand = [int(m.group(1), 16) - img for ins in ins_ui
            for m in [re.search(r"dword ptr \[(0x[0-9a-f]+)\]", ins.op_str)]
            if m and img + 0x100000 <= int(m.group(1), 16) < img + sz_img]
    freq = {r: cand.count(r) for r in cand}
    info["g_pGameUI"] = next((r for r in cand if freq[r] >= 2), cand[-1] if cand else None)

    # m_camera
    if info["GetCamera"]:
        for ins in disasm_fn(md, pe, info["GetCamera"], 0x20):
            m = re.search(r"\[e[a-z]{2} \+ (0x[0-9a-f]+)\]", ins.op_str)
            if m:
                info["off_m_camera"] = int(m.group(1), 16)
                break

    # SetPosition 内部: 修正 1.0.17~1.21 SetTargetController + 提取 m_worldFrame, m_camDirty
    ins_sp = disasm_fn(md, pe, info["SetPosition"], 0x240)
    sp_calls = [t for _, t, m in extract_calls(ins_sp, img, sz_img) if m == "call"]
    if len(sp_calls) >= 3 and abs(info["SetTargetController"] - info["SetPosition"]) > 0x10000:
        info["SetTargetController"] = sp_calls[2]
    seen_ui = False
    for ins in ins_sp:
        if ins.mnemonic == "call":
            try:
                if int(ins.op_str, 16) - img == info["GetCGameUI"]:
                    seen_ui = True
            except Exception:
                pass
        elif seen_ui:
            m1 = re.search(r"dword ptr \[e[a-z]{2} \+ (0x3[0-9a-f]{2})\]$", ins.op_str)
            if m1 and "off_m_worldFrame" not in info:
                info["off_m_worldFrame"] = int(m1.group(1), 16)
            m2 = re.search(r"dword ptr \[e[a-z]{2} \+ (0x3[0-9a-f]{2})\], 1$", ins.op_str)
            if m2 and "off_wf_camDirty" not in info:
                info["off_wf_camDirty"] = int(m2.group(1), 16)

    # SetTargetController -> m_targetUnit: 找 `mov dword ptr [reg + 0x44], 0` 或释放引用前的 `[reg + 0x44]`
    ins_stc = disasm_fn(md, pe, info["SetTargetController"], 0x140)
    for k, ins in enumerate(ins_stc):
        if ins.mnemonic == "dec" and "+ 4]" in ins.op_str:
            # 往前 6 条找 mov reg, [base + off]
            for j in range(max(0, k - 6), k):
                m = re.search(r"dword ptr \[e(?:ax|bx|cx|dx|si|di|bp) \+ (0x[0-9a-f]+)\]", ins_stc[j].op_str)
                if m and "ebp +" not in ins_stc[j].op_str and "esp +" not in ins_stc[j].op_str:
                    v = int(m.group(1), 16)
                    if 0x20 <= v <= 0x60:
                        info["off_cam_targetUnit"] = v
                        break
            if "off_cam_targetUnit" in info:
                break

    # ResetToGameCamera -> ResetCamera
    ins_rst = disasm_fn(md, pe, kn["ResetCam"], 0x70)
    calls_rst = [t for _, t, m in extract_calls(ins_rst, img, sz_img) if m == "call"]
    if calls_rst:
        info["ResetCamera"] = calls_rst[-1]

    # CWorldFrameWar3::OnMouseDown -> m_targetMode (+0x210 / +0x204) & IsCurrentMode -> m_currentMode (+0x1B4 / +0x1A8)
    t_sec = pe.sections[0]
    t_off, t_rva, t_sz = t_sec.PointerToRawData, t_sec.VirtualAddress, t_sec.SizeOfRawData
    tbuf = data[t_off:t_off + t_sz]
    pat_1a0068 = struct.pack("<I", 0x1A0068)
    p = 0
    while True:
        i = tbuf.find(pat_1a0068, p)
        if i < 0: break
        rva_hit = t_rva + i
        win_rva = max(t_rva, rva_hit - 0x1C0)
        ins_w = disasm_bytes(md, pe, win_rva, 0x1C0)
        offs = []
        for ins in ins_w:
            m = re.search(r"dword ptr \[e[a-z]{2} \+ (0x[12][0-9a-f]{2})\]", ins.op_str)
            if m:
                v = int(m.group(1), 16)
                if 0x1F0 <= v <= 0x240 and v not in offs:
                    offs.append(v)
        found_tgt = None
        for v in offs:
            if (v + 4) in offs and (v + 8) in offs and (v + 0x10) in offs:
                found_tgt = v
                break
        if found_tgt is not None:
            info["off_m_targetMode"] = found_tgt
            # 找紧随其后被多次调用(>=3次)的 IsCurrentMode(mode)
            call_cnt = {}
            for ins in ins_w:
                if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
                    tr = int(ins.op_str, 16) - img
                    call_cnt[tr] = call_cnt.get(tr, 0) + 1
            for tr, cnt in call_cnt.items():
                if cnt >= 3 and 0x1000 <= tr < sz_img:
                    ins_icm = disasm_fn(md, pe, tr, 0x25)
                    for x in ins_icm:
                        mm = re.search(r"\[e[a-z]{2} \+ (0x1[0-9a-f]{2})\]", x.op_str)
                        if mm:
                            info["IsCurrentMode"] = tr
                            info["off_m_currentMode"] = int(mm.group(1), 16)
                            break
                    if "off_m_currentMode" in info:
                        break
            break
        p = i + 1

    # CCameraWar3::HasTargetController: 在全 .text 中找短函数以 `mov ecx, [ecx + tu]` (8B 49 tu) 开头且 0x30 字节内含 0x2B61676C
    if "off_cam_targetUnit" in info:
        tu = info["off_cam_targetUnit"]
        head = bytes([0x8B, 0x49, tu])  # mov ecx, [ecx + tu]
        tag_pat = struct.pack("<I", 0x2B61676C)
        p = 0
        while True:
            i = tbuf.find(head, p)
            if i < 0: break
            if i > 0 and tbuf[i - 1] in (0xCC, 0x90, 0xC3):
                if tag_pat in tbuf[i:i + 0x38]:
                    info["HasTargetController"] = t_rva + i
                    break
            p = i + 1

    # HasTargetController xrefs -> SetMode & PopMode
    if "HasTargetController" in info:
        htc = info["HasTargetController"]
        xrefs = []
        for idx in range(0, t_sz - 5):
            if tbuf[idx] == 0xE8:
                rel = struct.unpack_from("<i", tbuf, idx + 1)[0]
                if (t_rva + idx + 5 + rel) == htc:
                    xrefs.append(t_rva + idx)
        info["HasTgtCtrl_xrefs"] = len(xrefs)
        for xr in xrefs:
            ins_x = disasm_bytes(md, pe, xr, 0x40)
            saw_push1 = False
            for ins in ins_x:
                if ins.mnemonic == "push" and ins.op_str == "1":
                    saw_push1 = True
                elif saw_push1 and ins.mnemonic == "call" and ins.op_str.startswith("0x"):
                    sm = int(ins.op_str, 16) - img
                    if 0x1000 <= sm < sz_img:
                        ins_sm = disasm_bytes(md, pe, sm, 0x80)
                        cm_hex = f"0x{info.get('off_m_currentMode', 0x1B4):x}"
                        if any(cm_hex in x.op_str for x in ins_sm):
                            info["SetMode"] = sm
                            break
            if "SetMode" in info:
                break

    if "SetMode" in info and "off_m_currentMode" in info:
        sm = info["SetMode"]
        stk_hex = f"0x{info['off_m_currentMode'] + 8:x}"
        for idx in range(0, t_sz - 5):
            if tbuf[idx] == 0xE8:
                rel = struct.unpack_from("<i", tbuf, idx + 1)[0]
                if (t_rva + idx + 5 + rel) == sm:
                    xr = t_rva + idx
                    o_xr = pe.get_offset_from_rva(xr)
                    fs = None
                    for back in range(6, 0x28):
                        if data[o_xr - back - 1] in (0xCC, 0x90, 0xC3) and data[o_xr - back] not in (0xCC, 0x90):
                            fs = xr - back
                            break
                    if fs:
                        ins_p = disasm_bytes(md, pe, fs, 0x40)
                        if any(x.mnemonic == "push" and x.op_str == "0" for x in ins_p[:8]) and any(stk_hex in x.op_str for x in ins_p):
                            info["PopMode"] = fs
                            break

    return info

def main():
    vers = sorted(KNOWN_NATIVES.keys())
    out = []
    out.append("=" * 165)
    out.append("War3 全 11 个版本 game.dll 镜头锁定与选目标状态核心 RVA / 偏移对照表 (v3 全量反汇编核验)")
    out.append("=" * 165)
    hdr = (
        f"{'版本':<13} | {'g_pGameUI':>9} | {'GetCGameUI':>10} | {'m_cam':>5} | {'SetTgtCtrl':>10} | {'tgtU':>4} | "
        f"{'SetPos':>8} | {'m_wf':>5} | {'dirty':>5} | {'ResetCam':>8} | {'HasTgtCtrl':>10} | {'xref':>4} | "
        f"{'SetMode':>8} | {'PopMode':>8} | {'curM':>5} | {'tgtM':>5}"
    )
    out.append(hdr)
    out.append("-" * 165)

    def fx(d, k, w=8):
        v = d.get(k)
        return f"0x{v:X}".rjust(w) if v is not None else "未确认".rjust(w)

    for v in vers:
        dll = find_dll(os.path.join(VER_ROOT, v))
        if not dll:
            out.append(f"{v:<13} | (缺少 game.dll)")
            continue
        info = analyze_version(v, dll)
        out.append(
            f"{v:<13} | {fx(info,'g_pGameUI',9)} | {fx(info,'GetCGameUI',10)} | {fx(info,'off_m_camera',5)} | "
            f"{fx(info,'SetTargetController',10)} | {fx(info,'off_cam_targetUnit',4)} | "
            f"{fx(info,'SetPosition',8)} | {fx(info,'off_m_worldFrame',5)} | {fx(info,'off_wf_camDirty',5)} | "
            f"{fx(info,'ResetCamera',8)} | {fx(info,'HasTargetController',10)} | {str(info.get('HasTgtCtrl_xrefs','-')):>4} | "
            f"{fx(info,'SetMode',8)} | {fx(info,'PopMode',8)} | {fx(info,'off_m_currentMode',5)} | {fx(info,'off_m_targetMode',5)}"
        )

    text = "\n".join(out)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)

if __name__ == "__main__":
    main()
