# -*- coding: utf-8 -*-
"""解析 DotA 6.83d 地图解包目录 (artifacts/ward-deward/map) 的真实武器、弹道速度/弧度、发射点、护甲与 war3mapMisc.txt。"""
import os, re

MAP_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map"
BASE_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\scoring\base\War3Patch.mpq"


def parse_slk(path):
    if not os.path.exists(path):
        return {}
    rows, hdr, cur_y = {}, {}, 0
    for line in open(path, encoding="utf-8", errors="replace"):
        if not line.startswith("C;"):
            continue
        my = re.search(r"Y(\d+)", line)
        if my:
            cur_y = int(my.group(1))
        mx = re.search(r"X(\d+)", line)
        mk = re.search(r";K(.*)", line)
        if not mx or not mk:
            continue
        x, val = int(mx.group(1)), mk.group(1).strip().strip('"')
        if cur_y == 1:
            hdr[x] = val
        else:
            rows.setdefault(cur_y, {})[x] = val
    return {cols[1]: {hdr.get(k, str(k)): v for k, v in cols.items()} for cols in rows.values() if 1 in cols}


def parse_funcs(folder):
    funcs = {}
    if not os.path.isdir(folder):
        return funcs
    for fn in os.listdir(folder):
        if fn.endswith("UnitFunc.txt"):
            cur = None
            for line in open(os.path.join(folder, fn), encoding="utf-8", errors="replace"):
                s = line.strip()
                if s.startswith("[") and s.endswith("]"):
                    cur = s[1:-1]
                    funcs.setdefault(cur, {})
                elif cur and "=" in s:
                    k, _, v = s.partition("=")
                    funcs[cur][k.strip()] = v.strip()
    return funcs


def main():
    wpn = parse_slk(os.path.join(MAP_DIR, "Units_UnitWeapons.slk"))
    bal = parse_slk(os.path.join(MAP_DIR, "Units_UnitBalance.slk"))
    pwpn = parse_slk(os.path.join(BASE_DIR, "Units_UnitWeapons.slk"))
    funcs = parse_funcs(MAP_DIR)
    pfuncs = parse_funcs(BASE_DIR)

    print("=== DotA 6.83d 地图真实 SLK + UnitFunc ===")
    units = ["Nfir", "esen", "edry", "ebal", "ugho", "unec", "umtw", "e00R", "u00M", "e011", "u00D"]
    for u in units:
        w = wpn.get(u) or pwpn.get(u) or {}
        b = bal.get(u) or {}
        f = funcs.get(u) or pfuncs.get(u) or {}
        print(
            f"{u:5s} | atk={w.get('atkType1')} dmg={w.get('dmgplus1')}+{w.get('dice1')}d{w.get('sides1')} "
            f"cool={w.get('cool1')} dmgpt={w.get('dmgpt1')} back={w.get('backSw1')} rng={w.get('rangeN1')} "
            f"| spd={f.get('Missilespeed')} arc={f.get('Missilearc')} "
            f"launch=({w.get('launchX')},{w.get('launchY')},{w.get('launchZ')}) impZ={w.get('impactZ')} "
            f"| def={b.get('def')} defType={b.get('defType')} col={b.get('collision')}"
        )

    print("\n=== DotA 6.83d war3mapMisc.txt DamageBonus / DefenseArmor / AttackSpeed ===")
    for line in open(os.path.join(MAP_DIR, "war3mapMisc.txt"), encoding="utf-8", errors="replace"):
        if any(k in line for k in ["DamageBonus", "DefenseArmor", "AttackSpeed", "Miss"]):
            print(" ", line.strip())


if __name__ == "__main__":
    main()
