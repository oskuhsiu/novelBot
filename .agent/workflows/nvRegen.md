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
若 `keep=true`，備份原章節到 `output/chapters/chapter_{ch}_backup.md`

### Step 2: 載入原節拍
// turbo
讀取原章節的節拍結構

### Step 3: 應用參數
// turbo
根據提供的參數調整設定

### Step 4: 重新生成
執行 `/nvChapter` 邏輯，但只針對指定章節

### Step 5: 輸出
// turbo
覆寫 `output/chapters/chapter_{ch}.md`

## 輸出

重新生成的章節寫入原位置，若設定 `keep=true` 則保留備份。
