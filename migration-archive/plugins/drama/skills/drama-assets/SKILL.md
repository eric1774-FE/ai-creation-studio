---
name: drama-assets
description: 从中文小说、漫剧剧本或高留存文案中提取并锁定角色、服装妆发、场景和关键道具等生产资产，输出 story-asset-manifest/v2，先确认核心资产清单，再用内置 imagegen 按依赖生成所选参考图、场景全景与九宫格机位图，并导出离线资产HTML报告。适用于固定资源、角色定妆、场景设定、道具参考、资产一致性或为分镜准备参考图；不负责分镜或视频生成。
---

# 漫剧固定资产

把叙事文本整理为可追踪的 `story-asset-manifest/v2`，再生成用户确认过的核心视觉资产。默认中文，提示词同时提供语义一致的英文版本。

## 必读参考

提取资产前完整读取 [prompt-standards.md](references/prompt-standards.md)。生成选择和登记图片前读取 [production-extension.md](references/production-extension.md)。

## 边界

- 完整读取用户指定的故事，不改写剧情、不拆分镜头。
- 资产事实、版本、提示词和依赖使用 `story-asset-manifest/v2`；不再发明另一套资产格式。
- 只调用内置 `imagegen`。内置工具不可用时说明情况并停止生图，不静默切换 CLI/API。
- 不覆盖已有图片；重生成使用 `-v2`、`-v3` 等新文件名。

## Phase 1：提取与第一次确认

1. 按提示词规范生成 `<project>-asset-manifest.json`。
2. 运行结构检查并生成默认选择：

```bash
python3 scripts/manage_assets.py plan <project>-asset-manifest.json \
  --output <project>-asset-selection.json
python3 scripts/manage_assets.py validate <project>-asset-selection.json
```

新项目还必须检查 A/B 级场景的全景图与九宫格机位图：

```bash
python3 scripts/manage_assets.py validate <project>-asset-selection.json \
  --require-scene-coverage
```

3. 默认预选全局视觉圣经、A/B级角色、A/B级场景的全景定场图与九宫格机位图、主要角色关联的服装妆发、在至少两个连续性阶段出现的关键道具，以及它们的提示词依赖。
4. 在聊天中展示核心与可选数量、预计生图调用数、依赖关系和输出规格，请用户增删。此处是第一次确认；确认前不得调用生图。
5. 用户确认后运行：

```bash
python3 scripts/manage_assets.py approve <project>-asset-selection.json \
  --include <额外prompt_id,可省略> --exclude <排除prompt_id,可省略> \
  --output <project>-asset-approved.json
```

## Phase 2：自动生图

运行 `queue` 获取依赖排序：

```bash
python3 scripts/manage_assets.py queue <project>-asset-approved.json
```

逐项处理：

1. 只对状态为 `ready` 的项调用一次内置 `imagegen`。
2. `generate` 直接使用该提示词；`edit` 必须先加载每个依赖输出，并按 `input_refs.role` 明确图片职责。
3. 检查主体、构图、风格、身份和禁止项。失败时只允许一次针对性修正重试。
4. 最终图片移入当前项目的 `assets/`，使用 `<prompt_id>.png`；存在同名文件时创建版本名。
5. 每次结果都登记到新一版 Manifest：

```bash
python3 scripts/manage_assets.py record <current.json> --prompt-id <id> \
  --status succeeded --uri assets/<id>.png --output <next.json>
```

单项失败登记 `failed --error <原因>` 后继续；依赖失败的下游登记 `skipped --error <上游失败>`。完成后运行：

```bash
python3 scripts/manage_assets.py validate <final.json> --require-ready
```

核心资产未齐时不得声称生产就绪，但应交付已成功图片、失败清单和可重试提示词。

随后立即生成资产阶段报告，不必等待分镜：

```bash
python3 scripts/manage_assets.py render <final.json> \
  --output <project>-assets-report.html
```

报告保持单文件离线运行，图片使用报告旁的相对路径；提供资产筛选、生成状态、场景定场职责、中英文提示词切换、复制、缺图占位、质量门和 JSON 导出。页面只审核、搜索、复制和导出，不内联编辑。

## 默认交付

- 第一次确认前：资产Manifest、核心/可选清单和预计生图数量。
- 生图后：带 `production` 状态的Manifest、项目资产目录、资产HTML报告、验证结果和失败摘要。
- `$drama-storyboard` 在分镜编译完成后另行生成资产与分镜双面板报告和生产包。
