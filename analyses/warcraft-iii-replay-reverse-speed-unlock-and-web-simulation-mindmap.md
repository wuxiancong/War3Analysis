# 思维导图：魔兽争霸3录像逆向、解锁8x速度与网页模拟回放

```mermaid
mindmap
  root((魔兽争霸3录像机制与模拟))
    录像实现逻辑 W3G
      本质原理
        非视频/非逐帧快照
        基于锁步机制的操作指令流 (Lockstep Actions Stream)
        本地引擎依据伪随机种子重新模拟运行整场比赛
      二进制文件结构
        48字节文件头 (Header)
        zlib 压缩数据块 (Data Blocks 8KB)
        核心数据包
          0x00 玩家与地图初始化
          0x1E / 0x1F 时间片 TimeSlot (100ms 推进)
          0x20 玩家退出
          0x22 / 0x23 同步校验点 Checksum
      动作包结构 (同网络协议)
        0x10 无目标命令/技能 (Stop, Hold, 技能)
        0x11 点目标命令 (Move/A地，含 X, Y 坐标)
        0x12 单位目标命令 (攻击/技能，含 X, Y, 目标ID)
        0x16 框选与选择单位
        0x17 编队操作
        0x60 聊天内容 (ChatText)
        0x6B DotA 专用 GameCache 同步数据
    解锁最大 8x 速度
      受限根因
        UI限制: CReplayPanel 仅预置 8 个离散档位 (1/4x 到 8x)
        逻辑限制: SpeedUp 函数达到最大索引后禁用按钮并置灰
        引擎限制: 暴雪针对旧单核 CPU 性能保护，避免特效与寻路卡死
      全版本主要函数偏移 (RVA / VA)
        1.0.17 / 1.0.20: Switch 0x1505D3 | SpeedUp 0x150400 | SpeedDown 0x1504A0 | 全局 0x6F87125C/0x6F87229C
        1.20.4: Switch 0x1505E3 | SpeedUp 0x150410 | SpeedDown 0x1504B0 | 全局 0x6F8722BC
        1.21.0: Switch 0x150643 | SpeedUp 0x150470 | SpeedDown 0x150510 | 全局 0x6F873334
        1.22.0: Switch 0x3636D0 | SpeedUp 0x363610 | SpeedDown 0x3582F0 | 全局 0x6FAA2FFC
        1.23.0: Switch 0x364C50 | SpeedUp 0x364B90 | SpeedDown 0x359870 | 全局 0x6FABBE4C
        1.24.1: Switch 0x364D10 | SpeedUp 0x364C50 | SpeedDown 0x359930 | 全局 0x6FACD44C
        1.24.4: Switch 0x364DD0 | SpeedUp 0x364D10 | SpeedDown 0x3599F0 | 全局 0x6FACD44C
        1.25.1: Switch 0x364060 | SpeedUp 0x363FA0 | SpeedDown 0x358C80 | 全局 0x6FAB65F4
        1.26.0: Switch 0x364290 | SpeedUp 0x3641D0 | SpeedDown 0x358EB0 | 全局 0x6FAB65F4
        1.27.0: Switch 0x3A0683 | SpeedUp 0x3A7300 | SpeedDown 0x3A73B0 | 全局 0x6FBE4238
      x64dbg解锁方案
        方案A (推荐内存验证): 跟踪全局指针 pReplayContext，直接修改 TimeScale 浮点倍率或 Tick 循环步长
        方案B (UI上限补丁): NOP 掉 SpeedUp 函数内的上限判定，开放更高移位索引
    网页端模拟实现
      方案对比
        100% 引擎复刻: 极难，需完全移植 JASS 虚拟机与复杂寻路碰撞
        3D 轨迹/动作还原 (当前 War3Angular 方案): 完全可行且体验极佳
      仅有同步数据 (.dat) 能否实现录像?
        完全可行!
        .dat 本质是 Qt qCompress 压缩的紧凑 JSON 格式
        包含 durationMs, heroId 和完整的动作矩阵 [t, a, x, y, target, ext, order]
        网页端利用 Three.js / mdx-m3-viewer 绑定英雄模型
        按时间轴插值位移 (0x11) 与播放 Run/Attack (0x12) 动画
    录像 (.w3g) 转换为同步数据 (.dat)
      可行性
        100% 可行，w3g 的 0x1F 数据包与 War3Bot 拦截的数据结构同源同构
      拖入网页转换流程
        1. 网页前端监听文件拖入事件 (Drag & Drop)
        2. JS 读取 ArrayBuffer 解析 48 字节 Header
        3. pako.inflate 解压缩各 8KB 数据块
        4. 遍历解压流累加 0x1F 的 TimeIncrement 得到绝对时间戳
        5. 提取 0x11 (移动), 0x12 (攻击), 0x60 (聊天), 0x6B (同步)
        6. 组装为目标 JSON 格式并直接存入内存驱动 3D 录像重放
```

