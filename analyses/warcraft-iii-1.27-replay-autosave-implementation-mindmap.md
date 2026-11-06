# 录像自动保存 — 思维导图

```mermaid
mindmap
  root((录像自动保存))
    原生机制
      LastReplay.w3g 局末覆盖
      autosaveReplay 注册表
        Replay/Autosaved 命名
      TempReplay.w3g 局中缓冲?
      SaveReplayPanel 手动
    Launcher现状
      handleGameExit 复制
      nameMode 时间/玩家/英雄
      saveIntervalMinutes UI
      间隔逻辑未接
    实现路径
      A 局末复制 P0
      B 同步官方 autosave P0.5
      C 快照 TempReplay P1
      D Hook Finalize 定时 P1/P2
      E 自合成 w3g P3
    工具
      Ghidra 12.1.4 War3_127
      REA 6.8.0 最新
      versions/1.27 game.dll
```

## 决策简图

```text
saveIntervalMinutes
        │
        ├─ 0 游戏结束 ──► A (±B) 复制 LastReplay
        │
        └─ N 分钟 ──────► 先验证 TempReplay 可播?
                              │
                              ├─ 可 ──► C 进程外轮询快照
                              │         └─ 再升级 D Hook 原生保存
                              └─ 否 ──► 必须 D（找 Finalize）或放弃间隔
```
