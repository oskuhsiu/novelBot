# World Rule Validator

世界規則驗證器 - 建立/驗證世界物理邏輯。

## 功能說明

建立世界觀的「邏輯物理量」，如魔法消耗與體力對比，並在寫作時驗證是否違規。

## 使用情境

- 建立新世界觀時定義基本規則
- 寫作時驗證劇情邏輯
- 防止「吃書」（自相矛盾）

## 執行邏輯

### Step 1: 讀取世界規則

從 `novel_config.yaml` 的 `world_rules` 區塊：

```yaml
world_rules:
  physics:
    - "靈氣等同於數據帶寬"
    - "強行破譯金丹會導致硬體自毀"
    - "每使用一次高階技能需要冷卻12小時"
    
  constraints:
    - "人類無法飛行（除非有特定裝備）"
    - "夜間城市封鎖（民用層禁止通行）"
    
  absolutes:
    - "死亡不可逆轉（除非有特定裝置）"
    - "時間無法倒流"
```

### Step 2: 建立規則矩陣

```yaml
rule_matrix:
  energy_system:
    base_unit: "算力"
    regeneration: "8小時休息恢復100%"
    consumption_rates:
      basic_skill: 10
      medium_skill: 30
      advanced_skill: 60
      ultimate: 100
    overdraft_penalty: "硬體損壞"
    
  movement:
    ground_speed: "正常人類"
    flight: "需要御劍或載具"
    teleportation: "不存在"
    
  combat:
    damage_types: ["物理", "數據", "混合"]
    healing_limits: "每日最多恢復30%傷勢"
    death_threshold: "致命傷害無法救治"
```

### Step 3: 驗證場景

當 `skill_scene_writer` 產生內容時，驗證是否違規：

```yaml
validation_check:
  scene: "李玄連續使用三次離線劍意"
  
  rule_check:
    - rule: "高階技能冷卻12小時"
      skill: "離線劍意"
      level: "高階"
      cooldown: 12
      violations:
        - "第二次使用時僅過1小時"
        - "第三次使用無冷卻"
      result: "FAIL"
      
  verdict: "違反世界規則"
  
  suggestions:
    - "延長時間跨度（讓三次使用間隔12小時）"
    - "改用低階技能（無冷卻限制）"
    - "支付代價（硬體損壞）"
```

### Step 4: 例外處理

```yaml
exception_handling:
  # 有些規則可以被打破，但需要代價
  breakable_rules:
    - rule: "高階技能冷卻"
      bypass_method: "消耗珍稀道具"
      consequence: "永久降低最大算力"
      
    - rule: "夜間封鎖"
      bypass_method: "高級通行證"
      consequence: "被系統記錄"
      
  # 這些規則絕對不可打破
  absolute_rules:
    - "死亡不可逆轉"
    - "時間無法倒流"
```

### Step 5: 輸出報告

```yaml
validation_report:
  scene_id: "CH15_SCENE_3"
  
  checks_passed: 5
  checks_failed: 2
  
  violations:
    - rule: "技能冷卻"
      severity: "high"
      auto_fix: false
      requires_rewrite: true
      
  warnings:
    - "能量消耗接近上限"
    - "建議下一場景安排休息"
```

## 輸出格式

```
⚖️ 世界規則驗證
═══════════════════════════════════════════════════
  場景：第15章戰鬥場景
═══════════════════════════════════════════════════
  ✅ 通過：5 條規則
  ❌ 違規：2 條規則
───────────────────────────────────────────────────
  違規詳情：
  
  [高] 技能冷卻違規
      離線劍意需冷卻12小時
      實際間隔：1小時
      建議：延長時間或支付代價
      
  [中] 能量透支
      當前算力：120%消耗
      後果：需描寫硬體損壞
───────────────────────────────────────────────────
  自動修復：不適用（需人工重寫）
═══════════════════════════════════════════════════
```
