# 預設模板參考

本文件列出所有可用的預設模板及其配置。

## xianxia (仙俠/修仙)

```yaml
pacing_pointer: 0.3
words_per_chapter:
  min: 3500
  max: 5500
  target: 4000
content_weights:
  combat: 0.40
  dialogue: 0.15
  internal_monologue: 0.20
  scenery_desc: 0.15
  world_building: 0.05
  action: 0.05
style_hints:
  - 古風用語
  - 修煉術語
  - 階級分明的用語體系（前輩、道友）
emotion_settings:
  high_tension_threshold: 75
  max_consecutive_high: 4
```

---

## scifi (科幻)

```yaml
pacing_pointer: 0.5
words_per_chapter:
  min: 3000
  max: 4500
  target: 3500
content_weights:
  combat: 0.25
  dialogue: 0.25
  internal_monologue: 0.10
  scenery_desc: 0.15
  world_building: 0.20
  action: 0.05
style_hints:
  - 科技術語
  - 冷硬風格
  - 注重邏輯解釋
emotion_settings:
  high_tension_threshold: 65
  max_consecutive_high: 3
```

---

## romance (言情)

```yaml
pacing_pointer: 0.4
words_per_chapter:
  min: 2500
  max: 4000
  target: 3000
content_weights:
  combat: 0.05
  dialogue: 0.40
  internal_monologue: 0.30
  scenery_desc: 0.15
  world_building: 0.05
  action: 0.05
style_hints:
  - 細膩情感描寫
  - 大量內心戲
  - 注重氛圍營造
emotion_settings:
  high_tension_threshold: 60
  max_consecutive_high: 2
```

---

## mystery (懸疑)

```yaml
pacing_pointer: 0.5
words_per_chapter:
  min: 3000
  max: 4500
  target: 3500
content_weights:
  combat: 0.10
  dialogue: 0.35
  internal_monologue: 0.20
  scenery_desc: 0.20
  world_building: 0.10
  action: 0.05
style_hints:
  - 埋設線索
  - 控制信息揭露節奏
  - 製造懸念
emotion_settings:
  high_tension_threshold: 70
  max_consecutive_high: 3
```

---

## fantasy (西幻)

```yaml
pacing_pointer: 0.4
words_per_chapter:
  min: 3500
  max: 5000
  target: 4000
content_weights:
  combat: 0.35
  dialogue: 0.20
  internal_monologue: 0.10
  scenery_desc: 0.20
  world_building: 0.10
  action: 0.05
style_hints:
  - 宏大世界觀
  - 種族設定
  - 魔法系統
emotion_settings:
  high_tension_threshold: 70
  max_consecutive_high: 3
```

---

## cyberpunk (賽博龐克)

```yaml
pacing_pointer: 0.6
words_per_chapter:
  min: 3000
  max: 4500
  target: 3500
content_weights:
  combat: 0.25
  dialogue: 0.25
  internal_monologue: 0.15
  scenery_desc: 0.20
  world_building: 0.10
  action: 0.05
style_hints:
  - 高科技低生活
  - 霓虹美學
  - 反烏托邦氛圍
  - 義體改造術語
emotion_settings:
  high_tension_threshold: 65
  max_consecutive_high: 3
```

---

## survival (末日生存)

```yaml
pacing_pointer: 0.5
words_per_chapter:
  min: 3000
  max: 4500
  target: 3500
content_weights:
  combat: 0.25
  dialogue: 0.20
  internal_monologue: 0.15
  scenery_desc: 0.20
  world_building: 0.10
  action: 0.10
style_hints:
  - 危機感營造
  - 資源管理描寫
  - 團隊協作
  - 恐怖氛圍
  - 簡潔實用的對話
emotion_settings:
  high_tension_threshold: 75
  max_consecutive_high: 4
  buffer_mode: "suggest"
```

---

## 使用方式

```bash
/nvGenesis name=xxx type=xxx preset=survival
```

預設值會被手動指定的參數覆蓋。

---

## 自定義覆蓋

可在 `/nvGenesis` 時覆蓋預設：

```bash
# 使用懸疑預設但增加戰鬥比例
/nvGenesis name=xxx preset=mystery weights="combat:0.3"

# 使用末日生存但放慢節奏
/nvGenesis name=xxx preset=survival pacing=0.3
```
