---
name: world_builder
description: 世界觀編織者 - 構建故事舞台的地理、規則與社會體系，生成 world_atlas.yaml
---

# 世界觀編織者 (World Builder)

## 功能概述

此 Skill 負責構建故事發生的舞台，包含地理環境、物理法則、社會體系。它會讀取風格設定，產生完整的世界觀資料並寫入 `world_atlas.yaml`。

## 輸入

1. 從 `templates/novel_config.yaml` 讀取：
   - `style_profile.genre`：小說類型
   - `world_rules`：世界觀核心規則

2. 從 `output/style_guide.md` 讀取風格指南

3. 使用者提供的世界觀關鍵字（可選）

## 輸出

更新 `templates/world_atlas.yaml`，包含：
- 區域定義 (regions)
- 地點細節 (locations)
- 特殊區域 (zones)
- 傳送網絡 (transit_network)

## 執行步驟

### Step 1: 讀取基礎設定
```
讀取 templates/novel_config.yaml
提取 style_profile.genre 與 world_rules
讀取 output/style_guide.md 獲取風格指南
```

### Step 2: 生成世界觀框架
```
你是一位擅長構建奇幻/科幻世界的設定專家。
請根據以下參數，設計這個故事世界的基礎架構：

【類型】：{{genre}}
【核心規則】：{{world_rules}}
【風格要求】：{{style_guide_summary}}

請輸出：

## 地理概覽
1. 世界整體結構（如：多層城市、多國大陸、星際聯邦）
2. 2-4 個主要區域，每個區域包含：
   - 名稱（符合風格的命名）
   - 類型（都市/荒野/禁地等）
   - 氣候與環境特色
   - 核心特徵（一句話描述其獨特性）

## 關鍵地標
為每個區域設計 1-2 個重要地點：
- 名稱
- 功能（居住/商業/禁區/資源點）
- 進入條件或限制
- 潛在劇情鈎子

## 禁忌之地
設計 1 個危險區域或密境：
- 名稱
- 危險等級（1-10）
- 特殊機制
- 吸引冒險者的原因
```

### Step 3: 深化地點細節
```
針對上述的「{{region_name}}」區域，請詳細設計其內部結構：

輸出格式：
- 子地點名稱
- 類型
- 描述（50字以內）
- 感官特徵（視覺、聽覺、嗅覺各一句）
- 出入口設定（通往何處、需要什麼條件）
- 可能遇到的角色類型
```

### Step 4: 設計傳送/交通網絡
```
這個世界的主要交通方式是什麼？

考慮因素：
- 符合 {{genre}} 的科技/魔法水平
- 區域之間的距離與隔閡
- 社會階層對交通的影響

請設計：
1. 主要交通工具類型
2. 連接哪些區域
3. 使用條件或成本
```

### Step 5: 寫入 world_atlas.yaml
將上述資料結構化後寫入模板

## 世界觀資料範例

```yaml
regions:
  - id: "REG_001"
    name: "上層天宮"
    type: "Metropolis"
    description: "懸浮於污染雲層之上的財閥聚集地，永恆的霓虹晝夜。"
    climate: "人工恆溫，空氣過濾"
    tags: ["High-Tech", "Elite", "Corporate"]
    
    locations:
      - id: "LOC_101"
        name: "聽劍閣"
        type: "Skyscraper"
        description: "地下黑市與高層會所並存的灰色地帶。"
        tags: ["Neutral Zone", "Black Market"]
        access_points:
          - target: "LOC_102"
            type: "Elevator"
            requirement: "Security Pass Level 4"
```

## 使用時機

- **創世階段**：在 `style_setter` 之後執行
- **劇情需要**：當主角需要前往新區域時，可單獨呼叫來擴展世界
- **按需擴張**：不必一次生成所有區域，可隨劇情逐步補充

## 與其他 Skill 的關聯

- **前置 Skill**：`skill_style_setter`（需要風格指南）
- **後續 Skill**：
  - `skill_faction_forge`：在地點上建立勢力
  - `skill_scene_writer`：使用地點資料寫場景
- **協作 Skill**：
  - `skill_chaos_engine`：可在現有地點生成特殊事件點

## 擴展功能

### 按需擴張模式
```
劇情需要主角前往一個「荒廢的研究設施」。
請根據現有的 world_atlas.yaml，在 {{parent_region}} 下新增此地點。

要求：
- 與現有世界觀邏輯一致
- 遵循命名風格
- 設定進入條件
```

### 密境生成模式
```
請設計一個等級為 {{hazard_level}} 的「{{zone_type}}」密境。

要求：
- 位於 {{parent_region}} 附近
- 特殊機制：{{mechanics_hint}}
- 包含 2-3 個興趣點
```

## 注意事項

1. 地點命名要符合世界觀風格（賽博龐克用科技感名稱，玄幻用古風名稱）
2. 每個地點都應有潛在的劇情價值，避免只是背景
3. 出入口設定要合理，為劇情衝突創造條件
4. 地點的「氛圍」應與可能發生的劇情類型匹配
