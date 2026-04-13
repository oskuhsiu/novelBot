---
description: "透過本地 LLM API 執行任務（審查輔助、內容生成）。當 nvReview assist=local 時自動觸發；或當使用者需要生成 Claude 拒絕撰寫的小說內容時使用。觸發詞：本地模型、local LLM、local model、Qwen、本機生成、用本地寫、bypass。"
---

# nvLocalLLM — 本地 LLM 閘道

透過 OpenAI-compatible API 呼叫本地/自架 LLM，兩大用途：

1. **nvReview assist partner** — 提供審查第二意見
2. **內容生成** — 撰寫 Claude 無法產出的場景內容

## 連線設定

**Endpoint URL 由使用者每次對話時提供**（Cloudflare tunnel URL 會變動）。收到後記在 context 中，以 `--url` 參數傳入腳本。

模型名稱可用 `--model` 指定，或由使用者告知。

> 使用前先 `ping` 確認連線正常。

## 兩支工具

| 工具 | 用途 |
|------|------|
| `tools/pack_context.py` | 打包 context（純 Python，直接查 DB） |
| `tools/local_llm.py` | 送 API + 取回結果 |

**全程 Bash 直接跑，不經 Agent，Claude 只讀最終結果檔。**

## 完整流程

### Step 1: Ping 測試

```bash
.venv/bin/python tools/local_llm.py --url "{URL}" ping
```

### Step 2: 打包 context

```bash
# 審查打包
.venv/bin/python tools/pack_context.py --proj {PROJ} review --chapters {A-B}

# 生成打包
.venv/bin/python tools/pack_context.py --proj {PROJ} generate --chapter {N} --instruction "生成指令"

# 指定 budget 和輸出路徑（臨時檔一律寫 $TMPDIR）
.venv/bin/python tools/pack_context.py --proj {PROJ} --budget 80000 -o "$TMPDIR/packed.md" review --chapters {A-B}
```

打包器按 token budget 分層填充：
- **P1（必填）**：指令 + 目標章節全文
- **P2（高優先）**：登場角色 JSON + 設定規則 + 進度
- **P3（中優先）**：ChromaDB 前文摘要 + 前 1-2 章全文
- **P4（低優先）**：能力系統

超過 budget 時低優先自動砍掉，stderr 會警告。

### Step 3: 送 API

```bash
# 審查
.venv/bin/python tools/local_llm.py --url "{URL}" review \
  --input "$TMPDIR/packed.md" --output {PROJECT_DIR}/reviews/review_ch{A}-{B}_local.md

# 生成
.venv/bin/python tools/local_llm.py --url "{URL}" generate \
  --prompt-file "$TMPDIR/packed.md" --output {PROJECT_DIR}/drafts/local_ch{N}.md \
  --max-tokens 8192 --temperature 0.8
```

### Step 4: Claude 讀結果

用 **Read tool** 讀取結果檔。結果已要求精簡（審查只列發現，生成只有內容）。

- 審查結果：比對 Claude 自己的審查，採納有價值的發現
- 生成結果：潤飾、校對、整合進章節

## 用途一：審查

典型用法（3 章 ≈ 15K tokens，budget 很充裕）：

```bash
.venv/bin/python tools/pack_context.py --proj bnf -o "$TMPDIR/packed.md" review --chapters 33-35
.venv/bin/python tools/local_llm.py --url "{URL}" review --input "$TMPDIR/packed.md" --output "$TMPDIR/review_local.md"
```

> 建議一次審查 ≤5 章，避免 context 太擠導致品質下降。

## 用途二：內容生成

```bash
# 用 pack_context 自動組裝前文 + 角色 + 設定
.venv/bin/python tools/pack_context.py --proj bnf -o "$TMPDIR/packed.md" generate --chapter 36 \
  --instruction "撰寫一段林默與趙天驕的對峙場景，約 2000 字，氣氛緊張，第三人稱限制視角（林默）。"

.venv/bin/python tools/local_llm.py --url "{URL}" generate \
  --prompt-file "$TMPDIR/packed.md" --output "$TMPDIR/scene_ch36.md" \
  --max-tokens 8192 --temperature 0.8
```

也可用 `--instruction-file` 從檔案讀取更詳細的指令。

## 注意事項

- Cloudflare tunnel URL 會過期，每次對話使用者會提供新的
- 本地模型品質不如 Claude，生成結果由 Claude 校對後再用
- `--max-tokens` 控制回應長度，審查建議 8192，生成視場景調整
- stderr 印 token 統計和耗時
- 全程不經 Agent、不讓 Agent 讀打包檔 — 省 token
