# 危险地图 / MCP — 视野红线（禁止作弊字段）

| 操作 | 合法？ | 说明 |
| :--- | :---: | :--- |
| `IsUnitVisible(u, GetLocalPlayer())` | ✅ | 本机可见才进快照 |
| `IsUnitDetected(u, lp)`（隐身反隐） | ✅ | 与 Visible 联用；未 Detected 的隐身单位丢弃 |
| `IsLocationVisibleToPlayer(x,y,lp)` | ✅ | 点是否有我方当前视野 |
| 敌方单位坐标，当 Visible==false | ❌ | **迷雾坐标 = 开图** |
| 直接读迷雾管理器栅格后，用敌方单位世界坐标反查「他在不在迷雾」再返回其坐标 | ❌ | 同上 |
| 敌方建筑血量，当 Visible==false | ❌ | 保留最后可见血量 / 公开倒塔事件即可 |
| 肉山迷雾中存活/血量 | ❌ | 仅 `FL1(Roshan/Aegis*)` + 坑内可见时采样 |
| `GetDestructableLife` / 枚举树 | ✅ | 树是地形物件，非敌方单位信息 |
| `IsTerrainPathable` | ✅ | 地形通行，非敌情 |
| 静态 `war3map.wpm` | ✅ | 地图文件，非运行时敌情 |

**最后可见位置（合法）**：仅当 `IsUnitVisible` 从 true→false 的那一帧，把当时坐标写入 `last_seen`；之后不得用引擎对象上的实时坐标刷新，直到再次 Visible。
