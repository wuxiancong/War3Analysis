import json
from pathlib import Path
b=json.loads(Path(r"D:\Qt\workspace\War3Angular\public\assets\maps\dota683\buildings.json").read_text(encoding="utf-8"))
keys=("r_t1_top","r_t1_mid","r_t1_bot","d_t1_top","d_t1_mid","d_t1_bot",
      "r_rax_melee_top","r_rax_range_top","r_rax_melee_mid","r_rax_range_mid","r_rax_melee_bot","r_rax_range_bot",
      "d_rax_melee_top","d_rax_range_top","d_rax_melee_mid","d_rax_range_mid","d_rax_melee_bot","d_rax_range_bot",
      "r_ancient","d_ancient","r_throne","d_throne")
by={x["id"]:x for x in b["buildings"]}
for k in keys:
    x=by.get(k)
    if x: print(f"{k:22} {x['x']:8} {x['y']:8}  {x['name']}")
    else: print(k, "MISSING")
# also search ancient
for x in b["buildings"]:
    if "ancient" in x["id"] or "throne" in x["id"] or "tree" in x["id"] or "fort" in x["id"]:
        print("extra", x["id"], x["x"], x["y"], x["name"])
