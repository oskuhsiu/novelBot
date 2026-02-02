---
name: schema_re_architect
description: 架構逆向與重鑄器 - 分析外部劇情結構，映射至專案世界觀，生成新大綱
---

# 架構逆向與重鑄器 (Schema Re-Architect)

## 功能概述

此 Skill 負責分析外部小說/大綱的劇情結構，將其抽象化後映射至目標專案的世界觀、角色與力量體系，生成符合本專案設定的新章節大綱。

核心流程：**解構 (Deconstruct)** → **映射 (Map)** → **重構 (Reconstruct)**

## 輸入

- `source_content`: 外部劇情/大綱文字
- `target_config`: 目標專案的 `novel_config.yaml`
- `target_characters`: 目標專案的 `character_db.yaml`
- `target_factions`: 目標專案的 `faction_registry.yaml`
- `target_world`: 目標專案的 `world_atlas.yaml`
- `target_powers`: 目標專案的 `power_system.yaml`
- `divergence`: 差異化程度 (0-1)，預設 0.5

## 輸出

生成 `mirror_structure.yaml`：

```yaml
source_structure:
  conflict_core: ""
  character_functions: []
  turning_points: []
  emotional_curve: ""

mapping:
  characters: {}
  locations: {}
  powers: {}

generated_outline:
  - chapter_x:
      title: ""
      beats: []
      divergence_notes: ""
```

## 執行步驟

### Step 1: 結構解構 (Deconstruct)

```
分析輸入的外部素材，提取以下抽象結構：

1. 衝突核心 (Conflict Core)
   - 主要矛盾類型：權力鬥爭/生存危機/復仇/成長/救贖
   - 核心驅動力：是什麼推動劇情前進？

2. 角色功能 (Character Functions)
   - Protagonist: 主角的敘事角色
   - Mentor: 導師的功能與退場時機
   - Antagonist: 反派代表的力量
   - Allies: 盟友的互補功能
   - Betrayer: 背叛者的位置（如有）

3. 轉折節點 (Turning Points)
   - 催化劑 (≈15%): 離開舒適區
   - 第一轉折 (≈25%): 進入新世界
   - 中點轉折 (≈50%): 假勝利或假失敗
   - 黑暗時刻 (≈75%): 最低谷
   - 高潮 (≈90%): 最終對決

4. 情感曲線 (Emotional Curve)
   - 張力變化模式
   - 高潮與低谷的分布
```

### Step 2: 載入目標專案

```
讀取目標專案的所有設定檔：
- novel_config.yaml → 風格與世界觀
- character_db.yaml → 可用角色
- faction_registry.yaml → 勢力結構
- world_atlas.yaml → 場景地圖
- power_system.yaml → 力量體系
```

### Step 3: 語義映射 (Map)

```
根據解構結果，建立映射關係：

【角色對應】
- 分析來源角色的敘事功能
- 在目標角色庫中找到功能匹配者
- 若無匹配，標記為「需新增」

【場景對應】
- 分析來源場景的敘事意義（封閉/開放/危險/安全）
- 在目標地圖中找到類似場景
- 若無匹配，標記為「需新增」

【力量對應】
- 分析來源中的能力/技術解決方案
- 映射至目標力量體系
- 保持邏輯自洽
```

### Step 4: 差異化處理 (Divergence)

```
根據 divergence 參數調整映射程度：

divergence = 0.0:
  - 完全複製轉折邏輯
  - 僅替換名詞和世界觀元素

divergence = 0.3:
  - 保留大框架和主要節點
  - 細節允許變化

divergence = 0.5 (預設):
  - 保留衝突核心和主要轉折
  - 解決問題的方法自由發揮
  - 角色互動方式可調整

divergence = 0.7:
  - 僅參考情感曲線和節奏
  - 具體事件自訂

divergence = 1.0:
  - 僅借用起始動機
  - 隨後完全自主演化
```

### Step 5: 大綱重構 (Reconstruct)

```
基於映射結果，生成新的章節大綱：

對於每個轉折點：
1. 使用映射後的角色
2. 使用映射後的場景
3. 使用目標力量體系解決衝突
4. 保持目標專案的風格語氣

輸出格式：
- chapter_id
- title (符合目標風格)
- beats (細分場景)
- weight_hint (內容權重)
- divergence_notes (與來源的差異說明)
```

## 差異化範例

假設來源是《三國演義》的「三顧茅廬」：

| divergence | 輸出 |
|------------|------|
| 0.0 | 主角三次拜訪隱居高人，獲得輔佐 |
| 0.5 | 主角通過某種挑戰證明誠意，獲得 AI 系統認可 |
| 1.0 | 主角意外觸發古老協議，被動獲得能力，但附帶代價 |

## 使用時機

- 被 `workflow_nvMirror` 調用
- 當需要借用其他作品的結構時
- 進行劇情重構或改編時

## 與其他 Skill 的關聯

- **調用前置**：此 Skill 會讀取所有專案設定檔
- **調用後續**：
  - `skill_consistency_validator` 驗證生成的大綱
  - `skill_outline_architect` 可能需要調整整合
- **被調用於**：`workflow_nvMirror`

## 注意事項

1. 映射過程應保持目標專案的邏輯一致性
2. 生成的大綱需要人工審核確認
3. divergence 參數影響創作自由度，建議初次使用 0.5
4. 若來源與目標類型差異過大，建議提高 divergence
