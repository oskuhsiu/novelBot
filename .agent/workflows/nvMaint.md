---
description: 維護記憶與設定檔同步
---

# /nvMaint - 維護記憶

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `mode` | ❌ | 維護模式 | `mode=full/light` |

### mode 參數說明
- `full`：完整維護所有設定檔（預設）
- `light`：僅更新 lore_bank + progress

## 使用範例

```
/nvMaint proj=霓虹劍仙
/nvMaint proj=霓虹劍仙 mode=light
```

## 執行步驟

### Step 1: 讀取最新章節
// turbo
讀取 `output/chapters/` 中最新完成的章節

### Step 2: 更新長期記憶（必執行）
更新 `memory/lore_bank.yaml`：

```yaml
更新項目:
  - events: 新增本章發生的事件
  - relationship_changes: 記錄關係變動
  - open_foreshadowing: 追蹤新埋設的伏筆
  - closed_foreshadowing: 標記已揭露的伏筆
  - world_facts: 新發現的世界規則
  - item_status: 物品狀態變動
  - permanent_changes: 永久性改變
```

### Step 2b: 更新情感記錄（必執行）
使用 `skill_emotional_wave_analyzer` 分析本章情感，更新 `memory/emotion_log.yaml`：

```yaml
更新項目:
  - chapters: 新增本章情感分析
    - tension_score: 本章張力值 (0-100)
    - primary_emotion: 主要情感類型
    - elements: 各元素強度
  - analysis: 更新整體統計
  - consecutive_tracking: 更新連續計數
  - buffer_suggestions: 如超過閾值則生成建議
```

### Step 3: 更新敘事進度（必執行）
更新 `config/narrative_progress.yaml`：

```yaml
更新項目:
  - meta.current_chapter: +1
  - meta.words_written: 累加字數
  - meta.last_updated: 今日日期
  - completed_chapters: 標記完成
```

### Step 4: 更新角色資料庫（mode=full）
更新 `config/character_db.yaml`：

```yaml
更新項目:
  已有角色:
    - current_state.location: 當前位置
    - current_state.health: 健康狀態
    - current_state.inventory: 物品變動
    - current_state.status_effects: 狀態效果
    
  新角色（如有）:
    - 使用 `skill_character_forge` 創建完整 base_profile
    - 使用 `skill_character_secret_seeder` 埋設隱藏動機
    - 初始化 current_state
```

### Step 5: 更新世界地圖（mode=full）
更新 `config/world_atlas.yaml`：

```yaml
更新項目:
  新區域/地點（如有）:
    - 使用 `skill_world_builder` 擴展世界觀
    - 確保與現有地圖連接
    - 設定危險等級
    - 列出可獲取資源
    - 描述威脅類型
    
  已有地點:
    - 更新控制勢力
    - 更新資源狀態
```

### Step 6: 更新勢力登記（mode=full）
更新 `config/faction_registry.yaml`：

```yaml
更新項目:
  新勢力（如有）:
    - 使用 `skill_faction_forge` 創建完整勢力定義
    - 設定成員列表
    - 初始化外交關係
    
  已有勢力:
    - 更新成員變動
    - 更新領土變動
    - 更新外交狀態
    
  外交矩陣:
    - 關係值調整
    - 新增關係記錄
```

### Step 6b: 更新勢力緊張度（mode=full）
使用 `skill_power_dynamic_updater` 自動分析本章事件對勢力關係的影響：
- 計算緊張度變化
- 檢查閾值觸發
- 更新 `faction_registry.yaml` 中的 `tension` 值

### Step 7: 更新力量體系（mode=full）
更新 `config/power_system.yaml`：

```yaml
更新項目:
  新能力（如有）:
    - 使用 `skill_power_architect` 擴展力量體系
    - 確保與現有體系郏輯自洽
    - 角色新獲得的技能
    
  新物品類別（如有）:
    - buff/道具
    - 建造圖紙
```

### Step 8: 更新物品目錄（mode=full）
更新 `config/item_compendium.yaml`：

```yaml
更新項目:
  新物品（如有）:
    - 使用 `skill_item_smith` 生成符合風格的道具定義
    - 名稱、類型、效果
    - 獲取來源
    - 當前持有者
    
  物品狀態變動:
    - 消耗/使用
    - 轉移/丟失
```

### Step 9: 輸出維護報告
// turbo
顯示維護摘要：
- 更新了哪些檔案
- 新增了多少條目
- 待處理事項提醒

## 維護優先級

| 優先級 | 類別 | 說明 |
|--------|------|------|
| 1 | 必更新 | lore_bank, narrative_progress |
| 2 | 高頻更新 | character_db.current_state |
| 3 | 中頻更新 | faction_registry, world_atlas |
| 4 | 低頻更新 | power_system, item_compendium |

## 輸出

維護完成後，所有設定檔與最新章節內容保持同步。
