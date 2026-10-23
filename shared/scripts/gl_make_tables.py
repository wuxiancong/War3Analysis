"""由 artifacts/opengl-draw/*-offsets.json 生成 Markdown 偏移表（stdout）。"""
import json, glob, os, re
rows = []
for p in sorted(glob.glob(r"D:\Qt\workspace\War3Analysis\artifacts\opengl-draw\*-offsets.json"), key=lambda x: [int(n) for n in re.findall(r"\d+", os.path.basename(x)[:-13])]):
    ver = os.path.basename(p)[:-13]
    r = json.load(open(p, encoding="utf-8"))
    g = r["glvtable"]; e = r["present"]["vtables"][0]["entries"]
    swapcall = [c["site"] for c in r["callsites"]["wglSwapLayerBuffers"] if c["kind"] == "call"][0]
    rows.append((ver, g["base"], e[17], e[16], swapcall, e[9], e[43], e[18], e[21], e[28], e[32], r["iat"],
                 r["present"]["prologue"].split(" ")[:6]))
H = lambda x: "`0x%06X`" % int(x, 16)
print("### 表 A：GL 设备虚表与关键槽位（RVA）\n")
print("| 版本 | GL 虚表 | [17] ScenePresent | [16] SceneClear | swap 调用点 | [9] 开窗+建上下文 | [43] GL 初始化 | [18] 视口/裁剪 | [21] 顶点数组 | [28] DrawElements | [32] DrawElements(多重纹理) |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print("| %s | %s | **%s** | %s | %s | %s | %s | %s | %s | %s | %s |" % ((r[0],) + tuple(H(x) for x in r[1:11])))
print("\n### 表 B：game.dll 中 opengl32 的 IAT 槽位（RVA，可直接 hook IAT）\n")
keys = ["wglSwapLayerBuffers", "wglMakeCurrent", "wglCreateContext", "wglDeleteContext", "wglGetProcAddress", "glDrawElements", "glClear", "glViewport", "glFinish", "glReadPixels"]
print("| 版本 | " + " | ".join(keys) + " |")
print("|---|" + "---|" * len(keys))
for r in rows:
    print("| %s | " % r[0] + " | ".join(H(r[11][k]) for k in keys) + " |")
print("\n### 表 C：ScenePresent 入口特征（前 6 字节，可用于 6 字节内联 Hook）\n")
print("| 版本 | RVA | 前 6 字节 |")
print("|---|---|---|")
for r in rows:
    print("| %s | %s | `%s` |" % (r[0], H(r[2]), " ".join(r[12])))
