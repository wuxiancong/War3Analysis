# 单位碰撞与被挡绕行 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Composer / Grok 路由（Cursor Agent） |
| **分析目的** | 导图配套 [`war3-unit-collision-and-repath.md`](./war3-unit-collision-and-repath.md) |
| **命名方式** | `war3-unit-collision-and-repath-mindmap` |
| **分析时间** | 2026-11-21 |

```mermaid
mindmap
  root((碰撞与绕行))
    碰撞半径
      UnitBalance collision ucol
      DotA esen16 edry32 ebal16 Hjai32
      CUnit 上无直接字段
      圆 r1+r2 移动分离
      32格 + 占用盒 寻路
    被挡处理
      CPoSeparate 每tick滑
      CPoPosCl 推进 propWin
      CLrPath 自带折线
      CLrPathingSys Acc 全局
      非纯原地等
      节流 400 700 候选
    绕行方向
      目标点 + 空格
      弯道外侧更空
      外侧兵 -175
    友军
      同域互碰
      叠出生 forceStop
      挤出外侧
    路径点
      COrder 48 50 命令终点
      CLrPath 34 步长20
      Amov挂接未完
    卡兵建议
      弯道偏外侧
      盖住 outer lat
      contactRadius+裕量
```

## RVA 速查（构造 / vtable）

| | 1.24.4 | 1.26 | 1.27 |
| :--- | :---: | :---: | :---: |
| `CLrPath` ctor | `0x49D52F` | `0x49CA1F` | `0x111F10` |
| `CLrPath` vt | `0x9654C4` | `0x95336C` | `0x961300` |
| `CPoSeparate` vt | `0x96430C` | `0x9521B4` | `0x960EB0` |

## 下路弯道站位（一句话）

`progress 3300~4300`：横向对准**最外侧未越过兵**，再向外偏约 `0.5×(heroCol+creepCol)`，前进仍保持 70~110。
