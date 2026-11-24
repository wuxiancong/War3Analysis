# -*- coding: utf-8 -*-
"""探测 war3map.doo 结构、Units_UnitBalance.slk 视野值、以及绘图库可用性"""
import struct
from collections import Counter
from pathlib import Path
import sys

MAP = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")

# 1. 检查 Python 绘图库
for mod in ("PIL", "matplotlib", "numpy"):
    try:
        __import__(mod)
        print(f"lib {mod}: OK")
    except ImportError:
        print(f"lib {mod}: MISSING")

# 2. 解析 war3map.doo 头部与全部 doodad/tree
data = (MAP / "war3map.doo").read_bytes()
magic = data[:4]
ver, subver, count = struct.unpack_from("<III", data, 4)
print(f"war3map.doo: magic={magic}, ver={ver}, subver={subver}, count={count}, size={len(data)}")

o = 16
types = Counter()
parsed = 0
for idx in range(count):
    if o + 42 > len(data):
        print(f"EOF at idx={idx}, o={o}")
        break
    tid = data[o : o + 4].decode("ascii", "replace")
    var = struct.unpack_from("<I", data, o + 4)[0]
    x, y, z = struct.unpack_from("<fff", data, o + 8)
    ang = struct.unpack_from("<f", data, o + 20)[0]
    sx, sy, sz = struct.unpack_from("<fff", data, o + 24)
    flags, life = struct.unpack_from("<BB", data, o + 36)
    o += 38
    if ver >= 8:
        item_table_ptr = struct.unpack_from("<i", data, o)[0]
        item_sets = struct.unpack_from("<I", data, o + 4)[0]
        o += 8
        for _ in range(item_sets):
            n_items = struct.unpack_from("<I", data, o)[0]
            o += 4 + n_items * 8
    doodad_id = struct.unpack_from("<I", data, o)[0]
    o += 4
    types[tid] += 1
    parsed += 1

print(f"Parsed {parsed}/{count} doodads, final offset={o}/{len(data)}, top types={types.most_common(15)}")

# 3. 从 Units_UnitBalance.slk 读取小兵 / 塔 / 影魔 sight & nsight & spd
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward")
from parse_unit_slk import parse_slk

cols, rows = parse_slk(MAP / "Units_UnitBalance.slk")
col_idx = {v: k for k, v in cols.items()}
print("SLK cols:", {k: col_idx.get(k) for k in ("unitBalanceID", "sight", "nsight", "spd", "collision", "def", "defType")})
targets = ["efon", "edry", "ugho", "unec", "ebal", "umtw", "e00R", "u00M", "e011", "u00D", "Nfir"]
for y, r in rows.items():
    uid = str(r.get(1, "")).strip('"')
    if uid in targets:
        sight = r.get(col_idx["sight"], "?")
        nsight = r.get(col_idx["nsight"], "?")
        spd = r.get(col_idx["spd"], "?")
        coll = r.get(col_idx["collision"], "?")
        print(f"  {uid:6s} (Y={y:4d}): sight={sight}, nsight={nsight}, spd={spd}, collision={coll}")
