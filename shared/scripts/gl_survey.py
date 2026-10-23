"""各版本 game.dll 的 OpenGL 相关导入/字符串普查。用法: python gl_survey.py <game.dll>"""
import sys, re, pefile

path = sys.argv[1]
pe = pefile.PE(path)
base = pe.OPTIONAL_HEADER.ImageBase
print("== %s imagebase=%X" % (path, base))
for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
    dll = e.dll.decode().lower()
    if dll in ("opengl32.dll", "glu32.dll") or dll.startswith("gdi32"):
        names = []
        for i in e.imports:
            n = i.name.decode() if i.name else "ord%s" % i.ordinal
            if dll.startswith("gdi32") and not re.search(r"Swap|PixelFormat|Display|Context", n):
                continue
            names.append("%s@IAT=%X" % (n, i.address - base))
        print(dll, len(names), names[:80])
data = open(path, "rb").read()
for pat in (rb"opengl32\.dll", rb"wgl[A-Z]\w+", rb"gl[A-Z]\w{3,}", rb"GL_\w+", rb"CGxDevice\w*", rb"GxDev\w*", rb"CGxFormat\w*"):
    seen = sorted(set(m.group(0) for m in re.finditer(pat, data)))
    print(pat, len(seen), [s.decode("latin1") for s in seen[:40]])
