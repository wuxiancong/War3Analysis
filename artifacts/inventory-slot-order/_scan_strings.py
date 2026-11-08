import mmap
import os
from pathlib import Path

candidates = [
    Path(r"C:\War3Analysis\samples\1.26.0.6401\game.dll"),
    Path(r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll"),
]
path = next(p for p in candidates if p.exists())
print("path", path, "size", path.stat().st_size)

needles = [
    b"moveslot",
    b"useslot",
    b"dropitem",
    b"getitem",
    b"UnitInventorySize",
    b"UnitItemInSlot",
    b"UnitAddItem",
    b"UnitAddItemToSlotById",
    b"UnitDropItemSlot",
    b"UnitRemoveItemFromSlot",
    b"Inventory",
    b"inventory",
]

with path.open("rb") as f:
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    for n in needles:
        hits = []
        start = 0
        while len(hits) < 8:
            i = mm.find(n, start)
            if i < 0:
                break
            ctx = mm[max(0, i - 20) : i + len(n) + 40]
            printable = bytes(b if 32 <= b < 127 else 0x2E for b in ctx).decode("ascii", "replace")
            hits.append(f"file+0x{i:X} | {printable}")
            start = i + 1
        print(f"\n== {n.decode()} ==")
        if hits:
            for h in hits:
                print(h)
        else:
            print("NONE")
    mm.close()
