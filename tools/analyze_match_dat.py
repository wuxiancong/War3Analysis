#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
War3 Match DAT Analysis Tool
解析由 War3Bot 导出的玩家全场比赛动作归档文件 (*.dat)
支持解压 Qt qCompress (Zlib) 格式，提取战绩统计、APM、聊天记录及 2D/3D 移动轨迹。
"""

import sys
import os
import struct
import zlib
import json
import argparse
from datetime import datetime, timedelta

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# 魔兽争霸 3 常用 Action ID 映射表
ACTION_NAMES = {
    0x03: "UI操作 (Pause/Unpause)",
    0x06: "保存游戏 (SaveGame)",
    0x10: "无目标技能/单位指令 (NoTargetOrder/Stop/Hold)",
    0x11: "点地移动/目标坐标 (PointTargetOrder/Move)",
    0x12: "双坐标/移动攻击/右键 (TargetOrder/Attack/RightClick)",
    0x13: "给予物品 (GiveItem)",
    0x14: "移动至坐标 (MoveToPoint)",
    0x16: "选择单位/取消选择 (SelectGroup/SelectUnits)",
    0x17: "指定单位编队 (AssignGroupHotkey)",
    0x18: "选择编队 (SelectGroupHotkey)",
    0x19: "购买/建造队列 (QueueSubgroup)",
    0x1A: "ESC取消/按键 (EscPress/KeyOrder)",
    0x1B: "小地图信号 (MinimapPing)",
    0x1C: "继续建造/升级 (ContinueBuilding)",
    0x21: "点地技能 (PointTargetSpell)",
    0x22: "目标技能 (TargetSpell)",
    0x27: "保持连接心跳 (KeepAlive)",
    0x28: "大厅聊天/控制 (ChatToHost)",
    0x35: "物品栏移动/交换 (MoveInventoryItem)",
    0x37: "丢弃物品 (DropItem)",
    0x4A: "英雄学习技能 (HeroLearnSkill)",
    0x4B: "英雄购买/使用物品 (HeroUseItem)",
    0x4E: "单选建筑/商店 (SelectBuilding)",
    0x57: "丢弃/出售物品 (DropOrSellItem)",
    0x60: "游戏内聊天 (InGameChat)",
    0x61: "离开游戏 (LeaveGame)",
    0x63: "设置小地图位置 (SetCameraPosition)",
    0x66: "字符串同步 (SyncStoredString)",
    0x67: "整数同步 (SyncStoredReal)",
    0x6B: "DotA战绩同步 (SyncStoredInteger)",
}

def load_dat_file(dat_path):
    if not os.path.exists(dat_path):
        raise FileNotFoundError(f"文件不存在: {dat_path}")
    
    with open(dat_path, "rb") as f:
        data = f.read()
    
    if len(data) < 4:
        raise ValueError(f"文件大小异常 ({len(data)} 字节)，无法解析")
    
    # Qt qCompress 前4字节为解压后大小 (Big-Endian quint32)
    expected_len = struct.unpack(">I", data[:4])[0]
    uncompressed_bytes = zlib.decompress(data[4:])
    
    if len(uncompressed_bytes) != expected_len:
        print(f"[警告] 解压大小 ({len(uncompressed_bytes)}) 与预期 ({expected_len}) 不完全一致，但继续解析")
        
    return json.loads(uncompressed_bytes.decode("utf-8", errors="replace")), len(data), len(uncompressed_bytes)

def analyze_match(match_data):
    meta = {
        "matchId": match_data.get("matchId", "未知"),
        "player": match_data.get("player", "未知"),
        "clientId": match_data.get("clientId", "未知"),
        "pid": match_data.get("pid", 0),
        "heroId": match_data.get("heroId", "0"),
        "gameStartMs": match_data.get("gameStartMs", 0),
        "gameEndMs": match_data.get("gameEndMs", 0),
        "durationMs": match_data.get("durationMs", 0),
        "totalActions": match_data.get("totalActions", 0),
    }

    actions = match_data.get("actions", [])
    
    # 统计 Action 频率
    action_counts = {}
    chats = []
    sync_stats = {}
    trajectories = []
    
    # 玩家相关统计
    pid = meta["pid"]
    csk_key = f"CSK{pid}"
    csd_key = f"CSD{pid}"
    nk_key = f"NK{pid}"
    
    dota_stats = {
        "mode": None,
        "hero": None,
        "creep_kills": 0,
        "denies": 0,
        "neutral_kills": 0,
        "level_ups": [],
        "roshan_events": [],
    }

    for act in actions:
        # 格式: [timeOffsetMs, actionId, x, y, targetId, extra]
        t = act[0] if len(act) > 0 else 0
        aid = act[1] if len(act) > 1 else 0
        x = act[2] if len(act) > 2 else 0.0
        y = act[3] if len(act) > 3 else 0.0
        target = act[4] if len(act) > 4 else 0
        extra = act[5] if len(act) > 5 else ""

        action_counts[aid] = action_counts.get(aid, 0) + 1

        # 记录有效移动/施法轨迹 (魔兽地图有效范围通常在 -8000 ~ +8000)
        if x != 0.0 or y != 0.0:
            trajectories.append({
                "t": t,
                "aid": aid,
                "x": round(x, 2),
                "y": round(y, 2),
                "target": target
            })

        # 记录聊天
        if aid == 0x60 and extra:
            chats.append({"t": t, "text": extra})

        # 解析 0x6B DotA 战绩数据同步
        if aid == 0x6B and extra:
            if "=" in extra:
                k, v = extra.split("=", 1)
                sync_stats[k] = v
                clean_k = k.replace("Data:", "").strip()
                if "Mode" in clean_k:
                    dota_stats["mode"] = v
                elif clean_k == f"Hero{pid}":
                    dota_stats["hero"] = v
                elif clean_k == f"CSK{pid}":
                    try: dota_stats["creep_kills"] = int(v)
                    except ValueError: pass
                elif clean_k == f"CSD{pid}":
                    try: dota_stats["denies"] = int(v)
                    except ValueError: pass
                elif clean_k == f"NK{pid}":
                    try: dota_stats["neutral_kills"] = int(v)
                    except ValueError: pass
                elif "Level" in clean_k:
                    dota_stats["level_ups"].append({"t": t, "level": v})
                elif "Roshan" in clean_k or "Aegis" in clean_k:
                    dota_stats["roshan_events"].append({"t": t, "event": f"{k}={v}"})

    duration_min = meta["durationMs"] / 60000.0 if meta["durationMs"] > 0 else 1.0
    apm = meta["totalActions"] / duration_min

    return {
        "meta": meta,
        "duration_min": duration_min,
        "apm": round(apm, 1),
        "action_counts": action_counts,
        "chats": chats,
        "dota_stats": dota_stats,
        "trajectories": trajectories,
        "sync_stats": sync_stats
    }

def print_summary(analysis, raw_size, decomp_size):
    meta = analysis["meta"]
    dota = analysis["dota_stats"]
    
    start_time_str = datetime.fromtimestamp(meta["gameStartMs"] / 1000.0).strftime("%Y-%m-%d %H:%M:%S") if meta["gameStartMs"] > 0 else "未知"
    
    print("\n" + "=" * 68)
    print(f"🎮 魔兽争霸 3 / DotA 比赛动作档案分析报告")
    print("=" * 68)
    print(f"  📌 比赛编号 (Match ID) : {meta['matchId']}")
    print(f"  👤 玩家名称 (Player)   : {meta['player']} (PID: {meta['pid']})")
    print(f"  💻 客户端 (Client ID)  : {meta['clientId']}")
    print(f"  ⏰ 开始时间 (Start)    : {start_time_str}")
    print(f"  ⌛ 持续时长 (Duration) : {analysis['duration_min']:.2f} 分钟 ({meta['durationMs']} ms)")
    print(f"  📊 动作总数 (Actions)  : {meta['totalActions']} 次")
    print(f"  ⚡ 平均手速 (APM)      : {analysis['apm']} APM")
    print(f"  📦 压缩比率 (Ratio)    : 压缩前 {decomp_size / 1024.0:.1f} KB -> 压缩后 {raw_size / 1024.0:.1f} KB (节省 {(1 - raw_size / decomp_size) * 100:.1f}%)")
    
    print("\n🏆 DotA 动态战绩统计 (0x6B Sync 数据):")
    print(f"  🗡 游戏模式 (Mode)     : {dota['mode'] or '-ap (默认/自选)'}")
    print(f"  🧙 英雄标识 (Hero ID)  : {dota['hero'] or meta['heroId']}")
    print(f"  🎯 补刀战绩 (CS/DN/NK) : 正补 {dota['creep_kills']} | 反补 {dota['denies']} | 野怪 {dota['neutral_kills']}")
    if dota['roshan_events']:
        print(f"  🐲 肉山事件记录       : {len(dota['roshan_events'])} 次")
        for ro in dota['roshan_events']:
            print(f"     └─ [{ro['t']/1000:.1f}s] {ro['event']}")

    print("\n💬 玩家聊天记录 (0x60):")
    if analysis["chats"]:
        for c in analysis["chats"]:
            sec = c["t"] / 1000.0
            print(f"  [{sec:6.1f}s] {c['text']}")
    else:
        print("  (无聊天记录)")

    print("\n📈 动作类型分布 (Top Actions):")
    sorted_actions = sorted(analysis["action_counts"].items(), key=lambda x: -x[1])
    for aid, count in sorted_actions[:10]:
        pct = (count / meta["totalActions"]) * 100.0
        name = ACTION_NAMES.get(aid, "未知指令")
        print(f"  0x{aid:02X} ({aid:3d}) | {count:5d} 次 ({pct:5.1f}%) | {name}")

    print(f"\n🗺 轨迹坐标采样点: {len(analysis['trajectories'])} 个有效空间操作点 (可用于 Three.js 小地图重放)")
    print("=" * 68 + "\n")

def export_standalone_html(analysis, output_html):
    meta = analysis["meta"]
    dota = analysis["dota_stats"]
    trajectories = analysis["trajectories"]

    # 抽取前 1500 个轨迹点以保证网页流畅
    sample_traj = trajectories[::max(1, len(trajectories) // 1500)]

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>DotA 比赛动作可视化 - {meta['player']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121418; color: #E0E0E0; margin: 0; padding: 20px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #2A2F3B; padding-bottom: 15px; margin-bottom: 20px; }}
        h1 {{ margin: 0; color: #00BCD4; font-size: 24px; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .card {{ background: #1B1E26; border-radius: 8px; padding: 15px; border-left: 4px solid #00BCD4; }}
        .card-label {{ font-size: 12px; color: #8F9BA8; }}
        .card-value {{ font-size: 22px; font-weight: bold; margin-top: 5px; color: #FFF; }}
        .main-layout {{ display: grid; grid-template-columns: 1fr 420px; gap: 20px; }}
        .panel {{ background: #1B1E26; border-radius: 8px; padding: 15px; }}
        canvas {{ width: 100%; height: 500px; background: #0A0C10; border-radius: 6px; }}
        .chat-list {{ max-height: 480px; overflow-y: auto; font-family: monospace; }}
        .chat-item {{ padding: 6px 10px; border-bottom: 1px solid #242933; }}
        .chat-time {{ color: #00BCD4; margin-right: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🎮 War3 Match Replay & Stats</h1>
            <div style="color: #8F9BA8; font-size: 13px; margin-top: 5px;">Match ID: {meta['matchId']} | Player: {meta['player']} (PID: {meta['pid']})</div>
        </div>
        <div style="font-size: 28px; font-weight: bold; color: #4CAF50;">{analysis['apm']} <span style="font-size: 14px; color: #8F9BA8;">APM</span></div>
    </div>

    <div class="cards">
        <div class="card" style="border-left-color: #2196F3;">
            <div class="card-label">游戏时长</div>
            <div class="card-value">{analysis['duration_min']:.2f} <span style="font-size: 14px;">分钟</span></div>
        </div>
        <div class="card" style="border-left-color: #4CAF50;">
            <div class="card-label">总动作数 (Actions)</div>
            <div class="card-value">{meta['totalActions']}</div>
        </div>
        <div class="card" style="border-left-color: #FF9800;">
            <div class="card-label">补刀 (正补 / 反补 / 野怪)</div>
            <div class="card-value">{dota['creep_kills']} / {dota['denies']} / {dota['neutral_kills']}</div>
        </div>
        <div class="card" style="border-left-color: #9C27B0;">
            <div class="card-label">轨迹采样点</div>
            <div class="card-value">{len(trajectories)}</div>
        </div>
    </div>

    <div class="main-layout">
        <div class="panel">
            <h3 style="margin-top: 0; color: #00BCD4;">🗺 玩家小地图移动轨迹图 (Minimap Canvas)</h3>
            <canvas id="mapCanvas" width="600" height="600"></canvas>
        </div>
        <div class="panel">
            <h3 style="margin-top: 0; color: #00BCD4;">💬 玩家操作与聊天流</h3>
            <div class="chat-list">
    """
    for c in analysis["chats"]:
        html_content += f'<div class="chat-item"><span class="chat-time">[{c["t"]/1000:.1f}s]</span><span>{c["text"]}</span></div>\n'
    
    html_content += f"""
            </div>
        </div>
    </div>

    <script>
        const points = {json.dumps(sample_traj)};
        const canvas = document.getElementById('mapCanvas');
        const ctx = canvas.getContext('2d');

        // 魔兽争霸 3 经典 DotA 地图范围大致为 [-8000, 8000]
        function mapX(x) {{ return ((x + 8000) / 16000) * canvas.width; }}
        function mapY(y) {{ return (1.0 - (y + 8000) / 16000) * canvas.height; }}

        // 绘制河道与阵营示意分割线
        ctx.strokeStyle = '#1D2533';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, 0); ctx.lineTo(canvas.width, canvas.height);
        ctx.stroke();

        // 绘制轨迹连线
        if (points.length > 0) {{
            ctx.beginPath();
            ctx.strokeStyle = 'rgba(0, 188, 212, 0.6)';
            ctx.lineWidth = 1.5;
            ctx.moveTo(mapX(points[0].x), mapY(points[0].y));
            for (let i = 1; i < points.length; i++) {{
                ctx.lineTo(mapX(points[i].x), mapY(points[i].y));
            }}
            ctx.stroke();

            // 绘制起点和终点
            ctx.fillStyle = '#4CAF50';
            ctx.beginPath();
            ctx.arc(mapX(points[0].x), mapY(points[0].y), 6, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = '#F44336';
            ctx.beginPath();
            ctx.arc(mapX(points[points.length-1].x), mapY(points[points.length-1].y), 6, 0, Math.PI * 2);
            ctx.fill();
        }}
    </script>
</body>
</html>
    """
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✨ 交互式可视化页面已生成: {output_html}")

def main():
    parser = argparse.ArgumentParser(description="War3 Match DAT 动作归档解析工具")
    parser.add_argument("dat_file", help="输入的 .dat 文件路径 (例如 D:\\match_xxx.dat)")
    parser.add_argument("--export-json", help="导出解压缩后的原始 JSON 文件路径")
    parser.add_argument("--export-trajectory", help="仅导出轨迹坐标为 JSON 文件 (用于 Three.js)")
    parser.add_argument("--export-html", help="导出独立的 HTML 可视化报告网页")
    
    args = parser.parse_args()

    match_data, raw_size, decomp_size = load_dat_file(args.dat_file)
    analysis = analyze_match(match_data)
    
    print_summary(analysis, raw_size, decomp_size)

    if args.export_json:
        with open(args.export_json, "w", encoding="utf-8") as f:
            json.dump(match_data, f, ensure_ascii=False, indent=2)
        print(f"💾 完整 JSON 数据已导出至: {args.export_json}")

    if args.export_trajectory:
        with open(args.export_trajectory, "w", encoding="utf-8") as f:
            json.dump(analysis["trajectories"], f, ensure_ascii=False, indent=2)
        print(f"🗺 移动轨迹坐标已导出至: {args.export_trajectory}")

    if args.export_html:
        export_standalone_html(analysis, args.export_html)

if __name__ == "__main__":
    main()
