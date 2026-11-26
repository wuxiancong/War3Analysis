# -*- coding: utf-8 -*-
"""
1秒解析 DotA 6.83d：
1. V80 (支配头盔 I08T) 在 Scripts_war3map.j 中的合成公式、组件 ID、商店单位与坐标
2. 解码 YFO 中的三个技能 1097167976 / 1094939243 / 1093818692 及 Y5O / QSI 函数体
3. 提取 6.83d 常见中立野怪（远程/近战大中小野）的 HP、移速、射程、技能与魔免标记
"""
import re
import struct
import sys
from pathlib import Path

MAP = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\helm-dominate\helm_683d_details.txt")

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\stealth-rune-route")
from parse_sight_and_doodads import parse_slk_clean


def i2fcc(n: int) -> str:
    return struct.pack(">I", n).decode("ascii", "replace")


def main():
    out = []
    j_lines = (MAP / "Scripts_war3map.j").read_text(encoding="utf-8", errors="replace").splitlines()

    # 1. 解码 YFO 的三个技能 + 查 Units_AbilityData.slk
    ab_ids = [1097167976, 1094939243, 1093818692]
    ab_fccs = [i2fcc(x) for x in ab_ids]
    out.append(f"=== 1. YFO 给被支配单位添加的 3 个技能: {list(zip(ab_ids, ab_fccs))} ===")
    acols, arows = parse_slk_clean(MAP / "Units_AbilityData.slk")
    for y, r in sorted(arows.items()):
        aid = r.get(1, "")
        if aid in ab_fccs:
            out.append(f"  {aid} (Y={y}): " + ", ".join(f"{acols.get(k, k)}={v}" for k, v in sorted(r.items())))

    # 2. 提取 Y5O 与 QSI 函数体
    for fn in ("function Y5O ", "function QSI "):
        for i, l in enumerate(j_lines):
            if l.startswith(fn):
                out.append(f"\n=== 2. {fn} @ L{i+1} ===")
                for k in range(i, min(len(j_lines), i + 40)):
                    out.append(f"  {k+1:6d}: {j_lines[k]}")
                    if j_lines[k].strip() == "endfunction":
                        break

    # 3. 搜索 V80 (I08T 配方索引) 在 Scripts_war3map.j 中的所有引用（合成公式！）
    v80_hits = [i + 1 for i, l in enumerate(j_lines) if re.search(r"\bV80\b", l)]
    out.append(f"\n=== 3. war3map.j 中 V80 (I08T) 引用: {v80_hits} ===")
    for ln in v80_hits[:10]:
        out.append(f"--- L{ln} ---")
        for k in range(max(0, ln - 3), min(len(j_lines), ln + 6)):
            out.append(f"  {k+1:6d}: {j_lines[k]}")

    # 4. 查找组件物品 I03B (铁意头盔) 与 I03G (死亡面具) 在 Units_ItemData.slk 中的价格，以及商店售卖关系
    # 先在 war3map.j 搜 I03B(1227895618) / I04E(1227895877) / I03G(1227895623) / I04K(1227895883)
    for name, num in [("I03B(铁意)", "1227895618"), ("I04E(铁意2)", "1227895877"), ("I03G(死面)", "1227895623"), ("I04K(死面2)", "1227895883")]:
        hs = [i + 1 for i, l in enumerate(j_lines) if num in l]
        out.append(f"\n=== 4. {name} ({num}) hits={hs[:6]} ===")
        for ln in hs[:2]:
            for k in range(max(0, ln - 2), min(len(j_lines), ln + 8)):
                out.append(f"  {k+1:6d}: {j_lines[k]}")

    # 5. 从 Units_UnitBalance.slk + Units_UnitWeapons.slk 提取常见可支配野怪属性
    bcols, brows = parse_slk_clean(MAP / "Units_UnitBalance.slk")
    bc2i = {v: k for k, v in bcols.items()}
    wcols, wrows = parse_slk_clean(MAP / "Units_UnitWeapons.slk")
    wc2i = {v: k for k, v in wcols.items()}
    w_by_id = {r.get(1, ""): r for r in wrows.values()}

    # 常见 DotA 6.83d 中立野怪 FourCC
    neutrals = [
        ("ndtw", "黑暗巨魔召唤法师 (Dark Troll Summoner)"),
        ("ndtr", "黑暗巨魔 (Dark Troll)"),
        ("nsth", "萨特苦难使者 (Satyr Tormenter)"),
        ("nstl", "萨特窃魂者 (Satyr Mindstealer)"),
        ("nsty", "萨特放逐者 (Satyr Banisher)"),
        ("ncen", "半人马征服者 (Centaur Conqueror)"),
        ("nowk", "枭兽撕裂者 (Wildwing Ripper)"),
        ("nwlg", "头狼 (Alpha Wolf)"),
        ("nplg", "熊怪粉碎者 (Hellbear Smasher)"),
        ("nhrr", "鹰身女妖风暴巫师 (Harpy Stormcrafter)"),
        ("nfsh", "丘陵巨魔牧师 (Hill Troll Priest)"),
        ("ngst", "鬼魂 (Ghost)"),
        ("nkol", "狗头人监工 (Kobold Foreman)"),
        ("ngrk", "泥土傀儡 (Mud Golem - 魔免)"),
    ]
    b_by_id = {r.get(1, ""): r for r in brows.values()}
    out.append("\n=== 5. DotA 6.83d 常见中立野怪属性 (HP / 移速 / 射程 / 护甲) ===")
    for uid, desc in neutrals:
        br = b_by_id.get(uid, {})
        wr = w_by_id.get(uid, {})
        hp = br.get(bc2i.get("HP", 0), "?")
        spd = br.get(bc2i.get("spd", 0), "?")
        df = br.get(bc2i.get("def", 0), "?")
        rng = wr.get(wc2i.get("rangeN1", 0), "?")
        wtp = wr.get(wc2i.get("weapTp1", 0), "?")
        out.append(f"  {uid:6s} | {desc:36s} | HP={hp:>5s} | spd={spd:>4s} | def={df:>3s} | rng={rng:>4s} ({wtp})")

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {OUT}")


if __name__ == "__main__":
    main()
