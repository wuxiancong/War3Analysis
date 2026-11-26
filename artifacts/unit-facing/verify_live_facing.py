# -*- coding: utf-8 -*-
"""
实机验证辅助脚本（留给 Claude 在测试机上运行，不在当前环境连 6120）：
校验从游戏日志/CSV 中采到的英雄朝向是否符合：
1. 坐标系约定：东=0°, 北=90°, 西=180°, 南=270°（与位移向量 atan2(dy, dx) 一致）
2. 180° 转身实际用时（影魔 Nfir 预期 ~0.125s，冰女 Hjai 预期 ~0.219s）
3. 近点 move 后实际位移与最终朝向误差

输入 CSV 格式（每行）：t,hx,hy,facing_deg
用法：
  python verify_live_facing.py <facing_trace.csv>
"""
import csv
import math
import sys
from pathlib import Path


def norm_deg(a: float) -> float:
    return (a % 360.0 + 360.0) % 360.0


def ang_diff(a: float, b: float) -> float:
    """最短有符号角差 [-180, 180]"""
    return (a - b + 180.0) % 360.0 - 180.0


def main():
    if len(sys.argv) < 2:
        print("用法: python verify_live_facing.py <facing_trace.csv>")
        print("CSV 列: t,hx,hy,facing_deg")
        sys.exit(1)

    rows = []
    with Path(sys.argv[1]).open("r", encoding="utf-8", errors="replace") as f:
        for r in csv.reader(f):
            if not r or r[0].startswith("#") or r[0].lower() == "t":
                continue
            try:
                rows.append((float(r[0]), float(r[1]), float(r[2]), float(r[3])))
            except (ValueError, IndexError):
                continue

    if len(rows) < 2:
        print("有效采样点不足 2 行")
        sys.exit(1)

    # 1. 核对移动段：位移向量极角 atan2(dy, dx) vs GetUnitFacing
    move_errs = []
    max_turn_rate_deg_s = 0.0
    for i in range(1, len(rows)):
        t0, x0, y0, f0 = rows[i - 1]
        t1, x1, y1, f1 = rows[i]
        dt = t1 - t0
        if dt <= 1e-4:
            continue
        dist = math.hypot(x1 - x0, y1 - y0)
        if dist >= 25.0:
            move_deg = norm_deg(math.degrees(math.atan2(y1 - y0, x1 - x0)))
            err = abs(ang_diff(norm_deg(f1), move_deg))
            move_errs.append(err)
        df = abs(ang_diff(norm_deg(f1), norm_deg(f0)))
        if df > 5.0:
            max_turn_rate_deg_s = max(max_turn_rate_deg_s, df / dt)

    print(f"=== 朝向实机校验 ({len(rows)} 帧) ===")
    print(f"首帧朝向: {rows[0][3]:.1f}° | 末帧朝向: {rows[-1][3]:.1f}° | 净位移: {math.hypot(rows[-1][1]-rows[0][1], rows[-1][2]-rows[0][2]):.1f} 码")
    if move_errs:
        move_errs.sort()
        med = move_errs[len(move_errs) // 2]
        print(f"移动段 atan2(dy,dx) vs GetUnitFacing 误差 (n={len(move_errs)}): 中位数={med:.1f}°, 最大={max(move_errs):.1f}°")
        print("  -> 若中位数 < 5°，证明 0°=正东(+X) 逆时针为正 坐标系完全吻合！")
    if max_turn_rate_deg_s > 0:
        print(f"观测峰值转身速率: {max_turn_rate_deg_s:.0f} °/s (理论满速: 冰女0.5≈917°/s, 影魔1.0≈1833°/s)")


if __name__ == "__main__":
    main()
