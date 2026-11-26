# -*- coding: utf-8 -*-
"""
支配头盔 (I08T) 自动合成、支配中立野怪、控怪囤野实机日志校验脚本。
用法（供 Claude 在实机测试后运行，不连接游戏端口）：
    python verify_live_helm_dominate.py [AiUnit.log 路径]
"""
import os
import re
import sys

DEFAULT_LOG = r"C:\War3Run\War3Launcher\logs\AiUnit.log"


def main():
    log_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LOG
    if not os.path.isfile(log_path):
        print(f"[ERROR] 找不到日志文件: {log_path}")
        sys.exit(1)

    # 统计关键里程碑事件
    bought_helm = 0
    bought_mask = 0
    got_i08t = 0
    dom_cast = 0
    dom_unit_seen = 0
    dom_orders = 0
    stack_pulls = 0

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            low = line.lower()
            if "helm_of_iron_will" in low or "h01h" in low:
                bought_helm += 1
            if "mask_of_death" in low or "h01m" in low:
                bought_mask += 1
            if "i08t" in low:
                got_i08t += 1
            if "a2v4" in low or "dominate" in low:
                dom_cast += 1
            if "a2yd" in low or "domunit" in low or "dom_unit" in low:
                dom_unit_seen += 1
            if "aiorderdominatedunit" in low or "dom_order" in low:
                dom_orders += 1
            if "dom_creep_pull" in low or "domstack" in low:
                stack_pulls += 1

    print(f"=== 支配头盔控怪囤野实机日志核验: {log_path} ===")
    print(f"  1. 购买铁意头盔 (h01H) 命中: {bought_helm}")
    print(f"  2. 购买死亡面具 (h01M) 命中: {bought_mask}")
    print(f"  3. 背包检出 I08T 命中:       {got_i08t}")
    print(f"  4. 施放支配 (A2V4) 命中:     {dom_cast}")
    print(f"  5. 识别支配怪 (A2YD) 命中:   {dom_unit_seen}")
    print(f"  6. 控怪发令命中:             {dom_orders}")
    print(f"  7. 支配怪拉野囤野命中:       {stack_pulls}")

    ok = (got_i08t > 0) and (dom_unit_seen > 0) and (dom_orders > 0)
    print("\n结论:", "[PASS] 合成、支配与控怪闭环已触发" if ok else "[INFO] 尚未检测到完整闭环（请确认日志中已开启支配囤野日志埋点）")


if __name__ == "__main__":
    main()
