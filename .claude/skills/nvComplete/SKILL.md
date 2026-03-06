---
description: 章節完成信號（供 hook 觸發用）
---

# /nvComplete - 章節完成信號

此 skill 為 nvChapter 工作流的結束信號。呼叫此 skill 表示一章已完整寫完（含審查與修正）。

> [!NOTE]
> 本 skill 不執行任何操作，僅作為 PostToolUse hook 的觸發點。
> 由 nvChapter Step 4 自動呼叫，不需手動執行。

收到此 skill 後，不需輸出任何內容，等待 hook 指示即可。
