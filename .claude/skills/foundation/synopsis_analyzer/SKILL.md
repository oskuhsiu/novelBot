---
name: synopsis_analyzer
description: 簡述分析器 - 從文字簡述分析出類型、大綱結構、角色概念
---

# 簡述分析器 (Synopsis Analyzer)

## 功能概述

此 Skill 負責分析用戶提供的故事簡述（文字或檔案），從中提取：
- 小說類型與風格
- 建議的大綱（Arc）數量與內容
- 各 Arc 的細目（SubArc）摘要
- 角色概念提示
- 世界觀提示

## 輸入

1. 簡述文字（直接或從檔案讀取）
2. 可選的用戶覆蓋指定（如已指定 type，則以用戶為準）

## 輸出

```yaml
synopsis_analysis:
  # 自動分析結果
  type: "主類型/次類型/風格標籤"
  tone: "語氣描述"
  
  # 建議結構
  suggested_arcs: 8
  
  # 各卷摘要與細目
  arc_summaries:
    - arc_id: 1
      title: "卷名"
      summary: "本卷主題摘要"
      subarcs:
        - "細目1摘要"
        - "細目2摘要"
        - ...
  
  # 角色提示
  character_hints:
    - role: protagonist
      concept: "角色概念描述"
      traits: ["特質1", "特質2"]
    - role: antagonist
      concept: "..."
    - role: mentor
      concept: "..."
  
  # 世界觀提示
  world_hints:
    setting: "時代/世界類型"
    special_rules: ["特殊規則1", "特殊規則2"]
    key_locations: ["重要地點1", "重要地點2"]
```

## 執行步驟

### Step 1: 載入簡述
```
若 source=text：使用 content 參數
若 source=file：讀取 path 指定的檔案
```

### Step 2: 類型分析
```
你是一位資深的小說編輯。
請分析以下故事簡述，判斷其類型與風格：

【簡述內容】
{{synopsis}}

請輸出：
1. **主類型**：如「仙俠」「都市」「科幻」「懸疑」「言情」等
2. **次類型**：如「輕鬆」「黑暗」「熱血」等
3. **風格標籤**：如「穿越」「系統」「基建」「群像」等
4. **語氣**：如「幽默吐槽」「沉穩大氣」「緊張刺激」等

格式：type: "主類型/次類型/風格標籤"
```

### Step 3: 結構分析
```
請分析這個故事可以分成幾個主要階段（Arc/卷）：

【簡述內容】
{{synopsis}}

分析要點：
1. 識別故事的起始狀態
2. 識別主要轉折點
3. 識別每個階段的核心主題
4. 每個 Arc 建議長度差不多

輸出格式：
- 建議 Arc 數量
- 每個 Arc 的標題和摘要
```

### Step 4: 細目拆解
```
對於每個 Arc，請拆解出 5-10 個細目（SubArc）：

【Arc 資訊】
Arc {{arc_id}}: {{arc_title}}
{{arc_summary}}

請輸出該 Arc 需要完成的具體情節點，每個用一句話描述。
確保：
- 首個 SubArc 承接前一 Arc 或故事開始
- 末個 SubArc 設下懸念或銜接下一 Arc
- 各 SubArc 之間有邏輯遞進
```

### Step 5: 角色識別
```
請從簡述中識別角色概念：

【簡述內容】
{{synopsis}}

對於每個識別出的角色，輸出：
- role：protagonist/antagonist/mentor/sidekick/other
- concept：角色概念描述
- traits：主要特質列表

若簡述中未明確提及某類角色，可標記為 "待創建"。
```

### Step 6: 世界觀提示
```
請從簡述中提取世界觀設定線索：

【簡述內容】
{{synopsis}}

分析：
1. setting：時代背景、世界類型
2. special_rules：特殊規則（魔法體系、科技設定等）
3. key_locations：重要地點
4. power_system_hints：力量體系提示

若簡述中未明確，可推測合理的設定。
```

### Step 7: 輸出分析結果
整合所有分析，輸出 `synopsis_analysis` 結構供後續步驟使用。

## 範例

### 輸入簡述
```
一個現代程式設計師穿越到修仙世界，發現這裡的修士用靈石驅動的計算陣來推演功法。
他利用現代的編程思維，從最底層的雜役弟子開始，一步步優化宗門的生產效率，
最終建立起一個橫跨大陸的「靈網」通訊系統，成為一代技術大能。
```

### 輸出分析
```yaml
synopsis_analysis:
  type: "修仙/輕鬆/穿越/基建/系統"
  tone: "輕鬆詼諧、技術流、逆襲爽文"
  
  suggested_arcs: 8
  
  arc_summaries:
    - arc_id: 1
      title: "第一卷：雜役弟子的日常"
      summary: "主角穿越覺醒，發現世界規則，開始利用編程思維理解修仙"
      subarcs:
        - "穿越覺醒，發現自己是雜役弟子"
        - "發現靈石計算陣，嘗試用編程思維理解"
        - "優化一個小流程，引起注意"
        - "被內門弟子刁難，危機"
        - "利用技術解決危機，小露鋒芒"
        
    - arc_id: 2
      title: "第二卷：外門崛起"
      summary: "晉升外門弟子，開始系統性改造宗門效率"
      subarcs:
        - "晉升外門，獲得更多權限"
        - "發現宗門效率問題"
        - ...
        
  character_hints:
    - role: protagonist
      concept: "現代程式設計師穿越，邏輯思維強，善於優化流程"
      traits: ["理性", "技術宅", "低調", "善於發現規律"]
    - role: mentor
      concept: "待創建 - 可能是發現主角才能的長老"
    - role: antagonist  
      concept: "待創建 - 可能是傳統派系的守舊者"
      
  world_hints:
    setting: "修仙世界，但融合了計算科技概念"
    special_rules: 
      - "靈石可以驅動計算陣"
      - "功法推演需要大量計算"
    key_locations:
      - "宗門（主角所在）"
      - "靈石礦脈"
      - "通訊樞紐（後期建設）"
    power_system_hints:
      - "傳統修仙境界體系"
      - "計算陣等級體系"
      - "靈網技術等級"
```

## 使用時機

- **nvGenesis**：用戶提供 source 參數時調用
- **nvImport**：導入外部內容時分析結構

## 注意事項

1. **用戶優先**：若用戶明確指定 type、arcs 等，以用戶為準
2. **合理推測**：簡述不完整時，可做合理推測，但標記為"推測"
3. **靈活處理**：簡述長度差異大，短簡述可能只有 3-5 個 Arc
4. **保留原意**：分析應忠於簡述原意，不要過度發散
