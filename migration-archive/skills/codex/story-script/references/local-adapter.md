# Codex 本地适配层

本文件只适配 Toonflow ScriptAgent 的运行环境，不修改其创作与审核标准。

## 项目目录

在用户指定目录工作；未指定时，在当前工作目录创建 `{作品名}-短剧改编/`。已有项目禁止覆盖，继续写入其现有结构。

```text
{项目目录}/
├── project-config.md
├── source/chapters/0001.md ...
├── events.md
├── viral-points.md
├── story-skeleton.md
├── adaptation-strategy.md
├── reviews/
│   ├── story-skeleton-review.md
│   └── adaptation-strategy-review.md
└── scripts/EP01.md ...
```

所有新建或修改文本文件使用 `apply_patch`。文件过长时可以分段读取，但选定的参考提示词必须读到末尾。

## 原工具映射

| Toonflow 工具/数据 | Codex 等价操作 |
|---|---|
| `get_novel_events(chapterIndexes)` | 从 `events.md` 读取指定章节行 |
| `get_planData(projectId, key)` | `storySkeleton` → `story-skeleton.md`；`adaptationStrategy` → `adaptation-strategy.md`；项目参数 → `project-config.md` |
| `get_novel_text(chapterIndex)` | 读取 `source/chapters/{四位编号}.md` |
| `get_script_content(ids)` | 只读取当前集的直接上一集；第一集不读 |
| 保存故事骨架 | 写入 `story-skeleton.md` |
| 保存改编策略 | 写入 `adaptation-strategy.md` |
| 保存分集剧本 | 每集单独写入 `scripts/EP{两位编号}.md` |
| 保存审核报告 | 写入 `reviews/` 对应文件，不覆盖被审核稿 |

## 角色隔离

原系统的决策代理、执行代理、审核代理在 Codex 中按三个串行工作回合模拟，不合并职责：

1. 决策回合：只判断阶段、依赖、用户确认项和文件范围，不写创作结果。
2. 执行回合：重新读取当前阶段原始提示词及项目文件，生成并落盘，不自行评分。
3. 审核回合：重新读取监督提示词、事件表和实际执行稿，仅输出审核报告，不直接改稿。

若用户要求根据审核修改，重新进入执行回合；修改完成后再次独立审核。

## 原文、事件表与爆款诊断

- 用户提供单文件小说时，按明确章节标题切分；没有可靠章节标题时保留为一个章节，禁止按字数猜章节。
- 保留原文，不润色、不覆盖。用户直接粘贴的短文本可写入 `source/chapters/0001.md`。
- `events.md` 使用事件提取提示词规定的七字段行；逐章处理，章节编号与原文件一致。
- `viral-points.md` 至少包含：故事核、受众心理、爽/虐/爆点、金手指、冲突等级、信息差、单集钩子、付费卡点、前三集付费冲动、前十集约十个可剪 30 秒素材点、约三次大反转及伏笔来源。每项注明原文章节证据，区分“原文已有”和“改编建议”。

## 阶段门禁

- 骨架和策略执行后必须按监督提示词生成审核报告，并把报告呈现给用户。
- A/B 可建议进入下一阶段；C/D 或任何严重问题必须提供原监督模板要求的选项并等待用户决定。
- 未收到用户决定，不跨过骨架审核或策略审核。
- 用户明确要求一次跑完时，可把 A/B 视为授权继续；遇到 C/D 仍停止。
- 剧本默认每批三集、最多五集；完成一批后等待用户继续，除非用户已明确指定完整集数和连续执行。

## 输出兼容

原始提示词要求调用代理或数据库工具时，改为执行上表文件操作。其余要求原样执行，包括 XML 标签、标题、表格、字数/时长、3-15-45 节奏、钩子、心理级爽点、三档信息密度、重大反转、付费卡点和禁止项。
