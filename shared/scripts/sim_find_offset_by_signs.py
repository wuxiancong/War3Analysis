#!/usr/bin/env python3
"""离线复现 war3hook.cpp 的 findOffsetBySigns（正向）：校验特征码链在各版本 game.dll 中是否唯一、命中位置是否正确。

规则与 hook 一致：
  - 第一段在整个模块中逐字节匹配；后续每段在上一段末尾之后 maxSearchRange(默认 128) 字节内查找；
  - 正向搜索返回 "最后一段的起始位置"；第一处完整命中即返回（hook 中按地址从小到大）。
  - "??" 为通配。

用法:
  python -I sim_find_offset_by_signs.py "E8 01 00 00" "8B CE 74 0E" "E8 ?? ?? ?? ?? B8 01 00 00 00" -- <game.dll> [...]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I 下也能导入同目录模块
from find_imm_xrefs import read_pe, file_to_va  # noqa: E402


def parse(p):
    out = []
    for t in p.split():
        out.append((0, True) if t == "??" else (int(t, 16), False))
    return out


def match_at(d, pos, pat):
    if pos + len(pat) > len(d):
        return False
    for i, (b, wild) in enumerate(pat):
        if not wild and d[pos + i] != b:
            return False
    return True


def find_all(d, pats, max_range=128):
    first = pats[0]
    hits = []
    fb = next((b for b, w in first if not w), None)
    start = 0
    while True:
        # 用第一段首个非通配字节加速
        idx = d.find(bytes([fb]), start) if fb is not None else start
        if idx == -1:
            break
        off0 = idx - next(i for i, (b, w) in enumerate(first) if not w) if fb is not None else idx
        start = idx + 1
        if off0 < 0 or not match_at(d, off0, first):
            continue
        prev_end = off0 + len(first)
        target = off0
        ok = True
        for pat in pats[1:]:
            found = None
            for p in range(prev_end, min(prev_end + max_range, len(d) - len(pat)) + 1):
                if match_at(d, p, pat):
                    found = p
                    break
            if found is None:
                ok = False
                break
            prev_end = found + len(pat)
            target = found
        if ok:
            hits.append(target)
    return hits


def main():
    argv = sys.argv[1:]
    sep = argv.index("--")
    pats = [parse(p) for p in argv[:sep]]
    for path in argv[sep + 1:]:
        d = open(path, "rb").read()
        base, secs = read_pe(d)
        hits = find_all(d, pats)
        vas = [file_to_va(h, base, secs)[0] for h in hits]
        print(f"{path}: {len(hits)} hit(s) " + " ".join(f"RVA {va - base:#x}" for va in vas if va))


if __name__ == "__main__":
    main()
