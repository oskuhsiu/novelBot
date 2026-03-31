---
name: power_dynamic_updater
description: 權力博弈監測 - 自動更新勢力間的緊張值
---

# Power Dynamic Updater

監測劇情中影響勢力關係的事件，調整 SQLite 勢力資料庫的 `tension` 值。

## 事件→張力變動表

| 事件類型 | 張力變動 |
|----------|----------|
| 殺死對方成員 | +15~30 |
| 偷取資源 | +10~20 |
| 公開對抗 | +20~40 |
| 結盟宣布 | -20~-40 |
| 領土佔領 | +30~50 |
| 談判成功 | -10~-30 |
| 背叛 | +40~60 |

## 閾值觸發

| 條件 | 觸發 | 效果 |
|------|------|------|
| tension ≥ 90 | OPEN_WAR | 全面攻擊、關閉和平途徑 |
| tension ≥ 70 | COLD_WAR | 邊境巡邏加強、商業禁運、間諜增加 |
| tension ≤ 20 | ALLIANCE | 合併選項、共同敵人出現 |

## 執行步驟

1. **事件分析**：從章節識別影響勢力的事件（actor/target/faction/impact）
2. **計算張力**：依事件表計算各勢力對的 tension 變動，上限 100
3. **閾值檢查**：達到閾值時記錄觸發事件，通知後續章節需包含對應衝突
4. **更新資料庫**：
   ```bash
   .venv/bin/python tools/faction_query.py --proj {proj} update-tension FAC_001 FAC_002 {new_tension}
   .venv/bin/python tools/faction_query.py --proj {proj} add-rel FAC_001 FAC_002 --status "Hostile" --tension {N} --history "..."
   ```
