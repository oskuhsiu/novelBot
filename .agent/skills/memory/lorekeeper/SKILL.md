---
name: lorekeeper
description: 長程記憶庫 - 壓縮並記錄已發生的關鍵事實，防止吃書
---

# 長程記憶庫 (Lorekeeper)

## 功能概述

此 Skill 負責維護故事的「長期記憶」，將已發生的重要事件壓縮為條目形式儲存。這是防止 AI 長篇創作「吃書」（前後矛盾）的核心機制。

## 核心功能

1. **事實記錄**：不可更改的已發生事件
2. **關係追蹤**：角色間關係的變化
3. **伏筆管理**：未解懸念的追蹤
4. **物品狀態**：重要物品的歸屬和狀態

## 輸入

1. 最近完成的章節內容
2. 需要壓縮的資訊

## 輸出

更新或新增 `output/lore_bank.yaml`

## 資料結構

```yaml
# 世界觀事實（不可變）
world_facts:
  - id: "FACT_001"
    category: "world_rule"
    content: "靈氣等同於數據帶寬，消耗過度會導致系統崩潰"
    established_in: "chapter_1"

# 已發生事件（不可變）
events:
  - id: "EVENT_001"
    chapter: 1
    summary: "主角在黑市完成硬盤交易，但被執法隊發現"
    participants: ["CHAR_001", "NPC_001"]
    consequences:
      - "主角成為通緝對象"
      - "獲得加密硬盤"
    location: "聽劍閣地下層"

# 關係變動
relationship_changes:
  - chapter: 1
    change: "CHAR_001 與 CHAR_002 從陌生變為追捕關係"
    current_state: "敵對"
    
# 物品狀態
item_status:
  - item_id: "加密硬盤"
    current_owner: "CHAR_001"
    condition: "完好"
    last_seen: "chapter_1"
    
# 永久傷害/狀態
permanent_changes:
  - character_id: "CHAR_001"
    chapter: 3
    description: "左臂在戰鬥中受傷，需要時間恢復"
    recovery_estimate: "chapter_7"

# 未解伏筆
open_foreshadowing:
  - id: "FORE_001"
    planted_in: "chapter_1"
    hint: "硬盤中閃過父親的編碼風格"
    expected_reveal: "大約第15章"
    category: "身世相關"
    
# 已回收伏筆
closed_foreshadowing:
  - id: "FORE_002"
    planted_in: "chapter_2"
    revealed_in: "chapter_10"
    description: "神秘人的真實身份"
```

## 執行步驟

### Step 1: 章節事實提取
```
請閱讀第 {{chapter_id}} 章的內容，提取關鍵事實：

## 提取規則

【必須記錄】
- 主要角色的重大行動
- 影響後續劇情的事件
- 新揭露的信息
- 物品的獲得或損失
- 角色關係的重大變化
- 永久性的改變（傷亡、破壞）

【可以忽略】
- 純粹的氛圍描寫
- 沒有後續影響的對話
- 已記錄事件的重複描述

請以條目形式輸出。
```

### Step 2: 關係變動追蹤
```
分析本章中的角色互動：

對於每對有互動的角色，判斷：
1. 關係是否有變化？
2. 如果有，從什麼變成什麼？
3. 這個變化是暫時的還是持久的？

格式：
- {{CHAR_A}} ↔ {{CHAR_B}}：{{變化描述}}
```

### Step 3: 伏筆管理
```
## 新埋設的伏筆
本章是否埋設了新的伏筆？
- 線索內容：
- 預計何時揭曉：
- 類別（身世/陰謀/物品/關係）：

## 回收的伏筆
本章是否回收了之前的伏筆？
- 伏筆 ID：
- 如何揭曉：
- 標記為已關閉
```

### Step 4: 寫入 lore_bank.yaml
將提取的資訊結構化後寫入

## 壓縮原則

### 保留什麼
- 「誰做了什麼」的事實
- 「結果是什麼」的後果
- 「狀態改變」的記錄

### 省略什麼
- 具體的對話內容
- 詳細的動作過程
- 情緒描寫
- 環境細節

### 範例
原文（500字）：
> 李玄舉起折疊飛劍，劍身閃爍著數據殘影。他深吸一口氣，感受著
> 丹田中的算力湧動……（戰鬥細節）……最終，飛劍刺入敵人的護盾
> 核心，王執法倒在地上。

壓縮後：
```yaml
- chapter: 5
  summary: "李玄在天台戰鬥中擊敗王執法"
  method: "使用折疊飛劍破壞護盾核心"
  consequence: "王執法重傷被俘"
```

## 使用時機

- **章節完成後**：自動呼叫壓縮記憶
- **定期整理**：每 5-10 章進行一次回顧整理
- **寫作前參考**：Scene Writer 需要讀取相關事實

## 與其他 Skill 的關聯

- **更新於**：`workflow_maintenance`
- **被讀取於**：
  - `skill_scene_writer`：確保連戲
  - `skill_logic_auditor`：檢查矛盾
  - `skill_loop_closer`：管理伏筆

## 注意事項

1. **只記錄事實**：不記錄推測或情緒
2. **保持更新**：每章結束後必須更新
3. **定期清理**：過於久遠且無後續影響的事件可以歸檔
4. **伏筆追蹤**：打開的伏筆必須最終關閉
5. **版本控制**：重大修改前應該備份
