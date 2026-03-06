---
name: relationship_dynamics
description: 關係動態器 - 追蹤角色間的動態張力，識別關係轉折點，讓關係發展更自然
---

# 關係動態器 (Relationship Dynamics)

## 功能概述

此 Skill 負責追蹤角色間的「動態關係」，不只是記錄「誰和誰是什麼關係」，而是追蹤關係的**張力曲線**、**信任積分**和**轉折點條件**。

## 設計理念

傳統的關係記錄是靜態的：
```yaml
CHAR_001 ↔ CHAR_002: "盟友"
```

關係動態器改為動態追蹤：
```yaml
CHAR_001 ↔ CHAR_002:
  surface: "盟友"
  trust_score: 45
  tension_score: 65
  unresolved_issues: ["曾見死不救"]
  ready_for_turning_point: true
```

## 核心概念

### 1. 信任積分 (Trust Score)

衡量角色之間的信任程度：

| 分數 | 狀態 | 行為影響 |
|------|------|----------|
| 0-20 | 深度不信任 | 不會分享資訊，隨時準備背叛 |
| 21-40 | 戒備 | 只分享必要資訊，保持距離 |
| 41-60 | 中立 | 合作但有保留 |
| 61-80 | 信任 | 願意冒險幫助對方 |
| 81-100 | 深度信任 | 無條件支持，可能犧牲自己 |

### 2. 張力積分 (Tension Score)

衡量關係中累積的未解決衝突：

| 分數 | 狀態 | 行為影響 |
|------|------|----------|
| 0-30 | 和諧 | 互動愉快，少有摩擦 |
| 31-50 | 微妙 | 偶爾不快，但能壓抑 |
| 51-70 | 緊繃 | 容易爆發口角，需要小心 |
| 71-85 | 臨界 | 任何觸發都可能引爆大衝突 |
| 86-100 | 爆發 | 已經或即將爆發重大衝突 |

### 3. 轉折點 (Turning Point)

當特定條件滿足時，關係會發生質變：

```yaml
turning_point:
  condition: "當 CHAR_002 需要選擇救 CHAR_001 還是目標時"
  current_readiness: 0.8  # 接近觸發
  possible_outcomes:
    - "選擇救人 → 信任+30，確立深度羈絆"
    - "選擇目標 → 信任-50，張力+40，可能決裂"
```

## 輸入

1. 從角色資料庫（SQLite）讀取：
   ```bash
   .venv/bin/python tools/char_query.py --proj {proj} relations
   .venv/bin/python tools/char_query.py --proj {proj} get {CHAR_IDS}
   ```
   
2. 從 ChromaDB 讀取（使用 `lore_query.py`）：
   - `category: relationship_change` 歷史
   - 相關 events 記錄

3. 從 `memory/motivation_map.yaml` 讀取：
   - 角色當前動機（影響互動方式）

## 輸出

使用 CLI 更新角色資料庫中的關係：
```bash
.venv/bin/python tools/char_query.py --proj {proj} update-rel {SOURCE_ID} {TARGET_ID} --surface "..." --hidden "..." --tension N
```
並產生 `memory/relationship_dynamics.yaml`

```yaml
# 關係動態記錄

last_updated: "chapter_5"

relationship_matrix:
  - pair_id: "REL_001"
    source: "CHAR_001"
    target: "CHAR_002"
    
    # 表面關係（外人看到的）
    surface_relation: "盟友"
    
    # 深層狀態
    dynamics:
      trust_score: 45
      tension_score: 65
      intimacy_score: 30  # 親密度（不一定是愛情）
      
    # 歷史累積
    history:
      positive_events: 3   # 正面互動次數
      negative_events: 2   # 負面互動次數
      major_incidents:
        - chapter: 2
          event: "CHAR_002 未能及時支援"
          impact: "trust -20, tension +25"
        - chapter: 4
          event: "CHAR_002 冒險救出 CHAR_001"
          impact: "trust +15, tension -10"
          
    # 未解決的問題
    unresolved_issues:
      - issue: "當初為何沒來救援？"
        severity: "major"
        addressed: false
        
    # 轉折點
    turning_point:
      ready: true
      condition: "當 CHAR_001 得知 CHAR_002 當時的真實處境"
      possible_outcomes:
        - outcome: "誤會解開"
          result: "trust +30, tension -40"
        - outcome: "發現是藉口"
          result: "trust -30, tension +30, 決裂風險"
          
    # 互動模式
    interaction_pattern:
      typical_tone: "表面客氣，暗藏芥蒂"
      trigger_topics: ["過去的任務", "信任問題"]
      safe_topics: ["任務進度", "敵人情報"]

# 群體關係（多人互動）
group_dynamics:
  - group_id: "GROUP_001"
    members: ["CHAR_001", "CHAR_002", "CHAR_003"]
    
    group_cohesion: 55  # 團隊凝聚力
    internal_factions:
      - faction: ["CHAR_001", "CHAR_003"]
        reason: "價值觀相近"
      - faction: ["CHAR_002"]
        reason: "獨來獨往"
        
    potential_split_trigger: "資源分配不均時"

# 關係建議
relationship_suggestions:
  - suggestion: "本章適合處理 CHAR_001 和 CHAR_002 的未解決問題"
    reason: "tension 已達 65，接近 70 的爆發閾值"
    recommended_scene: "私下對話，被打斷的質問"
```

## 執行步驟

### Step 1: 載入關係資料

```yaml
從角色資料庫（SQLite）讀取:
  .venv/bin/python tools/char_query.py --proj {proj} relations
  .venv/bin/python tools/char_query.py --proj {proj} get {CHAR_IDS}

從 ChromaDB 讀取:
  - .venv/bin/python tools/lore_query.py --proj {proj} lore "角色A 角色B" --category relationship_change
```

### Step 2: 計算積分變化

```
對於最近章節中的每次角色互動：

分析互動對關係的影響：

【互動事件】：{{event_description}}
【參與者】：{{participants}}
【事件性質】：{{positive/negative/neutral}}

計算影響：
- trust_score 變化：{{delta}}
- tension_score 變化：{{delta}}
- 是否產生新的 unresolved_issue：{{yes/no}}
- 是否解決已有 issue：{{yes/no}}
```

### Step 3: 檢查轉折點條件

```
對於每對關係：

檢查是否滿足轉折點條件：
- tension_score >= 70 → 可能爆發衝突
- trust_score 極端變化 → 可能質變
- unresolved_issues 累積 >= 3 → 需要處理

輸出 turning_point.ready 狀態
```

### Step 4: 生成互動建議

```
基於關係動態，建議：
- 哪些關係適合在本章發展？
- 推薦什麼類型的場景？
- 應該避免什麼話題？
```

### Step 5: 更新記錄

將分析結果寫入 `relationship_dynamics.yaml`

## 互動模式自動判斷

根據 trust/tension 組合，自動判斷互動模式：

| Trust | Tension | 模式 | 描述 |
|-------|---------|------|------|
| 高 | 低 | 深度信任 | 可以暢所欲言 |
| 高 | 高 | 複雜羈絆 | 深愛但常爭吵 |
| 低 | 低 | 陌生/冷漠 | 無特別互動 |
| 低 | 高 | 敵對/仇恨 | 隨時可能衝突 |
| 中 | 中 | 曖昧/試探 | 互相觀察評估 |

## 與其他 Skill 的關聯

- **前置 Skill**：
  - `motivation_engine`：動機影響互動方式
  
- **協作 Skill**：
  - `lorekeeper`：記錄關係變化事件
  - `dialogue_director`：對話反映關係狀態
  - `dialogue_subtext_editor`：潛台詞呼應張力
  
- **輸出給**：
  - `chapter_beater`：設計需要處理的關係節點
  - `scene_writer`：互動細節依據

## 事件對積分的影響指南

### 正面事件
| 事件類型 | Trust 變化 | Tension 變化 |
|----------|------------|--------------|
| 救命之恩 | +20~+40 | -20~-30 |
| 分享秘密 | +10~+20 | -5~-15 |
| 主動幫助 | +5~+15 | -5~-10 |
| 道歉/和解 | +5~+10 | -15~-25 |

### 負面事件
| 事件類型 | Trust 變化 | Tension 變化 |
|----------|------------|--------------|
| 背叛 | -30~-50 | +30~+50 |
| 見死不救 | -15~-30 | +20~+35 |
| 說謊被發現 | -10~-25 | +15~+25 |
| 公開羞辱 | -5~-15 | +20~+30 |

## 注意事項

1. **漸進變化**：積分不應突變，除非是重大事件
2. **保持平衡**：不要讓所有關係都走向極端
3. **服務劇情**：關係發展要配合大綱，但可以有機調整
4. **群體效應**：多人場景中的互動會影響整個群體動態
5. **記錄一致**：確保 lorekeeper 同步記錄關係變化
