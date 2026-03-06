---
description: 計算中文章節的準確字數（中文字＋中文標點＋英數單詞）
---

# word_counter — 字數計算技能

## 使用時機

任何需要計算章節字數的場合，包括但不限於：
- `/nvExpand` Step 1 字數檢測、Step 5 硬性閘門校驗
- `/nvChapter` 審查後的字數再校驗
- `/nvDraft` 草稿字數確認
- `/nvMaint` 更新 words_written

## 規則（強制）

1. **嚴禁**使用 `cd` 切換目錄。
2. **嚴禁**使用 `perl` 或 `awk` 自行編寫計算邏輯。
3. **嚴禁**用 `wc -m` 或 `wc -c`（它們不區分中英文）。
4. **必須**使用下方提供的 Python 內聯指令。

## 標準指令

直接在當前目錄執行，將 `{FILE}` 替換為章節檔案的相對路徑：

```bash
python3 -c "
import re, sys
t = open(sys.argv[1], encoding='utf-8').read()
cn = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
pn = len(re.findall(r'[\u3000-\u303f\uff01-\uff60\u2018-\u201f\u2014\u2026\uff5e]', t))
en = len(re.findall(r'[a-zA-Z0-9]+', t))
print(cn + pn + en)
" {FILE}
```

**範例：**
```bash
python3 -c "
import re, sys
t = open(sys.argv[1], encoding='utf-8').read()
cn = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t))
pn = len(re.findall(r'[\u3000-\u303f\uff01-\uff60\u2018-\u201f\u2014\u2026\uff5e]', t))
en = len(re.findall(r'[a-zA-Z0-9]+', t))
print(cn + pn + en)
" output/chapters/chapter_45.md
```

## 輸出

純數字，代表該檔案的字數（中文字 + 中文標點 + 英數單詞）。

## 計算規則說明

| 類別 | 範圍 | 計算方式 |
|------|------|----------|
| 中文字 | U+4E00–U+9FFF, U+3400–U+4DBF | 每字算 1 |
| 中文標點 | 全形標點（，。！？、；：「」『』（）—…～等） | 每個算 1 |
| 英數單詞 | 連續 a-z/A-Z/0-9 | 整串算 1 |
| Markdown 語法 | `#`, `*`, `-`, `` ` `` 等 | 不計入 |
| 空白/換行 | | 不計入 |
