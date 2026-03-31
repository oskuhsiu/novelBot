---
description: 重新生成指定章節
---

# /nvRegen - 重新生成

透過 nvDraft + nvExpand 重新生成指定章節，取代原版。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `ch` | ✅ | 章節號 | `ch=5` |
| `direction` | ❌ | 劇情導引（覆蓋原節拍） | `direction="改為伏擊失敗"` |
| `pacing` | ❌ | 覆蓋速度指針 | `pacing=0.2` |
| `weights` | ❌ | 覆蓋權重 | `weights="combat:0.7,dialogue:0.1"` |
| `style` | ❌ | 風格調整 | `style=dark` |
| `focus` | ❌ | 視角焦點角色 | `focus=CHAR_002` |
| `seed` | ❌ | 意外種子 | `seed=random` / `seed=none` |
| `keep` | ❌ | 保留原版備份 | `keep=true` |
| `review` | ❌ | 自動審查（預設 `true`） | `review=false` |

## 使用範例

```
/nvRegen proj=霓虹劍仙 ch=5
/nvRegen proj=霓虹劍仙 ch=5 direction="改為敵方先發制人" keep=true
/nvRegen proj=劍來 ch=10 weights="combat:0.7,dialogue:0.1" style=intense
```

---

## 執行步驟

### Step 1: 備份與清理
// turbo

1. 若 `keep=true` → 備份 `output/chapters/chapter_{ch}.md` 到 `output/chapters/chapter_{ch}_backup.md`
2. 讀取原章節的摘要（ChromaDB）：
   ```bash
   cd {REPO_ROOT} && .venv/bin/python tools/lore_query.py --proj {proj} chapters --ch {ch}
   ```
3. 清理該章的 ChromaDB lore 記錄：
   ```bash
   cd {REPO_ROOT} && .venv/bin/python tools/lore_update.py --proj {proj} delete --ch {ch}
   ```

### Step 2: 還原進度指針
// turbo

> [!IMPORTANT]
> 重寫時 narrative_progress 需要暫時指向該章，讓 nvDraft/nvExpand 寫入正確位置。

1. 記錄當前 `narrative_progress.yaml` 的值（備用還原）
2. 設定 `current_chapter` = `{ch}`，`current_subarc_id` 還原為該章所屬 SubArc
3. 還原該章的 `current_beat`（從原摘要或 outline 推斷）

### Step 3: 應用覆蓋參數

將使用者提供的參數注入到草稿/擴寫流程：

| 參數 | 注入方式 |
|------|---------|
| `direction` | 傳給 nvDraft 的 `direction` |
| `pacing` | 臨時覆蓋 `novel_config.yaml` 的 `pacing_pointer` |
| `weights` | 臨時覆蓋 `content_weights` |
| `style` | 附加到 nvExpand 的風格指引 |
| `focus` | 覆蓋視角焦點角色 |
| `seed` | `random` = 在草稿中強制加入一個意外事件；`none` = 禁用 |

### Step 4: 重新生成（nvDraft → nvExpand）

> [!CAUTION]
> 必須**完整執行** nvDraft 和 nvExpand 的所有步驟，不可跳過。

```
/nvDraft proj={proj} direction={direction}
```

草稿完成後：

```
/nvExpand proj={proj} chapter={ch}
```

### Step 5: 維護與審查

直接在主 context 內依序執行，同 nvChapter Step 3.5：

#### 5a: nvReview light（若 `review=true`）
讀取 `{REPO_ROOT}/.claude/skills/nvReview/SKILL.md` 的 Agent Prompt，**在主 context 中遵循執行**。
參數：`MODE`=light, `RANGE_OR_CHAPTER`=chapter={ch}

#### 5b: 自動修正
若有 Critical/Warning → 逐一修正（最多 2 輪）

#### 5c: nvMaint light
讀取 `{REPO_ROOT}/.claude/skills/nvMaint/SKILL.md` 的 Agent Prompt，**在主 context 中遵循執行**。
參數：`MODE`=light

### Step 6: 還原進度指針
// turbo

將 `narrative_progress.yaml` 還原為 Step 2 記錄的原始值（current_chapter、current_subarc_id 等），但更新 `words_written`（新舊字數差額）。

### Step 7: 完成確認
// turbo

```
═══════════════════════════════════════════════════════
  🔄 第 {ch} 章重新生成完成
═══════════════════════════════════════════════════════
  章節標題：{title}
  原版字數：{old_words} → 新版字數：{new_words}
  ChromaDB lore：已清理舊記錄 + 重建 ✅
  備份：{keep ? '已保存' : '未保存'}
  審查：{結果}
═══════════════════════════════════════════════════════
```

### Step 8: Cascade Warning（非最後一章時）

> [!WARNING]
> **連鎖影響檢查**
> 若重寫的**不是最後一章**，後續章節的連貫性可能受影響：
> - 新的章節摘要可能與第 {ch+1} 章開頭矛盾
> - 新增/移除的事件可能影響後續劇情邏輯
>
> 建議執行：
> ```
> /nvReview proj={proj} range={ch}-{last_chapter} mode=light
> ```
