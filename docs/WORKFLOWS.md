# Workflows 說明文檔

Genesis Engine 共有 16 個 Workflows。

## 核心流程

### /nvGenesis - 建立新專案

創建完整的專案結構和初始設定。

```bash
/nvGenesis name=霓虹劍仙 type=賽博龐克修仙 preset=cyberpunk
```

| 參數 | 說明 | 範例 |
|------|------|------|
| `name` | 專案名稱 | `name=霓虹劍仙` |
| `type` | 類型標籤 | `type=賽博龐克修仙` |
| `preset` | 預設模板 | `preset=cyberpunk` |
| `lang` | 語言 | `lang=zh-TW` |
| `pacing` | 速度指針 | `pacing=0.5` |
| `words` | 每章字數 | `words=4000` |

### /nvChapter - 寫一章

執行完整的單章生成流程。

```bash
/nvChapter proj=霓虹劍仙
```

### /nvBatch - 批次寫作

自動執行多章寫作，含維護。

```bash
/nvBatch n=10 proj=霓虹劍仙 maint=light
```

| 參數 | 說明 | 預設 |
|------|------|------|
| `n` | 章數 | 必填 |
| `proj` | 專案 | 必填 |
| `maint` | 維護模式 | `light` |

**maint 模式**：
- `light`：每章輕量維護，批次結束完整維護（預設）
- `every`：每章完整維護
- `end`：僅批次結束維護

### /nvMaint - 維護記憶

更新所有設定檔。

```bash
/nvMaint proj=霓虹劍仙 mode=full
```

**更新範圍**：
- lore_bank.yaml（事件、伏筆）
- narrative_progress.yaml（進度）
- character_db.yaml（角色狀態）
- world_atlas.yaml（新地點）
- faction_registry.yaml（勢力變動）
- power_system.yaml（新能力）
- item_compendium.yaml（新物品）

---

## 輔助工具

### /nvStatus - 狀態總覽

顯示專案進度、角色狀態、伏筆追蹤。

```bash
/nvStatus proj=霓虹劍仙
```

### /nvPreview - 預覽規劃

預覽接下來的章節規劃。

```bash
/nvPreview n=5 proj=霓虹劍仙
```

### /nvExport - 匯出章節

匯出所有章節到單一檔案。

```bash
/nvExport proj=霓虹劍仙 fmt=md range=1-25
```

### /nvReview - 一致性檢查

執行全面的一致性審查。

```bash
/nvReview proj=霓虹劍仙 range=1-15
```

### /nvChatTest - 角色對話測試

測試角色的對話風格。

```bash
/nvChatTest "林昊" CHAR_001 proj=別讓它們進門
```

---

## 進階功能

### /nvRegen - 重新生成章節

重寫指定章節，可調整參數。

```bash
/nvRegen proj=xxx ch=5 pacing=0.2 weights="combat:0.7"
```

| 參數 | 說明 |
|------|------|
| `pacing` | 改變節奏 |
| `weights` | 調整內容權重 |
| `style` | 風格(dark/light/intense/calm) |
| `focus` | 視角焦點角色 |
| `seed` | 觸發意外(random) |
| `beat` | 只重寫特定節拍 |
| `keep` | 保留原版備份 |

### /nvImport - 導入既有內容

從已有文本導入並繼續。

```bash
/nvImport file=/path/to/novel.md proj=新專案 type=outline
```

### /nvBranch - 分支劇情

從指定章節創建劇情分支。

```bash
/nvBranch ch=10 name=替代結局 proj=霓虹劍仙
```

### /nvMirror - 架構逆向與重鑄（新）

借用外部劇情骨架，填入自己的世界觀。

```bash
# 直接文字
/nvMirror proj=霓虹劍仙 source=text content="大綱..."

# 指定檔案
/nvMirror proj=霓虹劍仙 source=file path=/path/to/outline.md

# 指定網址
/nvMirror proj=霓虹劍仙 source=url url=https://example.com

# 調整差異化（0=照搬，1=自主演化）
/nvMirror proj=霓虹劍仙 source=text content="..." divergence=0.8
```

### /nvPreset - 查看預設模板

顯示所有可用的預設模板。

```bash
/nvPreset
```

### /nvEmotion - 情感波段分析（新）

分析專案的情感曲線，檢測張力失衡。

```bash
# 分析全專案
/nvEmotion proj=霓虹劍仙

# 分析特定範圍並自動修復
/nvEmotion proj=霓虹劍仙 range=10-20 fix=true
```

### /nvDungeon - 密境/副本生成（新）

自動生成可探索的密境結構。

```bash
# 基本生成
/nvDungeon proj=霓虹劍仙 name=數據廢墟

# 完整參數
/nvDungeon proj=霓虹劍仙 name=古老伺服器 type=branching level=8 floors=3
```

---

## Workflow 連動

### 標準創作流程

```
/nvGenesis → /nvBatch → /nvStatus → /nvExport
```

### 借鏡創作流程

```
/nvMirror → /nvBatch → /nvReview → /nvExport
```

### 分支探索流程

```
/nvBranch → /nvBatch (on branch) → /nvReview
```
