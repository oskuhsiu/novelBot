# Technique Elaborator

招式演繹器 - 根據速度指針展開技能描寫。

## 功能說明

根據 `pacing_pointer`（速度指針）決定技能/能力使用時的描寫精細度。

## 設定參數

此 Skill 受 `novel_config.yaml` 中以下設定影響：

```yaml
engine_settings:
  pacing_pointer: 0.5  # 0.1=極細 ~ 1.0=極快
  
  technique_settings:
    # 細節展開等級
    detail_levels:
      0.1: "完整展開"  # 數千字的對決描寫
      0.3: "詳細描寫"  # 500-1000字
      0.5: "標準描寫"  # 200-500字
      0.7: "簡略描寫"  # 100-200字
      1.0: "一筆帶過"  # 50字以內
      
    # 展開維度
    elaboration_aspects:
      - energy_flow: true      # 能量流動
      - physical_motion: true  # 身體動作
      - environmental: true    # 環境影響
      - mental_focus: true     # 精神集中
      - aftermath: true        # 招式後果
```

## 執行邏輯

### Step 1: 讀取技能定義

從 `power_system.yaml` 獲取技能資訊：

```yaml
skill_input:
  id: "SKILL_001"
  name: "離線劍意"
  execution:
    - step_1: "中斷與全域網絡的數據同步"
    - step_2: "將劍意壓縮至實體媒介"
  cost: "50% 算力負擔"
  visual_effects: "周圍霓虹燈光因電磁干擾而閃爍"
```

### Step 2: 根據 Pacing 決定展開程度

**pacing_pointer = 0.1（極細）**：
```markdown
李玄閉上眼睛，意識深入自己的底層代碼。

數據流在他的認知中呈現為無數光點，如同夜空中的星河。他開始逐一切斷與外界的連接——首先是公共頻道，那些嘈雜的信息流瞬間歸於沉寂；然後是防火牆的自動更新，系統發出警告但他強行覆蓋；最後是自己的義眼與骨骼中的維護協議。

每一條連接斷開，他都感到一陣輕微的眩暈，彷彿身體的某個部分正在脫離這個世界。

劍。

他將意識集中於手中的折疊義體飛劍。金屬結構在他的感知中變成一串串代碼，而他的意志則化作火焰，將這些代碼重新編譯。

劍身開始震顫。周圍的霓虹燈光因為電磁干擾而瘋狂閃爍——粉色、藍色、紫色，交織成詭異的光幕。

「離線劍意......」他低聲念道，嗓音因為算力負擔而略顯沙啞。

三秒。

他只有三秒的窗口。

空氣中響起刺耳的嗡鳴，那是數據與現實碰撞的聲音。劍尖出現藍色的殘影——不是光，而是真正的數據實體化......
```

**pacing_pointer = 1.0（極快）**：
```markdown
李玄啟動離線劍意，周圍霓虹燈瞬間閃爍。劍光一閃，敵人已經倒下。
```

### Step 3: 維度選擇

根據場景需要選擇展開維度：

| 維度 | 適用情境 | 範例 |
|------|----------|------|
| energy_flow | 修煉/突破 | 靈氣在經脈中流動 |
| physical_motion | 武打/動作 | 身體的移動軌跡 |
| environmental | 大場面 | 環境被招式影響 |
| mental_focus | 心理戰 | 意志與決心 |
| aftermath | 轉折點 | 招式的代價與後果 |

### Step 4: 輸出

```yaml
technique_elaboration:
  skill_id: "SKILL_001"
  pacing_pointer: 0.3
  word_count: 650
  
  elaboration:
    content: "..."  # 生成的描寫文本
    
  aspects_used:
    - energy_flow: "描寫數據流動"
    - physical_motion: "描寫手持劍的動作"
    - environmental: "霓虹燈閃爍"
    
  cost_applied:
    character: "CHAR_001"
    effect: "算力負擔 50%"
    duration: "120秒"
    updated_in: "character_db.yaml"
```

## 與其他 Skill 的連動

1. **skill_scene_writer**：寫戰鬥場景時調用
2. **skill_logic_auditor**：驗證能量消耗是否合理
3. **skill_consistency_validator**：確保技能描寫與設定一致
