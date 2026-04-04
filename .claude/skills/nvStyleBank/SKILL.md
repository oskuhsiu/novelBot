---
description: 從風格範本資料庫查詢適合的真人文本片段，接受自由格式參數（tags、genre、tone 等），自動解析並匹配最佳範本
---

# /nvStyleBank - 風格範本查詢

從全域 `data/style_bank.db` 查詢最適合的真人文本片段，供 nvExpand/nvDraft 做 few-shot priming。

接受**自由格式**的雜亂參數，自動拆解、匹配資料庫中實際存在的 tag，驗證後回傳結果。

## 參數（自由格式）

可用 key: `proj`(專案別名), `format`(brief=精簡), `tags`, `genre`, `tone`, `prose`, `scene`, `emotion`, `technique`, `interaction`, `author`, `n`(數量,預設3)。裸詞視為 tag。逗號/空格/頓號分隔。

例: `/nvStyleBank proj=gou1 搞笑 師徒互動 仙俠`

---

## DB Tags（由 /nvStyleBankBuilder 自動更新，勿手動編輯）
<!-- TAGS_START -->
反差, dialogue, tension, 冷幽默, 爽文, revelation, 都市, 搞笑, 留白, 玄幻, 節奏突變, 熱血, 仙俠, 成長, 環境描寫, 日常, combat, 伏筆, slice_of_life, 情感, 黑暗, 降格法, 吐槽風, 靈異, 腹黑, 溫暖, 懸疑, 遞進式誇張, 恐懼, 師徒, 穿越, 歷史, 暗喻, 悲傷, 科幻, emotion, 震驚, 孤獨, 古風, 荒誕, 權謀, 損友, negotiation, 小白文, 初遇, 荒謬升級, 諷刺, 凡人流, 絕望, 宿敵, farewell, 末世, comedy, 武俠, 荒誕升級, confession, 亦敵亦友, 敵對互動, 治癒, 釋然, 誤解, 單方面崇拜, 盜墓, 告別, 愧疚, 克蘇魯, 無限流, 意識流, 狂喜, 西幻, 喜劇, 疲憊
<!-- TAGS_END -->

---

## 專案級配對快取（style_anchors.yaml）

當帶有 `proj` 參數時，啟用專案級配對快取，確保同一專案不同章節使用一致的風格範本。

**檔案位置**：`{PROJECT_DIR}/config/style_anchors.yaml`

**格式**：
```yaml
# nvStyleBank 自動管理，記錄專案已配對的風格範本
anchors:
  - passage_id: 42
    tags_matched: ["搞笑", "仙俠"]
    style_note: "表面天真實則精準打擊"
  - passage_id: 17
    tags_matched: ["combat", "熱血"]
    style_note: "密集短句推疊壓迫感"
```

**運作邏輯**：
1. 有快取 → 先從 `anchors` 中的 passage_id 集合內篩選匹配的（用 `get {id}` 取回完整內容，比對 tags）
2. 快取中有足夠匹配 → 直接回傳，不查全域 DB
3. 快取中不足 → 查全域 DB 補足，**新結果自動追加到 style_anchors.yaml**
4. 無快取檔 → 走正常全域查詢流程，查完後建立 style_anchors.yaml

---

## 執行流程（主 context 執行，B 類）

### Step 1：環境 + 參數解析

1. `REPO_ROOT` = 當前工作目錄
2. 解析用戶輸入：
   - 用 `key=value` 格式拆出 `proj`、`author`、`n`、各 category 的值
   - 所有裸詞和各 category value 統一收集成 `RAW_TOKENS` 列表
   - 逗號、空格、頓號皆為分隔符
3. 若有 `proj` → 從 `projects/project_registry.yaml` 解析 → `PROJECT_DIR`

例：`proj=gou1 搞笑 師徒互動` → `RAW_TOKENS = ["搞笑", "師徒互動"]`，`PROJ = gou1`

### Step 2：取得資料庫 tag 清單

讀取上方 `DB Tags` 區塊作為 `DB_TAGS`。若區塊為空 → 空庫狀態，跳到 Step 6。

### Step 3：Token → Tag 匹配

對每個 `RAW_TOKEN`，依序嘗試：

1. **精確匹配**：token 完全等於某個 `DB_TAGS` 中的 tag → 直接採用
2. **包含匹配**：token 是某個 tag name 的子字串，或 tag name 包含 token → 採用（如 `搞笑` 匹配 `搞笑`、`腦洞` 匹配 `腦洞`）
3. **複合詞拆分**：將複合詞拆成子 token（如 `搞笑腦洞` → `搞笑` + `腦洞`），對每個子 token 重新執行精確/包含匹配。**拆分後的子 token 仍須在 DB_TAGS 中找到匹配**，禁止憑語義猜測不存在的 tag。
4. **無匹配**：記錄為 `UNMATCHED`，後續報告

產出：`MATCHED_TAGS = [tag_name, ...]`，`UNMATCHED = [token, ...]`

> 如果 MATCHED_TAGS 為空（所有 token 都無匹配）→ 跳到 Step 6 輸出（無匹配狀態）。

### Step 4：查詢

#### 4a：專案快取優先（僅 proj 模式）

若有 `proj` 且 `style_anchors.yaml` 存在：
1. 讀取 `style_anchors.yaml` 的 `anchors` 列表
2. 對每個 anchor，檢查其 `tags_matched` 是否與 `MATCHED_TAGS` 有交集
3. 將匹配的 anchor 的 `passage_id` 收集為 `CACHED_IDS`
4. 用 `get {id}` 逐一取回完整內容
5. 若取回數量 ≥ N → 跳到 Step 5（不查全域 DB）
6. 若不足 → 繼續 4b，但排除已取回的 ID

#### 4b：全域查詢

**查詢策略**（依序嘗試，直到結果 ≥ N）：

1. 先用 `--mode all`（要求同時符合所有 tag）；如果 MATCHED_TAGS > 4，只取最核心的 3-4 個
2. 如果結果 < N，改用 `--mode any`（符合任一即可）補足

```bash
# 先嘗試 all（有 author 就加 --author）
cd {REPO_ROOT} && .venv/bin/python tools/style_bank_query.py search --tags "MATCHED_TAGS_CSV" --mode all --n N

# 結果不足時改 any
cd {REPO_ROOT} && .venv/bin/python tools/style_bank_query.py search --tags "MATCHED_TAGS_CSV" --mode any --n N
```

> 將 `MATCHED_TAGS_CSV`、`N`、`--author AUTHOR` 替換為實際值。tags 用逗號分隔，整體加引號。

#### 4c：更新專案快取（僅 proj 模式）

若 4b 查到了新結果，將新 passage 追加到 `style_anchors.yaml`：
```yaml
  - passage_id: {id}
    tags_matched: [{匹配到的 tags}]
    style_note: "{style_note}"
```

若 `style_anchors.yaml` 不存在則建立。

### Step 5：驗證 + 篩選

對查詢結果逐一檢查：
- 該片段的 tags 和 style_note 是否確實與用戶需求相關？
- 如果查出的片段明顯不適合（如用戶要搞笑但查出悲傷場景）→ 排除
- 如果排除後結果不足：
  1. 先嘗試 `search --keyword "某個關鍵詞" --n N`（從用戶原始輸入中取關鍵詞）
  2. 若仍不足，回報「僅找到 X 段符合的範本」，不硬湊

### Step 6：輸出

根據 `format` 參數決定輸出格式：

#### format 未指定（用戶直接呼叫）

- **DB 為空** → 「風格範本庫尚未建立，請先執行 /nvStyleBankBuilder」
- **查無結果** → 「無匹配範本。建議執行：/nvStyleBankBuilder tags={RAW_TOKENS}」
- **正常** → 每段輸出 `#{id} — {author}《{work}》{chapter}`、Tags、Style、分隔線、正文

#### format=brief（被其他 skill 呼叫）

- **DB 為空** → `[STYLE_BANK_EMPTY]`
- **查無結果** → `[NO_MATCH: {RAW_TOKENS}]`
- **有結果但部分 tag 未匹配** →
```
[MATCHED: tag1,tag2 | UNMATCHED: tag3]

---
#42 Style: {style_note}
---
{text}

---
#17 Style: {style_note}
---
{text}
（每段重複上述格式）
```
- **全部匹配** → 同上，首行改為 `[MATCHED: tag1,tag2,tag3]`

> `#42` 為 passage_id，供呼叫端寫入 style_anchors.yaml 時使用。

## 被呼叫端須知

帶 `format=brief` 取得機器可解析格式。回傳首行標記：`[STYLE_BANK_EMPTY]` / `[NO_MATCH: ...]` / `[MATCHED: ... | UNMATCHED: ...]` / `[MATCHED: ...]`

## 注意事項

1. **不要猜測不存在的 tag**：所有匹配必須基於 `DB Tags` 區塊中的實際 tag
2. **寧缺勿濫**：如果匹配不到合適的，回報「無足夠匹配」比硬塞不相關的好
3. **複合詞要拆**：`搞笑腦洞` 應拆成 `搞笑` + `腦洞` 分別匹配
4. **category key 即 tag**：`genre=仙俠` 和裸詞 `仙俠` 效果相同，category key 只是幫助用戶組織輸入
5. **專案快取優先**：有 proj 時，優先用已配對的範本，保證風格一致性
