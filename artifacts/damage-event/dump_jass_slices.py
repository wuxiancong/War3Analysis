# -*- coding: utf-8 -*-
"""精确提取 Scripts_war3map.j 中的经验分配、反补经验、神符拾取与计分板片段（处理 \\r 换行）"""
from pathlib import Path

lines = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Scripts_war3map.j").read_text(
    encoding="utf-8", errors="replace"
).splitlines()

slices = [
    ("1. 小兵基础经验与死亡分配 (L13560-13700)", 13560, 13700),
    ("2. 反补经验 BWO/BXO (L13995-14060)", 13995, 14060),
    ("3. 神符拾取与装瓶 (L17115-17260)", 17115, 17260),
    ("4. 计分板 SY0 / SG0 (L26085-26155)", 26085, 26155),
]

out = []
for title, s, e in slices:
    out.append(f"\n================ {title} ================")
    for i in range(s - 1, min(e, len(lines))):
        out.append(f"{i+1:6d}: {lines[i]}")

# 同时查找主计分板 SG0 的创建/更新处（确认主计分板是否显示英雄等级）
out.append("\n================ 5. 主计分板 SG0 关键词搜索 ================")
sg_hits = [i + 1 for i, l in enumerate(lines) if "SG0" in l and ("Multiboard" in l or "GetHeroLevel" in l or "N5I(" in l)]
out.append(f"SG0 Multiboard/N5I lines (first 25): {sg_hits[:25]}")
for ln in sg_hits[:10]:
    out.append(f"  {ln:6d}: {lines[ln-1]}")

# 查找 RUI / SQI 函数定义（小兵经验表！）
out.append("\n================ 6. 小兵经验查询函数 RUI / SQI 定义 ================")
for fname in ("function RUI ", "function SQI ", "function D01 "):
    for i, l in enumerate(lines):
        if l.startswith(fname):
            out.append(f"--- {fname} @ L{i+1} ---")
            for k in range(i, min(len(lines), i + 40)):
                out.append(f"{k+1:6d}: {lines[k]}")
                if lines[k].strip() == "endfunction":
                    break

p = Path(r"D:\Qt\workspace\War3Analysis\artifacts\damage-event\dota683d_slices.txt")
p.write_text("\n".join(out), encoding="utf-8")
print(f"Wrote {len(out)} lines to {p}")
