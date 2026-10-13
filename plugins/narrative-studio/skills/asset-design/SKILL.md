---
name: asset-design
description: 从故事或剧本整理并锁定角色、服装妆发、场景、道具等制作资产，输出来源可追溯的资产清单和中英提示词；当用户要求固定资产、角色设定或资产提示词时使用。
---

# 固定资产

先读取用户指定的完整故事范围、已有项目索引和参考素材说明。字段约定见 [references/asset-manifest.schema.json](references/asset-manifest.schema.json)，可选风格见 [../creative-workflow/references/style-profiles.json](../creative-workflow/references/style-profiles.json)，项目及报告约定见 [../creative-workflow/references/project-format.md](../creative-workflow/references/project-format.md) 和 [../creative-workflow/references/report-format.md](../creative-workflow/references/report-format.md)。

## 风格确认

- 若项目索引已有经确认的 `visual_style`，直接沿用，不重复询问。
- 若没有选风格，在锁定资产前询问用户选择：温暖水彩手绘、皮克斯风格 3D，或自定义描述/参考。展示预设说明；等待用户选择后再生成详细资产提示词。
- 用户提供参考图时，记录其职责（身份、风格、服装、场景等）及允许/禁止影响。参考图只按指定职责影响资产，默认不覆盖原故事事实。
- 每个项目默认单一主风格。只有用户明确要求才做跨媒介或局部混合，并记录范围。
- 新风格加入共享配置时，只增加独立 profile，不改写既有 profile ID 或流程。

## 整理与锁定

1. 从原文提取实体和状态：角色、服装、妆发、场景、道具、载具/生物、环境、灯光、特效及声音。合并别名，不合并不同实体。
2. 分开记录稳定特征和随剧情变化的状态；按故事顺序保存换装、伤情、天气、损坏、置景变化等版本。
3. 每项事实记录来源、定位和可信状态：`confirmed`、`inferred` 或 `pending`。不得把推断写成原文事实；矛盾事实列为待确认。
4. 为参考图创建唯一 ID 并记录用途。输出资产 ID、类型、名称、稳定特征、状态版本、关联实体、来源、待确认项和生成提示词。
5. 生成每个视觉资产的中文与英文模型无关提示词。描述可见外观、材质、色彩、比例、姿态/状态、视角和背景；风格写在提示词中，但不重复无关风格词。声音资产单独记录，不混入图像提示词。
6. 输出清单草案，请用户确认核心资产后再标记为已锁定。用户要求只做部分资产时，不扩写未要求类别。

不生成参考图片，不调用图像模型。默认使用新格式 `creative-assets/v1`，不自动转换旧 Manifest；需要旧资料时先读内容并由当前格式重新整理。

## 交付

资产清单保存为 JSON，来源和编辑说明可用 Markdown 补充。关键资产交付可附独立离线 HTML 报告，展示资产关系、状态、事实来源及中英提示词。
