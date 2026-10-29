# Warcraft III：战网登录「密码不正确」对话框逆向

## 概要

弹出文案「你所提供的密码是不正确的，请重试。」（英文本「The password you provided is incorrect. Please try again.」）**不是硬编码在 `game.dll` / `Storm.dll` / `war3.mpq` 明文里**，而是通过字符串表键 `ERROR_ID_BADPASSWORD` 做本地化解析后，再交给通用 Glue 对话框函数显示。

| 项目 | 记录 |
| --- | --- |
| 对话框键 | `ERROR_ID_BADPASSWORD` |
| 内部结果码（UI event `+0x18`） | `0x1B`（十进制 27） |
| 协议侧常见来源 | `SID_AUTH_ACCOUNTLOGONPROOF`（`0x54`）S→C，`Status == 0x02`（Incorrect password）经客户端映射后进入 UI |
| 1.27 主处理函数 | `FUN_2C8E90`（RVA `0x2C8E90`） |
| 1.27 字符串解析 | RVA `0x90B00`（`ecx`=键，`edx`=缓冲，栈上传 `0x200`） |
| 1.27 弹窗显示 | RVA `0x29E8F0`（`ecx`=样式类，`edx`=已解析文本） |
| 样本 | `War3Launcher/versions/*/game.dll`；1.27 SHA-256 `E04D1716603C075EB0C8E1E21CF1093A664ADC5249EFAB396BFA08D7B09D0C3A` |
| 工具 | Capstone + PE 交叉引用；REA 6.8.0 / Ghidra 12.1.4（本次 Ghidra provider Java 探测超时，结论以静态 xref/反汇编为准） |
| 产物 | `artifacts/battlenet-badpassword/` |

> 所有地址均为相对 `game.dll` ImageBase 的 **RVA**（1.27 ImageBase = `0x6F000000`）。运行时 VA = `game.dll基址 + RVA`。不要把 RVA 当成文件偏移；字符串文件偏移见下表 `strFile`。

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
      mov ecx, &"ERROR_ID_BADPASSWORD"
      call StringResolve   ; 0x90B00  -> 本地化正文写入栈缓冲
      call DialogShow      ; 0x29E8F0 -> 弹出错误对话框
```

### 1.27 关键指令（账号路径）

`FUN_2C8E90` 内 `status == 0x1B` 分支：

```x86asm
; RVA 0x2C8FF7
push    0x200
lea     edx, [ebp-0x204]
mov     ecx, 0x6F97E838          ; "ERROR_ID_BADPASSWORD"
call    0x6F090B00               ; StringResolve
mov     ecx, [esi+0x254]
push    1
push    0x6F950D90               ; 空串
call    0x6F0B0450
...
push    1
push    4
push    0
push    esi
push    0x0C
lea     edx, [ebp-0x204]         ; 已解析的本地化文本
mov     ecx, 1
call    0x6F29E8F0               ; DialogShow（弹窗）
```

### `FUN_2C8E90` 状态码映射（`event+0x18`，1-based 跳转表）

| status | 字符串键 |
| --- | --- |
| `0x01` | `NETMESSAGE_PASSWORDCHANGE` |
| `0x0C` | `ERROR_ID_DISCONNECT` |
| `0x0E` | `ERROR_ID_NOTCONNECTED` |
| `0x18` | `ERROR_ID_BADSERVER` |
| `0x19` | `ERROR_ID_UNKNOWNACCOUNT` |
| `0x1A` | `ERROR_ID_UNSUPPORTEDACCOUNT` |
| **`0x1B`** | **`ERROR_ID_BADPASSWORD`** |

同一结果码 `0x1B` 也出现在**加入带密码房间**等路径（例如 `FUN_2D4740`），因此 hook 时要区分「账号登录」与「房间密码」。

---

## 2. 推荐 Hook 点（按目的）

| 目的 | 推荐位置（1.27 RVA） | 说明 |
| --- | --- | --- |
| **只拦账号登录错误弹窗** | `0x2C8FF7` 或函数入口 `0x2C8E90` | 入口可过滤 `status==0x1B`；case 点可直接吞掉弹窗 |
| **替换/改写提示文案** | `0x90B00` 返回后 / DialogShow 前 | 缓冲已填好本地化串，可改写再放行 |
| **统一吞掉所有 BADPASSWORD 弹窗**（含房间密码） | `0x29E8F0` 且校验文本键或调用栈 | 调用点很多（约 184 处），需配合调用栈或前置标志 |
| **协议层提前处理** | 解析 `SID_AUTH_ACCOUNTLOGONPROOF` 的 S→C `Status` | 启动器 `war3hook.cpp` 已有 `0x02 = 密码错误` 日志语义，可在此做异常分流，不必等 UI |

Hook 注意：

1. 对 **`.text` 入口/case** 做 inline hook，不要 hook 字符串数据 RVA `0x97E838`。
2. `StringResolve(0x90B00)` 约定：`__fastcall` 风格（`ecx`=键指针，`edx`=输出缓冲，`[esp+4]=容量`），成功返回 `1`。
3. `DialogShow(0x29E8F0)`：`ecx` 为对话框类别（账号错误路径传 `1`），`edx` 为宽/窄字符缓冲（由本地化表填入）。

---

## 3. 全版本偏移矩阵（`game.dll` RVA）

扫描条件：`mov ecx, imm32` 且 `imm32` 指向 `ERROR_ID_BADPASSWORD\0`。每版本约 6 处引用；**账号登录主路径**取「`mov ecx` 后紧跟 `call StringResolve`，且随后出现 `push 0x0C` + `DialogShow`」的那一处（下表 `AccountCase`）。

| 版本 | AccountFunc | AccountCase (`mov ecx`) | StringResolve | DialogShow | 字符串 RVA | 字符串文件偏移 |
| --- | --- | --- | --- | --- | --- | --- |
| 1.0.17.5988 | `0x22E530` | `0x22E736` | `0x0C32E0`* | `0x203A40` | `0x80AE60` | `0x80AE60` |
| 1.0.20.6048 | `0x22E530` | `0x22E736` | `0x0C32E0`* | `0x203A40` | `0x80BEA0` | `0x80BEA0` |
| 1.20.4.6074 | `0x22E640` | `0x22E846` | `0x0C32E0` | `0x203B50` | `0x80BEA0` | `0x80BEA0` |
| 1.21.0.6263 | `0x2317E0` | `0x2319E6` | `0x0C32E0` | `0x206D10` | `0x80CFAC` | `0x80CFAC` |
| 1.22.0.6328 | （ESP 帧，入口未标） | `0x56855D` | `0x5B96D0` | `0x54D1F0` | `0x94F4B0` | `0x94F4B0` |
| 1.23.0.6352 | （ESP 帧） | `0x56A44D` | `0x5BB350` | `0x54EFA0` | `0x9635F0` | `0x9635F0` |
| 1.24.1.6374 | （ESP 帧） | `0x578E3D` | `0x5C9D40` | `0x55D930` | `0x973B58` | `0x973B58` |
| 1.24.4.6387 | （ESP 帧） | `0x578EBD` | `0x5C9DF0` | `0x55D9B0` | `0x973B70` | `0x973B70` |
| 1.25.1.6397 | （ESP 帧） | `0x577FED` | `0x5C9420` | `0x55CC80` | `0x961A38` | `0x961A38` |
| 1.26.0.6401 | （ESP 帧） | `0x57821D` | `0x5C9650` | `0x55CEB0` | `0x961A38` | `0x961A38` |
| **1.27.0.52240** | **`0x2C8E90`** | **`0x2C9003`** | **`0x90B00`** | **`0x29E8F0`** | **`0x97E838`** | **`0x97DC38`** |

\*早期版本同键的其它 xref 也走 `0x0C32E0`。  
1.22–1.26 账号处理函数使用 `esp` 局部缓冲（`lea edx,[esp+…]`），无标准 `push ebp; mov ebp,esp` 序言；**稳妥 hook 点用 `AccountCase` / `StringResolve` / `DialogShow`**，不必强求函数入口。

### 1.27 全部 6 处 `ERROR_ID_BADPASSWORD` 引用

| xref RVA | 所属函数 | 场景（推断） |
| --- | --- | --- |
| `0x2C9003` | `0x2C8E90` | **账号登录**（主路径） |
| `0x2D4902` | `0x2D4740` | 加入游戏 / 房间密码 |
| `0x2D4A70` | `0x2D49D0` | 同类错误表 |
| `0x2D4BF7` | `0x2D4B60` | 同类错误表 |
| `0x2D9304` | `0x2D9160` | 另一 Glue 事件（创建/改密等相关） |
| `0x2DCD41` | `0x2DCC90` | 同类错误表 |

---

## 4. 与启动器现有逻辑的关系

`War3Launcher/hooker/war3hook.cpp` 在解析 `SID_AUTH_ACCOUNTLOGONPROOF` 时已将：

- `Status 0x00` → 登录成功  
- **`Status 0x02` → Incorrect password（密码错误）**

这与 UI 侧 `ERROR_ID_BADPASSWORD` / 内部码 `0x1B` 是同一失败语义的不同层。若要在「弹窗前」做异常处理，优先考虑：

1. 协议 hook：在 S→C `0x54` 看到 `0x02` 时置标志 / 改写 status；或  
2. UI hook：在 `FUN_2C8E90` 对 `0x1B` 分支短路，跳过 `0x29E8F0`。

---

## 5. 验证步骤

1. 附加调试器，在 `game.dll+0x2C9003`（1.27）下断，故意输错密码登录，确认命中。  
2. 单步进入 `0x90B00`，检查输出缓冲是否为中文「你所提供的密码是不正确的，请重试。」（视客户端语言包）。  
3. 再单步到 `0x29E8F0`，确认对话框出现。  
4. 换版本时用 `ERROR_ID_BADPASSWORD` 的 `mov ecx` xref 重定位，不要硬编码跨版本绝对 VA。

---

## 6. 限制与未尽事项

- 本地化正文未在 `war3.mpq` / `War3Patch.mpq` 明文中检出（可能压缩存储或位于其它 locale 包）；键名已确认。  
- REA/Ghidra 反编译本次因 Java provider 超时未出伪代码；汇编与 xref 已人工核对。  
- 未做实机 hook 验证；协议 status `0x02` → UI `0x1B` 的精确映射函数可继续向下追 BNCS 层。  
- 思维导图见同目录 `warcraft-iii-battlenet-badpassword-dialog-mindmap.md`。
