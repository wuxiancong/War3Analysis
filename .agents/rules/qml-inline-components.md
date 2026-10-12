---
trigger: always_on
---

# Qt 5.15 QML 属性与内联组件

## 已确认的崩溃原因

Qt 5.15.2 下，`components/RoomComponent.qml` 新增的 `CmDraftHeroRow` 把 `childrenRect.width` 赋给了 `Row.implicitWidth`。该版本中 `Row.implicitWidth` 是只读属性，不应由 QML 代码赋值。这个无效赋值在内联组件创建和绑定初始化期间触发访问冲突，转储落在 `Qt5Qml!QQmlObjectCreator::setupBindings`。

最小 QML 复现验证了该布局在包含此赋值时会崩溃；移除赋值后，Qt 5.15.2 运行时正常退出。`Row` 会根据子项自动计算隐式宽度，因此依赖内容宽度的 Flickable 可直接读取 `row.implicitWidth`。

## 后续修改规则

- 赋值前先确认目标 QML 类型的属性在项目使用的 Qt 版本中可写；不要假定 `implicitWidth`、布局属性或只读属性可以手动设置。
- `Row` 等布局项应优先使用其自动计算的隐式尺寸；只有在属性明确可写且布局需要时才显式赋值。
- Qt 崩溃栈若落在 `QQmlObjectCreator::setupBindings` 或对象创建路径，应优先检查最近新增的 QML 属性赋值、绑定和内联组件声明。
- 对此类问题至少用项目相同 Qt 版本做运行时最小复现。`qmlformat` 或 `qmlcachegen` 通过只能证明语法/缓存编译通过，不能代替运行时验证。
