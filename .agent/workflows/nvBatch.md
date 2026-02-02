---
description: 批次寫作多章
---

# /nvBatch - 批次寫作

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `n` | ✅ | 章數 | `n=5` |
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `maint` | ❌ | 維護頻率 | `maint=light/every/end` |

### maint 參數說明
- `light`：每章輕量維護，批次結束完整維護 **（預設）**
- `every`：每章完整維護（最完整但較慢）
- `end`：僅批次結束維護（不建議，可能遺漏細節）

## 使用範例

```
/nvBatch n=5 proj=霓虹劍仙
/nvBatch n=10 proj=劍來 maint=every
/nvBatch n=20 proj=霓虹劍仙 maint=end
```

## 執行步驟

### Step 1: 驗證專案
// turbo
確認 `projects/{proj}/` 存在且設定完整

### Step 2: 批次迴圈
重複 `n` 次：

#### 2a. 執行 /nvChapter
執行 `/nvChapter proj={proj}`

#### 2b. 章節維護
根據 `maint` 參數決定維護方式：

**若 `maint=light`（預設）：**
- 更新 `lore_bank.yaml`（本章事件、伏筆）
- 更新 `narrative_progress.yaml`（章節完成標記）
- 更新 `character_db.yaml` 角色 `current_state`
- 標記新增項目（新角色/地點/勢力）待完整維護

**若 `maint=every`：**
- 執行完整 `/nvMaint proj={proj} mode=full`

**若 `maint=end`：**
- 跳過，最後統一執行

#### 2c. 進度報告
// turbo
顯示完成進度：`已完成 {i}/{n} 章`

### Step 3: 批次結束完整維護（必執行）
無論 `maint` 設為何值，批次結束時**必定**執行完整維護：

執行 `/nvMaint proj={proj} mode=full`

包含：
1. **長期記憶** - `lore_bank.yaml`
2. **敘事進度** - `narrative_progress.yaml`
3. **角色資料庫** - `character_db.yaml`（含新角色）
4. **世界地圖** - `world_atlas.yaml`（含新地點）
5. **勢力登記** - `faction_registry.yaml`（含新勢力）
6. **力量體系** - `power_system.yaml`（含新能力）
7. **物品目錄** - `item_compendium.yaml`（含新物品）

### Step 4: 完成報告
顯示批次完成摘要：

```
═══════════════════════════════════
  批次寫作完成報告
═══════════════════════════════════
  完成章數：{n}
  總字數：{words}
  當前進度：第 {chapter} 章 / 共 {total} 章
───────────────────────────────────
  設定更新：
  ├─ 新增角色：{x} 人
  ├─ 新增地點：{y} 處
  ├─ 新增勢力：{z} 個
  ├─ 新增物品：{w} 件
  └─ 開放伏筆：{f} 條
───────────────────────────────────
  記憶庫狀態：✅ 已同步
═══════════════════════════════════
```

## 輸出

批次完成後：
- 所有章節已寫入 `output/chapters/`
- 所有設定檔已與劇情同步
- 記憶庫完整更新
