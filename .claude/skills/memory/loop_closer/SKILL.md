---
name: loop_closer
description: 伏筆閉環追蹤器 - 記錄並追蹤所有伏筆，確保挖坑填坑
---

# 伏筆閉環追蹤器 (Loop Closer)

## 功能概述

此 Skill 負責管理故事中的所有「開放迴圈 (Open Loops)」——即已埋設但尚未回收的伏筆。它確保：
1. 所有伏筆都被記錄
2. 伏筆在適當時機被回收
3. 不會挖坑不填

## 伏筆類型

| 類型 | 說明 | 回收時間 |
|------|------|----------|
| 身世伏筆 | 角色的隱藏身份/過去 | 中後期 |
| 物品伏筆 | 神秘物品的來歷/功能 | 視需要 |
| 關係伏筆 | 角色間的隱藏聯繫 | 中期 |
| 事件伏筆 | 未解釋的神秘事件 | 視劇情 |
| 預言伏筆 | 預示未來的暗示 | 後期 |
| 環境伏筆 | 場景中的異常細節 | 早中期 |

## 伏筆生命週期

```
埋設 (Plant) → 暗示 (Hint) → 強化 (Reinforce) → 揭曉 (Reveal)
```

- **埋設**：首次出現，看似普通的細節
- **暗示**：在其他場景輕觸，加深印象
- **強化**：更明顯的線索，讀者開始懷疑
- **揭曉**：真相大白，回收伏筆

## 資料結構

```yaml
# 開放伏筆
open_loops:
  - id: "LOOP_001"
    type: "身世"
    
    # 生命週期追蹤
    lifecycle:
      planted:
        chapter: 1
        beat: "B1_2"
        content: "硬盤中閃過父親熟悉的編碼風格"
        visibility: "subtle"  # subtle / moderate / obvious
        
      hints:
        - chapter: 3
          content: "系統偶爾出現父親時代的老舊介面"
        - chapter: 7
          content: "敵人提到了一個熟悉的名字"
          
      reinforced:
        chapter: 12
        content: "發現父親留下的加密日記"
        
      revealed: null  # 尚未揭曉
    
    # 揭曉計畫
    reveal_plan:
      target_chapter: "15-18"
      method: "角色揭露 + 閃回"
      impact: "改變主角對過去的認知"
      
    # 狀態
    status: "active"  # active / dormant / revealed
    priority: "high"  # high / medium / low
    
# 已關閉伏筆
closed_loops:
  - id: "LOOP_002"
    type: "物品"
    summary: "神秘硬盤的真正內容"
    planted_chapter: 1
    revealed_chapter: 10
    payoff_satisfaction: "high"  # 回收效果評估
```

## 執行步驟

### Step 1: 伏筆登記
```
當埋設新伏筆時，記錄：

## 新伏筆登記

【基本資訊】
- ID：自動生成
- 類型：{{type}}
- 章節：{{chapter}}

【埋設方式】
- 內容：{{what_was_planted}}
- 可見度：{{subtle/moderate/obvious}}
- 載體：{{角色對話/環境描寫/物品細節}}

【揭曉計畫】
- 預計章節：{{target_chapter}}
- 揭曉方式：{{reveal_method}}
- 與主線的關聯：{{connection}}
```

### Step 2: 伏筆追蹤
```
在每個章節規劃時，檢查：

## 伏筆追蹤報告

【本章可用伏筆】
根據進度，以下伏筆可以在本章輕觸或揭曉：
{{available_loops}}

【需要關注的伏筆】
以下伏筆已經很久沒有提及，需要暗示一下：
{{dormant_loops}}

【即將到期的伏筆】
以下伏筆已經強化多次，應該準備揭曉：
{{ready_to_reveal}}

【建議】
本章建議：
- 輕觸：{{hint_suggestions}}
- 揭曉：{{reveal_suggestions}}
```

### Step 3: 伏筆回收確認
```
當揭曉伏筆時，確認：

## 伏筆回收確認

【伏筆 ID】：{{loop_id}}
【揭曉方式】：{{how_revealed}}
【回顧性】：讀者回頭看是否有「原來如此」的感覺？
【情感影響】：這個揭曉帶來的情緒衝擊？
【後續影響】：這個揭曉會引發什麼新發展？

確認後標記為 closed，移入 closed_loops 列表。
```

## 伏筆健康檢查

### 定期檢查項目
```
每 5 章執行一次健康檢查：

## 伏筆健康報告

【活躍伏筆數量】：{{active_count}}
【休眠伏筆數量】：{{dormant_count}}（超過 5 章未提及）

【警告】
- 伏筆過多：當前有 {{count}} 個活躍伏筆，可能難以管理
- 長期休眠：{{loop_ids}} 已經 {{chapters}} 章沒有提及
- 即將逾期：{{loop_ids}} 已經超過預計揭曉章節

【建議調整】
- 合併：{{merge_suggestions}}
- 優先回收：{{prioritize_reveals}}
- 放棄：{{abandon_suggestions}}（謹慎使用）
```

## 伏筆植入建議

### 何時植入
- **開篇**：核心伏筆應該早埋
- **轉折點**：在重要轉折處埋設相關伏筆
- **平淡處**：用伏筆增加平淡場景的價值

### 如何植入
```markdown
【低可見度】
「角落裡堆著一些舊設備，其中一台的指示燈還在閃爍。」
→ 讀者不會注意，但可以在需要時說「那台設備記錄了一切」

【中可見度】
「她注意到他的袖口下有一道舊傷疤——符箓灼燒的痕跡。」
→ 讀者會記住，之後揭曉「他曾是某派弟子」

【高可見度】
「他臨死前說：『去找……找到那個人……』話沒說完就斷了氣。」
→ 讀者會期待知道「那個人」是誰
```

## 使用時機

- **章節規劃時**：檢查可用伏筆
- **寫作時**：按建議植入或暗示
- **章節結束後**：確認伏筆狀態更新
- **定期維護**：健康檢查

## 與其他 Skill 的關聯

- **寫入**：`skill_lorekeeper`（伏筆儲存）
- **讀取於**：`skill_beat_optimizer`（植入建議）
- **協作**：`skill_scene_writer`（實際執行）

## 注意事項

1. **不要挖太多坑**：活躍伏筆建議不超過 10 個
2. **定期輕觸**：每個伏筆至少每 5 章暗示一次
3. **兌現承諾**：挖的坑一定要填
4. **比例平衡**：揭曉速度應該與埋設速度大致匹配
5. **質量優先**：一個精心設計的伏筆勝過五個敷衍的
