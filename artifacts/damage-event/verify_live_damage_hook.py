# -*- coding: utf-8 -*-
"""
实机验证辅助脚本（留给 Claude 在测试机上运行）：
比对 records/lasthit/sf/*.csv 中方案 B（hookDispatchUnitDamaged 写入的 dmg 行）
与方案 A（trace 行的血量净降），校验伤害归属与数值精度。

用法：
  python verify_live_damage_hook.py <lasthit_csv_path>
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("用法: python verify_live_damage_hook.py <csv_path>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"文件不存在: {path}")
        sys.exit(1)

    dmg_by_src = defaultdict(float)
    dmg_cnt_by_src = defaultdict(int)
    dealt_hero = 0.0
    dealt_cnt = 0

    hp_drops_self = 0.0
    prev_hp = None
    first_t = last_t = None

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for row in csv.reader(f):
            if not row:
                continue
            tag = row[0].strip()
            # 方案 B 伤害事件行：dmg,<t>,<srcType>,<srcHandle>,<target>,<damage>
            if tag == "dmg" and len(row) >= 6:
                try:
                    t = float(row[1])
                    src_type = row[2].strip()
                    tgt = row[4].strip()
                    val = float(row[5])
                except ValueError:
                    continue
                if tgt == "self":
                    dmg_by_src[src_type] += val
                    dmg_cnt_by_src[src_type] += 1
                elif tgt == "enemyhero":
                    dealt_hero += val
                    dealt_cnt += 1
            # 方案 A trace 行（兼容现有 trace 格式，首列 trace，含 t 与英雄 hp）
            elif tag == "trace" and len(row) >= 5:
                try:
                    t = float(row[1])
                    # 尝试从键值对或固定列读取英雄血量
                    hp = None
                    for cell in row[2:]:
                        if cell.startswith("hp="):
                            hp = float(cell[3:])
                            break
                    if hp is None:
                        hp = float(row[2])
                except ValueError:
                    continue
                if first_t is None:
                    first_t = t
                last_t = t
                if prev_hp is not None and hp < prev_hp - 0.5:
                    hp_drops_self += (prev_hp - hp)
                prev_hp = hp

    total_taken_b = sum(dmg_by_src.values())
    print(f"=== 实机伤害挂钩核验报告: {path.name} ===")
    if first_t is not None and last_t is not None:
        print(f"对局 trace 时长: {last_t - first_t:.1f}s")
    print(f"方案 B 己方累计受伤: {total_taken_b:.1f} HP (共 {sum(dmg_cnt_by_src.values())} 次事件)")
    for k in ("tower", "creep", "hero", "other"):
        if dmg_cnt_by_src[k]:
            avg = dmg_by_src[k] / dmg_cnt_by_src[k]
            print(f"  - 来源 {k:6s}: {dmg_by_src[k]:7.1f} HP ({dmg_cnt_by_src[k]:3d} 次, 均伤 {avg:5.1f})")
    print(f"方案 B 对敌方英雄伤害: {dealt_hero:.1f} HP ({dealt_cnt} 次)")
    print(f"方案 A trace 累计血量下降(含回血抵消): {hp_drops_self:.1f} HP")
    if total_taken_b > 0:
        print(f"方案 B / 方案 A 比值: {total_taken_b / max(1.0, hp_drops_self):.2f}x（因方案 A 被自然回血/喝瓶抵消，通常 B >= A）")


if __name__ == "__main__":
    main()
