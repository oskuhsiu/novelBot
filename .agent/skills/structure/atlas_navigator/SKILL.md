# Atlas Navigator

導航員 - 查詢世界地圖，驗證角色移動的可行性。

## 功能說明

當劇情需要角色移動時，此 Skill 負責查詢 `world_atlas.yaml` 中的 `access_points`，確保移動邏輯合理。

## 使用情境

- 角色要從 A 地點移動到 B 地點
- 需要確認是否有通路
- 需要確認是否有進入條件（權限、道具、能力）

## 執行邏輯

### Step 1: 解析移動請求

```yaml
input:
  character_id: "CHAR_001"
  from_location: "LOC_101"  # 聽劍閣
  to_location: "LOC_102"    # 下層貧民窟
```

### Step 2: 查詢路徑

從 `world_atlas.yaml` 查詢 `access_points`：

```yaml
access_check:
  direct_paths:
    - path_type: "Elevator"
      requirement: "Security Pass Level 4"
      character_has: false
      accessible: false
      
    - path_type: "Emergency Chute"
      requirement: null
      character_has: true
      accessible: true
```

### Step 3: 驗證進入條件

對照角色的 `current_state`：

```yaml
validation:
  # 檢查角色物品欄
  inventory_check:
    required: "Security Pass Level 4"
    character_has: ["加密硬盤", "折疊義體飛劍"]
    result: false
    
  # 檢查角色能力
  ability_check:
    required: "Fly"
    character_has: ["離線劍意"]
    result: false
    
  # 檢查勢力關係
  faction_check:
    location_controller: "FAC_001"
    character_faction: "FAC_002"
    relation: "Hostile"
    result: "需要潛入"
```

### Step 4: 輸出結果

```yaml
navigation_result:
  can_travel: true
  available_paths:
    - path: "Emergency Chute"
      description: "直通下層貧民窟的廢料管"
      risk: "medium"
      travel_time: "30 分鐘"
      
  blocked_paths:
    - path: "Elevator"
      reason: "需要 4 級安全卡"
      alternatives:
        - "偷取安全卡"
        - "駭入電梯系統"
        - "找到內部人員協助"
        
  plot_suggestions:
    - "角色可選擇危險但快速的廢料管"
    - "或可設計任務獲取安全卡"
```

## 與 Scene Writer 的連動

當 `skill_scene_writer` 寫到移動場景時：

1. 自動調用 `atlas_navigator` 驗證路徑
2. 如果路徑不通，提供劇情轉向建議
3. 如果有多條路徑，根據 `pacing_pointer` 選擇：
   - 快節奏 → 選擇最短路徑
   - 慢節奏 → 可能選擇有事件的路徑

## 輸出格式

```
📍 導航分析
───────────────────────────
從：聽劍閣 (LOC_101)
到：下層貧民窟 (REG_002)
───────────────────────────
✅ 可用路徑：
   └─ 廢料管（風險中等，30分鐘）

❌ 封鎖路徑：
   └─ 電梯（需要4級安全卡）

💡 劇情建議：
   走廢料管可能遭遇流浪者伏擊
───────────────────────────
```
