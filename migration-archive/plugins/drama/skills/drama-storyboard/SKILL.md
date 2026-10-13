---
name: drama-storyboard
description: 将中文小说片段、漫剧剧本或解说文案拆成生产级导演分镜，在确认骨架后编译模型无关提示词、绑定固定资产、组合视频段，并导出无变量的离线HTML报告与生产包。输出 storyboard-manifest/v1 及 production-extension/v1。适用于分镜、镜头表、文案转视频、T2V/I2V、轴线连续性、固定资源绑定、视频段、生产报告或提示词交付；不负责扩写原故事、高留存改写、视频生成或厂商专属语法。
---

# 漫剧生产分镜

把已定稿的叙事文本编排成可确认、可编译、可校验的生产分镜，并把内部 Canonical Manifest 编译为用户可直接复制的无变量生产包。默认中文，保持模型和厂商无关。

## 边界

- 输入可来自原文、剧本、解说稿，或上游 `$drama-expand`、`$drama-retention`、`$story-script` 的结果；除非用户另行要求，不重跑或改写上游内容。
- 只把原文事实和已提供资产视为已确定信息。新增视觉意象必须标记为 `visual_inference`。
- 不承诺任一模型支持首帧、结束帧或视频续写。生成路径只表达能力需求。
- Canonical Manifest 不写供应商语法、模型参数或 LoRA 路径。
- 固定资产由 `$drama-assets` 提取和生成；本 Skill 只消费资产Manifest、判断逐镜可见性并绑定实际图片。
- HTML和生产包是解析后的交付层，不替代 Canonical Manifest。

## 必读参考

开始拆镜前完整读取 [directing-rules.md](references/directing-rules.md)。进入 Phase 2 前再完整读取 [prompt-compilation.md](references/prompt-compilation.md)。绑定资产或导出生产包前完整读取 [production-extension.md](references/production-extension.md)。Manifest 字段以 [storyboard-manifest-v1.schema.json](references/storyboard-manifest-v1.schema.json) 为准。

## Phase 0：生产参数预检

正式拆镜前确认以下五项：

1. 画幅；
2. 目标总时长；
3. 视觉风格；
4. 生成路径：`t2v`、`i2v_start`、`i2v_start_end`、`video_extend` 或 `mixed`；
5. 已确认的 `story-asset-manifest/v2` 或现有角色、场景、道具参考资产及其用途。

缺少任何一项时，集中询问缺失项并停止正式分镜。可以解释选项，但不得用臆测参数生成“正式版”。同时记录能力配置：是否支持输入图片、结束帧和视频续写。

## Phase 1：骨架确认

1. 对输入文本做 UTF-8 SHA-256，写为 `source_digest`。
2. 创建实体映射：角色、角色造型变体、场景、道具和稳定 `ref_tag`。Canonical 标签使用 `{{UPPER_SNAKE_CASE}}`；存在资产Manifest时同时建立 `entity_asset_map`。
3. 创建场景锚点：轴线、主光方向、色温、时间、天气和空间关系。
4. 按导演规则拆出简表：镜号、时长、来源、目的、景别、机位、动作演进、世界矢量、屏幕方向、连续性、声音和风险。
5. 创建 `storyboard-manifest/v1` 骨架，`phase_status` 为 `draft_skeleton`，`prompt_layers` 为 `null`。
6. 保存为 `<project_id>.storyboard-skeleton.r<revision>.json`，并运行验证器。
7. 在聊天中展示实体表、场景锚点和分镜简表，请用户确认。不得在确认前编译长提示词。

用户明确确认当前版本后，把 `approved_revision` 设为当前 `skeleton_revision`，状态变为 `approved_skeleton`。若来源文本、实体、时长或镜头结构改变，递增版本并退回 `draft_skeleton`。

## Phase 2：资产绑定与编译交付

开始前核对 `source_digest`、`skeleton_revision` 和 `approved_revision`。不一致时返回 Phase 1，不沿用旧确认结果。

按编译规则为每镜生成：

- `keyframe_prompt`；
- `motion_prompt`；
- 仅在路径和能力均支持时生成 `end_keyframe_prompt`；
- 与生成路径匹配的 `delivery_prompt`；
- `negative_constraints`；
- 独立 `audio` 声音轨。

把状态设为 `compiled`，并令 `compiled_from_revision == approved_revision == skeleton_revision`。保存完整单文件 `<project_id>.storyboard-manifest.r<revision>.json`，运行：

```bash
python3 scripts/validate_storyboard_manifest.py <manifest.json>
```

存在错误时修正后再交付。警告应修正或在摘要中说明；严谨门禁使用 `--strict`。

随后为每镜建立显式资产绑定：

1. 根据画面中实际可见的角色造型、场景、服装和关键道具填写 `extensions.production_v1.shot_asset_bindings`。
2. 只绑定需要上传给生成模型的图片；剧情提到但画面不可见的资产不得加入。
3. A/B级场景的大全景优先绑定 `scene_panorama`；对话正反打、侧拍或空间转向优先绑定 `scene_coverage_grid`，并写明最终只输出一个镜头、不得复制九宫格版式。
4. 资产输出存在成功 `prompt_id` 时让脚本补齐 URI；旧 `manual_continuity_assets` 只导入为 `legacy_manual`，不猜测归属。
5. 运行生产编译：

```bash
python3 scripts/production_pack.py prepare <storyboard.json> \
  --assets <asset-manifest.json> --output <storyboard.production.json>
python3 scripts/production_pack.py validate <storyboard.production.json> \
  --assets <asset-manifest.json>
```

脚本默认把同场景、同生成模式的连续镜头贪心组合为不超过10秒的视频段；明确 `segment_break`、场景/生成模式变化或时间跳跃必须另起一段。单镜超过上限时先回到骨架拆镜。

验证通过后生成一个离线双面板报告和生产包：

```bash
python3 scripts/production_pack.py render <storyboard.production.json> \
  --assets <asset-manifest.json> --output <project>-production-report.html
python3 scripts/production_pack.py export <storyboard.production.json> \
  --assets <asset-manifest.json> --out-dir <project>-production
```

报告和每段 `prompt.md` 必须没有 `{{...}}`；视觉提示词、参考图职责与声音轨分开显示。

## 默认交付

- Phase 1：参数摘要、实体映射、场景锚点、导演分镜简表、骨架 JSON 文件和待确认版本号。
- Phase 2：完整 Canonical Manifest、资产绑定与视频段、离线HTML报告、无变量生产包、验证结果和风险摘要。
- 聊天每页最多展示 10 镜，并根据实际体积缩小；完整 JSON 优先保存为文件。
- 无法写文件时，按编译规则输出一个合法索引对象和多个独立合法分卷。禁止截断 JSON。

## 质量门禁

交付前逐项确认：

- 总时长、镜头顺序和版本锁定正确；
- 所有 ID 和 `ref_tag` 唯一、已声明、引用完整；
- 起止状态结构化，动作节拍有序，一镜一个主要动作目标；
- 世界矢量与屏幕方向分开，越轴有策略；
- 主光、色温、视线、动作接点、服装和道具状态连续；
- 小于 30 度且景别变化不足两级的标准切镜已告警或有合法剪辑豁免；
- 三人以上复杂动作已拆镜；
- 抽象台词的新增画面被明确标为视觉推断；
- 首帧、动态、可选结束帧和声音轨没有混写；
- Canonical Manifest 不含供应商专属语法。
- 视频段按顺序且恰好覆盖全部镜头一次，不跨场景或生成模式，不超过生产上限；
- 逐镜资产只引用已声明实体、资产提示词和可访问图片，同一镜头不重复绑定；
- 已选核心资产缺失时生产状态不是 `ready`；
- HTML、生产Manifest和所有 `prompt.md` 不含 Canonical 标签。
