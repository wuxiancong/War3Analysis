# -*- coding: utf-8 -*-
"""在 1.24.4 / 1.26 / 1.27 的 game.dll 中批量提取『看局面』所需的 JASS 原生 RVA 与核心内部偏移。"""
import struct
import pefile

VERSIONS = [
    ("1.24.4.6387", r"D:\Qt\workspace\War3Launcher\versions\1.24.4.6387\game.dll"),
    ("1.26.0.6401", r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll"),
    ("1.27.0.52240", r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll"),
]

NATIVES = [
    "GetPlayerState",
    "GetFloatGameState",
    "GetHeroXP",
    "GetHeroLevel",
    "GetHeroStr",
    "GetHeroAgi",
    "GetHeroInt",
    "GetHeroSkillPoints",
    "GetUnitState",
    "GetWidgetLife",
    "GetUnitAbilityLevel",
    "UnitItemInSlot",
    "GetItemTypeId",
    "GetItemCharges",
    "IsUnitVisible",
    "IsUnitDetected",
    "IsUnitFogged",
    "IsUnitMasked",
    "IsUnitType",
    "GetUnitCurrentOrder",
    "GetUnitMoveSpeed",
]


def find_native(pe, data, tblob, trva, name):
    base = pe.OPTIONAL_HEADER.ImageBase
    pos = data.find(name.encode() + b"\x00")
    if pos < 0:
        return None
    va = base + pe.get_rva_from_offset(pos)
    pat = struct.pack("<I", va)
    k = 0
    while True:
        j = tblob.find(pat, k)
        if j < 0:
            return None
        # mov edx, str_va (BA ..); mov ecx, fn_va (B9 ..)
        if j >= 1 and j + 9 < len(tblob) and tblob[j - 1] == 0xBA and tblob[j + 4] == 0xB9:
            fn_va = struct.unpack_from("<I", tblob, j + 5)[0]
            return fn_va - base
        if j >= 6 and tblob[j - 6] == 0xB9 and tblob[j - 1] == 0xBA:
            fn_va = struct.unpack_from("<I", tblob, j - 5)[0]
            return fn_va - base
        k = j + 1


def main():
    table = {n: {} for n in NATIVES}
    for ver, dll in VERSIONS:
        data = open(dll, "rb").read()
        pe = pefile.PE(dll, fast_load=True)
        text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
        tblob = data[text.PointerToRawData : text.PointerToRawData + text.SizeOfRawData]
        trva = text.VirtualAddress
        for n in NATIVES:
            rva = find_native(pe, data, tblob, trva, n)
            table[n][ver] = f"0x{rva:X}" if rva else "-"
        pe.close()

    print(f"{'Native':24s} | {'1.24.4.6387':12s} | {'1.26.0.6401':12s} | {'1.27.0.52240':12s}")
    print("-" * 68)
    for n in NATIVES:
        print(
            f"{n:24s} | {table[n]['1.24.4.6387']:12s} | {table[n]['1.26.0.6401']:12s} | {table[n]['1.27.0.52240']:12s}"
        )


if __name__ == "__main__":
    main()
