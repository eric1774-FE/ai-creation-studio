---
name: story-asset-prompt-extractor
description: 从小说、故事、剧本、梗概或叙事文本中提取电影与漫剧制作所需的角色、服装妆发、场景置景、道具、载具与生物、环境、灯光、特效和声音资产，默认生成中英双语、模型无关的自然语言执行提示词，并输出 story-asset-manifest/v2 UTF-8 JSON。支持真人写实、二维漫剧、三维动画和混合风格，按角色与场景聚合状态和关联资产，记录事实来源、参考图职责、提示词依赖、输出规格和阶段连贯性；不生成 HTML、分镜或媒体。
---

# 电影漫剧资产提示词提取 V2

把完整故事转换为可复用、可追踪、可直接执行的电影漫剧资产提示词。忠于原文，有限补足生成所需细节，视觉与声音分离，所有交付使用 `story-asset-manifest/v2`。

## 必读规范

在分析或生成提示词前，完整阅读 [references/prompt-standards.md](references/prompt-standards.md)。严格使用其中的媒介门、事实来源、角色与场景分级、资产模板、依赖规则和质量检查。

## 边界

只执行：

- 读取完整故事，提取、合并、编号、分级和版本化资产。
- 为图片、图片编辑和声音模型生成中文与英文两套语义对齐的通用自然语言提示词。
- 在信息不足时有限补全，并在 `facts` 中记录来源、状态和依据。
- 输出 V2 Manifest；需要 HTML 时交给 `story-prompt-report-renderer`。

不要执行：

- 不改写、续写或重构故事。
- 不生成分镜、镜头表、运镜、剪辑方案或电影剧照提示词。
- 不调用生图、视频、音乐或音效模型。
- 不把声音要求混入视觉提示词。
- 只输出 `story-asset-manifest/v2`，不在本 Skill 内生成 HTML。

## 输入与参考图

1. 读取用户粘贴的完整故事或指定文件，不得跳段或只依据摘要。
2. 收集时代、地域、媒介、视觉风格、写实度、画幅、声音和禁止项。
3. 用户提供图片时，为每张建立唯一 `reference_inputs.id`，`role` 只使用 `identity/style/costume/scene`；写清 `source_ref`、说明、允许影响和禁止影响。
4. 身份参考只允许影响人物身份和用户指定的身体特征，不得污染风格、服装或背景；风格参考不得复制人物身份或服装；服装参考不得换脸、换身材或污染背景；场景参考不得成为人物身份来源。
5. 建立别名表，将同一实体的别称合并；每项固定使用 `alias`、`canonical` 和可选 `note`，一个别称写一项，不使用 `variants` 数组；不要合并同类但不同实体。
6. 按故事顺序记录换装、妆发、受伤、变身、老化、损坏、天气和置景变化，使用同一资产的 `v2`、`v3`，不创建重复实体。
7. 原文冲突写入 `facts.status: conflict` 和 `pending_questions`，继续处理不受影响内容。

## 两段式媒介与风格门

若用户已经明确媒介和风格，直接整理并锁定 `G01`。

若媒介未指定，先只询问一次：`真人写实 / 二维漫剧 / 三维动画 / 混合风格`。用户选定前不提供三套美术方向。

媒介确定但风格未确定时：

1. 在所选媒介内，依据时代、地域、类型和情绪提出三套真正不同的美术方向。
2. 每套只写：方向名、时代地域解释、生产设计、色彩、材质或绘制方式、灯光、影像质感和禁止漂移。
3. 用户可回复序号、要求再生成三套或输入自定义风格。
4. 用户选定前停止详细资产提示词；选定后只启用对应 `render_mode` 模块，不混入其他媒介规则。

`G01` 必须保存 `render_mode` 事实，值只使用 `live_action/2d_comic/3d_animation/hybrid`。

## 视觉执行硬规则

- 每条生图提示词先说明资产类型、图片数量、主体或视图数量、排列、取景、背景和基础布光；编辑提示词先说明每个输入的职责、允许改变的范围和必须保留的内容。
- 固定按“任务 → 主体与状态 → 视图与构图 → 可见形态与材料 → 环境与光线 → 一致性约束 → 风格 → 负面约束”组织；正文末尾明确写 `风格：` 和 `负面约束：`，英文对应 `Style:` 和 `Negative constraints:`。
- 执行提示词只保留可见、可定位、可比较的内容。来源和置信状态只写入 `facts`，不得把 `inference`、`estimated` 或“合理推断”复制进执行提示词。
- 禁止用“体现、传达、营造、象征、暗示、电影感、氛围感、高级、震撼、唯美、史诗”等词代替具体形态、材料、色彩、比例和光线。
- 每条提示词自包含，不使用“同上”“参考前文”，但其结构化依赖必须记录在 `input_refs`。
- 生成提示词前按“资产身份 + 版本状态 + 生产用途 + 输入职责 + 输出规格”查重：五项一致则合并为一条并复用引用；任一项不同则保留，但必须在 `id`、`label` 和正文中明确差异，不得只换 ID 后复制相同正文。
- `text` 写中文执行提示词，`text_en` 写专业英文执行提示词；英文不是逐字翻译，且不得增删中文版的数值、身份锚点、视图顺序、输入职责、输出要求和禁止项。
- 只保留高概率失败的禁止项，不堆砌无关否定词。

## 固定资产类型

只使用以下十类；连贯性保存在根节点 `continuity`，不创建 `K` 资产。

| 编号 | 类型 | 内容 |
|---|---|---|
| `G` | 全局视觉圣经 | 媒介、时代地域、生产设计、色彩、材质、灯光和影像质感 |
| `C` | 角色 | 不可变身份、骨相、五官比例、身体比例和角色母版 |
| `W` | 服装妆发 | `costume`、`hair`、`makeup` 三种子类型及状态版本 |
| `S` | 场景置景 | 空间结构、尺度、入口、固定陈设、材料和生活痕迹 |
| `P` | 道具 | 尺寸、材料、工艺、年代、状态、归属和用途 |
| `V` | 载具与生物 | 车辆、坐骑、动物、怪物和特殊群体 |
| `E` | 环境状态 | 时间、季节、天气、风、雾、烟、灰尘和空气状态 |
| `L` | 灯光色彩 | 光源、方向、光质、色温、反差和配色 |
| `F` | 特效 | 破坏、火焰、粒子、伤痕和异常现象 |
| `A` | 声音 | 角色声音、环境声、拟音、剧情音效、BGM 和静默 |

没有内容的类型不创建虚假资产，在 `asset_type_coverage` 中写 `status: none`、`count: 0` 和说明。编号使用 `C01`、`S01`；声音使用 `A-VO-01`、`A-AMB-01`、`A-FOL-01`、`A-SFX-01`、`A-BGM-01`、`A-SIL-01`。

只有 `W` 资产允许并必须使用 `subtype: costume/hair/makeup`。`A` 等其他九类不得写 `subtype`；声音功能只通过上述 `A-*` 编号区分。

## 事实来源与状态

每项事实独立保存于资产或版本的 `facts`。

- `source`: `user/source_text/style_bible/inference/creative`。
- `status`: `confirmed/estimated/pending/conflict`。
- 每项必须有 `key`、标量 `value`、`source`、`status`、`evidence`；有单位时写 `unit`。
- `source_text` 必须写 `source_locator`；其他来源按需写。
- 优先级：`user > source_text > style_bible > inference`；`creative` 仅在用户授权时使用。
- 稳定事实放资产级 `facts`，只属于某个状态的事实放对应版本 `facts`。

## 角色身份、体型与妆发

- `C.importance_level` 只使用 `A/B/C`：A 为主角、核心对手或反复出现角色；B 为有姓名或明确作用的次要角色；C 为群演、一次性角色或背景职业群体。
- A/B 级采用两步流程：先生成面部身份基准图，再以其产物作为完整人物四视图的唯一面部身份输入。两条提示词使用唯一 ID，并以 `prompt_output` 记录依赖。
- 不可变身份锚点只包括年龄、骨相、脸型、五官比例、肤色、稳定标记和发际线。发型、发色、胡须、妆容和彩绘属于 `W-hair` 或 `W-makeup`；面部图可呈现当前造型，但后续换发或换妆不得把造型当成不可变身份。
- 人类或类人 A/B 级缺少身高体重时，选择一个相互合理的整数厘米和公斤值；在 `facts` 中写 `source: inference/status: estimated`，在完整人物提示词中只写数值和至少两项可见比例。
- C 级人群使用身高体重数值区间。非人类、机械体和特殊变形体不强制公斤数，改用物种或结构尺寸、头身比以及与人物或道具的尺度关系；原文或用户明确给出重量时保留。
- 身高标尺只接受 `status: confirmed` 的身高；`estimated` 只能作为建模数值，不能成为准确标尺。
- 完整人物四视图按正面、四分之三侧面、标准侧面、背面排列，使用同一身份、身体比例、站姿、脚底基线、缩放、相机高度、服装、表情和光线。
- A 级基础服保持中性贴身结构；故事服装使用 `W` 的 `subtype: costume`，先生成隐形人台结构板，再通过 `input_refs` 同时引用角色四视图和服装结构图完成换装。

## 场景分级

`S.importance_level` 只使用 `A/B/C`：

- A：出现至少三个故事阶段、作为反复主场景，或承担必须保持方向连续性的核心事件。依次生成“空间布局”“四方向空间参考”“中性主视图”三条提示词；后两条引用前序产物。
- B：出现两个故事阶段。生成一条横向正向与反向空间参考提示词。
- C：只出现一次。生成一张中性三分之四置景参考图。

以上都是无人生产资产，不是分镜。固定门窗、动线、空间尺度和不可移动陈设属于场景锚点；昼夜、天气、损毁和改造使用版本或 `E/L/F` 资产。

## 提示词 V2 结构

每条提示词必须包含：

- 全局唯一 `id`，建议 `<asset-id>-<version>-<purpose>`，例如 `C01-v1-face`。
- `mode`: `generate` 或 `edit`；`edit` 至少有一个输入。
- `input_refs`: 每项使用 `source_kind: reference_input/prompt_output`、`ref_id` 和具体 `role`。不得自引用、悬空引用或形成循环。
- `output_spec`: `media_type: image/audio`、正整数 `count`；图片必须有 `layout` 和 `aspect_ratio`；声音按需写 `duration_seconds` 和 `loopable`。
- `text`: 必填的完整中文执行提示词；必须显式包含 `风格：` 和 `负面约束：`。
- `text_en`: 必填的完整英文执行提示词；必须显式包含 `Style:` 和 `Negative constraints:`，并与 `text` 逐项保持生产约束一致。

## 实体、状态与连贯性

- 每个角色或场景只建立一个实体。稳定共用资产放 `common_asset_refs`，只在某状态出现或变化的资产放该状态 `asset_refs`，两处不得重复。
- 角色实体关联其 `C` 本体、`W` 服装妆发、随身 `P` 道具、`A-VO` 角色声音和专属 `V` 载具或生物；场景实体关联其 `S` 本体、场景 `P` 道具、`E` 环境、`L` 灯光、`F` 特效、`A` 环境声音和场景 `V` 载具或生物。
- 同一资产关联多个实体时复用同一 `asset_id + version`；没有实体归属的资产放 `standalone_asset_refs`。
- 每个资产版本必须至少被实体、状态或独立资产区引用一次。
- `continuity` 按故事顺序保存阶段对象：`stage_id`、`label`、`source_locator` 和当时适用的 `asset_refs`。

## 提取工作流

1. 建立事实表、别名表和用户参考图职责表。
2. 建立角色与场景实体、稳定资产、状态和版本关系。
3. 分配十类资产编号、角色等级、场景等级和 `W` 子类型。
4. 完成两段式媒介与风格门，锁定 `G01.render_mode`。
5. 翻译修辞，把情绪和性格转换为可见或可听结果。
6. 先按资产身份、版本状态、生产用途、输入职责和输出规格查重，能合并的只保留一条并复用引用；不能合并的明确写出差异。再生成带唯一 ID、输入依赖、输出规格、风格和负面约束的中英双语提示词。
7. 建立阶段连贯性和十类资产覆盖。
8. 语义质检后写入 V2 Manifest；`quality_checks` 只记录语义自检，不冒充结构校验。
9. 调用渲染器 `--validate-only`；失败时修正 Manifest，禁止绕过。

## JSON Manifest V2

```json
{
  "schema_version": "story-asset-manifest/v2",
  "title": "故事名 · 电影漫剧资产提示词",
  "input_summary": "输入摘要",
  "constraints": ["用户约束"],
  "aliases": [{"alias": "她", "canonical": "主角A", "note": "同一角色"}],
  "pending_questions": [],
  "reference_inputs": [],
  "asset_type_coverage": [
    {"type": "G", "status": "present", "count": 1, "note": "已锁定视觉圣经"},
    {"type": "C", "status": "present", "count": 1, "note": "发现角色"},
    {"type": "W", "status": "none", "count": 0, "note": "未发现独立服装妆发资产"},
    {"type": "S", "status": "none", "count": 0, "note": "未发现相关资产"},
    {"type": "P", "status": "none", "count": 0, "note": "未发现相关资产"},
    {"type": "V", "status": "none", "count": 0, "note": "未发现相关资产"},
    {"type": "E", "status": "none", "count": 0, "note": "未发现相关资产"},
    {"type": "L", "status": "none", "count": 0, "note": "未发现相关资产"},
    {"type": "F", "status": "none", "count": 0, "note": "未发现相关资产"},
    {"type": "A", "status": "none", "count": 0, "note": "未发现相关资产"}
  ],
  "assets": [
    {
      "id": "G01",
      "type": "G",
      "name": "全局视觉圣经",
      "first_appearance": "项目全局",
      "definition": "锁定全项目媒介和美术规则",
      "anchors": ["只使用已选媒介模块"],
      "facts": [
        {"key": "render_mode", "value": "2d_comic", "source": "user", "status": "confirmed", "evidence": "用户选择二维漫剧"}
      ],
      "versions": [
        {
          "id": "v1",
          "label": "锁定风格",
          "story_stage": "项目全局",
          "changes": "无",
          "facts": [],
          "prompts": [
            {
              "id": "G01-v1-style",
              "label": "全局视觉圣经提示词",
              "mode": "generate",
              "input_refs": [],
              "output_spec": {"media_type": "image", "count": 1, "layout": "横向风格参考板", "aspect_ratio": "16:9"},
              "text": "完整中文提示词正文。风格：二维漫剧统一线稿与赛璐璐着色。负面约束：禁止真人皮肤质感、文字和水印。",
              "text_en": "Complete English production prompt. Style: unified 2D comic linework and cel shading. Negative constraints: no photoreal skin texture, text, or watermark."
            }
          ],
          "prohibitions": ["禁止混入未选媒介规则"]
        }
      ]
    },
    {
      "id": "C01",
      "type": "C",
      "name": "主角A",
      "importance_level": "A",
      "first_appearance": "阶段01",
      "definition": "角色不可变身份与身体母版",
      "anchors": ["固定骨相与五官比例", "发型和妆容由 W 资产控制"],
      "facts": [
        {"key": "height_cm", "value": 172, "unit": "cm", "source": "inference", "status": "estimated", "evidence": "根据年龄、职业和角色关系补全"}
      ],
      "versions": [
        {
          "id": "v1",
          "label": "正常",
          "story_stage": "阶段01",
          "changes": "无",
          "facts": [],
          "prompts": [
            {
              "id": "C01-v1-face",
              "label": "面部身份锁定提示词",
              "mode": "generate",
              "input_refs": [],
              "output_spec": {"media_type": "image", "count": 1, "layout": "单张四分之三头肩", "aspect_ratio": "4:5"},
              "text": "完整中文提示词正文。风格：二维漫剧统一线稿与赛璐璐着色。负面约束：禁止身份漂移、文字和水印。",
              "text_en": "Complete English production prompt. Style: unified 2D comic linework and cel shading. Negative constraints: no identity drift, text, or watermark."
            },
            {
              "id": "C01-v1-fullbody",
              "label": "完整人物四视图扩展提示词",
              "mode": "edit",
              "input_refs": [
                {"source_kind": "prompt_output", "ref_id": "C01-v1-face", "role": "唯一面部身份来源"}
              ],
              "output_spec": {"media_type": "image", "count": 1, "layout": "横向四视图", "aspect_ratio": "2:1"},
              "text": "完整中文提示词正文。风格：二维漫剧统一线稿与赛璐璐着色。负面约束：禁止换脸、比例漂移、文字和水印。",
              "text_en": "Complete English production prompt. Style: unified 2D comic linework and cel shading. Negative constraints: no face replacement, proportion drift, text, or watermark."
            }
          ],
          "prohibitions": ["禁止身份漂移"]
        }
      ]
    }
  ],
  "entities": [
    {
      "id": "character:C01",
      "type": "character",
      "name": "主角A",
      "description": "核心角色",
      "common_asset_refs": [{"asset_id": "C01", "version": "v1", "relation_label": "身份锚点"}],
      "states": [{"id": "default", "label": "默认状态", "story_stage": "阶段01", "asset_refs": []}]
    }
  ],
  "standalone_asset_refs": [{"asset_id": "G01", "version": "v1", "relation_label": "项目全局"}],
  "continuity": [
    {
      "stage_id": "stage-01",
      "label": "开场",
      "source_locator": "第一章",
      "asset_refs": [
        {"asset_id": "C01", "version": "v1", "relation_label": "角色状态"},
        {"asset_id": "G01", "version": "v1", "relation_label": "视觉圣经"}
      ]
    }
  ],
  "quality_checks": [
    {"label": "媒介规则未混用", "status": "pass", "note": "仅使用 2d_comic 模块"},
    {"label": "中英提示词语义对齐", "status": "pass", "note": "全部提示词均提供 text 与 text_en"}
  ]
}
```

## Manifest 交付

1. 输入来自文件时命名为 `<原文件名>-asset-prompts.json`；粘贴文本时使用故事标题，没有标题时使用 `story-asset-prompts.json`。
2. 不覆盖已有文件；重名依次使用 `-2`、`-3`。原目录不可写时回退当前任务目录并说明。
3. 保存后运行：

```bash
python3 <story-prompt-report-renderer-dir>/scripts/render_prompt_report.py --input <manifest.json> --validate-only
```

4. 只有“验证通过”、文件存在且非空时才交付链接。用户同时要求 HTML 时，再使用 `story-prompt-report-renderer` 渲染，不在本 Skill 内手写 HTML。
