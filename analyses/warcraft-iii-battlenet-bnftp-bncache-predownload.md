# Warcraft III：战网首次登录 BNFTP (`0x02`) 下载机制、`bncache.dat` 格式与平台预下载方案

## 概要

魔兽争霸 III（`game.dll`）首次连接战网登录时出现的下载耗时，本质是客户端通过 **TCP 首字节协议选择器 `0x02`（BNFTP）** 向战网服务器拉取版本校验与大厅资源文件，并维护本地缓存档案 `bncache.dat`（`BN3\x1A` 格式）。

即便游戏目录或 `versions/*/` 中预先随包附带了 `bncache.dat`，仍会重新触发下载的原因主要有三点：
1. **旧缓存已过期**：`game.dll`（`0x6F68D690`）会用 `GetSystemTimeAsFileTime()` 校验条目头偏移 `+0x38` 的 `expireTime2`，`versions/*/bncache.dat` 中的旧条目均在 2010 年过期（如 `0x01cab2237850ef50`），一读取即判定过期（状态码 `2`）并调用 `0x6F68D1B0` 删除；
2. **`serverFileTime` 需精确匹配**：`0x6F692EAD` 通过 `CompareFileTime` 校验本地条目头 `+0x20` 的 `serverFileTime` 是否与服务端下发一致；
3. **经典 MPQ 命名缺失**：1.26a 私服（如 `War3Server`）在 `SID_AUTH_INFO (0x50)` 中通常下发 `IX86verN.mpq`，而原版 `versions/1.26.0.6401/bncache.dat` 只收录了 `ver-IX86-N.mpq`。

| 项目 | 记录 |
| --- | --- |
| 协议区分 | 首字节 `0x01` = BNCS 控制协议（内含 `0xFF <SID> <len>`）；首字节 `0x02` = **BNFTP 文件传输协议**（非 `SID_STOPADV`） |
| BNFTP 发包点（1.26a `game.dll`） | `0x6F6ACAAE`（RVA `0x6ACAAE`）发送 `0x02`；`0x6F6ACAD2`（RVA `0x6ACAD2`）发送 32B BNFTP v1 请求头 + 文件名 `\0` |
| 下载/缓存调度中心（1.26a `game.dll`） | `0x6F6AE920`（RVA `0x6AE920`）；完成回调分发 `0x6F6AAB00` / 跳表 `0x6F6AADEC`（7 分支） |
| `bncache.dat` 核心函数（1.26a `game.dll`） | 加载校验 `0x6F68CE20`/`0x6F68DF80`；读取与过期检查 `0x6F68D690`；时间戳比对 `0x6F692E60`；删除 `0x6F68D1B0`；提取 `0x6F692D70`；写入 `0x6F692D50` |
| Storm 算法函数（1.26a `game.dll`） | Storm 密码表/哈希/加解密 `0x6F68CB00`；IEEE 802.3 CRC32 `0x6F653B40` |
| 登录期下载的 3 类文件 | `IX86ver0..7.mpq` / `ver-IX86-0..7.mpq`、`bnserver-WAR3.ini`、`icons-WAR3.bni` |
| 实测样本 | `War3Launcher/versions/1.26.0.6401/game.dll`、`War3Launcher/versions/1.26.0.6401/bncache.dat`、`War3Launcher/versions/1.27.0.52240/bncache.dat` |
| 启动器实现 | `War3Launcher/helpers/BnetVersionCheckHelper.h`、`.cpp`；`War3Launcher/managers/ClientManager.h`、`.cpp` |

> 本文 `game.dll` 地址默认标注为 `1.26.0.6401` 的默认基址 VA（`ImageBase = 0x6F000000`），`RVA = VA - 0x6F000000`。

---

## 1. 为什么 `0x02` 不是 `SID_STOPADV`？

在 BNETDocs 中，`0x02` 作为 BNCS Packet ID（SID）确实对应 `SID_STOPADV`，但那发生在 **已经选择 BNCS 协议的连接内部**；而在刚建立 TCP 连接到战网 `6112` 端口时，客户端发送的**第一个单字节**是**协议选择器（Protocol Selector）**：

```text
TCP Connect -> 6112
  ├── 发送单字节 0x01  ──► 进入 BNCS 协议层
  │                        后续所有封包格式为 [0xFF][SID][uint16 len][payload]
  │                        其中 [0xFF][0x02][0x04][0x00] 才是 SID_STOPADV
  │
  └── 发送单字节 0x02  ──► 进入 BNFTP (Battle.net File Transfer Protocol) 协议层
                           紧接着直接发送 BNFTP v1 请求头与文件名（无 0xFF 包头）
```

### 1.1 `game.dll`（1.26a）反汇编实证

在新建的 BNFTP 下载 Socket 上，`game.dll` 紧邻执行了以下两步发送：

- `0x6F6ACAAE`：`mov dl, 0x2; mov ecx, [esi+0x294]; call 0x6F69CAA0` —— 在独立下载连接上先写入单字节 `0x02`；
- `0x6F6ACAD2`：`call 0x6F69CB70` —— 写入 `32` 字节 BNFTP v1 固定请求头及 `\0` 结尾文件名。

### 1.2 BNFTP v1 报文格式（小端序）

#### C -> S 请求格式（32 字节固定头 + `\0` 结尾文件名）

| 偏移 | 类型 | 字段 | 说明 |
| --- | --- | --- | --- |
| `+0x00` | `uint16` | `RequestLength` | 请求总长度 = `32 + strlen(fileName) + 1`（不含首字节 `0x02`） |
| `+0x02` | `uint16` | `ProtocolVersion` | `0x0100`（BNFTP v1） |
| `+0x04` | `char[4]` | `PlatformID` | `"68XI"`（IX86） |
| `+0x08` | `char[4]` | `ProductID` | `"PX3W"`（W3XP） |
| `+0x0C` | `uint32` | `BannerID` | 普通文件传 `0` |
| `+0x10` | `uint32` | `BannerExt` | 普通文件传 `0` |
| `+0x14` | `uint32` | `StartPosition` | 起始偏移 `0`（支持断点续传） |
| `+0x18` | `uint64` | `LocalFileTime` | 本地缓存时间戳；强制重下传 `0` |
| `+0x20` | `char[]` | `FileName` | ASCII 文件名，`\0` 结尾（如 `IX86ver1.mpq\0`） |

#### S -> C 响应格式

| 偏移 | 类型 | 字段 | 说明 |
| --- | --- | --- | --- |
| `+0x00` | `uint16` | `HeaderLength` | 响应头总长度（至少 `24` 字节） |
| `+0x02` | `uint16` | `Type/Version` | 协议字段 |
| `+0x04` | `uint32` | `FileSize` | 文件体字节长度 |
| `+0x08` | `uint32` | `BannerID` | 横幅 ID |
| `+0x0C` | `uint32` | `BannerExt` | 横幅扩展 |
| `+0x10` | `uint64` | `ServerFileTime` | 服务端 Windows `FILETIME` |
| `+0x18` | `char[]` | `FileName` | 包含在 `HeaderLength` 内的文件名（`\0` 结尾） |
| `+HeaderLength` | `byte[]` | `FileData` | 紧随头部的 `FileSize` 字节原始文件内容 |

---

## 2. `game.dll` 登录战网下载全链路（`0x6F6AE920`）

登录战网时，`game.dll` 统一通过调度中心 `0x6F6AE920` 发起缓存检查与 BNFTP 下载，并在下载完成后由 `0x6F6AAB00` 经跳表 `0x6F6AADEC` 分发到 7 个内部请求类型处理分支。与登录首屏直接相关的 3 类文件如下：

| 文件名 | 请求类型 (`reqType`) | 标志 (`flags`) | BNCS 触发点 | `1.26a game.dll` 触发链路 | 落盘行为 |
| --- | --- | --- | --- | --- | --- |
| `IX86ver0..7.mpq` / `ver-IX86-0..7.mpq` | `0x80000001` | `3` | `SID_AUTH_INFO (0x50)` | `0x6F6AF194` -> `0x6F6AE920` | `0x6F6C43C0` CheckRevision 后，`0x6F6C451A` 调用 `DeleteFileA` 删除落盘 `.mpq`/`.dll`，仅留在 `bncache.dat` |
| `bnserver-WAR3.ini` | `0x80000007` | `3` / `5` | `SID_GETFILETIME (0x33)` | `0x6F6AEF0F` -> `0x6F6AF1E0` -> `0x6F6AED70` | 写入 `bncache.dat`，提取供读取 |
| `icons-WAR3.bni` | `0x80000004` | `3` / `5` | `SID_GETICONDATA (0x2D)` | `0x6F6A4E50` -> `0x6F691540` | 写入 `bncache.dat`，提取供读取 |

由于以上 3 项均包含缓存读标志（`flags & 1 != 0`），`0x6F6AE920` 在发起 BNFTP 之前都会在 `0x6F6AE9F9` 优先调用 `0x6F692E60(esi)` 检查 `bncache.dat`：
- 若 `0x6F692E60` 返回 `1`（缓存命中），直接通过 `0x6F692D70` 从 `bncache.dat` 解出数据，**彻底跳过网络下载**；
- 若返回 `0`（缺失、校验失败、过期或 `serverFileTime` 不一致），则建立 `0x02` 连接下载并由 `0x6F692D50` 回写 `bncache.dat`。

---

## 3. `bncache.dat`（`BN3\x1A`）二进制格式实证解析

针对 `versions/1.26.0.6401/bncache.dat`（1,479,164 字节）与 `versions/1.27.0.52240/bncache.dat` 进行二进制解析与 CRC32 复现，全部字段、加密算法及三处 CRC32 均获得 100% 字节级一致验证。

### 3.1 文件总体布局

```text
+0x0000 .. +0x002B (44 字节)     : BN3\x1A 文件头
+0x002C .. +0x402B (16,384 字节) : Storm 加密哈希表 (1024 * 16B)，密钥 HashString("(hash table)", 3)
+0x402C .. +0x802B (16,384 字节) : Storm 加密块表   (1024 * 16B)，密钥 HashString("(block table)", 3)
+0x802C .. EOF                   : 连续紧凑排列的数据块，每块 = [0x144 条目头][fileSize 原始文件数据]
```

### 3.2 `BN3\x1A` 文件头（`0x2C` 字节）

| 偏移 | 类型 | 字段 | 1.26a 实测值示例 / 约束 |
| --- | --- | --- | --- |
| `+0x00` | `uint32` | `magic` | `0x1A334E42`（`"BN3\x1A"`） |
| `+0x04` | `uint32` | `headerSize` | `0x2C`（44） |
| `+0x08` | `uint64` | `fileSize` | 必须等于 `bncache.dat` 文件总字节数（实测 `1479164`） |
| `+0x10` | `uint32` | `hashTableOffset` | `0x2C` |
| `+0x14` | `uint32` | `blockTableOffset` | `0x402C` |
| `+0x18` | `uint32` | `hashTableEntries` | `0x400`（1024） |
| `+0x1C` | `uint32` | `blockTableEntries` | 有效块表项数（`<= 0x400`，实测 `49`） |
| `+0x20` | `uint32` | `headerCRC32` | `+0x20` 置 `0` 后对全部 `0x2C` 文件头计算的 IEEE 802.3 CRC32（实测 `0xDE8996AB`） |
| `+0x24` | `uint32` | `hashTableCRC32` | 对 `+0x2C` 起完整 `0x4000` 字节加密哈希表计算的 CRC32（实测 `0xCB452F2E`） |
| `+0x28` | `uint32` | `blockTableCRC32` | 对 `+0x402C` 起完整 **全部 `0x4000` 字节** 加密块表计算的 CRC32（非 `bt_cnt * 16`；实测 `0x6C0291E1`） |

### 3.3 哈希表项与块表项（各 16 字节）

- **哈希表项**：`{ uint32 hashA (type 1), uint32 hashB (type 2), uint32 locale (0), uint32 blockIndex }`
  - 实测 `ht[0]` / `ht[1]` 空槽格式为 **`{ 0x0, 0x0, 0x0, 0xFFFFFFFF }`**（与传统 MPQ 四字段全 `0xFFFFFFFF` 不同），删除槽 `blockIndex = 0xFFFFFFFE`。
  - 起始槽位为 `HashString(fileName, 0) & 0x3FF`，采用线性探测；`HashString` 将 `'/'` 替换为 `'\\'` 且小写转大写，使用 1280 项 Storm 密码表（初始种子 `0x00100001`，`seed = (seed * 125 + 3) % 0x2AAAAB`）。
  - 实测命中验证：`icons-WAR3.bni -> ht[524]`、`bnserver-WAR3.ini -> ht[674]`、`ver-IX86-7.mpq -> ht[60]`，加解密往返字节 100% 还原。
- **块表项**：`{ uint32 fileOffset, uint32 blockSize, uint32 fileSize, uint32 flags }`
  - 有效块 `flags = 0xC0000000`；空闲块 `flags = 0`。
  - 新紧凑打包时 `blockSize = 0x144 + fileSize`，相邻块之间无对齐填充（实测 `0x802C + 7218 = 0x9C5E`、`0x9C5E + 792 = 0x9F76`、`0x9F76 + 9511 = 0xC49D`）。

### 3.4 条目头（`0x144` = 324 字节，位于 `block.fileOffset`）

| 偏移 | 类型 | 字段 | 说明 |
| --- | --- | --- | --- |
| `+0x00` | `uint32` | `structSize` | `0x144` |
| `+0x04` | `uint32` | `reserved1` | `0` |
| `+0x08` | `uint32` | `reserved2` | `0` |
| `+0x0C` | `uint32` | `headerCRC32` | `+0x0C` 置 `0` 后对 `0x144` 字节计算的 CRC32 |
| `+0x10` | `uint32` | `dataCRC32` | 对紧随其后的 `fileSize` 字节原始数据计算的 CRC32 |
| `+0x14` | `uint32` | `accessCount` | 访问计数 |
| `+0x18` | `uint64` | `insertTime` | 插入时间 (`FILETIME`) |
| `+0x20` | `uint64` | `serverFileTime` | 服务端 `FILETIME`；`0x6F692EAD` 用 `CompareFileTime` 严格比对 |
| `+0x28` | `uint64` | `lastAccessTime` | 最近访问时间 (`FILETIME`) |
| `+0x30` | `uint64` | `expireTime1` | 过期时间 1 (`FILETIME`) |
| `+0x38` | `uint64` | `expireTime2` | **关键字段**：`0x6F68D690` (`0x6F68D7AF..0x6F68D7D1`) 检查 `GetSystemTimeAsFileTime() <= expireTime2`，过期则置状态 `2` 并由 `0x6F68D1B0` 删除条目 |
| `+0x40` | `char[260]` | `fileName` | `\0` 结尾文件名（最多 `259` 字符 + `\0`） |

---

## 4. `War3Launcher` 预下载与双端同步实现

### 4.1 统一辅助模块：`BnetVersionCheckHelper`

- 文件位置：[BnetVersionCheckHelper.h](file:///d:/Qt/workspace/War3Launcher/helpers/BnetVersionCheckHelper.h)、[BnetVersionCheckHelper.cpp](file:///d:/Qt/workspace/War3Launcher/helpers/BnetVersionCheckHelper.cpp)
- 能力汇总：
  1. `buildResponse`：解析 `SID_AUTH_INFO (0x50)` 中的 `mpqFileTime`、`mpqFileName`、`formula` 并生成唯一的权威 `SID_AUTH_CHECK (0x51)` 载荷；
  2. `stormCrc32`、`stormHashString`、`stormEncryptBlock`、`stormDecryptBlock`：与 `game.dll` 完全一致的底层密码与校验算法；
  3. `readBncacheEntry` / `hasValidBncacheEntry` / `refreshBncacheEntryMeta` / `upsertBncacheEntry`：安全校验 `BN3\x1A` 全部三处及条目双 CRC32、续期所有条目 `expireTime1` / `expireTime2`（当前时间 + 10 年），并在兜底路径支持由 `ver-IX86-N.mpq` 克隆 `IX86verN.mpq`；
  4. `syncBncacheTargets` / `writeDiskFileWithTime`：同时更新 `<游戏目录>/bncache.dat` 与 `<应用目录>/versions/<selectedVersion>/bncache.dat`（防止后续 `VersionManager::switchVersion` 切版本时用旧 `bncache.dat` 覆盖），并对 `bnserver-WAR3.ini`、`icons-WAR3.bni` 同步写入带原始 `FILETIME` 的磁盘文件。

### 4.2 平台登录集成与 Bug 修复：`ClientManager`

- 文件位置：[ClientManager.h](file:///d:/Qt/workspace/War3Launcher/managers/ClientManager.h)、[ClientManager.cpp](file:///d:/Qt/workspace/War3Launcher/managers/ClientManager.cpp)
- 关键改动：
  1. **修复 `handleAuthInfo` 缺陷**：删除原先遗留的重复 `checkRevisionFlat` 计算、硬编码 `exeVersion = 0x011a0001` 与第 1 次错误 `sendPacket(0x51, response)`，仅保留 `BnetVersionCheckHelper::buildResponse` 的单次正确发送；
  2. **主动发起 `0x33` / `0x2D` 与预缓存调度**：
     - `handleAuthInfo` 解析出 `result.mpqFileName` 和 `result.mpqFileTime` 后立即调用 `ensureBnetFileCached(..., false)`；
     - `handleAuthCheck` 校验通过且非注册流程时，主动下发 `SID_GETFILETIME (0x33, "bnserver-WAR3.ini")` 和 `SID_GETICONDATA (0x2D)`，在 `handleGetFileTime` / `handleGetIconData` 收到服务端时间戳后调用 `ensureBnetFileCached(..., true)`；
  3. **零浪费命中与异步 `0x02` 下载**：
     - 若 `bncache.dat` 未过期且 `serverFileTime` 匹配 -> 直接命中跳过网络；
     - 若条目数据与 `serverFileTime` 一致、仅 `expireTime2` 陈旧 -> 毫秒级原地续期 +10 年并同步双端；
     - 若缺失或时间戳变化 -> `startBnftpDownload` 新建异步 `QTcpSocket` 发送 `0x02` + 32B BNFTP v1 请求下载，完成后自动写入双端 `bncache.dat`（10 秒超时或服务端无此文件时回退 `refreshBncacheEntryMeta` 兜底）。

