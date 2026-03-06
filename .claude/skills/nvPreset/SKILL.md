---
description: 查看可用預設模板
---

# /nvPreset - 查看預設

列出可用的類型預設模板及其配置。

## 參數

無參數，直接執行即可：

```
/nvPreset
```

## 可用預設

### xianxia (仙俠/修仙)
```yaml
pacing_pointer: 0.3
words_per_chapter:
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
  - 階級分明的用語體系
```

### scifi (科幻)
```yaml
pacing_pointer: 0.5
words_per_chapter:
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
```

### romance (言情)
```yaml
pacing_pointer: 0.4
words_per_chapter:
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
```

### mystery (懸疑)
```yaml
pacing_pointer: 0.5
words_per_chapter:
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
```

### fantasy (西幻)
```yaml
pacing_pointer: 0.4
words_per_chapter:
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
```

### cyberpunk (賽博龐克)
```yaml
pacing_pointer: 0.6
words_per_chapter:
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
```

## 使用方式

在 `/nvGenesis` 中使用 `preset` 參數：
```
/nvGenesis name=我的小說 type=仙俠 preset=xianxia
```

預設值會被手動指定的參數覆蓋。
