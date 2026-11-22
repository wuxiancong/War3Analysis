# -*- coding: utf-8 -*-
"""提取 War3Launcher RemoteControl 命令清单与 DotA 6.83d 地标坐标（buildings.json / 野点 / 眼位）。"""
import json
import os
import re

OUT_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp"
os.makedirs(OUT_DIR, exist_ok=True)


def extract_rc_commands():
    src = open(
        r"D:\Qt\workspace\War3Launcher\managers\AiControlManager.cpp",
        "r",
        encoding="utf-8",
        errors="replace",
    ).read()
    m = re.search(r"QString AiControlManager::handleRemoteCommand\b.*", src, re.S)
    body = m.group(0) if m else ""
    # 截到下一个类成员函数之前
    nxt = re.search(r"\n(?:void|bool|QString|int)\s+AiControlManager::", body[60:])
    if nxt:
        body = body[: 60 + nxt.start()]
    cmds = set()
    for a, b in re.findall(
        r'cmd\s*==\s*QLatin1String\("([^"]+)"\)|cmd\.startsWith\(QLatin1String\("([^"]+)"\)',
        body,
    ):
        c = (a or b).strip()
        if c:
            cmds.add(c)
    cmds = sorted(cmds)
    print(f"=== RemoteControl Commands ({len(cmds)}) ===")
    print(", ".join(cmds))
    return cmds


def extract_buildings():
    data = json.load(
        open(
            r"D:\Qt\workspace\War3Angular\public\assets\maps\dota683\buildings.json",
            "r",
            encoding="utf-8",
        )
    )
    print("\n=== Key Buildings (fountain / ancient / tower / rax_melee / shop) ===")
    for b in data["buildings"]:
        if b["kind"] in ("fountain", "ancient", "tower", "rax_melee", "rax_range"):
            print(f"  {b['id']:18s} | {b['name']:22s} | ({b['x']:6.0f}, {b['y']:6.0f}) | {b.get('unitId','')}")
    # Also check non-base shops (secret/side shops)
    for b in data["buildings"]:
        if b["kind"] == "shop" and (abs(b["x"]) < 5800 or abs(b["y"]) < 5800):
            print(f"  {b['id']:18s} | {b['name']:22s} | ({b['x']:6.0f}, {b['y']:6.0f}) | {b.get('unitId','')}")


def extract_camps_and_wards():
    print("\n=== Neutral Camps (dota-neutral-camp-spawn-box.md) ===")
    for line in open(
        r"D:\Qt\workspace\War3Analysis\analyses\dota-neutral-camp-spawn-box.md",
        "r",
        encoding="utf-8",
    ):
        if line.startswith("|") and any(c.isdigit() for c in line) and "---" not in line:
            print(" ", line.strip())

    print("\n=== Ward Spots (dota-683d-ward-and-deward.md) ===")
    in_ward = False
    for line in open(
        r"D:\Qt\workspace\War3Analysis\analyses\dota-683d-ward-and-deward.md",
        "r",
        encoding="utf-8",
    ):
        if "### 1.3" in line:
            in_ward = True
        elif line.startswith("## ") and in_ward:
            break
        if in_ward and line.startswith("|"):
            print(" ", line.strip())


if __name__ == "__main__":
    extract_rc_commands()
    extract_buildings()
    extract_camps_and_wards()
