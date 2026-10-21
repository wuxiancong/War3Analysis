# 魔兽争霸3 帧率限制解锁 Hook 审计与架构优化思维导图

```mermaid
mindmap
  root((魔兽争霸3 FPS 限制解锁 Hook 体系))
    现状诊断与审计结论
      缺少吗？
        机制完整不缺少
        已覆盖软件帽、D3D呈现、OpenGL呈现、配置上限、空设备保护
      多余吗？
        存在多余与未启用代码
        Direct3DPresentImmed 队列未调用且与 PresentParam 冲突
        Direct3DWindowedSync 与 PresentParam 功能重叠
        Direct3DLockableFlag 与 PresentParam 功能重叠
      位置正确吗？
        核心 Hook 位置完全正确
        Software_FpsKeepFlag 全版本特征对齐
        Direct3DPresentParam 区分 CreateDevice 与 Reset 极佳
        Direct3DNullDevice__ 精准拦截 0xECB54 空指针
        OpenGLSwapInterval__ 位置正确但汇编裸函数保护需优化
    8个函数逐项评估
      1. hookGameSoftware_FpsKeepFlag
        类别: 核心必选
        目标: 清除 64 FPS 软件轮询帽
        指令: and eax 0xFB -> and eax 0xFF
        适用: 1.0.17~1.21(war3.exe), 1.22~1.27(game.dll)
      2. hookGameDirect3DPresentParam
        类别: 核心必选 (1.27 D3D9)
        目标: 重写 D3DPRESENT_PARAMETERS
        逻辑: CreateDevice 时写入 IMMEDIATE(0x80000000)
        安全: Reset 保持原参数 彻底防止驱动死锁挂起
      3. hookGameDirect3DNullDevice__
        类别: 核心必选 (1.27 防御型)
        目标: 防御切分辨率空设备解引用
        位置: RVA 0xECB54 (TestCooperativeLevel)
        效果: 避免 0xC0000005 崩溃
      4. hookGameMaxFpsDefaultTo10000
        类别: 推荐保留 (1.22~1.27)
        目标: 防止设置重置后将 maxfps 限制为 200
        指令: 立即数 200 改为 10000
      5. hookGameOpenGLSwapInterval__
        类别: 核心必选 (全版本 -opengl)
        目标: wglSwapIntervalEXT(0)
        注意: 裸函数汇编需做完整的 caller-saved 寄存器保护
      6. hookGameDirect3DPresentImmed
        类别: 多余 / 死代码
        问题: installAllHooks 中未加入任务队列 实际未运行
        建议: 移除或废弃
      7. hookGameDirect3DWindowedSync
        类别: 多余 (功能重复)
        问题: 内部打补丁 已被 PresentParam 统一处理
        建议: 移除
      8. hookGameDirect3DLockableFlag
        类别: 多余 (功能重复)
        问题: 内部清 Flags 已被 PresentParam 统一处理
        建议: 移除
    精简与优化拓扑
      基础逻辑层
        hookGameSoftware_FpsKeepFlag (破除 64FPS 软件限制)
      图形呈现层
        D3D9 模式 (1.27)
          hookGameDirect3DPresentParam (安全呈现)
          hookGameDirect3DNullDevice__ (防崩溃)
        OpenGL 模式 (全版本)
          hookGameOpenGLSwapInterval__ (优化后汇编)
      引擎配置层
        hookGameMaxFpsDefaultTo10000 (防 200 帧重置)
```
