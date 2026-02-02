# Item Interactor

器具演繹器 - 根據速度指針決定道具描寫精度。

## 功能說明

當角色使用道具時，根據 `pacing_pointer` 決定描寫的詳細程度。

## 設定參數

```yaml
item_interaction_settings:
  # 細節展開等級
  detail_levels:
    0.1: "完整描寫道具操作的每個步驟"
    0.5: "標準描寫，點到為止"
    1.0: "僅提及道具名稱"
    
  # 可展開的維度
  interaction_aspects:
    - mechanism: true    # 運作機制
    - visual: true       # 視覺效果
    - sound: true        # 聲音描寫
    - tactile: true      # 觸感描寫
    - consequence: true  # 使用後果
```

## 執行邏輯

### Step 1: 讀取道具定義

從 `item_compendium.yaml` 獲取道具資訊

### Step 2: 根據 Pacing 決定展開程度

**pacing_pointer = 0.1（極細）- 宇宙飛船啟動**：
```markdown
林昊的手指懸停在控制台上方。

他深吸一口氣，開始按照標準程序啟動飛船。首先是主電源——他按下那個略微磨損的紅色按鈕，駕駛艙瞬間被柔和的藍光籠罩。儀表盤一個接一個亮起，像是沉睡的眼睛逐漸睜開。

「反應堆預熱中......」電腦的合成聲音響起。

接著是姿態控制系統。他扳動左手邊的三個開關——上、中、下，每一個都發出令人安心的咔噠聲。船體輕微震顫，那是陀螺儀開始轉動。

引擎點火。

這是最關鍵的一步。他將節流閥緩慢推進，感受著金屬握把傳來的微微震動。船身後方傳來低沉的轟鳴，起初像是野獸的呼吸，隨後越來越響，直到整個駕駛艙都在共振。

當速度表指針跨過紅線時，空間開始扭曲。艙外的星空變成拉長的光線，那是空間摺疊的前兆——

「跳躍準備完成。」

他握緊操縱桿，踏入未知......
```

**pacing_pointer = 1.0（極快）**：
```markdown
林昊啟動飛船，瞬間消失在視界。
```

### Step 3: 消耗追蹤

如果道具是消耗品，更新 `character_db.yaml`：

```yaml
consumption_check:
  item_id: "CON_001"
  type: "consumable"
  uses_before: 3
  uses_after: 2
  update_inventory: true
```

## 輸出格式

```yaml
item_interaction:
  item: "超時空跳躍模組"
  action: "activate"
  pacing: 0.3
  
  generated_text: "..."
  word_count: 450
  
  aspects_used:
    - mechanism: "描寫啟動步驟"
    - visual: "光線扭曲效果"
    - sound: "引擎轟鳴"
    
  inventory_update:
    required: false
```
