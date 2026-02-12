# Dynamic Character System & Trope Integration
# 動態角色系統與套路庫整合指南

Dynamic Character System (DCS) 是 Genesis Engine 的核心模組之一，旨在解決「角色臉譜化」與「行為邏輯僵硬」的問題。

本系統通過 **Static Profile (靜態設定)** 與 **Dynamic State (動態狀態)** 的雙軌制，結合 **Trope Library (套路庫)** 來驅動角色的行為演化。

## 1. 系統架構

系統由以下四個核心文件組成：

| 文件 | 作用 | 類型 |
|------|------|------|
| `character_db.yaml` | 角色的靈魂容器，包含「出場設定」與「當前狀態」。 | **Core Data** |
| `trope_library.yaml` | 提供行為模板、性格原型與劇情衝突的資料庫。 | **Library** |
| `motivation_map.yaml` | 記錄角色當前的慾望、阻礙與衝突節點。 | **Runtime Engine** |
| `emotion_log.yaml` | 追蹤情感波段，作為反饋調節角色行為的依據。 | **Feedback Loop** |

---

## 2. Trope Library (套路庫)

套路庫位於 `templates/trope_library.yaml`，包含 50+ 種經典網文套路，分為四大類：

1. **Archetype (原型)**:
   - 定義角色的「出廠設置」。
   - 例：`ARCH_001` (轉生老怪), `ARCH_002` (廢柴)
   - 用法：在 `character_db.yaml` 的 `base_profile.tropes` 中引用。

2. **Dynamic (動態行為)**:
   - 定義角色在特定情境下的行為模式。
   - 例：`DYN_001` (打臉), `DYN_003` (花式作死)
   - 用法：寫作 Skill (`scene_writer`) 檢索此類套路來決定角色反應。

3. **Relationship (關係模式)**:
   - 定義兩個角色之間的互動模板。
   - 例：`REL_001` (歡喜冤家), `REL_002` (師徒)
   - 用法：在 `character_db.yaml` 的 `relationships` 區塊中引用。

4. **Plot (劇情單元)**:
   - 以角色為核心的微型劇情模塊。
   - 例：`PLT_001` (拍賣會), `PLT_008` (身份曝光)
   - 用法：`chapter_beater` 在拆解章節時，可直接調用此模塊構建情節。

---

## 3. 使用流程 (Workflow)

### Step 1: 角色創建 (Genesis)
在 `nvGenesis` 或手動創建角色時，為角色分配 1-3 個 **Archetype**。

```yaml
# character_db.yaml
id: "CHAR_001"
name: "林昊"
tropes:
  - "ARCH_002"  # 廢柴開局
  - "ARCH_011"  # 系統宿主
```

### Step 2: 行為驅動 (Writing)
當 `scene_writer` 需要描寫角色反應時：
1. 讀取 `character_db.yaml` 獲取 Base Profile。
2. 讀取 `trope_library.yaml` 獲取該 Archetype 關聯的 Traits 和行為建議。
3. 結合當前 `motivation_map.yaml` (例如：急需靈石)。
4. 生成行為：「林昊面對嘲諷（觸發 `DYN_001` 打臉前置），選擇暫時隱忍（符合 `ARCH_002` 的韌性），並查看系統任務（符合 `ARCH_011`）。」

### Step 3: 狀態更新 (Maintenance)
章節結束後，`nvMaint` 會更新 `character_db.yaml` 的 `current_state`：
- 如果角色在章節中完成了「打臉」，情感狀態更新為 "Satisfied"。
- 如果角色觸發了 "Enemies to Lovers" 的事件，更新 `relationships` 中的 `tension` 值。

---

## 4. 擴充指南

要新增套路，請直接編輯 `templates/trope_library.yaml`。

**格式要求**：
```yaml
  - id: "DYN_NEW"
    name: "New Trope Name"
    name_zh: "中文名稱"
    category: "Dynamic"
    description: "描述這個套路的具體表現。"
    trigger: "什麼情況下觸發？"
```

建議保持 `id` 的唯一性與前綴規範 (`ARCH_`, `DYN_`, `REL_`, `PLT_`)。
