---
name: character_secret_seeder
description: 角色秘密種子器 - 生成角色的隱性動機
---

# Character Secret Seeder

角色秘密種子器 - 生成角色的隱性動機。

## 功能說明

專門生成角色的秘密、隱藏動機和私密資訊。這些資訊不對外公開，僅供寫作時參考。

## 使用情境

- 創建新角色時生成背景秘密
- 增加角色深度和複雜性
- 為未來劇情埋設伏筆

## 執行邏輯

### Step 1: 讀取角色基本設定

```yaml
character_input:
  id: "CHAR_001"
  name: "李玄"
  base_profile:
    identity: "底層黑客"
    core_desire: "修復妹妹的意識備份"
```

### Step 2: 生成秘密類型

```yaml
secret_types:
  - hidden_past: "過去的隱藏經歷"
  - secret_alliance: "秘密盟友/敵人"
  - forbidden_knowledge: "禁忌知識"
  - true_motivation: "真正動機（表面動機的底層）"
  - weakness: "隱藏弱點"
  - power: "未展現的能力"
  - relationship: "隱藏關係"
```

### Step 3: 生成秘密

```yaml
character_secrets:
  character_id: "CHAR_001"
  
  secrets:
    - id: "SECRET_001"
      type: "hidden_past"
      content: "妹妹的意識備份實際上包含了禁忌的金丹算法，這才是他真正想要修復的原因"
      reveal_timing: "中期轉折"
      foreshadow_in: ["chapter_5", "chapter_12"]
      
    - id: "SECRET_002"
      type: "secret_alliance"
      content: "他曾經是天宮財閥的內部人員，但因為某事件被迫叛逃"
      reveal_timing: "後期"
      impact: "改變與FAC_001的關係"
      
    - id: "SECRET_003"
      type: "weakness"
      content: "義眼其實有後門，可以被天宮遠程控制"
      reveal_timing: "危機時刻"
      story_use: "製造背叛/困境"
```

### Step 4: 寫入角色資料庫

擴展 `character_db.yaml`，增加隱藏區塊：

```yaml
CHAR_001:
  base_profile: {...}
  current_state: {...}
  
  # 這個區塊不用於對外展示
  hidden_profile:
    secrets: [...]
    true_motivation: "..."
    secret_relationships: [...]
```

## 輸出格式

```
🔒 角色秘密已生成
───────────────────────────
角色：李玄 (CHAR_001)
───────────────────────────
秘密數量：3

[隱藏過去]
妹妹的備份包含禁忌算法
→ 揭露時機：中期轉折
→ 伏筆章節：5, 12

[秘密盟友]
曾是天宮財閥內部人員
→ 揭露時機：後期

[隱藏弱點]
義眼有後門可被遠程控制
→ 揭露時機：危機時刻
───────────────────────────
已寫入：character_db.yaml
（hidden_profile 區塊）
```
