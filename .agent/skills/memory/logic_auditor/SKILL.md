---
name: logic_auditor
description: 邏輯審查員 - 檢查新寫內容與已有設定是否衝突
---

# 邏輯審查員 (Logic Auditor)

## 功能概述

此 Skill 負責檢查新生成的內容是否與已有設定存在邏輯衝突。它是防止「吃書」的最後一道防線。

## 檢查範圍

1. **世界觀規則**：是否違反已建立的物理/魔法法則
2. **角色設定**：行為是否符合性格，能力是否超標
3. **事件連貫**：是否與已發生事件矛盾
4. **時空邏輯**：時間、地點是否合理
5. **物品狀態**：物品歸屬和狀態是否正確

## 輸入

1. 需要審查的新內容（段落或章節）
2. 相關的設定資料庫

## 輸出

審查報告，包含：
- 發現的問題
- 問題嚴重程度
- 修正建議

## 執行步驟

### Step 1: 載入參考資料
```
載入以下資料庫供對照：
- templates/novel_config.yaml（世界規則）
- templates/character_db.yaml（角色設定）
- templates/power_system.yaml（力量體系）
- output/lore_bank.yaml（已發生事實）
- output/status_snapshot.yaml（當前狀態）
```

### Step 2: 執行邏輯檢查
```
請審查以下新生成的段落，找出可能的邏輯問題：

【新段落】
{{new_content}}

【檢查清單】

## 1. 世界觀規則
對照 world_rules，檢查：
□ 力量使用是否符合規則？
□ 代價是否合理支付？
□ 物理現象是否合理？

## 2. 角色行為
對照 character_db.base_profile，檢查：
□ 角色說話方式是否符合 speech_pattern？
□ 行為是否符合 traits 描述的性格？
□ 能力是否超出技能範圍？

## 3. 能力限制
對照 power_system，檢查：
□ 技能使用是否符合等級限制？
□ 冷卻時間是否過去？
□ 消耗的能量是否有支付？

## 4. 事實一致性
對照 lore_bank.events，檢查：
□ 是否與已發生事件矛盾？
□ 被殺/重傷的角色是否復活？
□ 已毀壞的物品是否重現？

## 5. 即時狀態
對照 status_snapshot，檢查：
□ 位置轉換是否合理？
□ 物品是否在角色身上？
□ 傷勢是否被遺忘？
```

### Step 3: 輸出審查報告
```yaml
audit_report:
  chapter: {{chapter_id}}
  beat: {{beat_id}}
  audit_time: {{timestamp}}
  
  issues:
    - id: "ISSUE_001"
      severity: "critical"  # critical / warning / minor
      category: "power_system"
      description: "主角使用了金丹級技能，但當前等級只有築基"
      location: "第3段"
      suggested_fix: "改為築基級技能，或增加說明為何能越級使用"
      
    - id: "ISSUE_002"
      severity: "warning"
      category: "character"
      description: "李玄在此處突然變得話多，與寡言的設定不符"
      location: "對話段落"
      suggested_fix: "減少台詞，或解釋為何此時例外"
      
  passed_checks:
    - "時空邏輯：通過"
    - "物品狀態：通過"
    
  overall_status: "需要修正"
```

## 常見邏輯問題

### 嚴重問題 (Critical)
- 死人復活
- 違反核心世界觀規則
- 能力嚴重越級
- 時間線錯亂

### 警告問題 (Warning)
- 角色行為略有偏差
- 次要設定遺忘
- 物品狀態小錯誤
- 傷勢恢復過快

### 輕微問題 (Minor)
- 環境描寫與之前略有出入
- 語氣細微不一致
- 可解釋的小矛盾

## 特殊情況處理

### 刻意違反
如果違反是刻意為之（如：角色偽裝、能力爆發）：
```
標記為「疑似問題，可能為刻意設計」
由作者確認：是/否
如果是刻意：記錄原因，不視為錯誤
```

### 解釋性違反
某些「違反」可以通過添加解釋來修復：
```
例如：築基使用金丹技能
修復：「他將父親留給他的一縷金丹真元壓縮在符箓中，此刻終於釋放」
→ 不違反規則，但需要補充設定
```

## 使用時機

- **即時審查**：每個節拍寫完後
- **章節審查**：全章完成後
- **全書審查**：多章積累後的全面檢查

## 與其他 Skill 的關聯

- **讀取**：
  - `skill_lorekeeper`（已發生事實）
  - `skill_status_monitor`（當前狀態）
- **被呼叫於**：
  - `workflow_chapter`（寫作後）
- **輸出到**：
  - `skill_scene_writer`（修正建議）

## 注意事項

1. **嚴格但不僵化**：有些問題可以通過解釋修復
2. **保留判斷空間**：刻意的違反不是錯誤
3. **優先級排序**：優先處理嚴重問題
4. **持續學習**：記錄屢次出現的問題類型
5. **效率考量**：不需要每次都做全面審查
