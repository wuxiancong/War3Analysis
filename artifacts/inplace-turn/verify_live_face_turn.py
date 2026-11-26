# -*- coding: utf-8 -*-
"""
实机验证脚本（留给 Claude 在测试机上运行，解析 AiUnit.log 中的 🧭 [Face] 行）：
核对 -face 原地转向实测误差与位移是否达到「误差 <= 10°, 位移 <= 10 码」。

用法：
  python verify_live_face_turn.py C:\War3Run\War3Launcher\logs\AiUnit.log
"""
import re
import sys
from pathlib import Path

PAT = re.compile(
    r"\[Face\]\s*英雄面朝\s*([0-9.]+)°.*?目标\s*([0-9.]+)°\s*\|\s*移动了\s*([0-9.]+).*?第\s*(\d+)\s*次"
)


def ang_diff(a: float, b: float) -> float:
    return abs((a - b + 540.0) % 360.0 - 180.0)


def main():
    if len(sys.argv) < 2:
        print("用法: python verify_live_face_turn.py <AiUnit.log>")
        sys.exit(1)

    p = Path(sys.argv[1])
    if not p.exists():
        print(f"文件不存在: {p}")
        sys.exit(1)

    rows = []
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = PAT.search(ln)
        if m:
            got, tgt, moved, tries = float(m.group(1)), float(m.group(2)), float(m.group(3)), int(m.group(4))
            rows.append((got, tgt, ang_diff(got, tgt), moved, tries))

    if not rows:
        print("未在日志中找到 [Face] 实测记录")
        return

    ok_ang = sum(1 for r in rows if r[2] <= 10.0)
    ok_mov = sum(1 for r in rows if r[3] <= 10.0)
    ok_both = sum(1 for r in rows if r[2] <= 10.0 and r[3] <= 10.0)

    print(f"=== [Face] 原地转向实测汇总 (共 {len(rows)} 次) ===")
    print(f"朝向误差 <= 10°: {ok_ang}/{len(rows)} | 位移 <= 10 码: {ok_mov}/{len(rows)} | 双达标: {ok_both}/{len(rows)}")
    print(f"平均朝向误差: {sum(r[2] for r in rows)/len(rows):.1f}° | 平均位移: {sum(r[3] for r in rows)/len(rows):.1f} 码")
    print("--- 最近 15 条明细 ---")
    for got, tgt, err, mv, tr in rows[-15:]:
        mark = "OK" if (err <= 10.0 and mv <= 10.0) else "WARN"
        print(f"  [{mark:4s}] 目标={tgt:5.1f}° 实际={got:5.1f}° 误差={err:4.1f}° | 位移={mv:5.1f} 码 (第{tr}次)")


if __name__ == "__main__":
    main()
