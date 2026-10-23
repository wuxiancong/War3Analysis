"""打印每个版本 wglSwapLayerBuffers / wglMakeCurrent 调用点前的指令，用于确定 HDC/HGLRC 成员偏移。"""
import sys, json, glob, pefile, capstone, os
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for p in sorted(glob.glob(r"D:\Qt\workspace\War3Analysis\artifacts\opengl-draw\*-offsets.json")):
    ver = os.path.basename(p)[:-13]
    r = json.load(open(p, encoding="utf-8"))
    dll = [f for f in glob.glob(r"D:\Qt\workspace\War3Launcher\versions\%s\*" % ver) if f.lower().endswith("game.dll")][0]
    pe = pefile.PE(dll)
    print("==", ver)
    for api in ("wglSwapLayerBuffers", "wglMakeCurrent", "wglCreateContext"):
        for c in r["callsites"][api]:
            if c["kind"] != "call":
                continue
            site = int(c["site"], 16)
            data = pe.get_data(site - 40, 48)
            ins = list(md.disasm(data, site - 40))
            tail = [i for i in ins if i.address <= site][-5:]
            print("  %s @%X:  " % (api, site) + " ; ".join("%s %s" % (i.mnemonic, i.op_str) for i in tail))
