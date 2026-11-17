# Warcraft III：战网「密码不正确」对话框逆向与拦截

| 项 | 值 |
| --- | --- |
| 分析模型 | Composer |
| 分析目的 | 定位「你所提供的密码是不正确的，请重试。」弹窗链路，并在 war3hook 中阻止弹出 |
| 命名方式 | `GameBnetBadPassDialog__`（与 `GameBnetLoginEmailPanel_` 等长 24） |
| 分析时间 | 2026-11-17 |

## 概要

弹出文案「你所提供的密码是不正确的，请重试。」（英文本「The password you provided is incorrect. Please try again.」）**不是硬编码在 `game.dll` / `Storm.dll` / `war3.mpq` 明文里**，而是通过字符串表键 `ERROR_ID_BADPASSWORD` 做本地化解析后，再交给通用 Glue 对话框函数 `DialogShow` 显示。

| 项目 | 记录 |
| --- | --- |
| 对话框键 | `ERROR_ID_BADPASSWORD` |
| 内部结果码（UI event `+0x18`） | `0x1B`（十进制 27） |
| 协议侧常见来源 | `SID_AUTH_ACCOUNTLOGONPROOF`（`0x54`）S→C，`Status == 0x02` |
| 1.27 主处理函数 | `FUN_2C8E90`（RVA `0x2C8E90`） |
| 1.27 字符串解析 | RVA `0x90B00`（`ecx`=键，`edx`=缓冲，栈上传 `0x200`） |
| 1.27 弹窗显示 | RVA `0x29E8F0`（`ecx`=样式类，`edx`=已解析文本，`ret 14h`） |
| Hook 符号 | `GameBnetBadPassDialog__`（`War3Launcher/hooker`） |
| 样本 | `War3Launcher/versions/*/game.dll`；1.27 SHA-256 `E04D1716603C075EB0C8E1E21CF1093A664ADC5249EFAB396BFA08D7B09D0C3A` |
| 产物 | `artifacts/battlenet-badpassword/` |

> 所有地址均为相对 `game.dll` ImageBase 的 **RVA**（ImageBase = `0x6F000000`）。运行时 VA = `game.dll基址 + RVA`。

**结论（已落地）：** war3hook **原先没有**拦截该窗口；现已在 `DialogShow` 入口安装 `GameBnetBadPassDialog__`，仅当调用点前方 `0xA0` 字节内存在 `mov ecx, &"ERROR_ID_BADPASSWORD"` 时 `ret 14h` 吞掉弹窗（覆盖账号登录与房间密码等全部 6 处同源路径）。

---

## 1. 调用链（账号登录密码错误）

```
SID_AUTH_ACCOUNTLOGONPROOF (0x54) S->C
  Status = 0x02  (bnetdocs: Incorrect password)
        |
        v
BNCS / 连接状态机映射为 UI 结果码 0x1B
        |
        v
Battle.net Glue 事件分发  FUN_2D0DB0  (1.27)
  event+0x08 == 0x0B  ----call---->  FUN_2C8E90
        |
        v
FUN_2C8E90
  读取 event+0x18 作为 status
  status == 0x1B:
      mov ecx, &"ERROR_ID_BADPASSWORD"   ; B9 在 RVA 0x2C9002
      call StringResolve   ; 0x90B00
      call DialogShow      ; 0x29E8F0  ← Hook 点
```

### 1.27 关键指令（账号路径）

```x86asm
; RVA 0x2C8FF7
push    0x200
lea     edx, [ebp-0x204]
mov     ecx, 0x6F97E838          ; "ERROR_ID_BADPASSWORD"  (B9 @ 0x2C9002)
call    0x6F090B00               ; StringResolve
...
push    1
push    4
push    0
push    esi
push    0x0C
lea     edx, [ebp-0x204]
mov     ecx, 1
call    0x6F29E8F0               ; DialogShow（弹窗）
```

### `FUN_2C8E90` 状态码映射（`event+0x18`）

| status | 字符串键 |
| --- | --- |
| `0x01` | `NETMESSAGE_PASSWORDCHANGE` |
| `0x0C` | `ERROR_ID_DISCONNECT` |
| `0x0E` | `ERROR_ID_NOTCONNECTED` |
| `0x18` | `ERROR_ID_BADSERVER` |
| `0x19` | `ERROR_ID_UNKNOWNACCOUNT` |
| `0x1A` | `ERROR_ID_UNSUPPORTEDACCOUNT` |
| **`0x1B`** | **`ERROR_ID_BADPASSWORD`** |

---

## 2. Hook 实现：`GameBnetBadPassDialog__`

| 项 | 说明 |
| --- | --- |
| 挂钩类型 | `HookType::Other`（函数入口 5 字节） |
| 挂钩目标 | `DialogShow` 入口（非字符串数据区） |
| 过滤 | `isGameBnetBadPassDialog__Caller`：自 `retAddr-5` 向前扫 `0xA0`，匹配 `B9 <keyVA>` |
| 吞掉 | naked 桩 `ret 0x14`（各版本 DialogShow 均为 `ret 14h`，5 个栈参数） |
| 放行 | `jmp` 跳板执行原序言 |
| 键串 | 运行时在 `game.dll` 内精确查找 `ERROR_ID_BADPASSWORD\0`，缓存到 `g_gameBnetBadPassDialog__KeyAddress` |

### 特征码（三组，等长命名）

| 版本段 | `g_signForGameBnetBadPassDialog__` | 唯一命中 |
| --- | --- | --- |
| `< 1.22` | `55 8B EC 56 57 8B FA 85 FF 8B F1 0F 84 C2 01 00 00` | 是 |
| `1.22 ~ 1.26`（默认） | `56 57 8B FA 85 FF 8B F1 0F 84 DB 01 00 00` | 是 |
| `>= 1.27` | `55 8B EC 56 57 8B FA 8B F1 85 FF 0F 84 9E 01 00 00` | 是 |

`initializeSigns()`：`isHighWar3Version()` / `isLowerWar3Version()` 分别覆盖高低组；中间组保留 offsets 默认值。

### 符号一览（与 `GameBnetLoginEmailPanel_` 对齐）

- `g_offsetForGameBnetBadPassDialog__` / `g_offsetsForGameBnetBadPassDialog__` / `g_signForGameBnetBadPassDialog__`
- `g_currentBytesForCallGameBnetBadPassDialog__` / `g_originalBytesForCallGameBnetBadPassDialog__`
- `g_trampolinesForCallGameBnetBadPassDialog__`
- `g_originalGameBnetBadPassDialog__` / `GameBnetBadPassDialog__Func`
- `g_gameBnetBadPassDialog__ReturnAddress` / `g_gameBnetBadPassDialog__KeyAddress` / `g_gameBnetBadPassDialog__ReturnValue`
- `hookGameBnetBadPassDialog__` / `unhookGameBnetBadPassDialog__`
- `jumpWhenCallGameBnetBadPassDialog__` / `doSomeThingsBeforeCallGameBnetBadPassDialog__`
- `findGameBnetBadPassDialog__Key` / `isGameBnetBadPassDialog__Caller`

安装任务名：`Bnet: BadPassDialog__`（`war3hook.cpp`）。

---

## 3. 全版本偏移矩阵（`game.dll` RVA）

### 3.1 DialogShow / AccountCase / 字符串

| 版本 | DialogShow（Hook） | AccountCase (`B9`/`mov ecx`) | StringResolve | 字符串 RVA | 字符串文件偏移 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1.0.17.5988 | `0x203A40` | `0x22E735` | `0x0C32E0` | `0x80AE60` | `0x80AE60` |
| 1.0.20.6048 | `0x203A40` | `0x22E735` | `0x0C32E0` | `0x80BEA0` | `0x80BEA0` |
| 1.20.4.6074 | `0x203B50` | `0x22E845` | `0x0C32E0` | `0x80BEA0` | `0x80BEA0` |
| 1.21.0.6263 | `0x206D10` | `0x2319E5` | `0x0C32E0` | `0x80CFAC` | `0x80CFAC` |
| 1.22.0.6328 | `0x54D1F0` | `0x56855C` | `0x5B96D0` | `0x94F4B0` | `0x94F4B0` |
| 1.23.0.6352 | `0x54EFA0` | `0x56A44C` | `0x5BB350` | `0x9635F0` | `0x9635F0` |
| 1.24.1.6374 | `0x55D930` | `0x578E3C` | `0x5C9D40` | `0x973B58` | `0x973B58` |
| 1.24.4.6387 | `0x55D9B0` | `0x578EBC` | `0x5C9DF0` | `0x973B70` | `0x973B70` |
| 1.25.1.6397 | `0x55CC80` | `0x577FEC` | `0x5C9420` | `0x961A38` | `0x961A38` |
| 1.26.0.6401 | `0x55CEB0` | `0x57821C` | `0x5C9650` | `0x961A38` | `0x961A38` |
| **1.27.0.52240** | **`0x29E8F0`** | **`0x2C9002`** | **`0x90B00`** | **`0x97E838`** | **`0x97DC38`** |

> 注：旧文档中 AccountCase 曾写作 imm 操作数地址（如 `0x2C9003`）；现统一记 **`B9` 指令起点**。

### 3.2 每版本 6 处 `ERROR_ID_BADPASSWORD` → DialogShow 调用点

`mov ecx` RVA → `call DialogShow` RVA（距离 ≤ 151，Hook 回扫窗口 `0xA0` 足够）

| 版本 | 六处 `call DialogShow`（RVA） |
| --- | --- |
| 1.0.17.5988 | `0x21BE98`, `0x21CACC`, `0x227854`, `0x227DFD`, `0x22E7A6`, `0x22FAAA` |
| 1.0.20.6048 | `0x21BE98`, `0x21CACC`, `0x227854`, `0x227DFD`, `0x22E7A6`, `0x22FAAA` |
| 1.20.4.6074 | `0x21BFA8`, `0x21CBDC`, `0x227964`, `0x227F0D`, `0x22E8B6`, `0x22FBBA` |
| 1.21.0.6263 | `0x21F168`, `0x21FD9C`, `0x22AB34`, `0x22B0DD`, `0x231A56`, `0x232D5A` |
| 1.22.0.6328 | `0x56859C`, `0x59BA72`, `0x5A1BC7`, `0x5A5122`, `0x5A54AC`, `0x5A87C3` |
| 1.23.0.6352 | `0x56A48C`, `0x59D592`, `0x5A36E7`, `0x5A6C42`, `0x5A6FCC`, `0x5AA2E3` |
| 1.24.1.6374 | `0x578E7C`, `0x5ABF82`, `0x5B20D7`, `0x5B5632`, `0x5B59BC`, `0x5B8CD3` |
| 1.24.4.6387 | `0x578EFC`, `0x5AC032`, `0x5B2187`, `0x5B56E2`, `0x5B5A6C`, `0x5B8D83` |
| 1.25.1.6397 | `0x57802C`, `0x5AB662`, `0x5B17B7`, `0x5B4D12`, `0x5B509C`, `0x5B83B3` |
| 1.26.0.6401 | `0x57825C`, `0x5AB892`, `0x5B19E7`, `0x5B4F42`, `0x5B52CC`, `0x5B85E3` |
| 1.27.0.52240 | `0x2C9044`, `0x2D495C`, `0x2D4B06`, `0x2D4C5B`, `0x2D936E`, `0x2DCDA2` |

### 1.27 六处 xref 场景

| xref (`B9`) | DialogShow call | 所属函数 | 场景（推断） |
| ---: | ---: | ---: | --- |
| `0x2C9002` | `0x2C9044` | `0x2C8E90` | **账号登录** |
| `0x2D4901` | `0x2D495C` | `0x2D4740` | 加入游戏 / 房间密码 |
| `0x2D4A6F` | `0x2D4B06` | `0x2D49D0` | 同类错误表 |
| `0x2D4BF6` | `0x2D4C5B` | `0x2D4B60` | 同类错误表 |
| `0x2D9303` | `0x2D936E` | `0x2D9160` | 登录相关 Glue |
| `0x2DCD40` | `0x2DCDA2` | `0x2DCC90` | 同类错误表 |

---

## 4. DialogShow 序言差异

| 版本段 | 入口字节（Hook 改写前 5 字节起点） |
| --- | --- |
| ≤1.21 / 1.27 | `55 8B EC 56 57`（`push ebp; mov ebp,esp; push esi; push edi`） |
| 1.22~1.26 | `56 57 8B FA 85`（无 EBP 帧：`push esi; push edi; mov edi,edx; test edi,edi`） |

各版本函数尾均为 **`ret 14h`**。

---

## 5. 与协议层关系

`war3hook_proto.cpp` 解析 `SID_AUTH_ACCOUNTLOGONPROOF` 时：

- `Status 0x00` → 登录成功  
- **`Status 0x02` → Incorrect password（密码错误）**

与 UI 侧 `ERROR_ID_BADPASSWORD` / 内部码 `0x1B` 同义不同层。本 Hook 在 UI 层统一吞掉该弹窗；协议层仍可另做分流。

---

## 6. 验证步骤

1. 安装后日志应出现 `[game.dll] GameBnetBadPassDialog__ 钩子安装成功` 与键串地址。  
2. 故意输错密码登录：应打出 `🛡 [BadPassDialog] 拦截 ERROR_ID_BADPASSWORD 弹窗`，且不再出现该对话框。  
3. 其它非 BADPASSWORD 的 Glue 对话框应仍正常弹出。  
4. 换版本时以偏移表 + 特征码兜底；过滤逻辑不依赖绝对 VA。

---

## 7. 限制

- 吞掉后用户界面不再提示密码错误（符合「阻止弹出」需求）；如需仅静默模式生效，可在 `doSomeThingsBeforeCallGameBnetBadPassDialog__` 加 `isSilentMode()` 门闩。  
- 思维导图：`warcraft-iii-battlenet-badpassword-dialog-mindmap.md`。
