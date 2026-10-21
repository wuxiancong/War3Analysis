# Warcraft III 1.27 分辨率切换崩溃：思维导图

```mermaid
mindmap
  root((分辨率切换崩溃))
    分析范围
      Warcraft III 1.27.0.52240
      game.dll SHA256 e04d1716...09d0c3a
      Hook RVA 0xECFF0
      原始字节确认读取设备并调用 EndScene
      REA 目标文件哈希已核对
      REA 函数分析请求超时
      暂无运行时崩溃转储
    普通焦点切换
      窗口焦点或最小化恢复
      通常保留同一设备
      仍可能发生设备丢失
      独占全屏 Alt+Tab 也可能触发 Reset
    选项中更改分辨率
      呈现参数发生变化
      进入 D3D9 Reset 或恢复流程
      Reset 前释放自有纹理和状态块
      设备可能丢失；指针为空仍是待证假设
      客户区大小和渲染资源变化
    优先排查的代码风险
      GetCreationParameters 早于设备空值检查
        oldWndProc 为空时会逐帧重试
        设备指针是否会变空需要运行时确认
      callback 返回不会跳过 trampoline
        trampoline 重放 mov eax [ecx+584]
        从偏移 +6 继续执行 push eax
        mov ecx [eax] 解引用设备 vtable
        call [ecx+A8] 调用 EndScene 槽
        RVA 0xECB54 的保护是另一处 hook
    次级候选原因
      Reset 或设备丢失窗口仍执行自定义绘制
      Reset 前释放资源但未见统一的恢复门闩
      naked stub 保存通用寄存器和标志，不保存 x87/SIMD
      渲染线程上增加回调与日志工作
    卡住但没有 Dump
      VEH 只在异常分发时运行，不监视线程卡死
      死循环、锁等待和驱动阻塞不会自动触发异常
      HRESULT 设备丢失不是 SEH 异常
      过滤器只处理有限的异常码
      AddVectoredExceptionHandler 返回值未检查
      MiniDumpWriteDump 结果未检查
      VEH 文件在 hook DLL 同目录
      CrashMonitor 等待异常事件，不是 hang watchdog
      卡死时需要进程外完整 dump 和线程栈
    跨版本判断
      版本表中 RVA 不同
      多个版本共用 C++ callback
      优先检查共享渲染和 Reset 副作用
      1.27 原始字节不能推广到其它版本
    验证方法
      捕获 EIP、ECX、renderer+584 和线程栈
      记录 Reset 前后及 cooperative-level HRESULT
      每次只禁用一种 callback 副作用做 A/B
      安全分支设计前核实目标版本反汇编
    修复方向
      COM 调用前检查 renderer 和设备指针
      空设备时不得继续进入原始 trampoline 路径
      将 HWND 初始化与逐帧渲染分离
      设备状态未就绪时禁止绘制
      Reset 成功后再恢复自有资源
      核实并遵循 FP/SIMD 保存约定
```

**阅读说明：** 风险控制流由源码和目标样本原始字节确认；真正的故障地址及 Reset 时设备指针状态，仍待 dump 或受控运行日志确认。
