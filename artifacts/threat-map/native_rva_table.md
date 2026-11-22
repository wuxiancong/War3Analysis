# game.dll natives — pathing / vision (all versions)

Resolved via name-string xrefs + registration (`mov ecx, native` / documented overrides from llm-mcp & eat-tree).  
Source scripts: `scan_threat_natives.py`, `resolve_natives_from_xrefs.py`.

| Version | IsTerrainPathable | IsLocationVisibleToPlayer | IsUnitVisible | IsUnitFogged | IsUnitMasked | IsUnitDetected | GetLocalPlayer | GetLocationZ | GetDestructableLife | EnumDestructablesInRect |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1.0.17.5988 | `0x2DC5C0` | `0x2CDCC0` | `0x2C60D0` | `0x2C6E20` | `0x2C7020` | `0x2C6B40` | `0x2CC8E0` | `0x2AD910` | `0x2BC8C0` | `0x2BCF40` |
| 1.0.20.6048 | `0x2DC5C0` | `0x2CDCC0` | `0x2C60D0` | `0x2C6E20` | `0x2C7020` | `0x2C6B40` | `0x2CC8E0` | `0x2AD910` | `0x2BC8C0` | `0x2BCF40` |
| 1.20.4.6074 | `0x2DC6E0` | `0x2CDDE0` | `0x2C61F0` | `0x2C6F40` | `0x2C7140` | `0x2C6C60` | `0x2CCA00` | `0x2ADA30` | `0x2BC9E0` | `0x2BD060` |
| 1.21.0.6263 | `0x2DFCB0` | `0x2D13B0` | `0x2C97C0` | `0x2CA510` | `0x2CA710` | `0x2CA230` | `0x2CFFD0` | `0x2B1000` | `0x2BFFB0` | `0x2C0630` |
| 1.22.0.6328 | `0x3B7440` | `0x3C2BE0` | `0x3C0D90` | `0x3C0FA0` | `0x3C1020` | `0x3C0F20` | `0x3B6080` | `0x3BA2D0` | `0x3BDB30` | `0x3BDD30` |
| 1.23.0.6352 | `0x3B0790` | `0x3C4900` | `0x3C2AB0` | `0x3C2CC0` | `0x3C2D40` | `0x3C2C40` | `0x3B7DA0` | `0x3BBFF0` | `0x3BF850` | `0x3BFA50` |
| 1.24.1.6374 | `0x3B4D50` | `0x3CA3C0` | `0x3C8570` | `0x3C8780` | `0x3C8800` | `0x3C8700` | `0x3BC5E0` | `0x3C18B0` | `0x3C5310` | `0x3C5510` |
| 1.24.4.6387 | `0x3B4E10` | `0x3CA480` | `0x3C8630` | `0x3C8840` | `0x3C88C0` | `0x3C87C0` | `0x3BC6A0` | `0x3C1970` | `0x3C53D0` | `0x3C55D0` |
| 1.25.1.6397 | `0x3B40A0` | `0x3C9710` | `0x3C78C0` | `0x3C7AD0` | `0x3C7B50` | `0x3C7A50` | `0x3BB930` | `0x3C0C00` | `0x3C4660` | `0x3C4860` |
| 1.26.0.6401 | `0x3B42D0` | `0x3C9940` | `0x3C7AF0` | `0x3C7D00` | `0x3C7D80` | `0x3C7C80` | `0x3BBB60` | `0x3C0E30` | `0x3C4890` | `0x3C4A90` |
| 1.27.0.52240 | `0x1E8440` | `0x1E7DE0` | `0x1E8E80` | `0x1E8640` | `0x1E8B00` | `0x1E8580` | `0x1E3150` | `0x1E3260` | `0x1E1F70` | `0x1E0140` |

Related (trees, from eat-and-cut doc): `EnumWidgetsInRect` / `GetWidgetWorldPos` — see `dota-6.83d-eat-and-cut-tree-reverse.md` §3.4.
