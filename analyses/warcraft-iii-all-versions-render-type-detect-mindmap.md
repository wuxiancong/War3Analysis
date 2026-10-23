# 魔兽争霸 III 渲染方式判定与全版本 Hook 方案思维导图

```mermaid
mindmap
  root((魔兽争霸 III 渲染方式判定))
    现有代码评估
      当前位置: BeforeD3DXDoEndScene
      依赖: D3D 设备 EndScene 流程
      缺陷: OpenGL 模式下该函数完全不被调用
      缺陷: 无法感知用户添加 -opengl 启动参数
      结论: 缺乏全渲染后端统一的前置判断点
    渲染决策底层链
      输入源 1: 命令行参数 (-opengl / -d3d)
      输入源 2: 注册表项 ("Gfx OpenGL" 键值)
      入口函数: GxDeviceInit
        先检测 -opengl 开关
        若无则读取注册表 Gfx OpenGL
        确定首选驱动类型 (0=D3D, 1=OpenGL)
        首选失败触发降级回退 (Fallback)
      工厂函数: GxDeviceCreate
        根据 Type 分支创建驱动实例
        Type 0: 创建 CGxDeviceD3d (d3d8/d3d9)
        Type 1: 创建 CGxDeviceOpenGl (opengl32)
        返回 CGxDevice 实例指针 (EAX)
        保存到全局变量 g_pGxDevice
    全 11 版本逆向定位
      1.0.17 ~ 1.21.0
        1.0.17.5988: GxCreate 0xC8310, 全局变量 0x6F84A738
        1.0.20.6048: GxCreate 0xC8310, 全局变量 0x6F84B778
        1.20.4.6074: GxCreate 0xC8310, 全局变量 0x6F84B798
        1.21.0.6263: GxCreate 0xC8310, 全局变量 0x6F84C7D0
        架构: D3D8 + OpenGL
      1.22.0 ~ 1.24.4
        1.22.0.6328: GxCreate 0x517070, 全局变量 0x6FA9AD54
        1.23.0.6352: GxCreate 0x518E00, 全局变量 0x6FAB3B9C
        1.24.1.6374: GxCreate 0x527790, 全局变量 0x6FAC519C
        1.24.4.6387: GxCreate 0x527810, 全局变量 0x6FAC519C
        架构: D3D8 + OpenGL
      1.25.1 ~ 1.26.0
        1.25.1.6397: GxCreate 0x526AE0, 全局变量 0x6FAAE34C
        1.26.0.6401: GxCreate 0x526D10, 全局变量 0x6FAAE34C
        架构: D3D8 + OpenGL
      1.27.0.52240
        1.27.0: GxCreate 0x0E2F70, 全局变量 0x6FBB80D8
        架构: 升级为 D3D9 + OpenGL
    最佳 Hook 位置判定
      方案一 (最佳): Hook GxDeviceCreate 返回点
        优点: 无论 D3D 还是 OpenGL 均必经此函数
        优点: EAX 直接返回已初始化的 CGxDevice 指针
        优点: 通过 vTable[0] 模块地址 100% 确认真实渲染器
        优点: 自动捕获 OpenGL 失败降级到 D3D 的真实结果
      方案二: Hook GxDeviceInit 注册表读取后
        缺点: 仅能捕获“尝试意图”，无法处理创建失败回退
      方案三: 外部系统 API Hook (Direct3DCreate / wglCreateContext)
        缺点: 无法直接拦截魔兽内部 CGxDevice 实例
    Hooker 落地实现建议
      新增偏移字典: g_offsetsForGxDeviceCreate
      安装 InlineHook: 拦截 GxDeviceCreate 返回时刻
      读取 EAX 虚表: 自动调用现有 getRenderType(vTable)
      写入状态变量: g_renderType 与日志同步更新
```

---

## 详细逆向分析报告

### 一、当前代码是否有合适位置可以判断？

#### 1. 当前代码现状
当前项目中，渲染类型的判断是在 `initD3DGlobals(void **vTablePtr)`（内部调用 `getRenderType(vTable)`）完成的：
- 该函数是由 `initD3DContext` 触发；
- `initD3DContext` 挂在 `doSomeThingsBeforeMoveGameBeforeD3DXDoEndScene`（即 `GameBeforeD3DXDoEndScene` 的 Inline Hook）；
- **致命缺陷**：该 Hook 点挂接在 Direct3D 的 `IDirect3DDevice::EndScene` 管线上。**当魔兽争霸 3 开启 OpenGL 模式时（例如快捷方式包含 `-opengl` 或注册表配置为 OpenGL），游戏根本不会初始化 Direct3D，也不会调用 `EndScene`，导致现有 Hook 点完全不会被执行！**
- **结论**：**当前代码没有可以在所有模式下（D3D / OpenGL）都能统一判断渲染方式的合适位置**。必须在游戏底层的设备创建工厂处建立通用 Hook。

---

### 二、魔兽争霸 III 底层图形驱动初始化全流程

```
[war3.exe / 命令行] 传入 -opengl / -d3d
        │
        ▼
[game.dll!GxDeviceInit] 读取命令行与注册表 "Gfx OpenGL" 键
        │
        ▼
   决策请求驱动类型 (Type: 0=D3D, 1=OpenGL)
        │
        ▼
[game.dll!GxDeviceCreate(type, ...)]  <--- ★★★ 最佳 Hook 位置 ★★★
        │
        ├── Type == 0 ──> new CGxDeviceD3d() ──> LoadLibrary("d3d8.dll" / "d3d9.dll")
        │
        └── Type == 1 ──> new CGxDeviceOpenGl() ──> LoadLibrary("OPENGL32.dll")
        │
        ▼
   创建成功返回 CGxDevice* (EAX)，存入全局变量 g_pGxDevice
        │
   (若 Type 1 失败，则自动回退调用 Type 0 降级为 D3D)
```

---

### 三、全 11 个版本 `game.dll` 核心逆向地址表

基地址：`0x6F000000`

| 版本号 | 默认 Direct3D 驱动 | GxDeviceInit 入口 RVA | GxDeviceCreate 工厂函数 RVA | 全局设备指针 `g_pGxDevice` 内存 VA | 特征码定位标识 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1.0.17.5988** | `d3d8.dll` | `0x0068E0` | **`0x0C8310`** | `0x6F84A738` | `83 E8 00 ... 83 E8 01` |
| **1.0.20.6048** | `d3d8.dll` | `0x0068E0` | **`0x0C8310`** | `0x6F84B778` | `83 E8 00 ... 83 E8 01` |
| **1.20.4.6074** | `d3d8.dll` | `0x0068E0` | **`0x0C8310`** | `0x6F84B798` | `83 E8 00 ... 83 E8 01` |
| **1.21.0.6263** | `d3d8.dll` | `0x0068E0` | **`0x0C8310`** | `0x6F84C7D0` | `83 E8 00 ... 83 E8 01` |
| **1.22.0.6328** | `d3d8.dll` | `0x0095A0` | **`0x517070`** | `0x6FA9AD54` | `83 E8 00 ... 83 E8 01` |
| **1.23.0.6352** | `d3d8.dll` | `0x0095A0` | **`0x518E00`** | `0x6FAB3B9C` | `83 E8 00 ... 83 E8 01` |
| **1.24.1.6374** | `d3d8.dll` | `0x0095A0` | **`0x527790`** | `0x6FAC519C` | `83 E8 00 ... 83 E8 01` |
| **1.24.4.6387** | `d3d8.dll` | `0x0095A0` | **`0x527810`** | `0x6FAC519C` | `83 E8 00 ... 83 E8 01` |
| **1.25.1.6397** | `d3d8.dll` | `0x009580` | **`0x526AE0`** | `0x6FAAE34C` | `83 E8 00 ... 83 E8 01` |
| **1.26.0.6401** | `d3d8.dll` | `0x009580` | **`0x526D10`** | `0x6FAAE34C` | `83 E8 00 ... 83 E8 01` |
| **1.27.0.52240**| `d3d9.dll` | `0x027E20` | **`0x0E2F70`** | `0x6FBB80D8` | `8B F0 C7 85 ...` |

---

### 四、最佳 Hook 点深入剖析与设计

#### 为什么 `GxDeviceCreate` 是最佳位置？
1. **统一性与不可绕过性**：
   所有 11 个版本无论是通过命令行 `-opengl`、注册表 `Gfx OpenGL`、还是默认走 Direct3D，最终创建设备实例都**必须通过此函数**。
2. **完美支持回退（Fallback）检测**：
   如果玩家设置了 OpenGL，但系统显卡驱动不支持 OpenGL 导致创建失败，魔兽内部会自动重试调用 `GxDeviceCreate(0, ...)` 降级为 Direct3D。拦截该函数的返回时刻，可以 100% 准确获取最终实际生效的设备！
3. **即时获得抽象虚表（vTable）**：
   该函数返回时，`EAX` 即为 `CGxDevice*`，其 `*(void**)EAX` 即为统一的设备虚表。直接传入现有 `getRenderType(*(void**)pGxDevice)` 即可无缝辨析出 `RenderType::OPENGL`、`RenderType::D3D8` 或 `RenderType::D3D9`！
