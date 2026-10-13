# 项目文件格式

## 目录建议

```text
creative-projects/<slug>/
├── project.json
├── sources/                 # 用户授权复制的原始输入，只读
├── story/                   # 故事、事件表、故事骨架与改编策略
├── scripts/                 # 分集剧本与审核记录
├── assets/                  # 固定资产清单与提示词
├── storyboard/              # 分镜清单、检查与模型提示词
├── picturebook/             # 绘本分页、插画和微动作提示词
└── reports/                 # 关键阶段离线 HTML
```

只建立当前任务所需目录。文件名使用稳定阶段名和版本号，例如 `story-skeleton-v1.md`、`episode-01-v2.md`、`asset-manifest-v1.json`、`storyboard-v1.json`。报告可以按阶段分别保存，例如 `story-review-v1.html`、`assets-v1.html`、`storyboard-v1.html`。

## `project.json`

顶层 `schema_version` 固定为 `creative-project/v1`。至少记录：

- `project_id`、`title`、`project_type`、`created_at`、`updated_at`。
- `visual_style`：尚未选定时为 `null`；选定后记录配置 ID、显示名称、来源（预设/自定义/参考）、描述和确认时间。
- `sources[]`：来源 ID、文件路径/章节定位、类型、是否复制到 `sources/`、只读标记。
- `stages`：阶段名、状态、输出相对路径、版本、更新时间。
- `approvals[]`：确认阶段、确认范围、时间和用户决定摘要。
- `provenance_policy`：事实/推断/创作新增的标记约定。

路径必须相对项目目录，使用 `/` 分隔。不得记录机器凭据、私密环境变量或云端地址作为写入目标。

## 来源追踪

建议来源定位格式：`文件名 > 第 N 章 > 第 N 段`；Markdown 还可记录行号或标题。对无法精确定位的粘贴文本，用稳定编号（如 `P-001`）并说明编号基于输入顺序。后续阶段沿用来源 ID，不重新编造定位。

## 阶段状态

`pending`、`in_progress`、`awaiting_confirmation`、`approved`、`needs_revision`、`blocked`、`complete`。用户未确认的产物不能记录为 `approved`。
