---
name: style_sampler
description: 風格採樣器 - 從網路搜尋參考作家的真實文本片段，作為寫作風格錨定範本
---

# 風格採樣器 (Style Sampler)

## 功能概述

從網路搜尋 `reference_authors` 的代表作品片段，按場景類型分類後存入 `style_guide.md` 的「風格錨定範本」區塊。這些真人寫的片段供 nvExpand / nvDraft 在生成時做 few-shot priming，避免 model 回歸 AI 預設語調。

## 輸入

從 `config/novel_config.yaml` 讀取：
```yaml
style_profile:
  genre: ""
  reference_authors: []
```

從 `output/style_guide.md` 讀取已有內容（將追加風格錨定區塊）。

## 輸出

更新 `output/style_guide.md`，在末尾（`---` 分隔線之前）追加「風格錨定範本」區塊。

## 執行步驟

### Step 1: 讀取設定

從 context 或檔案中取得 `reference_authors` 和 `genre`。

確認 `output/style_guide.md` 已存在（本 skill 在 style_setter 之後執行）。

### Step 2: 搜尋參考片段

> [!CAUTION]
> **次數限制（硬性）**
> - **WebSearch**：每位作家最多 2 次（全部作家合計最多 6 次）
> - **網頁抓取（curl / WebFetch）**：全部作家合計最多 10 次
> - 超過次數仍未取得 → 該分類標註「未找到可驗證的原文片段」，**停止重試**
> - 禁止對同一網站反覆嘗試不同 URL

**抓取方式優先順序：**
1. **Bash curl**（優先）— 不受 WebFetch 權限限制，前景/背景 agent 都能用
2. **WebFetch**（備選）— 前景 agent 可用（會跳權限詢問），背景 agent 會被自動拒絕

**已知可用來源站（curl 驗證過）：**
- `tw.hjwzw.com`（黃金屋，繁中小說正文）
- `big5.quanben-xiaoshuo.com`（全本小說網）
- `juzikong.com`（句子控，語錄）
- `zh.wikiquote.org`（維基語錄）
- `mingjuzi.com`（名句子）
- `goodreads.com`（英文語錄）
- `home.gamer.com.tw`（巴哈姆特）

**已知不可用：** czbooks.net（Cloudflare 防護）

對每位 reference_author：

1. 使用 WebSearch 搜尋：`"{作者名}" 小說 經典段落` 或 `"{作者名}" "{代表作}" 精彩片段`
2. 若第一次搜尋結果不佳，嘗試 1 次變體關鍵字（這是該作家的第 2 次搜尋機會）
3. 從搜尋結果中選擇 URL，用 curl 抓取頁面內容，提取小說正文片段
4. 抓取失敗 → 換一個 URL 再試（計入 10 次總額度），不要在同一站重試

**篩選標準：**
- 片段長度 200-400 字（太短沒有風格資訊，太長浪費 token）
- 必須是**從網頁實際抓取的文本**，禁止用 model 記憶重構或仿寫
- 必須是**小說正文**（非書評、非簡介、非廣告）
- 優先選擇能展示該作者風格特色的段落（對話風格、敘事節奏、幽默感等）
- 避免純打鬥招式名堆疊或純設定介紹的段落

### Step 3: 分類

將蒐集到的片段按場景類型分類。分類依據 `genre` 動態調整：

**通用分類（所有 genre）：**
- `dialogue` — 對話密集場景（展示角色聲音區分、語氣節奏）
- `tension` — 緊張/衝突場景（展示節奏控制、氣氛營造）
- `emotion` — 情感/內心場景（展示心理描寫方式）

**按 genre 追加：**
- 搞笑/幽默類 → 追加 `comedy`（展示笑點節奏、語氣反差）
- 仙俠/武俠/戰鬥類 → 追加 `combat`（展示動作描寫風格）
- 日常/輕鬆類 → 追加 `slice_of_life`（展示日常氛圍）
- 恐怖/懸疑類 → 追加 `suspense`（展示懸念營造）

每個分類保留 **1-2 段**最能代表風格的片段。若某分類找不到合適片段，留空不強湊。

### Step 4: 格式化並寫入

在 `output/style_guide.md` 的末尾分隔線之前，插入以下區塊：

```markdown
## 風格錨定範本

> 以下片段摘自參考作家的公開作品，僅作為寫作風格錨定之用。
> nvExpand 在每場景生成前，應從下方選取最接近該場景類型的片段作為 few-shot priming。

### dialogue — 對話場景
**出處**：{作者} 《{書名}》
> {片段內容}

### tension — 緊張場景
**出處**：{作者} 《{書名}》
> {片段內容}

### emotion — 情感場景
**出處**：{作者} 《{書名}》
> {片段內容}

### {genre 專屬分類}
**出處**：{作者} 《{書名}》
> {片段內容}
```

### Step 5: 輸出確認

```
✅ 風格採樣完成
   參考作家：{authors_list}
   採集片段：{total_count} 段（{category_breakdown}）
   已寫入：output/style_guide.md「風格錨定範本」區塊
```

## 注意事項

1. 本 skill 在 nvGenesis 的 style_setter 之後執行，style_guide.md 必須已存在
2. 若 WebSearch 找不到某位作家的片段（冷門作家），跳過並在報告中說明
3. 片段僅供風格參考，不會出現在小說正文中
4. 用戶可隨時手動編輯 style_guide.md 的風格錨定區塊，替換為自己喜歡的片段
5. 對已有專案補充風格錨定：直接讀取該專案的 novel_config.yaml 和 style_guide.md 執行 Step 2-5
