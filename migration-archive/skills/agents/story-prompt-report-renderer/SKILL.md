---
name: story-prompt-report-renderer
description: 校验 story-asset-prompt-extractor 产出的 story-asset-manifest/v2 UTF-8 JSON，并渲染为离线单文件 HTML 提示词报告。按角色、场景、实体状态和独立资产聚合，再按角色本体、服装妆发、场景、道具、载具与生物、环境、灯光、特效和声音分类；支持中文默认显示、英文就地切换和当前语言正文复制；不读取故事、不补写资产、不修改提示词。
---

# 故事提示词 HTML 报告

只校验或渲染 `story-asset-manifest/v2`。不要读取原故事补写资产，不要修改提示词正文，也不要把 Markdown 或散乱文本猜测成 Manifest。

## 输入边界

- 接受 UTF-8 `.json`；用户粘贴完整 JSON 时，先原样写入当前任务临时文件。
- `assets` 是资产、事实和提示词的唯一数据源；实体、状态、独立资产和连贯性只保存引用。
- 必须包含 `schema_version`、`reference_inputs`、`asset_type_coverage`、`assets`、`entities`、`standalone_asset_refs`、`continuity` 和 `quality_checks`；详细字段由脚本校验。
- 每条提示词必须同时包含非空中文 `text` 与英文 `text_en`；中文分别含 `风格：`、`负面约束：`，英文分别含 `Style:`、`Negative constraints:`，同一语言不得出现完全相同的提示词正文。
- 输入不是有效 V2 时停止并返回具体错误，不生成残缺报告，不绕过校验。

## 仅校验

用户只需校验，或提取器在交付 Manifest 前执行：

```bash
python3 <skill-dir>/scripts/render_prompt_report.py --input <manifest.json> --validate-only
```

成功时输出“验证通过”；失败时返回版本、事实、提示词依赖、资产引用、覆盖或连贯性错误。

## 渲染流程

1. 确认输入存在并为 UTF-8 JSON。
2. 默认将 `.json` 替换为 `.html`；用户指定文件名时服从。
3. 目标已存在时依次追加 `-2`、`-3`，不要覆盖。
4. 运行：

```bash
python3 <skill-dir>/scripts/render_prompt_report.py --input <manifest.json> --output <report.html>
```

5. 确认 HTML 存在且非空，返回摘要和可点击链接。

## 输出约束

- 保持单文件、离线可用；CSS、JavaScript 与 Manifest JSON 安全内嵌。
- 页面先按“角色 / 场景 / 独立资产 / 项目报告”组织，再在实体内部按 `type + W.subtype` 派生角色本体、服装、发型与胡须、妆容与彩绘、场景本体、道具、载具与生物、环境、灯光与色彩、特效和声音分类；只显示非空分类。
- 分类内继续区分共用资产与各故事状态；人物默认打开角色本体，场景默认打开场景本体，分类数量按唯一资产版本计算。
- 展示稳定事实、版本事实、英文枚举的中文标签、参考图允许与禁止影响、提示词输入依赖、输出规格、资产覆盖和阶段连贯性。
- 结构校验状态由脚本产生；Manifest 中的 `quality_checks` 只作为语义自检显示。
- 每条提示词默认显示中文，并提供“查看英文版本”按钮原位切换；复制按钮只复制当前显示语言正文。
- 同一资产在多处展示时仍读取同一底层记录；不得复制提示词正文。
- 保留特殊字符转义、引用完整性、提示词依赖无环校验、键盘页签、移动端布局、语言切换可访问性和复制回退。

## 资源

- `scripts/render_prompt_report.py`：V2 校验、`--validate-only` 与 HTML 生成。
- `scripts/test_render_prompt_report.py`：校验器和渲染器回归测试。
- `assets/prompt-report/`：HTML 模板、样式和运行时脚本。
