# 叙事工坊

Codex 本地创作插件，包含 5 个可独立调用的 Skill，支持短剧/漫剧和绘本创作。V1 只生成文本、结构化制作资料和模型提示词，不调用图片或视频生成。

## 安装

```bash
codex plugin marketplace add /Users/a0000/project/ai-creation-studio
codex plugin add narrative-studio --marketplace ai-creation-studio
```

安装后可以使用 `$creative-workflow`、`$story-development`、`$shot-design`、`$asset-design` 和 `$illustrated-book`。

## 项目输出

所有项目资料保存在当前工作区的 `creative-projects/<project-slug>/`。插件会维护 `project.json`，阶段正文以 Markdown 为主，资产和分镜清单使用 JSON，关键交付附离线 HTML 报告。

资产阶段沿用项目已确认的主风格。若项目尚未选风格，资产整理开始前会询问；V1 预设为温暖水彩手绘与皮克斯风格 3D，可提供自定义描述或参考。

## 仓库结构

- `.agents/plugins/marketplace.json`：本地 Marketplace 清单。
- `plugins/narrative-studio/`：可安装插件。
- `migration-archive/`：迁移来源的只读备份，不属于插件包。
- `tests/acceptance-cases.md`：手工验收场景。
