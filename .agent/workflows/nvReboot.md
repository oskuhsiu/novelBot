---
description: 重啟專案，保留設定但重新生成世界觀、角色和大綱
---

# /nvReboot - 重啟專案

從既有專案的 `novel_config.yaml` 設定重新開始，保留風格和引擎設定，重新生成世界觀、角色和大綱。適用於想要重新嘗試不同發展的情況。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 來源專案名稱或代號 | `proj=goblin` |
| `arcs` | ❌ | 新大綱數量（覆蓋原設定） | `arcs=8` |
| `subarcs` | ❌ | 每卷細目數（覆蓋原設定） | `subarcs=5~8` |

## 使用範例

```
/nvReboot proj=goblin
/nvReboot proj=door arcs=8 subarcs=5~8
```

## 版本命名規則

重啟後的專案會自動加上流水號：
- 首次重啟：`goblin` → `goblin_1`
- 再次重啟：`goblin_1` → `goblin_2`
- 或從原版：`goblin` → `goblin_3`（找最大流水號 +1）

## 執行步驟

### Step 1: 查找來源專案
// turbo
1. 若 `proj` 是代號，從 `project_registry.yaml` 查找完整專案名
2. 讀取來源專案的 `config/novel_config.yaml`
3. 掃描 projects/ 目錄找出該專案的現有版本
4. 決定新版本流水號

### Step 2: 建立新專案目錄
// turbo
建立 `projects/{base_name}_{version}/` 目錄結構（與 nvGenesis 相同）：
```
projects/{base_name}_{version}/
├── config/
│   ├── novel_config.yaml      ← 從來源複製
│   ├── character_db.yaml      ← 重新生成
│   ├── world_atlas.yaml       ← 重新生成
│   ├── faction_registry.yaml  ← 重新生成
│   ├── power_system.yaml      ← 重新生成
│   ├── item_compendium.yaml   ← 重新生成
│   └── narrative_progress.yaml ← 重新生成
├── output/
│   ├── chapters/
│   └── style_guide.md         ← 重新生成
└── memory/
    ├── lore_bank.yaml         ← 空白初始化
    └── emotion_log.yaml       ← 空白初始化
```

### Step 3: 複製並更新設定檔
// turbo
1. 複製來源的 `novel_config.yaml`
2. 更新 `meta.project_id` → 新的唯一 ID
3. 更新 `meta.alias` → `{base_alias}_{version}`（如 goblin_2）
4. 若指定 `arcs`，更新 `structure.arcs`
5. 若指定 `subarcs`，更新 `structure.subarcs_per_arc`
6. 更新 `meta.created_at` → 當前日期

### Step 4: 更新專案註冊檔
// turbo
在 `projects/project_registry.yaml` 新增：
```yaml
{new_alias}: "{new_project_folder}"
```

### Step 5: 重新生成風格指南
使用 `skill_style_setter` 生成 `output/style_guide.md`

### Step 6: 重新建構世界觀
使用 `skill_world_builder` 生成新的世界觀，寫入 `world_atlas.yaml`

### Step 7: 重新設計力量體系
使用 `skill_power_architect` 設計力量系統，寫入 `power_system.yaml`

### Step 8: 重新創建角色
使用 `skill_character_forge` 創建：
- 1 個主角（可參考原版概念，但重新設計）
- 1 個主要反派
- 2-3 個配角

### Step 9: 重新建立勢力
使用 `skill_faction_forge` 創建 2-4 個勢力

### Step 10: 重新規劃大綱
使用 `skill_outline_architect` 規劃全書結構，基於 `target_chapters` 設計各卷和章節分配

### Step 11: 生成初始道具
使用 `skill_item_smith` 為主角生成初始裝備

### Step 12: 埋設角色秘密
使用 `skill_character_secret_seeder` 為主要角色生成隱藏動機

### Step 13: 輸出確認
顯示專案建立結果摘要：
```
=== Reboot 完成 ===
來源專案：{source_project}
新專案：{new_project}
代號：{new_alias}
大綱數：{arcs}
細目數：{subarcs_per_arc}
預估章數：約 {estimated_chapters}

可使用 /nvChapter proj={new_alias} 開始寫作
```

## 與 nvGenesis 的差異

| 項目 | nvGenesis | nvReboot |
|------|-----------|----------|
| 設定 | 全新輸入 | 從原專案繼承 |
| 代號 | 使用者指定 | 自動加流水號 |
| 世界觀 | 全新生成 | 全新生成 |
| 角色 | 全新創建 | 全新創建 |

## 注意事項

1. **來源專案不受影響**：Reboot 不會修改或刪除來源專案
2. **完全獨立**：新專案與來源專案完全獨立，可自由發展
3. **代號唯一**：新代號會自動確保唯一性
