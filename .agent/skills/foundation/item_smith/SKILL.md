# Item Smith

器具鍛造師 - 根據風格自動生成道具。

## 功能說明

根據 `novel_config.yaml` 的風格定調，動態生成符合世界觀的道具。

## 使用情境

- 劇情需要新道具時自動生成
- 將通用道具轉化為風格化道具
- 填充寶箱/獎勵/戰利品

## 執行邏輯

### Step 1: 讀取風格設定

```yaml
style_input:
  genre: "賽博龐克修仙"
  tone: "冷峻、高科技與古風混搭"
  linguistic_rules:
    - "術語混合：築基防火牆、金丹反應堆"
```

### Step 2: 接收需求

```yaml
item_request:
  category: "Weapon"
  base_concept: "長劍"
  rarity: "Epic"
  purpose: "主角的新武器"
```

### Step 3: 風格轉化

| 基礎概念 | 賽博龐克修仙風格 | 玄幻仙俠風格 | 末日生存風格 |
|----------|------------------|--------------|--------------|
| 長劍 | 震動粒子刀 | 靈劍·斷水 | 合金鋼刀 |
| 盔甲 | 量子護盾模組 | 玄武甲 | 防刺背心 |
| 藥品 | 納米修復液 | 回氣丹 | 急救包 |
| 交通工具 | 反重力載具 | 御劍飛行 | 改裝摩托 |

### Step 4: 生成完整定義

```yaml
generated_item:
  id: "WEP_AUTO_001"
  name: "震動粒子刀"
  category: "Weapon"
  sub_type: "Cyber-Sword"
  rarity: "Epic"
  
  description: |
    由舊時代合金重新鍛造，刀身內嵌高頻震動模組。
    啟動時粒子共振產生的光芒如同古老的劍氣。
    
  logic_module: "PWR_001"  # 連結力量體系
  
  attributes:
    damage: "Physical/Energy Hybrid"
    special_effect: "切割時產生電磁脈衝"
    durability: 85
    
  acquisition:
    method: "Quest Reward"
    quest: "第X章支線任務"
    
  visual_style: |
    刀身呈暗銀色，啟動時邊緣泛起藍光。
    握柄處有古老的符文與現代電路交織。
```

### Step 5: 寫入物品庫

自動添加到 `config/item_compendium.yaml`

## 批量生成模式

可一次生成多個相關道具：

```yaml
batch_request:
  theme: "黑市交易獎勵"
  count: 5
  rarity_distribution:
    common: 2
    uncommon: 2
    rare: 1
```

## 輸出

```
🔨 器具鍛造完成
───────────────────────────
名稱：震動粒子刀
稀有度：Epic
類型：Weapon/Cyber-Sword
───────────────────────────
特效：切割時產生電磁脈衝
已寫入：item_compendium.yaml
───────────────────────────
```
