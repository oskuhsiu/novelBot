---
description: 生成新章節的情節草稿（精簡骨架，可搭配 /nvExpand 擴寫）
---

# /nvDraft - 章節草稿

為下一章生成精簡的情節草稿——只包含事件骨架（發生什麼、誰做了什麼、結果如何），不寫完整正文。產出寫入章節檔案，之後可用 `/nvExpand` 擴寫。

## 參數

| 參數 | 必填 | 說明 | 預設 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | — |
| `direction` | ❌ | 劇情導引 | — |

## 使用範例

```
/nvDraft proj=霓虹劍仙
/nvDraft proj=霓虹劍仙 direction="主角小隊潛入敵方基地失敗"
```

---

## 執行模式：Main Context (B 類)

直接在當前 session 執行，不啟動 sub-agent。

### 初始化
1. `REPO_ROOT` = 當前工作目錄
2. 從 `projects/project_registry.yaml` 解析 `proj` → `PROJECT_DIR`
3. 將下方所有 `{{...}}` 替換為實際值後，依序執行各 Step

> [!IMPORTANT]
> **Sub-agent 環境規則**：若本 SKILL.md 在 sub-agent 內被讀取執行，無法使用 Skill tool。所有 `/nvStyleBank` 調用改為「Read `{{REPO_ROOT}}/.claude/skills/nvStyleBank/SKILL.md` 並按其指令執行」。Skill 結果不是本流程的最終輸出，取得風格範本後必須繼續執行後續步驟。

## CLI Placeholder

以下為 CLI 命令縮寫。`{{...}}` = 初始化/本表定義的固定值；`{...}` = 執行時動態替換。`{{REPO_ROOT}}`/`{{PROJ}}`/`{{PROJECT_DIR}}` 定義見上方初始化 section。**先解析 `{{PROJ}}`，再展開其他 Placeholder。** Step 內 code block 省略 `cd` 前綴，實際執行時補上：

1. 讀取：`cd {{REPO_ROOT}} && cmd1 && cmd2`（失敗即停）

| Placeholder | 展開為 |
|-------------|--------|
| `{{CHAR}}` | `.venv/bin/python tools/char_query.py --proj {{PROJ}}` |
| `{{LORE_Q}}` | `.venv/bin/python tools/lore_query.py --proj {{PROJ}}` |

## 執行步驟

### Step 1: 載入專案狀態
// turbo

> [!IMPORTANT]
> **Context 去重（強制）— 適用於本 Skill 所有步驟**
> 讀取前先檢查 context 中是否已存在（由 nvChapter Step 0/1、nvBeat 等載入）。
> **已在 context** → 直接複用，**禁止重複 Read**。

載入（僅 context 中尚未存在的）：
- `{{PROJECT_DIR}}/config/novel_config.yaml` — 風格、pacing_pointer
- `{{PROJECT_DIR}}/config/narrative_progress.yaml` — 進度
- `{{PROJECT_DIR}}/config/outline_index.yaml` + `{{PROJECT_DIR}}/config/outline/arc_{current_arc}.yaml` — 大綱
- 角色資料庫：`{{CHAR}} list` → 按需 `{{CHAR}} get-public {IDS}` → 按需 `{{CHAR}} relations-public {ID}`
- ChromaDB：`{{LORE_Q}} lore "{關鍵詞}" --n 10` + `{{LORE_Q}} chapters --recent 5`
- **伏筆清單**（ChromaDB）：`{{LORE_Q}} lore "伏筆" --category foreshadowing --n 20`
- `{{PROJECT_DIR}}/output/style_guide.md`（若存在且 context 中尚未載入）— 聲音指導的風格定位參考

### Step 2: 載入連貫性上下文
// turbo

```yaml
連貫性檢查:
  1. 當前 SubArc（從 outline 讀取，❌ 禁止讀取未來大綱）
  2. 滑動視窗:
     - 當前 SubArc 前文: ChromaDB chapters summary
     - 上一章: 唯一允許讀取全文的舊章節
     - 上一個 SubArc: 僅 summary
  3. Context 去重: 已在 context 的章節跳過
  4. 跨 Arc: 僅讀取 previous_arc_ending
```

### Step 2.5: 檢查冷儲存索引
// turbo
讀取 `{{PROJECT_DIR}}/memory/archive_index.yaml`，若本章涉及已歸檔條目則提取注入。

### Step 3: 確定劇情範圍 (Beat Control)
// turbo

> [!IMPORTANT]
> **絕對聚焦於 current_beat.summary**
> SubArc summary 僅作為大方向背景。**嚴禁**超車推進到下一個節拍或演完結尾。

### Step 4: 動機地圖與關係動態

分析出場角色動機、識別衝突節點、檢查關係轉折閾值。

**伏筆整合**：檢查 active/dormant 伏筆清單，判斷本章是否適合 hint（暗示）、reinforce（強化）或 reveal（揭曉）某條伏筆。若適合，在 Step 5 草稿的對應事件中自然融入。優先處理長期休眠的伏筆。

### Step 5: 草稿生成

#### 5a: 確定指導
有 `direction` → 使用之。無 → 依 SubArc 自然推進。注入 `pacing_pointer` 指導。
聲音指導須參考 style_guide.md 的風格定位（narrator personality、dialogue density、rhythm），確保草稿的聲音方向與專案風格一致。

**風格錨定（強制）：** 決定聲音指導前，使用 Skill tool 呼叫 `/nvStyleBank` 取得真人範本：
```
Skill: nvStyleBank
args: "proj={{PROJ}} {專案genre} {本章emotion_objective} n=2 format=brief"
```
用回傳片段的語感校準 narrator_attitude、dialogue_texture 的設定方向，而非憑空想像。
- 收到 `[STYLE_BANK_EMPTY]` 或以 `[NO_MATCH` 開頭的回傳 → 退回使用 style_guide.md 的示範段落
- 收到帶 `UNMATCHED` 的結果 → 仍使用回傳的範本（最接近的），記錄缺失 tags 到 `MISSING_STYLE_TAGS`

> **草稿完成後**：若 `MISSING_STYLE_TAGS` 非空，在完成訊息末尾附加：
> `建議補充風格範本：/nvStyleBankBuilder tags={MISSING_STYLE_TAGS}`

**逐事件聲音判斷**：先決定章節整體的預設聲音，再逐一判斷每個事件的語調/能量/情緒是否與預設一致。若明顯不同，在該事件下方加 `voice:` 行覆蓋（只列與預設不同的欄位）。若一致，不加。

**逐事件情緒標注（強制）**：每個事件**必須**標注 `emotion:` 行，描述該段落的情緒基調和張力方向。同一章的不同事件可以（且應該）有不同情緒——前段悲、中段苦、後段爽完全正常。章節級的 `emotion_objective` 是整體目標，事件級的 `emotion:` 才是實際驅動擴寫筆觸的依據。

#### 5b: 生成草稿

> [!IMPORTANT]
> 草稿只寫「發生什麼」，不寫「怎麼發生」。
> 角色描述用行動和事件，不用性格標籤。「李玄潛入基地」✅ vs「冷靜的李玄」❌
> 禁止引用章節編號描述過往事件。「第82章時他曾…」❌ →「他還記得那次在廢墟裡…」✅

輸出格式：

```markdown
# 第 {N} 章 — {標題}

## 事件序列
1. {事件}
   emotion: 緊張不安——角色發現異狀，張力上升
2. {事件}
   emotion: 沉重壓抑——真相逐漸浮現，角色承受衝擊
3. {事件}
   emotion: 陰沉詭異——氣氛轉冷，讀者感到不對勁
   voice: narrator_attitude=冷靜觀察 | scene_energy=low
4. {事件}
   emotion: 爆發宣洩——壓抑後的反擊，節奏加速

（emotion 行為每個事件必填，描述該段的情緒基調和張力方向）
（voice 行僅在該事件聲音與章節預設不同時加上，只列需覆蓋的欄位）

## 關鍵決策
- {角色} 選擇 {X}（影響：{後果}）

## 衝突與互動
- {A} vs {B}：{核心}，結果：{結果}

## 狀態變化
- {角色}: {變化}

## 章末鉤子
{懸念/轉折}

## 聲音指導（章節預設）
- narrator_attitude: {旁白的基調，如：吐槽/冷靜觀察/緊張/戲謔/溫柔}
- scene_energy: {high/low/chaotic/chill}
- dialogue_texture: {嘴炮/正式/碎念/沉默為主/混戰}
- emotion_objective: {整章的主要情緒目標}
```

#### 5c: 寫入
// turbo
寫入 `{{PROJECT_DIR}}/output/chapters/chapter_{N}.md`

### Step 6: 輸出確認
// turbo

使用 `word_counter` 計算字數。

```
📝 第 {N} 章草稿完成 | 標題：{title} | {words} 字 | {event_count} 事件 | SubArc：{id}
下一步：/nvExpand proj={proj} chapter={N}
```

**不修改任何設定檔**（維護由 nvChapter/nvBatch 負責）。
