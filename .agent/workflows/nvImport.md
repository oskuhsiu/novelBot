---
description: 從既有內容導入並繼續寫作
---

# /nvImport - 導入既有內容

從已有的小說內容導入，建立資料庫後繼續寫作。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `file` | ✅ | 來源檔案 | `file=existing.txt` |
| `proj` | ✅ | 新專案名稱 | `proj=霓虹劍仙` |
| `type` | ❌ | 小說類型 | `type=仙俠` |
| `lang` | ❌ | 語言 | `lang=zh-TW` |

## 使用範例

```
/nvImport file=~/novels/my_novel.txt proj=霓虹劍仙 type=賽博龐克
/nvImport file=existing.md proj=劍來
```

## 執行步驟

### Step 1: 讀取來源
// turbo
讀取指定檔案內容

### Step 2: 分析結構
分析既有內容：
- 章節劃分
- 角色提取
- 場景識別
- 事件提取

### Step 3: 建立專案
// turbo
建立 `projects/{proj}/` 目錄結構

### Step 4: 提取角色
從文本中識別角色：
- 名稱
- 出場頻率
- 性格推測
- 關係推測

寫入 `character_db.yaml`，然後執行遷移寫入 SQLite：
```bash
.venv/bin/python tools/migrate_db.py --proj {proj} char
```

### Step 5: 提取場景
識別地點和場景：
- 場景名稱
- 場景描述
- 出現章節

寫入 `world_atlas.yaml`

### Step 6: 建立記憶庫
提取已發生事件：
- 關鍵事件
- 關係變動
- 物品交換

使用 `.venv/bin/python tools/lore_update.py --proj {proj} event ...` 寫入 ChromaDB `lore_bank` collection。

### Step 7: 分析風格
分析既有風格特徵：
- 句式偏好
- 用詞風格
- 節奏特徵

寫入 `output/style_guide.md`

### Step 8: 複製章節並建立向量索引
// turbo
將既有章節複製到 `output/chapters/`
對於每一章，生成 `ending_summary` 並使用 `.venv/bin/python tools/lore_update.py --proj {proj} chapter ...` 寫入 ChromaDB。

### Step 9: 準備繼續
設定 `narrative_progress.yaml`:
- `current_chapter` = 既有章節數 + 1

生成後續大綱建議，寫入 `story_outline.yaml`

## 輸出

專案建立完成，可用 `/nvChapter proj={proj}` 繼續寫作。
