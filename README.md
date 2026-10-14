# 叙事工坊

叙事创作 Skill 的开发仓库，目前仅包含一个 Skill：`kids-story-planner`（少儿双语动画·爆款故事策划师）。每次只新增、打磨和验收一个 Skill，再决定下一项能力。

## 当前能力

为 2–6 岁儿童策划双语英语启蒙短视频，根据教学词汇匹配八大反差戏剧母题。`auto` 自动选择节奏，`rapid` 为 10–15 秒两拍，`standard` 为 15–25 秒三至四拍。

每条故事最多一个场景、两个角色、一个核心道具。输出规格设定、选定母题、教学与 TPR 映射、动态节拍和家长 CTA；策划说明用中文，成片采用英文原声与轻量中文词义字幕。产出仅为故事策划，不划分镜头、不生成媒体 Prompt 或图片/视频。

## 安装与使用

首个 Skill 已实现。需要验收安装效果时，由你手动注册本地来源并安装：

```bash
codex plugin marketplace add /Users/a0000/project/ai-creation-studio
codex plugin add narrative-studio --marketplace ai-creation-studio
```

安装并加载技能后，在新对话中调用：

```text
$kids-story-planner
teaching_words: Jump
characters: 小恐龙 Pip、小柴犬 Toby
target_platform: YouTube Shorts
pacing_mode: auto
```

只有 `teaching_words` 必需，其余参数可省略，也可以直接用自然语言提出请求。技能原文见 [SKILL.md](plugins/narrative-studio/skills/kids-story-planner/SKILL.md)，验收场景见 [验收记录](tests/acceptance-cases.md)。

## 仓库结构

- `plugins/narrative-studio/`：插件清单与后续 Skill 的开发位置。
- `.agents/plugins/marketplace.json`：本地插件来源清单。
- `migration-archive/`：保留的迁移记录，不作为当前实现。
- `tests/acceptance-cases.md`：当前 Skill 的验收场景与执行记录。
