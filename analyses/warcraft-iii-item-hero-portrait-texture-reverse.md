# 魔兽争霸 III（War3）商店物品、英雄装备与头像图像处理逆向分析

> **分析对象**：`D:\Qt\workspace\War3Launcher\versions\*\game.dll`（覆盖 `1.0.17.5988` 至 `1.27.0.52240` 共 11 个版本，核心反编译以 `1.26.0.6401` 为基准）  
> **关联地图与源码**：`D:\Maps\DotA v6.83d.w3x`、`d:\Qt\workspace\War3Launcher\hooker\war3hook.cpp`  
> **分析工具**：Ghidra 12.1.4（无头反编译）、PE 字节码扫描、像素级二进制比对、x32dbg 内存调试

---

## 1. 核心结论摘要

1. **为什么 MPQ 原图与游戏内图像不同（“特殊处理”的本质）**：
   - **BLP1 JPEG 通道序为 BGRA 而非 RGB**：暴雪 BLP1（`compression == 0`）使用共享 JPEG 头 + Mipmap 数据块，并直接以 `ijl15.dll` 的 `IJL_OTHER` (`0xFF`) 模式按 4 通道 `BGRA` 写入显存缓冲，直接匹配 Direct3D `D3DFMT_A8R8G8B8`（小端序字节序 `[B, G, R, A]`）。常规 PNG/JPEG 工具若按 RGB/YCbCr 解码，会导致 **红蓝（R/B）通道互换**。
   - **BLP1 调色板与独立 Alpha 合并**：BLP1（`compression == 1`）将 256 项 `BGRA` 调色板与独立 `1/4/8-bit` Alpha 数组分开存放，加载时再将 Alpha 写入每个像素的 `+3` 字节偏移。
   - **UI 层动态派生与叠加**：按钮控件自动通过 `%sDIS%s` 拼接禁用态图标路径（`CommandButtonsDisabled\DISBTN...`），并在渲染时叠加冷却遮罩、物品充能/层数数字与自动施法边框；主界面大头像则完全不走 2D BLP，而是由 `CPortraitButton` 渲染 3D `.mdx` 模型。
2. **为什么 `war3hook.cpp` 无法拦截并转换“铁树枝干”图标**：
   - **主因（地图配置与脚本路径不一致）**：在 `DotA v6.83d.w3x` 中，铁树枝干物品（`I04G`/`I0CU`）在商店与背包实际加载的是 `ReplaceableTextures\CommandButtons\BTNIronwoodbranch.blp`（及 `DISBTNIronwoodbranch.blp`），但地图脚本 `war3map.j` 多面板图标映射表 `G00[GO0]` 却将 `I04G`/`I0CU` 错误映射为 `ReplaceableTextures\CommandButtons\BTNNatureTouchGrow.blp`。由于游戏中从未加载 `BTNNatureTouchGrow.blp`，`findRealD3DTextureByPath` 重试 40 次仍无法命中。
   - **次因（Hook 查找范围局限）**：`findRealD3DTextureByPath` 仅扫描 `g_blpLastStartHandle & 0xFFFF0000` 所在的单个 64KB Storm 堆段，且回退列表仅查找 `g_war3GxDevices1`、忽略了 `g_war3GxDevices2`。

---

## 2. MPQ 解压图片 vs 游戏内图片：像素对比与底层处理逻辑

### 2.1 实测像素对比（以攻击之爪 `BTNClawsOfAttack` 为例）

使用 `System.Drawing.Bitmap` 直接对比 MPQ 解压 PNG 与 `war3hook.cpp` 从 D3D 显存导出的 PNG：

| 采样坐标 | MPQ 解压原图 (`BTNClawsOfAttack.png`) | 游戏内 D3D 导出图 (`ReplaceableTextures_CommandButtons_BTNClawsOfAttack.png`) | 差异 |
| :--- | :--- | :--- | :--- |
| `(0, 0)` | `ARGB(255, 11, 18, 18)` | `ARGB(255, 18, 18, 11)` | **R 与 B 通道互换** (`11 <-> 18`) |
| `(32, 32)` | `ARGB(255, 0, 2, 77)` | `ARGB(255, 77, 2, 0)` | **R 与 B 通道互换** (`0 <-> 77`) |

### 2.2 底层图像处理发生的位置与代码逻辑（1.26.0.6401）

1. **BLP1 JPEG 解码（`BLP1_DecodeJPEG` @ `0x6F78B2C0`）**：
   - 检测 BLP1 文件头 `compression == 0` 后，从 `blp + 0xA4` 读取共享 JPEG 头长度，从 `blp + 0xA8` 读取共享 JPEG 头，并与对应 Mipmap 数据块拼接。
   - 调用 `ijl15.dll`：`ijlInit` (`0x6F78B634`) -> 设置 `DIBChannels = 4`、`DIBColor = 0xff`、`JPGColor = 0xff`（即 `IJL_OTHER`，跳过 YCbCr->RGB 色彩空间转换）-> `ijlRead(..., 3)` (`0x6F78B62E`)。
   - 由于暴雪制作 BLP1 JPEG 时直接把 `[B, G, R, A]` 4 个分量作为原始通道压入 JPEG，因此 `IJL_OTHER` 解码输出的就是 **直接可供 `D3DFMT_A8R8G8B8` 使用的 BGRA 字节流**。
2. **BLP1 调色板解码（`BLP1_DecodePaletted` @ `0x6F78AA10`）**：
   - 当 `*(int*)(blp + 0x0C) == 1` 时进入。
   - 从 `blp + 0xA4` 读取 256 项 `BGRA` 调色板，按像素索引填色后，再读取独立的 `alpha_map` 数组，将 Alpha 值覆写到目标像素的第 `+3` 字节。
3. **禁用态（DISBTN）路径自动派生（`CommandButtonDisabledArtPath` @ `0x6F3207A0`）**：
   - 商店缺货/无权限、技能未学习或冷却/禁用状态并不依赖单独手写每个禁用路径，而是由引擎自动截取图标路径末尾文件名（`\` 或 `/` 之后），用格式串 `"%sDIS%s"`（`0x6F938588`）拼出 `ReplaceableTextures\CommandButtonsDisabled\DISBTN...`，然后分别以状态 `0x15`（正常态）和 `0x16`（禁用态）调用 `0x6F60EDA0` 绑定纹理。
4. **UI 控件二次渲染与 3D 头像分流**：
   - **商店物品 / 技能按钮**：`CCommandButton.cpp` 负责，额外叠加 `CommandButtonCooldown`（冷却扇形遮罩）、`CommandButtonNumber` / `CommandButtonNumberOverlay`（物品使用次数/库存数）和 `CommandButtonAutocast`（自动施法旋转边框）。
   - **英雄装备栏（6 格背包）**：`CInventoryBar.cpp` 复用命令按钮纹理管线。
   - **英雄头像**：
     - **主界面左下角动态大头像**：`CPortraitButton.cpp` 通过 `RegisterPortraitModel` 加载 `%s_portrait.mdx` / `%s_portrait.mdl` **3D 模型**，不走 2D `.blp` 图标管线。
     - **左上角英雄图标 / 编队 / 信息面板 / 计分板**：`CHeroBar.cpp`、`CInfoPanelUnitDetail.cpp`、`CInfoPanelGroupButton.cpp`、`CInfoPanelItemDetail.h` 等通过 `CSimpleButton::SetTexture` 加载 2D `.blp` 纹理。

---

## 3. 完整纹理加载与渲染管线（1.26.0.6401，ImageBase = `0x6F000000`）

```text
UI 控件 (CCommandButton / CInventoryBar / CHeroBar / CInfoPanel*)
  │
  ├─► [可选] CommandButtonDisabledArtPath (RVA 0x3207A0)
  │       └─ 格式串 "%sDIS%s" 生成 DISBTN 路径，分别设置正常(0x15)与禁用(0x16)纹理
  │
  └─► CSimpleButton::SetTexture (RVA 0x60E090)
        ├─ 检查 path[len-4] == '.'，否则自动补 ".blp"
        ├─ 调用 LoadTexture (RVA 0x4E3BE0)
        ├─ 若失败：将 .blp <-> .tga 互换后再次调用 LoadTexture(..., 1)
        ├─ 若仍失败：生成 0xFF00FF00 纯绿回退纹理 (0x4E3C80)
        └─ 返回 HTEXTURE 句柄存入按钮对象 this + 0x8C
              │
              ▼
        LoadTexture (RVA 0x4E3BE0)
          ├─ TextureLookupCache (RVA 0x4E1410) —— 命中缓存直接返回 HTEXTURE
          ├─ 格式探测 (RVA 0x4DDE80): 0 -> LoadTGATexture (0x4DF230), 1 -> LoadBLPTexture (0x4DF470)
          └─ LoadBLPTexture (RVA 0x4DF470)
                ├─ BLP1_ParseHeader (RVA 0x78A800, 校验魔数 'BLP1' = 0x31504C42)
                ├─ 分配 War3TextureHandle（+0x0C 为 pGxDevice，+0x20 为纹理路径）
                └─ GxTexCreate (RVA 0x526510) 注册 BLP_UpdateCallback (RVA 0x4DF3A0)
                      │
                      ▼
                BLP_UpdateCallback (0x4DF3A0) -> 0x4DE020 -> BLP1_DecodeMipmapLoop (0x78B560)
                  └─ BLP1_DecodeMipmap (RVA 0x78B4F0)
                        ├─ comp == 1 -> BLP1_DecodePaletted (RVA 0x78AA10)
                        └─ comp == 0 -> BLP1_DecodeJPEG (RVA 0x78B2C0) -> ijl15.dll (BGRA)
                      │
                      ▼
                CGxDevice 创建 D3D 纹理 -> GxDeviceCreateResult (RVA 0x5295A8)
                  └─ pSurface + 0x34 即 IDirect3DTexture8/9*
```

---

## 4. 全 11 个版本 `game.dll` 主要函数 RVA 偏移总表

以下偏移均为相对 `game.dll` 模块基址的 **RVA**（实测覆盖 `D:\Qt\workspace\War3Launcher\versions` 全部 11 个版本）：

| 版本 | `CSimpleButton::SetTexture` | `LoadTexture` | `TextureLookupCache` | `LoadBLPTexture` | `GxTexCreate` | `GxDeviceCreateResult` | `CommandButtonDisabledArtPath` | `BLP1_ParseHeader` | `BLP1_DecodeMipmap` | `BLP1_DecodeJPEG` | `BLP1_DecodePaletted` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `1.0.17.5988` | `0x65D190` | `0x055310` | `0x0553C0` | `0x0557E0` | `0x0C8CC0` | `0x0CAEDB` | `0x116570` | `0x0D7710` | `0x0D78E0`* | `0x0D7F80` | `0x0D7A50` |
| `1.0.20.6048` | `0x65D690` | `0x055310` | `0x0553C0` | `0x0557E0` | `0x0C8CC0` | `0x0CAEDB` | `0x116570` | `0x0D7710` | `0x0D78E0`* | `0x0D7F80` | `0x0D7A50` |
| `1.20.4.6074` | `0x65DFD0` | `0x055310` | `0x0553C0` | `0x0557E0` | `0x0C8CC0` | `0x0CAEDB` | `0x116580` | `0x0D7710` | `0x0D78E0`* | `0x0D7F80` | `0x0D7A50` |
| `1.21.0.6263` | `0x661FF0` | `0x055310` | `0x0553C0` | `0x0557E0` | `0x0C8CC0` | `0x0CAEDB` | `0x1165A0` | `0x0D7710` | `0x0D7910`* | `0x0D7F80` | `0x0D7A50` |
| `1.22.0.6328` | `0x5FE110` | `0x4D3F40` | `0x4D1770` | `0x4D47D0`* | `0x516870` | `0x519908` | `0x31FC20` | `0x779730` | `0x77A420` | `0x77A1F0` | `0x779940` |
| `1.23.0.6352` | `0x5FFD90` | `0x4D5CD0` | `0x4D3500` | `0x4D6560`* | `0x518600` | `0x51B698` | `0x321160` | `0x77BCB0` | `0x77C9A0` | `0x77C770` | `0x77BEC0` |
| `1.24.1.6374` | `0x60E780` | `0x4E4660` | `0x4E1E90` | `0x4E4EF0`* | `0x526F90` | `0x52A028` | `0x321220` | `0x78AEE0` | `0x78BBD0` | `0x78B9A0` | `0x78B0F0` |
| `1.24.4.6387` | `0x60E830` | `0x4E46E0` | `0x4E1F10` | `0x4E4F70`* | `0x527010` | `0x52A0A8` | `0x3212E0` | `0x78AFA0` | `0x78BC90` | `0x78BA60` | `0x78B1B0` |
| `1.25.1.6397` | `0x60DE60` | `0x4E39B0` | `0x4E11E0` | `0x4E4240`* | `0x5262E0` | `0x529378` | `0x320570` | `0x78A5D0` | `0x78B2C0` | `0x78B090` | `0x78A7E0` |
| `1.26.0.6401` | `0x60E090` | `0x4E3BE0` | `0x4E1410` | `0x4E4470`* -> `0x4DF470` | `0x526510` | `0x5295A8` | `0x3207A0` | `0x78A800` | `0x78B4F0` | `0x78B2C0` | `0x78AA10` |
| `1.27.0.52240` | `0x0C11E0` | `0x197440` | `0x194270` | `0x193B30` | `0x0E37E0` | `0x0E6AA5` | `0x332860` | `0x7BFA50` | `0x7C0420` | `0x7C0780` | `0x7BFD80` |

> 注：表中 `1.26.0.6401` 经 Ghidra 完整反编译确认 `LoadBLPTexture = 0x4DF470`、`LoadTGATexture = 0x4DF230`；带 `*` 项为基于邻近版本调用特征与特征码扫描定位的对应分发入口，使用前可在 x32dbg 中对照 `LoadTexture` 内部第 2 个分支 `call`（`BLP1` 分支）核对。

---

## 5. 为何 `war3hook.cpp` 无法拦截并转换“铁树枝干”图标

### 5.1 根本原因：DotA v6.83d 地图自身物品路径与多面板脚本路径不一致

对 `D:\Maps\DotA v6.83d.w3x` 解包文件与运行日志的交叉验证结果如下：

1. **物品定义（`File00000369.xxx` & `File00000465.xxx`）**：
   - 铁树枝干对应的物品 ID 为 `I03D`、`I04G`、`I0CU`。
   - `[I04G]` 的 `Art` 字段为：`ReplaceableTextures\CommandButtons\BTNIronwoodbranch.blp`
   - `[I0CU]` 的 `Art` 字段为：`ReplaceableTextures\CommandButtonsDisabled\DISBTNIronwoodbranch.blp`
2. **地图脚本多面板表（`File00000808.xxx` 即 `war3map.j` 第 92596 行）**：
   - `G00[GO0]` 映射表中，将 `I04G`（整数 `1227895879`）和 `I0CU`（`1227899733`）映射到了：
     `"ReplaceableTextures\\CommandButtons\\BTNNatureTouchGrow.blp"`
3. **Hook 触发链路断裂**：
   - `war3hook.cpp` 在 `HASH_MULTIBOARD_SET_ITEM_ICON`（第 26752–26800 行）拦截 JASS 多面板设图标函数时，拿到的 `rawPathStr` 是 `BTNNatureTouchGrow.blp`，并将其入队给 `iconConvertRequestThread`（第 49619–49673 行）。
   - 但商店与英雄背包实际加载的是 `BTNIronwoodbranch.blp`；游戏中只要玩家或单位未用到该自然之触图标，`BTNNatureTouchGrow.blp` 就从未进入游戏 `HTEXTURE` 与 `CGxDevice` 缓存（`D3dxHook2.log` 实测未出现 `btnnaturetouchgrow`）。
   - `iconConvertRequestThread` 调用 `findRealD3DTextureByPath` 重试 40 次均返回空，转换直接失败。

### 5.2 次要原因：`war3hook.cpp` 自身检索逻辑的三处局限

即使路径一致，`findRealD3DTextureByPath`（第 57931–58032 行）和 `saveTextureAsPng`（第 58124–58190 行）也存在漏检风险：

1. **单块 64KB `HTEXTURE` 堆段扫描**：`findRealD3DTextureByPath` 仅以 `g_blpLastStartHandle & 0xFFFF0000` 为基址向上扫描一个 64KB Storm 堆块。若图标分配在更早创建的其他 64KB 堆块中，遍历就会遗漏。
2. **设备缓存只查 `g_war3GxDevices1` 忽略 `g_war3GxDevices2`**：`doSomeThingsBeforeCallGameGxDeviceCreateResult` 将纹理按路径前缀分流到 `g_war3GxDevices1` 和 `g_war3GxDevices2` 两个集合，而 `findRealD3DTextureByPath` 回退遍历时只查了 `g_war3GxDevices1`。
3. **格式与后端限制**：`saveTextureAsPng` 仅导出 `D3DFMT_A8R8G8B8` (21) 和 `D3DFMT_X8R8G8B8` (22) 纹理，若游戏以 OpenGL 模式运行会直接跳过。

### 5.3 修复建议（分析参考）

1. **直接 Hook 纹理创建/解码点或从物品 ID 查实际 `Art` 路径**：对商店/装备图标，除监听 `MultiboardSetItemIcon` 外，可在 `CSimpleButton::SetTexture` 或 `GxDeviceCreateResult` 阶段直接记录所有 `CommandButtons\BTN...`（及 `DISBTN...`）纹理句柄与路径映射，或对 `I04G`/`I0CU` 等已知别名做规范化映射。
2. **补全设备缓存遍历**：在 `findRealD3DTextureByPath` 中同时遍历 `g_war3GxDevices1` 与 `g_war3GxDevices2`（并记录所有出现过的 `HTEXTURE` 高 16 位段基址），避免因分流或跨 64KB 块导致漏检。

---

## 6. x32dbg 内存断点与篡改验证指南（1.26.0.6401）

> `war3.exe` 为 32 位进程，请使用 **x32dbg** 附加运行中的 `war3.exe`（非 x64dbg）。

1. **查看商店/装备/2D 头像加载路径与替换图标**：
   - 在符号/反汇编窗口定位 `game.dll+0x60E090`（`CSimpleButton::SetTexture`）下硬件/软件断点。
   - 断下后查看栈顶参数 `[esp+4]`（`const char* texturePath`），即可看到诸如 `ReplaceableTextures\CommandButtons\BTNIronwoodbranch.blp`。
   - **内存修改验证**：在数据窗口跟随 `[esp+4]` 指针地址，直接将字符串改写为另一个已存在的图标路径（如 `ReplaceableTextures\CommandButtons\BTNClawsOfAttack.blp`），按 `F9` 继续运行，即可看到对应商店/背包按钮实时变成目标图标。
2. **查看并验证禁用态图标（DISBTN）派生**：
   - 在 `game.dll+0x3207A0`（`CommandButtonDisabledArtPath`）下断点，单步执行至 `0x320846` 附近，可观察到引擎拼接出 `DISBTN...` 路径并分别提交给状态 `0x15` 与 `0x16`。
3. **验证 BLP1 JPEG 的 BGRA 内存通道布局**：
   - 在 `game.dll+0x78B2C0`（`BLP1_DecodeJPEG`）下断点，执行到 `ijlRead` (`call 0x78B62E`) 返回后，查看输出像素缓冲区内存：每 4 字节依次为 `[B, G, R, A]`。
   - **内存修改验证**：在数据窗口把某像素的 Byte 0（B）与 Byte 2（R）互换后继续运行，游戏中图标对应位置会出现红蓝反转；或在 `game.dll+0x5295A8`（`GxDeviceCreateResult`）处观察 `pSurface + 0x34` 指向的 `IDirect3DTexture*`，验证 `D3DFMT_A8R8G8B8` 格式与 `war3hook.cpp` 读显存结果完全一致。

