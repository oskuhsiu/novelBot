---
name: faction_forge
description: 勢力鑄造廠 - 生成派系與勢力，建立外交矩陣，寫入 faction_registry.yaml
---

# 勢力鑄造廠 (Faction Forge)

## 功能概述

此 Skill 負責創建故事中的派系與勢力，包含組織架構、資源分配、外交關係。派系是推動劇情的「劇本背景」，為角色提供舞台與衝突來源。

## 輸入

1. 從 `templates/novel_config.yaml` 讀取：
   - `style_profile.genre`：確保派系符合類型
   - `meta.language`：命名語言

2. 從 `templates/world_atlas.yaml` 讀取：
   - 可用的區域和地點（用於分配領土）

3. 從 `templates/character_db.yaml` 讀取：
   - 現有角色（用於分配成員）

## 輸出

更新 `templates/faction_registry.yaml`

## 執行步驟

### Step 1: 讀取世界背景
```
讀取 templates/novel_config.yaml
讀取 templates/world_atlas.yaml
讀取 templates/character_db.yaml
```

### Step 2: 設計派系架構
```
你是一位政治與組織設計專家。
請為這個 {{genre}} 世界設計主要勢力：

【世界背景】：{{world_summary}}
【現有區域】：{{regions_list}}

## 主要勢力設計

請設計 3-5 個勢力，每個包含：

1. **名稱**：符合世界觀風格
2. **等級 (Tier)**：
   - S = 超級勢力（可影響整個世界）
   - A = 主要勢力（區域霸權）
   - B = 地區勢力
   - C = 本地勢力
   - D = 小型組織

3. **類型**：Corporation / Government / Guild / Cult / Rebel / Criminal / etc.

4. **核心理念**：這個組織相信什麼？追求什麼？

5. **主要資源**：他們控制什麼？
   - 經濟資源
   - 武力
   - 情報
   - 技術

6. **階層結構**：
   - 最高領導層
   - 中層管理
   - 基層成員
   
7. **公開秘密**：組織內部不為外人知的事
```

### Step 3: 建立領土與成員連結
```
請將勢力與現有資源連結：

## 領土分配
根據 {{regions_list}} 和 {{locations_list}}，
為每個勢力分配控制區域。
注意：同一地點可能有多個勢力爭奪。

## 成員分配
根據 {{characters_list}}，
標記哪些角色屬於哪個勢力。
注意：角色可以是臥底或雙面人。
```

### Step 4: 設計外交矩陣
```
請建立勢力之間的關係網絡：

對於每一對勢力，定義：
1. **外交狀態**：
   - Allied（盟友）
   - Neutral（中立）
   - Tolerated（容忍/表面和平）
   - Hostile（敵對）
   - At War（戰爭狀態）

2. **緊張度 (tension)**：0-100
   - 0-30：穩定
   - 31-60：摩擦
   - 61-80：危機
   - 81-100：一觸即發

3. **衝突根源**：為什麼有矛盾？
   - 領土爭端
   - 資源競爭
   - 意識形態對立
   - 歷史恩怨

4. **檯面下的交易**：是否有秘密協議？
```

### Step 5: 寫入 faction_registry.yaml
結構化後寫入資料庫

## 派系資料範例

```yaml
factions:
  - id: "FAC_001"
    name: "天宮財閥 (Tiangong Corp)"
    tier: "S"
    type: "Corporation/Government"
    philosophy: "秩序、利益、人類優化"
    description: "控制全球靈氣帶寬的超級企業，實質上的世界政府。"
    
    assets:
      - "全球靈氣帶寬控制權"
      - "私有執法軍隊"
      - "頂尖研究設施"
    
    territory: ["REG_001"]
    notable_members: ["CHAR_002"]
    
    hierarchy:
      - rank: 1
        title: "董事會"
        privileges: "最高決策權"
      - rank: 2
        title: "執行官"
        privileges: "區域管理權"
      - rank: 3
        title: "執法者"
        privileges: "執法與逮捕權"
    
    secrets:
      - "正在秘密開發意識上傳技術"
      - "與霓虹叛軍有過去的合作關係"

relations:
  - source_id: "FAC_001"
    target_id: "FAC_002"
    status: "Hostile"
    tension: 95
    trade_agreement: false
    history: "叛軍由前財閥核心成員創立"
    secret_dealings: "偶爾進行武器技術的黑市交易"
```

## 動態更新模式

### 緊張度調整
```
事件：{{event_description}}
涉及勢力：{{faction_a}} 與 {{faction_b}}

請評估此事件對緊張度的影響：
- 當前緊張度：{{current_tension}}
- 建議調整：+/- 多少？
- 調整理由：
- 若緊張度超過 80，可能觸發的後果：
```

### 新勢力介入
```
劇情需要引入一個新勢力：{{faction_hint}}

請設計符合以下條件的勢力：
- 與現有勢力的關係定位
- 初始緊張度設定
- 對主角陣營的態度
```

## 使用時機

- **創世階段**：建立主要勢力格局
- **劇情推進**：當需要新的政治力量介入時
- **衝突升級**：調整勢力關係以推動劇情

## 與其他 Skill 的關聯

- **前置 Skill**：
  - `skill_world_builder`：需要領土資訊
  - `skill_character_forge`：需要角色資訊
- **協作 Skill**：
  - `skill_power_dynamic_updater`（計畫中）：自動調整緊張度
  - `skill_identity_validator`（計畫中）：檢查角色派系一致性
- **被使用於**：
  - `skill_scene_writer`：場景需要派系背景
  - `skill_dialogue_director`：對話需要反映派系立場

## 注意事項

1. **勢力不是非黑即白**：每個勢力都應有其合理的立場
2. **緊張度是動態的**：劇情推進應反映在緊張度變化上
3. **個人與組織可能矛盾**：角色可以不完全認同所屬組織
4. **秘密是劇情寶藏**：每個勢力的秘密都是潛在的伏筆
5. **階層提供劇情可能**：不同階層的接觸可以產生資訊差
