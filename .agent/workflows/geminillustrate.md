---
description: 使用 Gemini 為小說生成插圖並自動插入章節
---

# /geminillustrate - Gemini 插畫生成與插入

專門使用 Gemini 模型（透過 generate_image 工具）依據小說內容生成插圖，並自動將圖片插入到對應的章節段落中。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=goblin_3` |
| `target` | ❌ | 生成對象 (ID 或描述)，不插入章節 | `target=CHAR_001` |
| `ch` | ❌ | 指定章節號，自動分析並插入圖片，與 `target` 二選一 | `ch=10` |
| `num` | ❌ | 生成數量（僅對 `ch` 有效），預設 1 | `num=2` |
| `style` | ❌ | 藝術風格 | `style=anime/realistic` |

## 使用範例

```
/geminillustrate target=CHAR_001 proj=goblin_3
/geminillustrate ch=10 proj=goblin_3 num=2
```

## 執行步驟

### Step 1: 確定生成內容與位置
// turbo
1. **若指定 `ch` (例如 ch=10)**:
   - 讀取 `output/chapters/chapter_{ch}.md` 的完整內容。
   - 使用 LLM 分析章節，識別 `num` 個**視覺化價值最高**的關鍵場景（例如戰鬥高潮、重要登場、環境描寫）。
   - 對於每個場景，找出其在原文中的**插入锚点**（即圖片應該插入在哪一段文字之後）。通常是該場景描寫結束後的段落。
   - 輸出：
     - `Scene 1 Prompt`: ...
     - `Scene 1 Insertion Point`: (原文的某一句話或段落末尾)
   
2. **若指定 `target`**:
   - 僅生成與展示，不涉及檔案修改。

### Step 2: 構建提示詞 (Prompting)
對於每一個確定的場景：
- 使用 `skill_illustrator` 將文字描述轉換為高解析度的 Image Prompt。
- 確保融入專案的 `style_profile`。

### Step 3: 生成圖像
呼叫 `generate_image` 工具：
- `ImageName`: `illust_ch{ch}_{scene_id}_{timestamp}`
- 生成後獲取圖片的絕對路徑。

### Step 3.5: 移動與整理圖像
// turbo
1. 建立圖片目錄（若不存在）：`mkdir -p projects/{proj}/output/images/`
2. 將生成的圖片移動到該目錄：`mv {image_path} projects/{proj}/output/images/`

### Step 4: 插入章節 (僅 ch 模式)
使用 `replace_file_content` 或 `multi_replace_file_content` 工具：
- 讀取 `output/chapters/chapter_{ch}.md`。
- 在 Step 1 確定的 `Insertion Point` 之後，插入 Markdown 圖片語法：
  
  ```markdown
  ![場景描述](../images/{image_name}.png)
  *（插圖：場景描述）*
  ```

### Step 5: 結果展示
- 顯示生成的圖像（縮圖）。
- 確認圖片已成功插入到文檔的指定位置。

## 輸出
- 圖像檔案保存於 `projects/{proj}/output/images` 目錄。
- 章節檔案 (`chapter_{N}.md`) 被更新。
