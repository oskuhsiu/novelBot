# Skills 說明文檔

Genesis Engine 共有 32 個 Skills，分為四大類。

## Foundation（基石類）- 7 個

負責專案初始化和基礎設定。

| Skill | 功能 |
|-------|------|
| `style_setter` | 設定風格（語言、語氣、參考作家） |
| `world_builder` | 建立世界觀地圖 |
| `character_forge` | 創建角色（含雙軌制設定） |
| `faction_forge` | 創建勢力和外交關係 |
| `power_architect` | 設計力量體系 |
| `item_smith` | 根據風格生成道具 |
| `character_secret_seeder` | 生成角色隱藏動機 |

## Structure（結構類）- 8 個

負責大綱、節奏和結構規劃。

| Skill | 功能 |
|-------|------|
| `pacing_calculator` | 計算本章應涵蓋的內容範圍 |
| `chapter_beater` | 拆解章節為節拍(beats) |
| `beat_optimizer` | 優化節拍的張力曲線 |
| `weight_balancer` | 分配內容權重 |
| `outline_architect` | 設計全書大綱 |
| `atlas_navigator` | 驗證角色移動路徑 |
| `dungeon_generator` | 自動生成密境/副本結構 |
| `schema_re_architect` | 架構逆向與重鑄，借用外部劇情骨架 |

## Execution（執行類）- 8 個

負責實際的正文撰寫和潤色。

| Skill | 功能 |
|-------|------|
| `scene_writer` | 撰寫場景正文 |
| `dialogue_director` | 優化對話 |
| `sensory_amplifier` | 增強五感描寫 |
| `cliffhanger_generator` | 設計章節結尾懸念 |
| `chaos_engine` | 隨機生成意外事件 |
| `technique_elaborator` | 根據速度指針展開技能描寫 |
| `item_interactor` | 根據速度指針展開道具使用 |
| `dialogue_subtext_editor` | 為對話加入潛台詞 |

## Memory（記憶類）- 9 個

負責狀態追蹤和一致性維護。

| Skill | 功能 |
|-------|------|
| `lorekeeper` | 管理長期記憶(lore_bank) |
| `status_monitor` | 更新角色即時狀態 |
| `logic_auditor` | 檢查邏輯衝突 |
| `consistency_validator` | 驗證設定一致性 |
| `loop_closer` | 追蹤和關閉伏筆 |
| `emotional_wave_analyzer` | 監控情感波段 |
| `power_dynamic_updater` | 更新勢力緊張度 |
| `identity_validator` | 根據派系調整對話風格 |
| `world_rule_validator` | 驗證世界規則一致性 |

---

## Skill 連動機制

### 章節寫作流程

```
1. pacing_calculator    → 計算本章範圍
2. chapter_beater       → 拆解節拍
3. beat_optimizer       → 優化張力
4. weight_balancer      → 分配權重
5. scene_writer         → 撰寫正文
   ├── dialogue_director    (對話場景)
   ├── technique_elaborator (戰鬥場景)
   └── item_interactor      (道具使用)
6. sensory_amplifier    → 潤色五感
7. cliffhanger_generator → 設計結尾
```

### 維護流程

```
1. lorekeeper           → 記錄事件
2. status_monitor       → 更新狀態
3. logic_auditor        → 檢查衝突
4. consistency_validator → 驗證一致
5. loop_closer          → 伏筆管理
6. emotional_wave_analyzer → 情感分析
7. power_dynamic_updater → 勢力更新
```

## 速度指針影響

`pacing_pointer` 影響最大的 Skills：

| pacing | technique_elaborator | item_interactor | scene_writer |
|--------|---------------------|-----------------|--------------|
| 0.1 | 數千字對決描寫 | 完整道具操作 | 極度細節 |
| 0.5 | 200-500字 | 標準描寫 | 平衡 |
| 1.0 | 一句帶過 | 僅提名稱 | 快速推進 |
