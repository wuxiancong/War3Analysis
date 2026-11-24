# -*- coding: utf-8 -*-
"""
精确解析 1.27 JASS VM 指针链与结构体偏移（G4）：
1. 0x7E0400 (GetVM: 从 g_jassEnv+0x08 取 VirtualMachine*)
2. 0x7E2C30 / 0x7EC540 (TSHashTable::Find: 确认哈希表 buckets/mask/next/key 偏移)
3. 0x7E2DB0 (查找全局变量或数组) 与 JassArray 元素读取（确认 JassArray::data 和 count 偏移）
4. 验证读图阶段为何 0x2BD982 会崩（反汇编 1.27 0x2BD960..0x2BD9B0）
"""
from pe_util import PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\probe_g4_layout_127.txt"


def main():
    dll = dll_path_for("1.27.0.52240")
    pe = PE32(dll)
    base = pe.image_base
    lines = []

    def dump(title, rva, sz):
        lines.append(f"\n=== {title} @ 0x{rva:X} ===")
        lines.extend("  " + l for l in disasm(dll, base, rva, sz))

    dump("1. GetVM (0x7E0400)", 0x7E0400, 0x50)
    dump("2. TSHashTable::Find (0x7EC540)", 0x7EC540, 0xA0)
    dump("3. GlobalTable lookup/insert (0x7E2C30)", 0x7E2C30, 0x90)
    dump("4. 0x7E2DB0 & 0x7EC810", 0x7EC810, 0x70)
    dump("5. 读图阶段崩溃点 0x2BD960..0x2BD9B0", 0x2BD960, 0x50)
    # 搜 JassArray 访问：在 0x7E0000..0x7F0000 搜 0x2000 (8192 = JASS_MAX_ARRAY_SIZE!)
    import struct
    hits_8192 = [h for h in pe.find_all_bytes(struct.pack("<I", 0x2000), ".text") if 0x7D0000 <= h <= 0x800000]
    lines.append(f"\n=== 6. JASS_MAX_ARRAY_SIZE (0x2000) in VM region: {[hex(h) for h in hits_8192[:8]]} ===")
    for h in hits_8192[:3]:
        dump(f"JassArray around 0x{h:X}", max(0, h - 0x20), 0x70)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")


if __name__ == "__main__":
    main()
