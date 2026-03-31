---
name: identity_validator
description: 角色立場鑑定器 - 根據派系調整對話風格
---

# Identity Validator

角色立場鑑定器 - 根據派系調整對話風格。

## 功能說明

檢查角色的派系背景，確保對話風格符合其立場。

## 使用情境

- 生成對話前驗證角色立場
- 調整對話語氣和用詞
- 確保敵對關係反映在對話中

## 執行邏輯

### Step 1: 查詢角色派系

```yaml
character_faction_check:
  character_id: "CHAR_002"
  name: "王執法"
  
  faction_info:
    primary: "FAC_001"  # 天宮財閥
    role: "High Executive"
    loyalty: 95
```

### Step 2: 讀取派系語言風格

從 SQLite 資料庫獲取（`faction_query.py --proj {proj} get FAC_001`）：

```yaml
faction_speech_patterns:
  FAC_001:  # 天宮財閥
    tone: "傲慢、官僚"
    vocabulary:
      - "法律術語"
      - "企業行話"
      - "權威語氣"
    speech_patterns:
      - "以命令句為主"
      - "很少使用疑問句"
      - "常引用條款和規定"
    sample_dialogues:
      - "根據第七條第三款，你已經構成違規。"
      - "這是最終決定。沒有上訴餘地。"
      
  FAC_002:  # 霓虹叛軍
    tone: "直接、粗獷"
    vocabulary:
      - "街頭俚語"
      - "技術術語"
      - "諷刺用語"
    speech_patterns:
      - "短句為主"
      - "常用反問"
      - "帶有嘲諷"
```

### Step 3: 驗證對話

檢查待生成對話是否符合角色立場：

```yaml
dialogue_validation:
  character: "王執法"
  faction: "FAC_001"
  
  proposed_dialogue: "拜託放過我們吧..."
  
  validation_result:
    passed: false
    reason: "該角色不會使用乞求語氣"
    suggested_revision: "你有三秒鐘時間解釋，為什麼我不該當場處決你。"
```

### Step 4: 關係影響

根據對話雙方的勢力關係調整：

```yaml
relationship_impact:
  speaker: "CHAR_001"  # FAC_002
  listener: "CHAR_002"  # FAC_001
  
  relation: "Hostile"
  tension: 95
  
  dialogue_adjustments:
    - "增加敵意和警戒"
    - "避免友好用語"
    - "可能包含威脅"
```

## 輸出格式

```yaml
identity_validation:
  character: "王執法"
  faction: "天宮財閥"
  
  speech_style:
    tone: "傲慢、官僚"
    vocabulary_type: "法律術語 + 企業行話"
    
  dialogue_guidance:
    do:
      - "使用命令句"
      - "引用條款"
      - "保持權威感"
    dont:
      - "使用乞求語氣"
      - "表現猶豫"
      - "過度解釋"
```

## 驗證維度

```yaml
presence_usage:
  description: "對話場景中角色是否有物理存在感"
  check: "角色是否只有聲音沒有身體？是否有穿插 presence 來源的動作？"
  fix: "從角色 presence 取習慣動作穿插在對話間隙"
```

## 與 Dialogue Director 的連動

在生成對話前：
1. 調用 `identity_validator` 確認角色立場
2. 傳遞語言風格指導給 `dialogue_director`
3. 生成符合派系特色的對話
