---
name: character_forge
description: 角色鑄造廠 - 生成有血有肉的角色，維護 base_profile 與 current_state 雙軌制
---

# 角色鑄造廠 (Character Forge)

## 功能概述

此 Skill 負責創造角色並寫入 `character_db.yaml`。每個角色採用「雙軌制」設計：
- **base_profile**：性格錨點，固定不變
- **current_state**：動態狀態，隨劇情更新

## 輸入

1. 從 `templates/novel_config.yaml` 讀取：
   - `style_profile`：確保角色符合風格
   - `meta.language`：命名語言

2. 從 `templates/power_system.yaml` 讀取（如果存在）：
   - 可用的技能框架

3. 使用者提供：
   - 角色類型（主角/反派/配角）
   - 關鍵特徵（可選）

## 輸出

更新 `templates/character_db.yaml`，新增角色條目

## 執行步驟

### Step 1: 讀取上下文
```
讀取 templates/novel_config.yaml 的 style_profile
讀取 templates/world_atlas.yaml 了解世界背景
讀取 templates/power_system.yaml 了解可用技能（如有）
```

### Step 2: 生成角色核心
```
你是一位專精於角色塑造的小說家。
請設計一名 {{role_type}} 角色，符合以下世界觀：

【類型】：{{genre}}
【風格】：{{tone}}
【世界背景】：{{world_summary}}

## 基本資料
請輸出：
1. 姓名/外號（符合 {{language}} 的命名風格）
2. 外觀特徵：
   - 整體印象（一句話）
   - 視覺錨點（一個讓讀者記住的特徵：疤痕/異色瞳/獨特服飾等）
   - 肢體語言習慣

## 內在驅動
3. 核心慾望：他/她最想要什麼？（這是行動的根本動力）
4. 恐懼/弱點：他/她最害怕什麼？（這是內心衝突的來源）
5. 秘密：一個不為人知的過去或真相

## 性格與表達
6. 性格關鍵字：3 個形容詞
7. 說話方式：口頭禪、慣用語氣、說話節奏
8. 行為模式：面對壓力時的典型反應
```

### Step 3: 設計技能樹
```
根據 {{power_system}} 的規則，為 {{character_name}} 設計技能：

## 表層技能（公開）
- 技能名稱
- 等級/熟練度
- 使用場景

## 隱藏技能（秘密）
- 技能名稱
- 為何隱藏
- 何時會被揭露

## 技能限制
- 使用代價
- 與角色弱點的關聯
```

### Step 4: 設定初始狀態
```
請設定 {{character_name}} 在故事開始時的狀態：

## current_state
- 所在位置：{{initial_location}}
- 健康狀態：100%
- 能量狀態：100%
- 情緒狀態：{{emotional_state}}
- 隨身物品：列出 2-4 件物品
- 當前目標：故事開始時想要達成什麼
```

### Step 5: 寫入 character_db.yaml
結構化後寫入資料庫

## 角色資料範例

```yaml
characters:
  - id: "CHAR_001"
    name: "李玄 (Li Xuan)"
    role: "Protagonist"
    
    base_profile:
      identity: "底層黑客，擁有舊時代金丹算法"
      traits: ["冷靜", "偏執", "技術高手"]
      appearance: "磨損的長風衣，胸口有符箓紋路，左眼為電子義眼"
      core_desire: "修復妹妹的意識備份"
      fear: "失去僅存的人性，變成純粹的機器"
      speech_pattern: "少話，習慣用技術術語作比喻"
      secret: "妹妹的意識備份中藏有上一代的禁忌代碼"
      skills:
        - name: "離線劍意"
          level: "中位"
          description: "斷開網絡連接，將劍意壓縮至實體"
    
    current_state:
      last_updated_chapter: 1
      location: "第108層聽劍閣露台"
      health: "95%"
      energy_level: "80%"
      emotional_state: "警覺"
      inventory: ["加密硬盤", "折疊義體飛劍", "低階修復貼片x3"]
      active_goals: ["完成黑市交易", "躲避執法隊"]
      relationships:
        - target_id: "CHAR_002"
          relation: "追捕者"
          attitude: -70
```

## 特殊模式

### 配角快速生成
```
在 {{scene_location}} 需要一個 {{npc_type}} 配角。
請快速生成基本資料：
- 名稱、外觀（一句話）
- 職能（在場景中的作用）
- 一個記憶點
不需要完整的 base_profile，只需能支撐場景即可。
```

### 反派深化模式
```
這個反派不能只是「純粹的壞人」。
請為 {{villain_name}} 設計：
- 他認為自己是正確的理由
- 他的「正義」與主角的衝突點
- 一個讓讀者同情的細節
```

### 關係網生成
```
基於現有角色 {{character_list}}，請建立關係矩陣：

對於每一對角色，描述：
1. 表面關係（朋友/敵人/上下屬）
2. 潛在衝突（利益/價值觀/過去恩怨）
3. 隱藏動態（誰在利用誰/誰在保護誰）
4. 緊張度（0-100）
```

## 使用時機

- **創世階段**：創建主要角色陣容
- **章節需要**：新配角登場時
- **深化角色**：為已有角色補充細節

## 與其他 Skill 的關聯

- **前置 Skill**：
  - `skill_world_builder`：需要世界背景
  - `skill_power_architect`：需要技能體系（如有）
- **後續 Skill**：
  - `skill_status_monitor`：維護 current_state
  - `skill_dialogue_director`：使用說話方式
- **協作 Skill**：
  - `skill_faction_forge`：將角色分配到派系

## 注意事項

1. **base_profile 是錨點**：一旦設定不應輕易修改，這是保持角色一致性的關鍵
2. **current_state 隨時更新**：每章結束後由 status_monitor 更新
3. **秘密要有揭露計畫**：設定秘密時應考慮何時、如何揭露
4. **動機要具體**：「想變強」太模糊，「拯救被凍結的妹妹」才有戲劇性
5. **弱點要可利用**：弱點應該能在劇情中造成真實的困境
