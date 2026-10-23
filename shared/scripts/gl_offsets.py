"""OpenGL 绘制相关偏移普查：IAT、调用点、所属函数、CGxDeviceOpenGL 相关字符串引用。
用法: python gl_offsets.py <game.dll> [json输出路径]
"""
import sys, re, json, struct, pefile, capstone

path = sys.argv[1]
pe = pefile.PE(path)
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
secs = [(s.Name.rstrip(b"\0").decode(), s.VirtualAddress, s.Misc_VirtualSize, s.Characteristics, s.get_data()) for s in pe.sections]
text = [s for s in secs if s[3] & 0x20000000]

WANT = ["wglSwapLayerBuffers", "wglMakeCurrent", "wglCreateContext", "wglDeleteContext", "wglGetProcAddress",
        "glDrawElements", "glClear", "glClearColor", "glViewport", "glScissor", "glFinish", "glDrawBuffer",
        "glMatrixMode", "glLoadMatrixf", "glBindTexture", "glEnable", "glDisable", "glBlendFunc", "glDepthMask",
        "glDepthFunc", "glVertexPointer", "glColorPointer", "glTexCoordPointer", "glEnableClientState",
        "glDisableClientState", "glReadPixels", "glTexImage2D", "glTexSubImage2D", "glGetString", "glGetIntegerv"]
iat = {}
for e in pe.DIRECTORY_ENTRY_IMPORT:
    if e.dll.decode().lower() in ("opengl32.dll", "gdi32.dll"):
        for i in e.imports:
            if i.name:
                iat[i.name.decode()] = i.address - base

def rva_to_off(rva):
    for n, va, sz, ch, d in secs:
        if va <= rva < va + max(sz, len(d)):
            return n, rva - va
    return None, None

def find_all(data, pat):
    i = -1
    while True:
        i = data.find(pat, i + 1)
        if i < 0:
            return
        yield i

def func_start(rva):
    """向上回溯寻找函数起始：以 CC 填充之后的第一个非 CC 字节为准（MSVC 函数对齐填充）。"""
    for n, va, sz, ch, d in text:
        if va <= rva < va + len(d):
            o = rva - va
            for k in range(o, max(1, o - 0x2000), -1):
                if d[k - 1] == 0xCC and d[k] != 0xCC:
                    return va + k
            return None
    return None

def read_text(rva, n):
    for nm, va, sz, ch, d in secs:
        if va <= rva < va + len(d):
            return d[rva - va: rva - va + n]
    return b""

def vtables_with(rva):
    """返回包含该函数指针的所有虚表 (表起点RVA, 槽位, 表项RVA列表)。"""
    pat = struct.pack("<I", base + rva)
    ok = lambda v: any(a <= v - base < b for a, b in [(s[1], s[1] + len(s[4])) for s in text])
    out = []
    for nm, va, sz, ch, d in secs:
        if ch & 0x20000000:
            continue
        for i in find_all(d, pat):
            if i % 4:
                continue
            lo = i
            while lo >= 4 and ok(struct.unpack_from("<I", d, lo - 4)[0]):
                lo -= 4
            hi = i
            while hi + 8 <= len(d) and ok(struct.unpack_from("<I", d, hi + 4)[0]):
                hi += 4
            ents = [struct.unpack_from("<I", d, k)[0] - base for k in range(lo, hi + 4, 4)]
            out.append({"vtable": hex(va + lo), "slot": (i - lo) // 4, "count": len(ents), "entries": [hex(e) for e in ents]})
    return out

res = {"imagebase": hex(base), "iat": {k: hex(v) for k, v in iat.items() if k in WANT}, "callsites": {}, "strings": {}}

# 调用点：FF 15 <IAT VA> (call [iat]) 以及 FF 25 (jmp [iat] thunk)
for name in WANT:
    if name not in iat:
        continue
    va = base + iat[name]
    out = []
    for pre in (b"\xFF\x15", b"\xFF\x25"):
        pat = pre + struct.pack("<I", va)
        for n, sva, sz, ch, d in text:
            for i in find_all(d, pat):
                out.append({"site": hex(sva + i), "func": hex(func_start(sva + i) or 0), "kind": "call" if pre[1] == 0x15 else "thunk"})
    res["callsites"][name] = out

# 字符串引用
data_all = open(path, "rb").read()
STR = [b"CGxDeviceOpenGL", b"CGxDeviceOpenGl", b"GxDeviceOpenGL", b"GxDeviceOpenGl", b"CGxDeviceD3d", b"GL_ARB_multitexture",
       b"GL_EXT_bgra", b"GL_EXT_compiled_vertex_array", b"GL_EXT_texture_edge_clamp", b"glActiveTextureARB", b"glLockArraysEXT"]
for s in STR:
    for n, sva, sz, ch, d in secs:
        for i in find_all(d, s + b"\0"):
            strva = base + sva + i
            refs = []
            for tn, tva, tsz, tch, td in secs:
                for j in find_all(td, struct.pack("<I", strva)):
                    refs.append("%s:%X" % (tn, tva + j))
            res["strings"].setdefault(s.decode(), []).append({"va": hex(strva), "rva": hex(sva + i), "refs": refs[:12]})

txt_pre = None
# 以调用 wglSwapLayerBuffers 的非 thunk 点所在函数作为 ScenePresent，并反查虚表
sw = [c for c in res["callsites"].get("wglSwapLayerBuffers", []) if c["kind"] == "call"]
if sw:
    site = int(sw[0]["site"], 16)
    # 虚表项集合：取不超过调用点的最大虚表函数地址作为 ScenePresent（对无 CC 填充的旧版本同样有效）
    cand = set()
    for nm, va, sz, ch, d in secs:
        if ch & 0x20000000:
            continue
        for k in range(0, len(d) - 3, 4):
            v = struct.unpack_from("<I", d, k)[0] - base
            if site - 0x600 <= v <= site:
                cand.add(v)
    pf = max(cand) if cand else int(sw[0]["func"], 16)
    res["present"] = {"func": hex(pf), "prologue": read_text(pf, 12).hex(" ").upper(), "vtables": vtables_with(pf)}
    vt = res["present"]["vtables"]
    if vt:
        e = vt[0]["entries"]
        res["glvtable"] = {"base": vt[0]["vtable"], "count": vt[0]["count"], "presentSlot": vt[0]["slot"],
                           "slot16_clear": e[16] if len(e) > 16 else None,
                           "drawSlots": {str(i): e[i] for i in range(26, min(33, len(e)))}}

txt = json.dumps(res, indent=1, ensure_ascii=False)
if len(sys.argv) > 2:
    open(sys.argv[2], "w", encoding="utf-8").write(txt)
else:
    print(txt)
