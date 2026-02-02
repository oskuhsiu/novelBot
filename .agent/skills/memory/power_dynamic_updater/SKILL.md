# Power Dynamic Updater

權力博弈監測 - 自動更新勢力間的緊張值。

## 功能說明

監測劇情中影響勢力關係的事件，自動調整 `faction_registry.yaml` 中的 `tension` 值。

## 觸發條件

以下行為會觸發緊張值更新：

| 事件類型 | 張力變動 | 範例 |
|----------|----------|------|
| 殺死對方成員 | +15~30 | 主角殺死財閥高管 |
| 偷取資源 | +10~20 | 潛入偷走機密 |
| 公開對抗 | +20~40 | 當眾挑戰勢力權威 |
| 結盟宣布 | -20~-40 | 與敵對勢力達成協議 |
| 領土佔領 | +30~50 | 攻佔對方據點 |
| 談判成功 | -10~-30 | 和平解決爭端 |
| 背叛 | +40~60 | 間諜身份暴露 |

## 執行邏輯

### Step 1: 事件分析

從章節內容中識別影響勢力的事件：

```yaml
event_detection:
  chapter: 15
  events:
    - type: "kill"
      actor: "CHAR_001"
      actor_faction: "FAC_002"
      target: "老蔡"
      target_faction: "FAC_002"  # 內部衝突
      impact: "faction_leader_death"
      
    - type: "territory_capture"
      actor_faction: "FAC_001"
      target: "地下停車場"
      previous_controller: "FAC_002"
```

### Step 2: 計算張力變動

```yaml
tension_calculation:
  FAC_001_vs_FAC_002:
    current_tension: 95
    events:
      - event: "faction_leader_death"
        change: 0  # 老蔡是敵對勢力，死亡不增加緊張
      - event: "territory_capture"
        change: +20
    new_tension: 100  # 封頂
    
  FAC_001_vs_FAC_003:
    current_tension: 40
    events:
      - event: "alliance_maintained"
        change: -5
    new_tension: 35
```

### Step 3: 閾值觸發

當張力達到特定閾值時，觸發連鎖事件：

```yaml
threshold_triggers:
  tension >= 90:
    trigger: "OPEN_WAR"
    effects:
      - "對方勢力發動全面攻擊"
      - "關閉所有和平途徑"
      - "觸發 chaos_engine 生成戰爭事件"
      
  tension >= 70:
    trigger: "COLD_WAR"
    effects:
      - "加強邊境巡邏"
      - "商業禁運"
      - "間諜活動增加"
      
  tension <= 20:
    trigger: "ALLIANCE"
    effects:
      - "可能的合併選項"
      - "共同敵人出現"
```

### Step 4: 更新資料庫

寫入 `faction_registry.yaml`：

```yaml
relations:
  - target_id: "FAC_002"
    status: "Hostile"
    tension: 100
    last_updated: "chapter_15"
    history:
      - chapter: 13
        event: "siege_failed"
        change: +15
      - chapter: 15
        event: "leader_death"
        change: +20
```

### Step 5: 觸發後續

如果達到閾值，通知其他 Skill：

```yaml
triggered_actions:
  - skill: "chaos_engine"
    reason: "tension >= 90"
    instruction: "下一章必須包含勢力衝突事件"
    
  - skill: "beat_optimizer"
    reason: "open_war_triggered"
    instruction: "調整大綱，加入戰爭相關 beats"
```

## 輸出格式

```
═══════════════════════════════════════════════════
  勢力動態更新
═══════════════════════════════════════════════════
  本章事件：
  ├─ 林昊擊殺老蔡（領袖死亡）
  └─ 接收地下停車場（領土變動）
───────────────────────────────────────────────────
  緊張度變化：
  
  FAC_001 (傾斜公寓團隊)
    └─ vs FAC_002 (老蔡團隊): 95 → 100 ⚠️ 封頂
    └─ vs FAC_003 (獵人小隊): 40 → 35 ✅ 緩和
        
───────────────────────────────────────────────────
  觸發事件：
  ⚠️ FAC_002 已滅亡，標記為 defunct
  ⚠️ 領土控制權轉移完成
═══════════════════════════════════════════════════
```

## 連動機制

1. **nvChapter 結束時**：自動分析本章的勢力影響
2. **nvMaint 執行時**：更新 faction_registry.yaml
3. **chaos_engine**：高緊張度時可能觸發
