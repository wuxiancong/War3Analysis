# -*- coding: utf-8 -*-
r"""
Warcraft III 1.27 (.w3g) 全量二进制解析器 (纯 Python 标准库，无第三方依赖)
功能：
1. 解析 1.27 w3g 文件头 (68B)、zlib 压缩块 (8B 块头)、玩家表、编码地图串、槽位表；
2. 逐帧解析 0x1F / 0x1E TimeSlot 动作块与 0x20 聊天块，精确对齐 1.27 全量 Action ID 长度；
3. 维护每个玩家的「当前选中单位集合 (0x16/0x17/0x18/0x19)」，解码 OrderId (0x000Dxxxx) 与 FourCC (学技能/买物品/选英雄)；
4. 提取 0x6B GameCache 同步事件（击杀/死亡/助攻/升级/正反补/推塔/买活/终局结算）与 0x60 触发聊天；
5. 自动推断每位玩家使用的英雄。
用法：python w3g_parser.py <path_to.w3g> [--out out.json]
"""
import os
import sys
import json
import zlib
import struct
from collections import defaultdict, Counter

# 常见 War3 / DotA OrderId (0x000Dxxxx) 人类可读名称表
ORDER_NAMES = {
    0x000D0003: "smart(右键移动/攻击/拾取)",
    0x000D0004: "stop(停止 S)",
    0x000D0005: "stunned(眩晕)",
    0x000D0008: "cancel(取消 ESC)",
    0x000D000C: "setrally(集结点)",
    0x000D000D: "getitem(拾取物品)",
    0x000D000F: "attack(攻击 A)",
    0x000D0010: "attackground(攻击地面 G)",
    0x000D0012: "move(移动 M)",
    0x000D0016: "patrol(巡逻 P)",
    0x000D0019: "holdposition(保持原位 H)",
    0x000D0021: "dropitem(丢弃/给予物品)",
    0x000D0022: "moveslot1(移至物品格1)",
    0x000D0023: "moveslot2(移至物品格2)",
    0x000D0024: "moveslot3(移至物品格3)",
    0x000D0025: "moveslot4(移至物品格4)",
    0x000D0026: "moveslot5(移至物品格5)",
    0x000D0027: "moveslot6(移至物品格6)",
    0x000D0028: "useslot1(使用物品格1)",
    0x000D0029: "useslot2(使用物品格2)",
    0x000D002A: "useslot3(使用物品格3)",
    0x000D002B: "useslot4(使用物品格4)",
    0x000D002C: "useslot5(使用物品格5)",
    0x000D002D: "useslot6(使用物品格6)",
    # DotA 常用技能 OrderId (基于原生技能基底)
    0x000D0079: "spell_blizzard/torrent/flare(点地AOE)",
    0x000D007F: "spell_thunderbolt(单体晕/锤)",
    0x000D0081: "spell_frostnova(冰霜新星/冰女V)",
    0x000D0083: "spell_entanglingroots(缠绕/冰女E)",
    0x000D00A1: "spell_windwalk/leap(隐身/跳跃)",
    0x000D00C5: "spell_chainlightning(闪电链)",
    0x000D00D2: "spell_frostarmor(冰甲)",
    0x000D00D7: "spell_hex(妖术/变羊)",
    0x000D00F9: "spell_carrionswarm(冲击波)",
    0x000D00FA: "spell_impale/wave(穿刺/冲锋)",
    0x000D0107: "spell_charge/lifebreak(目标冲刺)",
    0x000D0118: "spell_starfall/freezingfield(范围引导大招)",
    0x000D0129: "spell_shadowstrike(暗影突袭)",
    0x000D022D: "spell_blink(闪烁)",
    0x000D0247: "spell_ward/summon(插眼/召唤)",
    0x000D0278: "spell_channel_notarget(无目标主动技)",
    0x000D02B6: "spell_point_projectile(点地弹道技)",
}

# 常见 DotA 6.83d 英雄 FourCC 名称表（覆盖常见英雄与本地测试英雄）
HERO_NAMES = {
    "Hjai": "水晶室女 (Crystal Maiden)",
    "H008": "影魔 (Shadow Fiend)",
    "Nbbc": "剑圣 (Juggernaut)",
    "Edem": "敌法师 (Anti-Mage)",
    "E002": "月之骑士 (Luna)",
    "U00F": "屠夫 (Pudge)",
    "H001": "流浪剑客 (Sven)",
    "H004": "火女 (Lina)",
    "H00D": "宙斯 (Zeus)",
    "H00H": "发条技师 (Clockwerk)",
    "H00I": "地卜师 (Meepo)",
    "H00K": "船长 (Kunkka)",
    "H00N": "蓝猫 (Storm Spirit)",
    "H00Q": "祈求者 (Invoker)",
    "H00R": "风行者 (Windranger)",
    "H00S": "神灵武士 (Huskar)",
    "H00U": "灰烬之灵 (Ember Spirit)",
    "Hamg": "光之守卫 (KotL)",
    "Hblm": "祈求者旧/卡尔",
    "Hmkg": "宙斯/山丘",
    "O00J": "撼地者 (Earthshaker)",
    "Obla": "剑圣模型",
    "U00A": "混沌骑士 (Chaos Knight)",
    "U00K": "沙王 (Sand King)",
    "U00P": "幽鬼 (Spectre)",
    "Ucrl": "司夜刺客 (Nyx)",
    "Udea": "死亡先知 (Death Prophet)",
    "Udre": "暗夜魔王 (Night Stalker)",
    "Ulic": "巫妖 (Lich)",
    "Emoo": "月之女祭司 (Mirana)",
    "Ekee": "先知 (Nature's Prophet)",
    "Ewar": "幻影刺客 (Phantom Assassin)",
    "N00B": "仙女龙 (Puck)",
    "N016": "巨魔战将 (Troll Warlord)",
    "N01A": "变体精灵 (Morphling)",
    "Nbrn": "卓尔游侠 (Drow Ranger)",
    "Nfir": "影魔模型",
    "Nngs": "美杜莎 (Medusa)",
    "Npbm": "酒仙 (Brewmaster)",
    "Ntin": "修补匠 (Tinker)",
}

# 行业标准计入有效 APM 的 Action ID 集合
APM_ACTION_IDS = {0x10, 0x11, 0x12, 0x13, 0x14, 0x16, 0x17, 0x18, 0x19, 0x1B, 0x1C, 0x66}

def is_printable_fourcc(val):
    b = struct.pack("<I", val)[::-1]
    return all(32 <= ch <= 126 for ch in b)

def u32_to_fourcc(val):
    return struct.pack("<I", val)[::-1].decode("ascii", errors="replace")

def decode_order_id(order_id):
    if order_id in ORDER_NAMES:
        return ORDER_NAMES[order_id], "order"
    if (order_id & 0xFFFF0000) == 0x000D0000:
        return f"order_0x{order_id:08X}", "order"
    if is_printable_fourcc(order_id):
        fc = u32_to_fourcc(order_id)
        if fc in HERO_NAMES:
            return f"pick_hero:{fc}({HERO_NAMES[fc]})", "hero_pick"
        if fc.startswith("A"):
            return f"learn_skill:{fc}", "skill_learn"
        if fc.startswith(("I", "h0", "n0", "e0", "u0", "o0")):
            return f"buy_or_unit:{fc}", "shop_or_unit"
        return f"fourcc:{fc}", "fourcc"
    return f"raw_0x{order_id:08X}", "unknown"

def read_cstr(buf, pos):
    end = buf.find(b"\x00", pos)
    if end < 0:
        return "", len(buf)
    raw = buf[pos:end]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("gbk", errors="replace")
    return text, end + 1

def decode_w3g_encoded_string(raw_bytes):
    """解码 War3 录像头部的 odd-byte bitmask 编码字符串（含地图路径与房主名）"""
    out = bytearray()
    i = 0
    n = len(raw_bytes)
    while i < n:
        mask = raw_bytes[i]
        i += 1
        for bit in range(7):
            if i >= n:
                break
            b = raw_bytes[i]
            i += 1
            if (mask & (1 << (bit + 1))) == 0:
                b = (b - 1) & 0xFF
            out.append(b)
    return bytes(out)

def decompress_w3g(path):
    with open(path, "rb") as f:
        raw = f.read()
    magic = raw[:28]
    if not magic.startswith(b"Warcraft III recorded game"):
        raise ValueError(f"Not a valid w3g file: {path}")

    hdr_size, comp_size, hdr_ver, decomp_size, nblocks = struct.unpack_from("<IIIII", raw, 0x1C)
    # Sub-header (20 bytes at 0x30..0x44 for hdr_ver == 1)
    game_id = raw[0x30:0x34][::-1].decode("ascii", errors="replace")
    patch_ver, build_num, flags, duration_ms, crc32 = struct.unpack_from("<IHHII", raw, 0x34)

    header = {
        "file": os.path.basename(path),
        "file_size": len(raw),
        "header_size": hdr_size,
        "header_version": hdr_ver,
        "compressed_size": comp_size,
        "decompressed_size": decomp_size,
        "num_blocks": nblocks,
        "game_id": game_id,
        "patch_version": f"1.{patch_ver}",
        "build_number": build_num,
        "flags": flags,
        "duration_ms": duration_ms,
        "crc32": f"0x{crc32:08X}",
    }

    pos = hdr_size
    out = bytearray()
    for _ in range(nblocks):
        if pos + 8 > len(raw):
            break
        csize, dsize, _chk = struct.unpack_from("<HHI", raw, pos)
        pos += 8
        chunk = raw[pos:pos + csize]
        pos += csize
        try:
            dec = zlib.decompress(chunk)
        except zlib.error:
            dec = zlib.decompressobj().decompress(chunk)
        out.extend(dec[:dsize])

    return header, bytes(out)

def parse_startup_header(data):
    """解析解压后的玩家表、地图名、槽位表，返回 (meta, stream_start_offset)"""
    pos = 4  # 跳过前 4 字节未知头 (0x00000110 等)
    players = {}

    def read_player_record(p):
        rec_id = data[p]
        pid = data[p + 1]
        name, p2 = read_cstr(data, p + 2)
        add_len = data[p2]
        p2 += 1 + add_len
        return rec_id, pid, name, p2

    # 1. Host PlayerRecord
    rec_id, host_pid, host_name, pos = read_player_record(pos)
    players[host_pid] = {"pid": host_pid, "name": host_name, "is_host": True}

    # 2. Game Name + null byte
    game_name, pos = read_cstr(data, pos)
    if pos < len(data) and data[pos] == 0x00:
        pos += 1

    # 3. Encoded String (到 0x00 结束)
    enc_end = data.find(b"\x00", pos)
    enc_raw = data[pos:enc_end]
    pos = enc_end + 1
    dec_str = decode_w3g_encoded_string(enc_raw)
    # 解码串格式: 13 字节设置 + map_path\0 + creator\0
    map_path = ""
    creator_name = ""
    if len(dec_str) > 13:
        map_path, mp_end = read_cstr(dec_str, 13)
        creator_name, _ = read_cstr(dec_str, mp_end)

    # 4. PlayerCount(4) + GameType(4) + LanguageID(4)
    player_count, game_type, lang_id = struct.unpack_from("<III", data, pos)
    pos += 12

    # 5. Additional PlayerRecords (0x16)
    while pos < len(data) and data[pos] == 0x16:
        rec_id, pid, pname, pos = read_player_record(pos)
        pos += 4  # 4 字节未知尾部
        players[pid] = {"pid": pid, "name": pname, "is_host": False}

    # 6. GameStartRecord (0x19)
    slots = []
    if pos < len(data) and data[pos] == 0x19:
        rec_len = struct.unpack_from("<H", data, pos + 1)[0]
        rec_end = pos + 3 + rec_len
        num_slots = data[pos + 3]
        sp = pos + 4
        for s_idx in range(num_slots):
            if sp + 9 > rec_end:
                break
            s_pid, dl_pct, status, is_comp, team, color, race, ai_lvl, handicap = struct.unpack_from("<BBBBBBBBB", data, sp)
            sp += 9
            slots.append({
                "slot": s_idx, "pid": s_pid, "status": status, "is_comp": is_comp,
                "team": team, "color": color, "race": race, "handicap": handicap
            })
            if s_pid in players:
                players[s_pid]["team"] = team
                players[s_pid]["color"] = color
                players[s_pid]["slot"] = s_idx
        pos = rec_end

    meta = {
        "game_name": game_name,
        "map_path": map_path,
        "creator_name": creator_name,
        "player_count": player_count,
        "players": players,
        "slots": slots,
    }
    return meta, pos

def parse_action_block(pid, abuf, time_ms, player_state, actions_out, events_out):
    """解析单个 CommandData 内的全部串联 Action"""
    i = 0
    n = len(abuf)
    sel = player_state["selected"]
    groups = player_state["groups"]

    while i < n:
        aid = abuf[i]
        i += 1
        rec = {"t_ms": time_ms, "pid": pid, "aid": f"0x{aid:02X}", "aid_int": aid}

        if aid in (0x01, 0x02, 0x04, 0x05, 0x1A, 0x61, 0x66, 0x67):
            # 0 字节载荷
            names_0 = {
                0x01: "pause_game", 0x02: "resume_game", 0x04: "speed_inc", 0x05: "speed_dec",
                0x1A: "pre_subselection", 0x61: "esc_cancel", 0x66: "hero_skill_menu", 0x67: "build_menu"
            }
            rec["type"] = names_0[aid]
            if aid != 0x1A:  # 0x1A 为切换选中前的自动前缀，无需膨胀动作流（但统计可记）
                rec["selected_count"] = len(sel)
                actions_out.append(rec)
            continue

        elif aid == 0x03:
            if i + 1 > n: break
            rec["type"] = "set_speed"
            rec["val"] = abuf[i]; i += 1
            actions_out.append(rec)

        elif aid == 0x06:
            s, i = read_cstr(abuf, i)
            rec["type"] = "save_game"; rec["text"] = s
            actions_out.append(rec)

        elif aid == 0x07:
            i += 4

        elif aid == 0x10:
            # 无目标指令 (14B): Flags(2) + OrderId(4) + Unknown(8)
            if i + 14 > n: break
            flags, order_id = struct.unpack_from("<HI", abuf, i)
            i += 14
            oname, okind = decode_order_id(order_id)
            rec.update({"type": "order_immediate", "flags": flags, "order_id": f"0x{order_id:08X}",
                        "order_name": oname, "order_kind": okind, "selected": list(sel[:4])})
            actions_out.append(rec)
            if okind == "hero_pick" and not player_state["hero"]:
                player_state["hero"] = u32_to_fourcc(order_id)

        elif aid == 0x11:
            # 点目标指令 (22B): Flags(2) + OrderId(4) + Unknown(8) + X(4f) + Y(4f)
            if i + 22 > n: break
            flags, order_id, _u1, _u2, x, y = struct.unpack_from("<HIIIff", abuf, i)
            i += 22
            oname, okind = decode_order_id(order_id)
            rec.update({"type": "order_point", "flags": flags, "order_id": f"0x{order_id:08X}",
                        "order_name": oname, "order_kind": okind, "x": round(x, 1), "y": round(y, 1),
                        "selected": list(sel[:4])})
            actions_out.append(rec)

        elif aid == 0x12:
            # 单位目标指令 (30B): Flags(2) + OrderId(4) + Unknown(8) + X(4f) + Y(4f) + Obj1(4) + Obj2(4)
            if i + 30 > n: break
            flags, order_id, _u1, _u2, x, y, o1, o2 = struct.unpack_from("<HIIIffII", abuf, i)
            i += 30
            oname, okind = decode_order_id(order_id)
            rec.update({"type": "order_target", "flags": flags, "order_id": f"0x{order_id:08X}",
                        "order_name": oname, "order_kind": okind, "x": round(x, 1), "y": round(y, 1),
                        "target_obj1": f"0x{o1:08X}", "target_obj2": f"0x{o2:08X}",
                        "selected": list(sel[:4])})
            actions_out.append(rec)

        elif aid == 0x13:
            # 给予/丢弃物品 (38B): 30B + ItemObj1(4) + ItemObj2(4)
            if i + 38 > n: break
            flags, order_id, _u1, _u2, x, y, o1, o2, io1, io2 = struct.unpack_from("<HIIIffIIII", abuf, i)
            i += 38
            oname, okind = decode_order_id(order_id)
            rec.update({"type": "order_item_give", "flags": flags, "order_id": f"0x{order_id:08X}",
                        "order_name": oname, "x": round(x, 1), "y": round(y, 1),
                        "target_obj1": f"0x{o1:08X}", "item_obj1": f"0x{io1:08X}",
                        "selected": list(sel[:4])})
            actions_out.append(rec)

        elif aid == 0x14:
            # 双目标指令 (43B): Flags(2) + OrderA(4) + Unk(8) + X1(4f) + Y1(4f) + OrderB(4) + FlagsB(9) + X2(4f) + Y2(4f)
            if i + 43 > n: break
            flags, order_id, _u1, _u2, x, y = struct.unpack_from("<HIIIff", abuf, i)
            i += 43
            oname, okind = decode_order_id(order_id)
            rec.update({"type": "order_two_target", "flags": flags, "order_id": f"0x{order_id:08X}",
                        "order_name": oname, "x": round(x, 1), "y": round(y, 1), "selected": list(sel[:4])})
            actions_out.append(rec)

        elif aid == 0x16:
            # 选择单位: Mode(1B: 1=add, 2=remove) + Count(2B) + Count * (Obj1(4), Obj2(4))
            if i + 3 > n: break
            mode, cnt = struct.unpack_from("<BH", abuf, i)
            i += 3
            if i + cnt * 8 > n: break
            objs = []
            for _ in range(cnt):
                o1, o2 = struct.unpack_from("<II", abuf, i)
                i += 8
                objs.append(f"0x{o1:08X}")
            if mode == 1:
                for o in objs:
                    if o not in sel:
                        sel.append(o)
            elif mode == 2:
                sel[:] = [o for o in sel if o not in objs]
            rec.update({"type": "select_add" if mode == 1 else "select_remove", "count": cnt, "objs": objs[:6]})
            actions_out.append(rec)

        elif aid == 0x17:
            # 设置编队: GroupIdx(1B) + Count(2B) + Count * 8B
            if i + 3 > n: break
            grp, cnt = struct.unpack_from("<BH", abuf, i)
            i += 3
            if i + cnt * 8 > n: break
            objs = []
            for _ in range(cnt):
                o1, o2 = struct.unpack_from("<II", abuf, i)
                i += 8
                objs.append(f"0x{o1:08X}")
            groups[grp] = objs
            rec.update({"type": "assign_group", "group": grp, "count": cnt, "objs": objs[:6]})
            actions_out.append(rec)

        elif aid == 0x18:
            # 选中编队: GroupIdx(1B) + Unk(1B)
            if i + 2 > n: break
            grp, unk = struct.unpack_from("<BB", abuf, i)
            i += 2
            if grp in groups:
                sel[:] = list(groups[grp])
            rec.update({"type": "select_group", "group": grp, "selected": list(sel[:4])})
            actions_out.append(rec)

        elif aid == 0x19:
            # 子组切换: UnitTypeId(4B FourCC) + Obj1(4B) + Obj2(4B)
            if i + 12 > n: break
            utype, o1, o2 = struct.unpack_from("<III", abuf, i)
            i += 12
            fc = u32_to_fourcc(utype) if is_printable_fourcc(utype) else f"0x{utype:08X}"
            if fc in HERO_NAMES and not player_state["hero"]:
                player_state["hero"] = fc
                player_state["hero_obj1"] = f"0x{o1:08X}"
            rec.update({"type": "select_subgroup", "unit_type": fc, "obj1": f"0x{o1:08X}"})
            actions_out.append(rec)

        elif aid in (0x1B, 0x1C):
            if i + 9 > n: break
            i += 9
            rec["type"] = "select_trigger_unit" if aid == 0x1B else "select_ground_item"
            actions_out.append(rec)

        elif aid == 0x1D:
            if i + 8 > n: break
            i += 8
            rec["type"] = "cancel_revive"
            actions_out.append(rec)

        elif aid == 0x1E:
            if i + 5 > n: break
            i += 5
            rec["type"] = "cancel_queue"
            actions_out.append(rec)

        elif aid == 0x21:
            if i + 8 > n: break
            i += 8

        elif aid == 0x50:
            if i + 5 > n: break
            i += 5
            rec["type"] = "change_ally"
            actions_out.append(rec)

        elif aid == 0x51:
            if i + 9 > n: break
            i += 9
            rec["type"] = "transfer_resources"
            actions_out.append(rec)

        elif aid == 0x60:
            # Trigger Chat: Unk1(4) + Unk2(4) + Text\0
            if i + 8 > n: break
            i += 8
            text, i = read_cstr(abuf, i)
            rec.update({"type": "trigger_chat", "text": text})
            actions_out.append(rec)
            events_out.append({"t_ms": time_ms, "pid": pid, "source": "0x60_chat", "text": text})

        elif aid == 0x62:
            if i + 12 > n: break
            i += 12

        elif aid == 0x68:
            # Minimap Ping: X(4f) + Y(4f) + Duration(4f)
            if i + 12 > n: break
            x, y, dur = struct.unpack_from("<fff", abuf, i)
            i += 12
            rec.update({"type": "minimap_ping", "x": round(x, 1), "y": round(y, 1)})
            actions_out.append(rec)

        elif aid in (0x69, 0x6A):
            if i + 16 > n: break
            i += 16

        elif aid == 0x6B:
            # GameCache Sync: cache\0 + mission_key\0 + key\0 + u32 val
            cache_name, i = read_cstr(abuf, i)
            mkey, i = read_cstr(abuf, i)
            key, i = read_cstr(abuf, i)
            if i + 4 > n: break
            val = struct.unpack_from("<I", abuf, i)[0]
            i += 4
            ev = {"t_ms": time_ms, "pid": pid, "source": "0x6B", "cache": cache_name,
                  "mkey": mkey, "key": key, "val": val}
            # 解码 DotA 6.83d 常见 0x6B 事件
            if key == "9" and is_printable_fourcc(val):
                ev["decoded"] = f"end_hero:{u32_to_fourcc(val)}"
            elif key.startswith("Hero"):
                ev["decoded"] = f"hero_kill_event:{key}={val}"
            elif key.startswith("Tower"):
                ev["decoded"] = f"tower_event:{key}={val}"
            elif key.startswith("Level"):
                ev["decoded"] = f"level_up:{key} (slot={val})"
            elif key.startswith("CSK"):
                ev["decoded"] = f"creep_kill:{key}={val}"
            elif key.startswith("CSD"):
                ev["decoded"] = f"creep_deny:{key}={val}"
            elif key == "Winner":
                ev["decoded"] = f"winner={'Sentinel' if val == 1 else 'Scourge'}"
            events_out.append(ev)

        elif aid == 0x75:
            if i + 1 > n: break
            i += 1

        else:
            # 未知 Action ID，停止本 CommandData 以免错位
            break

def parse_w3g(path):
    header, data = decompress_w3g(path)
    meta, pos = parse_startup_header(data)

    time_ms = 0
    actions = []
    events = []
    chats = []
    player_states = defaultdict(lambda: {"selected": [], "groups": {}, "hero": "", "hero_obj1": ""})

    n = len(data)
    while pos < n:
        blk = data[pos]
        pos += 1
        if blk == 0x17:
            # LeaveGame (13B)
            if pos + 13 > n: break
            reason, pid, result, unk = struct.unpack_from("<IBII", data, pos)
            pos += 13
            events.append({"t_ms": time_ms, "pid": pid, "source": "0x17_leave", "reason": reason})
        elif blk in (0x1A, 0x1B, 0x1C):
            pos += 4
        elif blk in (0x1E, 0x1F):
            # TimeSlot Block: u16 nbytes, u16 time_inc
            if pos + 4 > n: break
            nbytes, time_inc = struct.unpack_from("<HH", data, pos)
            pos += 4
            time_ms += time_inc
            cmd_end = pos + nbytes - 2
            if cmd_end > n:
                break
            cp = pos
            while cp + 3 <= cmd_end:
                pid = data[cp]
                alen = struct.unpack_from("<H", data, cp + 1)[0]
                cp += 3
                if cp + alen > cmd_end:
                    break
                parse_action_block(pid, data[cp:cp + alen], time_ms, player_states[pid], actions, events)
                cp += alen
            pos = cmd_end
        elif blk == 0x20:
            # PlayerChat: pid(1) + len(2) + flags(1) + [chat_mode(4) if flags==0x20] + msg\0
            if pos + 3 > n: break
            pid, clen = struct.unpack_from("<BH", data, pos)
            pos += 3
            cend = pos + clen
            if cend > n: break
            cflags = data[pos]
            tp = pos + 1
            chat_mode = 0
            if cflags == 0x20 and tp + 4 <= cend:
                chat_mode = struct.unpack_from("<I", data, tp)[0]
                tp += 4
            msg, _ = read_cstr(data, tp)
            chats.append({"t_ms": time_ms, "pid": pid, "mode": chat_mode, "text": msg})
            events.append({"t_ms": time_ms, "pid": pid, "source": "0x20_chat", "text": msg})
            pos = cend
        elif blk == 0x22:
            if pos + 1 > n: break
            sz = data[pos]
            pos += 1 + sz
        elif blk == 0x23:
            pos += 10
        elif blk == 0x2F:
            pos += 8
        elif blk == 0x00:
            break
        else:
            break

    # 汇总玩家英雄与 APM
    dur_min = max(0.05, max(header["duration_ms"], time_ms) / 60000.0)
    apm_counts = Counter()
    for a in actions:
        if a["aid_int"] in APM_ACTION_IDS:
            apm_counts[a["pid"]] += 1

    for pid, pinfo in meta["players"].items():
        pst = player_states[pid]
        pinfo["hero_code"] = pst["hero"]
        pinfo["hero_name"] = HERO_NAMES.get(pst["hero"], pst["hero"] or "Unknown")
        pinfo["hero_obj1"] = pst["hero_obj1"]
        pinfo["apm_actions"] = apm_counts[pid]
        pinfo["apm"] = round(apm_counts[pid] / dur_min, 1)

    return {
        "header": header,
        "meta": meta,
        "parsed_duration_ms": time_ms,
        "actions": actions,
        "events": events,
        "chats": chats,
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python w3g_parser.py <replay.w3g> [--out out.json]")
        sys.exit(1)
    res = parse_w3g(sys.argv[1])
    print(f"File: {res['header']['file']} | Patch: {res['header']['patch_version']} | Dur: {res['parsed_duration_ms']/1000:.1f}s")
    print(f"Map: {res['meta']['map_path']}")
    for pid, p in res["meta"]["players"].items():
        print(f"  PID {pid}: {p['name']} | Hero={p['hero_name']} | APM={p['apm']} ({p['apm_actions']} actions)")
    print(f"Total actions={len(res['actions'])}, events={len(res['events'])}, chats={len(res['chats'])}")
    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        with open(sys.argv[idx + 1], "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
