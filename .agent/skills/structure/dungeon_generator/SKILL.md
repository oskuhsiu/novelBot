---
name: dungeon_generator
description: 地城構造師 - 自動生成密境/副本的房間結構
---

# Dungeon Generator

地城構造師 - 自動生成密境/副本的房間結構。

## 功能說明

針對 `type: "Dungeon"` 的區域，自動生成內部房間結構、陷阱設定與寶物分布。

## 使用情境

- 主角進入新的密境/副本
- 需要生成探索地圖
- 隨機地城生成

## 參數設定

```yaml
dungeon_settings:
  # 地城類型
  archetypes:
    - linear: "線性推進（一條主路）"
    - branching: "分支結構（多條路線）"
    - hub: "中心輻射（核心+分支）"
    - maze: "迷宮式（複雜交錯）"
    
  # 難度等級
  difficulty_scaling:
    1-3: "新手區"
    4-6: "進階區"
    7-9: "高難度"
    10: "終極挑戰"
    
  # 房間類型分布
  room_distribution:
    combat: 0.4      # 戰鬥房
    puzzle: 0.2      # 謎題房
    treasure: 0.15   # 寶藏房
    rest: 0.1        # 休息房
    boss: 0.05       # BOSS房
    empty: 0.1       # 空房
```

## 執行邏輯

### Step 1: 讀取區域設定

從 `world_atlas.yaml` 獲取密境基本資訊：

```yaml
zone_input:
  id: "ZONE_001"
  name: "數據廢墟"
  hazard_level: 8
  mechanics: "靈氣頻段不穩定"
```

### Step 2: 生成結構

```yaml
dungeon_structure:
  type: "branching"
  total_rooms: 12
  floors: 3
  
  layout:
    floor_1:
      rooms:
        - id: "R1_1"
          type: "entrance"
          description: "廢棄的數據節點大廳"
          exits: ["R1_2", "R1_3"]
          
        - id: "R1_2"
          type: "combat"
          description: "損壞的伺服器室"
          enemies: ["數據殘魂 x3"]
          exits: ["R1_4"]
          
        - id: "R1_3"
          type: "puzzle"
          description: "密碼鎖保險庫"
          puzzle_type: "解密"
          reward: "古代算法碎片"
          exits: ["R1_4"]
          
        - id: "R1_4"
          type: "rest"
          description: "倖存的充電站"
          effects: ["恢復30%能量"]
          exits: ["floor_2_entrance"]
```

### Step 3: 填充內容

根據世界觀生成具體內容：

```yaml
room_content:
  enemies:
    - name: "數據殘魂"
      level: 7
      abilities: ["腐蝕攻擊", "數據干擾"]
      drops: ["能量碎片", "故障模組"]
      
  traps:
    - name: "頻段錯亂區"
      trigger: "踩踏"
      effect: "隨機傳送到其他房間"
      disarm: "使用穩頻器"
      
  treasures:
    - name: "古老伺服器核心"
      rarity: "Legendary"
      location: "隱藏房間"
      requirement: "解開所有謎題"
      
  puzzles:
    - name: "算法重組"
      description: "將散落的代碼碎片排列正確順序"
      hints: ["伺服器日誌中有線索"]
      solution: "3-1-4-1-5-9-2-6"
```

### Step 4: BOSS 房設計

```yaml
boss_room:
  id: "R3_BOSS"
  type: "boss"
  description: "古老伺服器祭壇"
  
  boss:
    name: "廢棄協議守護者"
    level: 10
    abilities:
      - name: "協議重載"
        effect: "重置所有增益效果"
      - name: "數據風暴"
        effect: "全場持續傷害"
    phases: 3
    weak_points: ["核心暴露期"]
    
  mechanics:
    - "每損失25%血量進入下一階段"
    - "第二階段召喚小怪"
    - "第三階段場地變化"
    
  rewards:
    - "古老祭壇核心"
    - "協議碎片 x3"
    - "生存積分 +500"
```

### Step 5: 寫入世界地圖

擴展 `world_atlas.yaml`：

```yaml
write_to:
  zones:
    - id: "ZONE_001"
      internal_structure:
        floors: 3
        rooms: 12
        room_map: [...]
```

## 輸出格式

```
🏰 地城生成完成
═══════════════════════════════════════════════════
  名稱：數據廢墟
  類型：分支結構
  樓層：3
  房間：12
───────────────────────────────────────────────────
  樓層分布：
  ├─ F1：入口大廳 → 戰鬥室/謎題室 → 休息站
  ├─ F2：走廊 → 寶藏室/陷阱區 → 隱藏房
  └─ F3：前廳 → BOSS戰場
───────────────────────────────────────────────────
  內容統計：
  ├─ 戰鬥房：5
  ├─ 謎題房：2
  ├─ 寶藏房：2
  ├─ 休息房：1
  ├─ BOSS房：1
  └─ 空房：1
═══════════════════════════════════════════════════
```
