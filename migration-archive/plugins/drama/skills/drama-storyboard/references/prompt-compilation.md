# 分镜提示词编译规则

## 1. 编译前置条件

Phase 2 只编译当前已确认骨架。必须同时满足：

- `phase_status` 已由 `approved_skeleton` 进入 `compiled`；
- `approved_revision == skeleton_revision`；
- `compiled_from_revision == approved_revision`；
- 当前输入计算出的 `source_digest` 与确认时一致。

来源文本、实体、时长或镜头骨架发生变化时，增加 `skeleton_revision`，状态退回 `draft_skeleton`，重新确认。

## 2. Canonical 标签

核心 Manifest 只使用稳定占位符，如 `{{CHAR_SHENLING_BATTLE_V1}}`、`{{LOC_GRAVEYARD_NIGHT}}`。标签必须唯一、已声明，并在相应镜头的提示词中出现。不得在 v1 中写入 `@角色名`、LoRA 权重、节点名称或供应商专属参数；这些由下游适配器转换。

角色有造型变体时，镜头引用变体标签而不是角色基础标签。地点、关键道具及需要一致性的其他实体也用其已声明标签。

## 3. 提示词分层

### `keyframe_prompt`

描述开场画面：主体和造型、姿态、构图、场景、世界空间中的光源、景深、色彩与关键物品。它负责“这一帧是什么”，不写完整动作链。

推荐顺序：实体标签 → 姿态和画面位置 → 构图与机位 → 场景标签 → 光向与色温 → 景深和色彩 → 必要的连续性约束。

### `motion_prompt`

描述片段变化：一个主要动作目标、运动方向、速度、按序动作节拍、相机运动和结束状态。避免重复大段静态环境修饰，但保留身份标签、主光方位、轴线和关键道具状态等必要不变量。

推荐顺序：主体标签 → 起始状态 → 动作节拍 → 结束状态 → 世界/屏幕运动方向 → 运镜中英标签 → 不可变化项。

### `end_keyframe_prompt`

仅当生成路径为 `i2v_start_end` 且能力配置 `supports_end_frame: true` 时生成。它描述结束帧可见状态，不承诺任何具体模型支持该能力。

其他路径该字段必须为 `null`。

### `delivery_prompt`

面向当前通用生成路径的完整交付提示。它整合本路径必要的提示层，但不加入供应商参数。`negative_constraints` 只列本镜最重要的失败边界，不堆砌通用负面词。

## 4. 按生成路径编译

| 路径 | 编译方式 |
|---|---|
| `t2v` | `delivery_prompt` 同时包含完整视觉锚点、动作变化、相机和连续性约束。 |
| `i2v_start` | 首帧由 `keyframe_prompt` 负责；`motion_prompt` 聚焦变化，但保留身份、光向、轴线和道具不变量。 |
| `i2v_start_end` | 在 `i2v_start` 基础上增加 `end_keyframe_prompt`，并核对结构化起止状态。能力不支持结束帧时必须报错。 |
| `video_extend` | 把已有视频末态视为新镜头起态，描述下一段动作与相机延续；能力不支持续写时必须报错。 |
| `mixed` | 每镜通过 `generation_mode` 指定上述路径，并逐镜检查能力。 |

生成路径描述的是能力需求，不代表任何厂商或模型必然支持。

使用 `scene_coverage_grid` 九宫格机位图作为参考时，在参考图职责中明确“只读取空间结构、相机方向和正反打关系；最终输出一个单一完整镜头，不复制九宫格、边框、拼贴或多视图版式”。这句话属于参考图职责，不混入视觉叙事正文。

## 5. 语言和术语

默认输出中文。人类可读表格中的机位与运镜使用中英对照，例如“缓慢推近 (Slow Push In)”“低角度仰拍 (Low Angle)”“向左平摇 (Pan Left)”。这样做是为了术语稳定和跨工具沟通，不声称英文普遍优于中文。

提示词使用明确、可见、可执行的描述：主体、动作、相机、场景、光线。避免“震撼、电影感拉满、极致高级”等无法验证的形容。

## 6. 声音轨

对白、旁白、环境声、拟音和音乐意图存于 `audio`，不复制进视觉提示词。若需要口型，只在 `motion_prompt` 写可见的嘴部动作，并在声音轨保留原句和说话人引用。

## 7. 完整文件与聊天分页

完整 `storyboard-manifest/v1` JSON 是唯一规范交付物，优先保存为一个 UTF-8 JSON 文件。聊天只展示骨架、提示词表或分页摘要，默认每页最多 10 镜，并根据实际序列化体积进一步缩小。

无法写文件而必须在聊天交付长 JSON 时：

1. 先输出一个独立合法的 `storyboard-manifest-index/v1` 对象，记录 `project_id`、`source_digest`、`skeleton_revision`、`total_shots`、`page_size` 和分卷清单；
2. 再输出若干独立合法的 `storyboard-manifest-part/v1` 对象，每卷最多 10 镜，并包含 `part_index`、`part_count` 和镜头范围；
3. 每个代码块必须能独立解析，禁止截断 JSON 或把一个对象从中间拆开。

分卷只是聊天运输格式，不替代 canonical Manifest。

## 8. 推荐文件名与验证

- Phase 1：`<project_id>.storyboard-skeleton.r<revision>.json`
- Phase 2：`<project_id>.storyboard-manifest.r<revision>.json`

交付前运行：

```bash
python3 scripts/validate_storyboard_manifest.py <manifest.json>
```

有 `error` 时不得交付。`warning` 必须修正或在交付摘要中说明；生产门禁可增加 `--strict` 将警告视为失败。
