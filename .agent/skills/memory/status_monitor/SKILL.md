---
name: status_monitor
description: 短程狀態欄 - 維護當前狀態快照，確保場景連戲
---

# 短程狀態欄 (Status Monitor)

## 功能概述

此 Skill 維護故事的「即時狀態」，類似遊戲的 HUD 顯示。它追蹤：
- 當前時間和地點
- 角色的即時狀態
- 手持物品和隨身裝備
- 在場人物

這是保證「連戲」的關鍵工具。

## 核心功能

1. **狀態快照**：提供給 Scene Writer 的即時參考
2. **狀態更新**：場景結束後更新角色狀態
3. **連戲檢查**：確保相鄰場景狀態連續

## 資料結構

```yaml
# 狀態快照
current_snapshot:
  timestamp: "第1章 - 深夜"
  
  # 場景狀態
  scene:
    location: "聽劍閣地下層 - 108號雅間"
    environment: "昏暗燈光，金屬牆壁，空氣混濁"
    time_of_day: "深夜"
    weather: "建築內部，無天氣"
    
  # 在場角色
  present_characters:
    - id: "CHAR_001"
      name: "李玄"
      position: "門口站立"
      current_action: "與神秘人交談"
      
  # 主角狀態
  protagonist_status:
    health: "95%"
    energy: "80%"
    emotional_state: "警覺"
    active_abilities: null
    
    # 隨身物品
    equipped:
      weapon: "折疊義體飛劍（收納狀態）"
      armor: "磨損長風衣"
      accessory: "電子義眼（左）"
      
    inventory:
      - "加密硬盤（剛獲得）"
      - "低階修復貼片 x3"
      - "信用幣 500"
      
    # 所在派系/身份
    current_identity: "自由黑客"
    
  # 最近發生的事（短期記憶）
  recent_events:
    - "完成了硬盤交接"
    - "發現硬盤有異常數據"
    - "聽到門外有動靜"
```

## 執行步驟

### Step 1: 讀取當前狀態
```
在撰寫新節拍前，呼叫此 Skill 獲取狀態快照：

## 當前狀態快照

【時間/地點】
- {{timestamp}}
- {{location}}

【在場人物】
{{present_characters_list}}

【主角狀態】
- 健康：{{health}}
- 能量：{{energy}}
- 情緒：{{emotional_state}}
- 手持物：{{equipped}}
- 口袋：{{inventory}}

【最近發生】
{{recent_events}}

Scene Writer 應參考此快照，確保連戲正確。
```

### Step 2: 狀態更新
```
節拍/場景完成後，更新狀態：

## 狀態變更記錄

【位置變化】
- 原地點：{{old_location}}
- 新地點：{{new_location}}

【角色狀態變化】
- {{character_id}}:
  - 健康：{{old}} → {{new}}
  - 能量：{{old}} → {{new}}
  - 情緒：{{old}} → {{new}}
  
【物品變化】
- 獲得：{{gained_items}}
- 失去：{{lost_items}}
- 使用：{{used_items}}

【在場人物變化】
- 進場：{{entered}}
- 離場：{{exited}}
```

### Step 3: 同步到 character_db.yaml
```
將角色的 current_state 同步更新：
- last_updated_chapter: {{current_chapter}}
- location: {{new_location}}
- health: {{new_health}}
- inventory: {{updated_inventory}}
- active_goals: {{updated_goals}}
```

## 連戲檢查清單

### 場景開始前檢查
```
□ 角色從上一場景的位置合理移動到這裡了嗎？
□ 之前受的傷現在還在嗎？
□ 手裡拿著的東西還在嗎？
□ 穿著和上一場景一致嗎？
□ 時間流逝合理嗎？
□ 情緒延續合理嗎？
```

### 常見連戲錯誤
| 錯誤類型 | 範例 | 檢查方法 |
|----------|------|----------|
| 物品消失 | 前一章拿著的劍不見了 | 檢查 inventory |
| 傷勢蒸發 | 剛受傷就生龍活虎 | 檢查 health |
| 瞬間移動 | 沒有交代如何移動 | 檢查 location |
| 人物穿越 | 剛離開的人突然出現 | 檢查 present |
| 時間錯亂 | 深夜突然變白天 | 檢查 timestamp |

## 狀態繼承規則

### 自動繼承
以下狀態在場景切換時自動繼承：
- 位置（除非明確移動）
- 裝備
- 永久傷害
- 基礎物品

### 需要明確更新
以下狀態需要手動更新：
- 臨時效果（buff/debuff）
- 情緒狀態
- 當前目標
- 能量消耗

## 使用時機

- **每個節拍開始前**：生成狀態快照供寫作參考
- **每個節拍結束後**：更新狀態變化
- **章節結束時**：全面同步到資料庫

## 與其他 Skill 的關聯

- **讀取者**：
  - `skill_scene_writer`（寫作時參考）
  - `skill_logic_auditor`（檢查矛盾）
- **更新於**：
  - `workflow_maintenance`
  - 每次場景切換

## 注意事項

1. **即時性**：狀態應該隨時反映最新情況
2. **精確性**：數值要具體，不要模糊
3. **連貫性**：每次更新都要考慮前後連接
4. **可追溯**：保留狀態變化的歷史記錄
5. **輕量化**：只記錄必要資訊，不要過度詳細
