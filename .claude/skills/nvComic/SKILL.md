---
description: 將小說章節轉換為漫畫格式 (Webtoon 風格)
---

# /nvComic - 小說轉漫畫 (Novel to Comic Workflow)

將指定章節轉換為漫畫分鏡腳本，並生成對應的漫畫圖像。此工作流會自動管理角色與艦船的一致性參考圖。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=Mankind` |
| `ch` | ✅ | 章節號 | `ch=21` |
| `style` | ❌ | 藝術風格 (預設: Webtoon) | `style="cyberpunk, dark comic"` |
| `panels` | ❌ | 限制生成的格數 (用於測試) | `panels=5` |
| `provider` | ❌ | 圖像生成服務 (預設: google) | `provider=openrouter` |

## 使用範例

```
/nvComic proj=Mankind ch=21
/nvComic proj=Mankind ch=21 provider=openrouter
```

## 執行步驟

### Step 0: 初始化與檢查
// turbo
1. 建立必要的目錄結構：
   - `mkdir -p projects/{proj}/assets/comic/refs/` (存放角色/艦船參考圖)
   - `mkdir -p projects/{proj}/output/comic/ch_{ch}/` (存放本章漫畫輸出)

### Step 1: 生成漫畫腳本 (Script Generation)
讀取 `projects/{proj}/output/chapters/chapter_{ch}.md`，使用 LLM 分析並生成漫畫腳本：

1. **分析內容**：
   - 識別場景、角色、對話、動作、分鏡。
2. **生成結構化腳本** (YAML 格式)：
   - 儲存至 `projects/{proj}/output/comic/ch_{ch}/script.yaml`
   - 包含欄位：
     - `panel_id`: 序號
     - `description`: 畫面詳細描述 (作為 Image Prompt 的基礎)
     - `characters`: 出場角色列表 (需與角色資料庫中的名稱一致)
     - `dialogue`: 對話內容 (可留空)
     - `composition`: 構圖 (Close-up, Wide shot, etc.)

> [!TIP]
> **Prompt 建議**
> "You are a professional comic script writer/director. Convert the following novel chapter into a **HIGH-DENSITY, CINEMATIC** visual script for a Webtoon.
> **CRITICAL RULES for STRIP MODE:**
> 1. **Group by Strips**: Organize panels into `strip_id` groups (3-4 panels per strip) based on scene flow.
> 2. **Narrative-Driven Pacing**: Use as many strips as needed. Decompress action into multiple panels within a strip.
> 3. **Input Format**: Output as YAML with `strip_id`, `panels` (list of descriptions), and a `combined_prompt` for the entire strip.
>    - `combined_prompt`: "Comic strip format, vertical layout, 4 panels. Panel 1: [desc], Panel 2: [desc]..."
> Output as YAML."

### Step 2: 資產一致性檢查 (Ref Check & Gen)
讀取 `script.yaml` 的 `characters` (角色) 與 `assets` (物件/場景) 列表。

**對於每一個實體 (Entity)**：
1. **檢查是否存在**：查看 `projects/{proj}/assets/comic/refs/{name}.png`。
2. **若不存在 (MISSING)**：
   - 🔍 **查詢外觀**：使用 `.venv/bin/python tools/char_query.py --proj {proj} get-base {CHAR_ID}` 或從 `script.yaml` 描述中提取特徵。
   - 🎨 **生成參考圖**：
     - Prompt: "Character sheet of {name}, {description}, white background, full body, multiple angles, {style} style." (若是物件則改為 Object sheet)。
     - Tool: `generate_image(prompt=..., image_name="{name}")`。
     - Move: 將生成圖移至 `projects/{proj}/assets/comic/refs/{name}.png`。
   - ✅ **確認**：確保所有登場角色都有對應的 `.png` 檔案。

### Step 3: 生成漫畫 (2x2 Grid Generation)
讀取 `script.yaml`，依序生成每一個 Strip。
**強制使用 2x2 Grid 佈局以獲得最佳解析度。**

1. **構建 Prompt**：
   - 必須包含：`A square comic strip page with 4 panels arranged in a 2x2 grid.`
   - 必須包含：`Use the provided character reference for {name} ({feature description}).`
   - 分鏡描述：`Top-Left: ..., Top-Right: ..., Bottom-Left: ..., Bottom-Right: ...`
   - 風格：`{style}, masterpiece, best quality.`
2. **引用參考圖**：
   - Tool `generate_image` 的 `image_paths` 參數 **必須** 包含該 Strip 主要角色的參考圖路徑 (如 `.../refs/CHAR_MC.png`)。
3. **生成與儲存**：
   - Image Name: `strip_{id}` (例如 `strip_1`)。
   - 系統會自動生成 `strip_{id}.png` (2x2 Grid 原圖)。
4. **速率限制 (Rate Limiting)**：
   - ⚠️ **Batch Mode Warning**: 若連續生成多個 Strip，**必須** 在每次生成後等待 **40秒**。
   - Command: `run_command(sleep 40)`。
   - 這是為了避免 Google Imagen 3 的 `503/429` 錯誤。

> [!NOTE]
> **Strip Mode**: 每次生成 3-4 格，大幅降低 API 呼叫次數並保持光影連貫性。

### Step 4: 後期處理 (Slicing & Assembly)
// turbo
將生成的 2x2 Grid 切割為垂直 Webtoon 格式，並更新檢視器。

1. **切割圖片**：
   - 執行 `tools/slice_grid.py` (需在 `.venv` 下運行 Pillow)。
   - Command: `.venv/bin/python tools/slice_grid.py projects/{proj}/output/comic/ch_{ch}/strip_*.png`
   - 這會生成 `strip_{id}_p1.png` ~ `strip_{id}_p4.png`。

2. **更新檢視器**：
   - 確保 `projects/{proj}/output/comic/ch_{ch}/view.html` 包含動態加載腳本 (Dynamic Landscape-to-Portrait Loader)。
   - 檢視器會自動偵測 `_p1.png` 是否存在，若存在則顯示垂直堆疊的 Panel，否則顯示原圖。

### Step 5: 結果展示
- ✅ **漫畫腳本**: `projects/{proj}/output/comic/ch_{ch}/script.yaml`
- ✅ **資產庫**: `projects/{proj}/assets/comic/refs/` (已更新)
- ✅ **檢視器**: `projects/{proj}/output/comic/ch_{ch}/view.html` (請用瀏覽器開啟)

### Step 5: 結果展示
- 顯示生成的漫畫腳本路徑 `projects/{proj}/output/comic/ch_{ch}/script.yaml`
- 顯示 HTML 檢視器路徑 `projects/{proj}/output/comic/ch_{ch}/view.html`
- 若環境支援，嘗試直接顯示第一張生成的 Panel。

## 輸出結果

- **漫畫腳本**: `projects/{proj}/output/comic/ch_{ch}/script.yaml`
- **參考圖**: `projects/{proj}/assets/comic/refs/` (累積)
- **漫畫圖檔**: `projects/{proj}/output/comic/ch_{ch}/`
- **檢視器**: `projects/{proj}/output/comic/ch_{ch}/view.html`
