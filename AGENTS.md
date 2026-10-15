# 叙事工坊 (ai-creation-studio) - Agent 规则与项目指引

本项目是一个面向 2–6 岁儿童双语英语启蒙短视频的故事到提示词编译管线。作为 AI 智能助手（如 Google Antigravity / Gemini、OpenAI Codex、Claude Code 等），在此工作区操作或响应叙事工坊相关任务时，请遵循以下流程与规则。

---

## 核心技能流水线

本项目包含 4 个核心技能，按顺序逐步递进：

1. **`kids-story-planner`（故事策划师）**
   - **输入**：教学词汇（必需），可选角色、平台、节奏模式。
   - **交付**：规格设定、选定戏剧母题、教学与 TPR 映射、剧情节拍大纲、家长 CTA，共五栏。
   - **边界**：不划分具体镜头、景别、机位或生成提示词；策划稿必须交由 reviewer 审查。

2. **`kids-story-reviewer`（剧本医生）**
   - **输入**：planner 的完整五栏策划稿。
   - **职责**：执行四条硬性红线筛查（`VOCAB_GROUNDING_MISMATCH`、`UNCLOSED_AIRBORNE_ACTION`、`TEACHING_POLLUTION_AT_END`、`MAGIC_RESET`）与四维诊断。
   - **交付**：红线体检、打磨建议；全部通过时生成 Golden 4 拍润色稿（首钩示范 ➔ 反向加码 ➔ 失控破功 ➔ 物理回弹复位）。未通过时严禁进入导演阶段。

3. **`storyboard-director`（分镜导演）**
   - **输入**：reviewer 完整且严格通过的输出。
   - **交付**：导演总览、8 列秒级视听分镜表（序号、秒数/区间、景别与机位、三段式画面与物理黏土动态、角色英文台词、音效 SFX、平台安全字幕/花字、连续性与参考锚点）、首尾无缝循环验证（含 `first_start` / `last_end` 状态 JSON）。
   - **约束**：单镜时长 2.5–4.5 秒，镜数满足 `ceil(T / 4.5) ≤ N ≤ floor(T / 2.5)`。

4. **`ai-prompt-generator`（提示词编译器）**
   - **输入**：director 的完整输出。
   - **交付**：全局一致性资产卡（Preset + Adapter）、逐镜 T2I/I2V 制作矩阵、6 列后期音画装配清单。
   - **边界**：视觉动作与后期音画分离，末镜 Keyframe Control 指向首镜起始帧实现循环。

---

## 共同制作硬约束

- **资产预算**：全片最多 **1 个场景、2 个角色、0 至 1 个核心道具**。背景物件一旦参与交互即计入预算。
- **接地与受力**：每镜首帧与 Hold 均需明确地面支点；跳跃须在同镜单拍内完成起落与缓冲，滞空不超过 1 秒；手部阀门临时封口与施力因果明确。
- **构图与机位**：9:16 竖屏，顶部 25% 留作叠字安全区，道具几何中心保持在画面宽度 35%–65%。首末镜机位与构图严格对齐。
- **首尾无缝循环**：末镜尾帧状态必须与首镜首帧完全匹配（物理因果复位或匹配的循环运动）。

---

## 自动化闭环校验（自主运行）

当具备终端/沙盒执行能力的 Agent 在执行 `storyboard-director` 或 `ai-prompt-generator` 阶段的生成与修改时：

1. **自动运行 Python 校验**：
   在输出分镜表或提示词矩阵后，利用终端工具自动运行校验脚本：
   ```bash
   python3 plugins/narrative-studio/skills/storyboard-director/scripts/validate_production_markdown.py <director.md> [prompts.md]
   ```
2. **自我修正**：
   若脚本报告时间轴重叠、花字生命周期冲突、镜头数不合规或循环状态键值缺失等错误，请在最终回复用户前自动修正内容，直至校验输出 `PASS`。
