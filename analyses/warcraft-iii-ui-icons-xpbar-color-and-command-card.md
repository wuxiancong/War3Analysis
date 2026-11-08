# 魔兽争霸3 UI：命令图标颜色、经验条与命令卡修复

日期：2026-11-08  
范围：`War3Angular` replay-3d 控制台图标 / 经验条 / 技能面板

## 1. 图标为何偏蓝？原版是红的吗？

### 结论

- **不是**游戏运行时对图标做“染红”特殊处理才变红。
- `ReplaceableTextures\CommandButtons\BTNStatUp.blp` 用 `mdx-m3-viewer` BLP1 正确解码后，平均色约为 **RGB(77,62,23) 金黄/深金**，不是红，也不是蓝。
- 网页里偏蓝的 `BTNStatUp.png`（约 RGB(2,77,243)）来自 **错误的 BLP→PNG 导出（R/B 通道对调）**：金黄色 `(R,G,B)` 被写成 `(B,G,R)` 后就会变成青蓝。

JPG 类 BLP 在引擎里按 **BGRA** 存像素；`mdx-m3-viewer` 的 JPG 解码注释写明强制 BGR→RGB。War3Bot 侧部分 PNG 未做这次交换，导致命令按钮发蓝。

### 对照

| 资源 | 错误 PNG (War3Bot) | 正确 BLP 解码 |
|---|---|---|
| BTNStatUp | 青蓝加号 | 金黄加号 |
| BTNSkillz | 洗白金色 | 偏红棕书本色 |

人族经验条 fill（`UI\Feedback\XpBar\human-bigbar-fill.blp`）本身是**灰阶高光条**；游戏内用 UI 顶点色/混合乘上**紫色**。网页曾用 `hue-rotate(245deg)` 硬转色相，观感发蓝且不像原生。

## 2. 经验条一直在走

`replay-timeline.ts` 旧公式：

```ts
xpPercent: Math.round(((t % 60000) / 60000) * 100)
```

用录像时间模 60 秒伪造进度，故即使未获得经验也会一直涨。录像事件里通常只有 `Data:LevelN=`，**没有精确当前经验值**，因此改为：

- 等级 < 25 → `xpPercent = 0`
- 等级 ≥ 25 → `100`

并换用从 `war3.mpq` 提取的 `human-bigbar-fill` / `human-xpbar-border`，紫色 multiply 混合。

## 3. 多出来的 U 加号

命令卡默认常驻 `statup`（快捷键 U）+ `BTNStatUp`。对齐 WC3/DotA：

- **属性附加**：仅 `attrBonusLevel > 0` 时显示（快捷键按 DotA 习惯改为 T）
- **学习技能**：仅 `unspentSkillPoints > 0` 时显示书本图标

## 4. 图标被裁切

`.wc3-slot .ico` 使用了 `object-fit: cover`，会裁掉 64×64 BTN 自带金属边框。改为：

- `object-fit: fill`
- `image-rendering: pixelated`
- 略减 inventory/command grid gap

## 5. 修复落点

- 资源：`public/assets/wc3/ui/icons/cmd/BTNStatUp.png` 等（BLP 重解码）
- 经验条贴图：`bar-xp-fill.png` / `bar-xp-border.png`（来自 `UI\Feedback\XpBar\`）
- 逻辑：`replay-timeline.ts` xpPercent；`replay-3d.component.ts` 命令卡条件显示与 CSS

## 6. 技能/物品图标批量纠偏（2026-11-08 续）

错误的整图 PNG 重编码曾损坏资源；已从 `War3Launcher/deploy/msvc/images` 恢复，再用 **pngjs 选择性像素纠偏**：

- 仅当像素满足 `B > R+28` 且偏蓝时交换该像素 R/B
- 保留金色/红色区域（避免剑刃风暴金刃被整图 swap 毁掉）
- 结果：`A05G` 气旋由青蓝→金黄；`I02O` 速度之鞋由蓝→红
- 学习技能（O）恢复为**始终显示**，无点数时灰显

槽位居中：去掉 `button` 默认 padding，flex 居中 + `object-fit: contain`。
