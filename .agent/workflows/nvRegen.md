---
description: 重新生成指定章節
---

# /nvRegen - 重新生成

用不同參數重新生成指定章節。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `ch` | ✅ | 章節號 | `ch=5` |
| `pacing` | ❌ | 覆蓋速度指針 | `pacing=0.2` |
| `weights` | ❌ | 覆蓋權重 | `weights="combat:0.7,dialogue:0.1"` |
| `style` | ❌ | 風格調整 | `style=dark` 或 `style=light` |
| `focus` | ❌ | 視角焦點角色 | `focus=CHAR_002` |
| `seed` | ❌ | 意外種子 | `seed=random` 或 `seed=none` |
| `beat` | ❌ | 只重寫特定節拍 | `beat=B5_3` |
| `keep` | ❌ | 保留原版備份 | `keep=true` |

## 使用範例

```
/nvRegen proj=霓虹劍仙 ch=5
/nvRegen proj=霓虹劍仙 ch=5 pacing=0.2
/nvRegen proj=劍來 ch=10 weights="combat:0.7,dialogue:0.1"
/nvRegen proj=霓虹劍仙 ch=5 style=dark focus=CHAR_002
/nvRegen proj=霓虹劍仙 ch=5 seed=random
/nvRegen proj=霓虹劍仙 ch=5 beat=B5_3
```

## 參數詳解

### `pacing`
覆蓋本章的速度指針：
- `0.1` - 極慢節奏，細膩展開
- `0.5` - 中等節奏
- `1.0` - 快節奏

### `weights`
臨時覆蓋內容權重：
```
weights="combat:0.7,dialogue:0.1,internal:0.1,scenery:0.1"
```

### `style`
調整風格語氣：
- `dark` - 更陰暗、沉重
- `light` - 更輕鬆、明快
- `intense` - 更緊張
- `calm` - 更平靜

### `focus`
改變視角焦點到其他角色（限第三人稱受限視角）

### `seed`
控制意外事件：
- `random` - 強制觸發隨機意外
- `none` - 禁用意外事件
- 不設定 - 使用正常邏輯

## 執行步驟

### Step 1: 備份原版
// turbo
- 若 `keep=true`，備份原章節到 `output/chapters/chapter_{ch}_backup.md`
- 讀取原章節的 `ending_summary`（從 ChromaDB `chapters` collection）

### Step 2: 清理舊章節衍伸資料
// turbo

> [!CAUTION]
> **重寫章節 = 該章產生的所有資料都可能失效**
> 必須在重新生成前清理，否則會留下與新內容矛盾的舊記錄。

```yaml
清理項目:
  ChromaDB lore_bank:
    # 刪除該章的所有 lore 記錄（事件、伏筆、關係變化等）
    # .venv/bin/python tools/lore_update.py --proj {proj} delete --ch {ch}
    
  ChromaDB chapters:
    # 不用刪除 — lore_update chapter 是 upsert，重寫後會自動覆蓋
    
  角色資料庫（SQLite novel.db）:
    # 暫不回退（角色狀態難以自動回退）
    # 重寫後由 nvMaint 重新更新
```

### Step 3: 載入原節拍 + 應用參數
// turbo
1. 讀取原章節的節拍結構
2. 根據提供的參數（`pacing`, `weights`, `style`, `focus`, `seed`, `beat`）調整設定

### Step 4: 重新生成
執行 `/nvChapter` 邏輯，但只針對指定章節。
- 若設定 `beat` 參數，僅重寫該節拍的場景

### Step 5: 重新維護（強制）
// turbo

> [!IMPORTANT]
> 重寫章節後**必須**執行輕量維護，確保資料庫與新內容同步。

```yaml
必更新:
  ChromaDB chapters collection:
    - `.venv/bin/python tools/lore_update.py --proj {proj} chapter ...` 寫入新的 ending_summary（upsert 覆蓋）
    
  ChromaDB lore_bank:
    - 根據新內容重新產生 lore 記錄（事件、角色記憶、伏筆等）
    - 使用 `.venv/bin/python tools/lore_update.py --proj {proj} event ...` 寫入
    
  角色資料庫（SQLite）:
    - 使用 char_query update-state 更新涉及角色的 current_state（若重寫後有變化）
    ```bash
    .venv/bin/python tools/char_query.py --proj {proj} update-state {CHAR_ID} --json '{...}'
    ```

  narrative_progress.yaml:
    - 更新字數統計
```

### Step 6: 覆寫章節 + 輸出
// turbo
覆寫 `output/chapters/chapter_{ch}.md`

```
═══════════════════════════════════════════════════════
  🔄 第 {ch} 章重新生成完成
═══════════════════════════════════════════════════════
  章節標題：{title}
  原版字數：{old_words} → 新版字數：{new_words}
  ending_summary：已更新 ✅
  ChromaDB lore：已清理舊記錄 + 重建 ✅
  備份：{keep ? '已保存' : '未保存'}
═══════════════════════════════════════════════════════
```

### Step 7: Cascade Warning（非最後一章時）

> [!WARNING]
> **連鎖影響檢查**
> 若重寫的**不是最後一章**，後續章節的連貫性可能受影響：
> - 新的 `ending_summary` 可能與第 {ch+1} 章開頭矛盾
> - 新增/移除的事件可能影響後續劇情邏輯
>
> 建議執行：
> ```
> /nvReview proj={proj} range={ch}-{last_chapter} mode=light
> ```

## 輸出

重新生成的章節寫入原位置，若設定 `keep=true` 則保留備份。
