# 叙事工坊

叙事创作 Skill 的开发仓库，目前包含 `kids-story-planner`（少儿双语动画·爆款故事策划师）、`storyboard-director`（少儿双语动画·分镜导演）和 `ai-prompt-generator`（AI 提示词与制作清单编译器）。三个 Skill 分工交接，共用物理、时间与提示词硬规则。

## 当前能力

`kids-story-planner` 为 2–6 岁儿童策划双语英语启蒙短视频，根据教学词汇匹配八大反差戏剧母题。`auto` 自动选择节奏，`rapid` 为 10–15 秒两拍，`standard` 为 15–25 秒三至四拍。

每条故事最多一个场景、两个角色、一个核心道具。输出规格设定、选定母题、教学与 TPR 映射、动态节拍和家长 CTA；策划说明用中文，成片采用英文原声与轻量中文词义字幕。教学词绑定可观察实体状态，垂直受力有把手/边缘/指痕凹陷等着力点；未封闭气动/流体道具写清主手外缘抓握、副手临时封口与释放因果；双角色各至少一句台词，全片有一处情绪感叹词，母题动作次数与 Beat 正文逐项一致。产出仅为故事策划，不划分镜头、不生成媒体 Prompt 或图片/视频。

`storyboard-director` 接收上述完整故事大纲，保持故事逻辑与资产预算，将节拍拆成秒级视听分镜。极速版使用 3–4 镜，标准版使用 4–6 镜、必要时允许 ±1 镜，每镜 2.5–4.5 秒。仅输出导演总览、8 列分镜表和首尾循环验证，包含三段式黏土动力学、英文原声、玩具拟声音效与同步英文花字；不生成媒体 Prompt、工具参数或图片/视频。

`ai-prompt-generator` 严格接收导演总览、8 列秒级分镜表和首尾循环验证，编译为三个固定栏目：全局一致性资产卡、逐镜 T2I 故事板起始帧与 I2V 动态驱动矩阵、后期音画装配清单。采用 Preset + Adapter：Pip、Toby 与 Cozy Playroom 使用内置黄金锚点，自定义角色、场景和道具保留身份与剧情功能并适配为统一黏土风格；继承一个场景、最多两个角色、最多一个核心道具的预算，保留上游剧情与时序。仅对常规旧 Pan 提供有限的 Static 规范化：原固定取景必须能覆盖完整动作，并同步提示词与控制字段，否则要求上游修正。

构图、T2I 与 I2V 显式锁定角色中心、道具中心和脚底基线等数值坐标，按上游空间关系填写，零道具不补物件。T2I 只描述 t=0 的静态切片、地面支点与接触阴影，过滤过程动作描述；全局资产卡与每条 T2I 固定加入暖粉彩、3200K studio warm lighting 和 consistent clay material index。双角色入镜的 I2V 用 while 描述副角色在场微动，Hold 明确 aftermotion decays；依赖开口泄压的道具禁止永久封闭描述。每镜通用负向词放入代码块之外的独立 `Negative Prompt:` 字段；`Motion Strength:`、`Camera Mode:`、`Start-Frame:`、`End-Frame:` 也分别单列，台词、SFX 与英文花字进入后期六列表格，单次花字/字幕生命周期合并在触发行，独立声音与镜尾检查仍保留。

`Reference Asset:` 标明首镜起始关键帧作为角色与风格参考、上一镜实际生成的尾帧作为连续性参考；未生成资产标记待生成。末镜保留物理复位过程，在提示词代码块之外分别声明 `Keyframe Control: First-Last Frame Mode` 与 `End-Frame: Shot 1 Start Keyframe`。

导演阶段可补充目标平台：Douyin 仅为核心教学词加轻量中文词义；TikTok、YouTube Shorts 及平台缺省时使用英文花字，可配英文字幕。编译器沿用该字幕策略。三个 Skill 按“故事策划 → 秒级分镜 → 提示词与后期装配”分别手动调用，不自动调用下游技能；全部只生成文字，不直接调用外部绘图或视频模型 API，也不生成图片或视频。

## 一致性与时间约束

- 每镜首帧与整个 Hold，所有角色均有地面支点。被动冲击优先贴地滑行或单脚后仰；教学语义确需的跳跃须在同镜爆发段完成起落与缓冲，滞空 ≤1.0 秒。
- 默认 Static，首末镜固定为中全景 / Static 且取景对齐，默认禁用常规 Pan/Tilt；中间升级镜最多一次单向微推，终点 ≤1.1×。跟随仅适用于既有、语义确需的单角色大范围位移。道具几何中心全过程保持在画面宽度 35%–65%，膨胀轮廓可以超出。
- 花字只承载核心教学词，弹出即完整可读，保持 1.2–1.5 秒，退场固定 0.5 秒；满足 `T_trigger + T_hold + 0.5s ≤ T_shot`。同屏最多一个花字，前字完全消失至后字触发间隔 ≥0.5 秒。末镜触发 ≤单镜时长−3.0 秒，完全消失 ≤单镜时长−1.25 秒，镜尾至少 1.25 秒无花字、无字幕。
- 声音按台词/主要 SFX 实际区间的并集审计：一般前景空白 ≤1.5 秒，高潮空白 ≤2.0 秒；持续声明区间内禁止重复触发，环境微声不计入前景覆盖，跨镜空白连续计算。缺少区间或生命周期时，编译器要求补充导演稿。

## 本地工业化校验

三个技能各含坐标级 Golden Case 与三类 Bad Case。正例以 Pip x=30%、Toby x=70%、道具 x=50%、脚底基线 y=88% 说明空间与教学实体绑定；球形拉扯需具备可见受力指痕凹陷。末镜不得添加 step away / walk away 等离场位移，物理坐标与姿态须回到首镜。原始三模型样稿保留为历史素材，不自动视为新版合格产物。

在仓库根目录执行：

```bash
python3 plugins/narrative-studio/skills/storyboard-director/scripts/validate_production_markdown.py tests/fixtures/industrial-upgrade/golden-director.md tests/fixtures/industrial-upgrade/golden-prompts.md
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

校验器只依赖 Python 标准库，输入为导演八列表 Markdown 和可选制作矩阵 Markdown。导演稿须按模板显式声明出场角色、高潮 Beat、每镜首帧/Hold支点；制作矩阵可声明每镜入镜角色，单角色入镜无需补人或 while；花字使用标准单行生命周期，声音使用明确起止区间。配套字幕可在花字行末写 `；字幕：High/高处（与花字同生命周期）`。缺少可解析证据报 `INPUT_FORMAT`，不会猜测或通过。

跨镜/Hold 悬空报 `ZERO_AIRBORNE_CUT`，花字重叠或安全期不足报 `TEXT_OVERLAP`，镜头/阶段/音画越界报 `SHOT_TIME_OVERFLOW`；均包含镜号或秒点并返回非零退出码。可选矩阵同时检查坐标锚点、Palette Lock、T2I 过程词、开口道具禁词、双角色 while 保活、独立控制字段及后期花字生命周期是否保持上游时序。脚本检查显式声明和确定性规则，教学语义、完整受力因果、姿态复原及最终媒体质量仍需复核。

## 安装与使用

三个 Skill 已实现，通过插件的 `"skills": "./skills/"` 入口自动发现。需要验收安装效果时，由你手动注册本地来源并安装：

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

策划师只有 `teaching_words` 必需，其余参数可省略，也可以直接用自然语言提出请求。拿到完整策划后，在同一对话调用导演，或在新对话粘贴完整上游输出：

```text
$storyboard-director
target_platform: YouTube Shorts
以下是 kids-story-planner 的完整输出：
[粘贴规格设定、选定戏剧母题、教学与 TPR 映射、剧情节拍大纲及家长 CTA]
```

导演仅接收上游策划，不能用一句题材或教学词替代故事大纲；缺失契约、超出预算或无法物理复位时，先要求补充或修正上游。拿到完整导演输出后，再调用编译器：

```text
$ai-prompt-generator
以下是 storyboard-director 的完整输出：
[粘贴导演总览、完整 8 列秒级分镜表、首尾无缝循环验证]
```

编译器不能用故事大纲替代导演输出，也不自行补写台词、音效、花字或时间点。输入缺项、对白配额不齐、接地/构图/时限冲突或循环无效时，先指出需要上游修正的内容。技能原文见 [故事策划师](plugins/narrative-studio/skills/kids-story-planner/SKILL.md)、[分镜导演](plugins/narrative-studio/skills/storyboard-director/SKILL.md) 与 [提示词编译器](plugins/narrative-studio/skills/ai-prompt-generator/SKILL.md)，验收场景及历史执行记录见 [验收记录](tests/acceptance-cases.md)。

## 仓库结构

- `plugins/narrative-studio/`：插件清单与三个独立 Skill。
- `.agents/plugins/marketplace.json`：本地插件来源清单。
- `migration-archive/`：保留的迁移记录，不作为当前实现。
- `tests/acceptance-cases.md`：三个 Skill 的当前验收口径与历史记录；`tests/fixtures/industrial-upgrade/`、`tests/test_industrial_validator.py`：正反例与自动回归测试。
