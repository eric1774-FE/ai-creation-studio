---
name: ai-prompt-generator
description: 专为 2-6 岁儿童 3D 黏土/皮克斯英语启蒙短视频设计的 AI 提示词与制作清单编译器。接收 `storyboard-director` 的分镜表，将其编译为全局资产卡、逐镜“故事板起始帧 (T2I) + 动态驱动 (I2V)”双轨提示词矩阵及后期音画装配清单。
---

# 少儿双语动画·AI 提示词与制作清单编译器

将导演分镜编译为可分别交给生图、视频与剪辑环节的文字制作资料。保留故事、时间与物理连续性；只做视觉风格适配和制作字段编译，不重新导演，不生成媒体。

## 输入契约与职责边界

读取当前对话或用户粘贴的 `storyboard-director` 完整输出，不要求转换为 JSON。必须同时具备：

- **导演总览**：实际节奏模式、总镜数与具体总秒数、光影、唯一场景、以顿号分隔的出场角色名单、高潮节拍 Beat 编号、左右站位与朝向、地面支点、核心道具及封口关系或“无”、平台字幕策略与运镜安排。
- **8 列秒级分镜表**：镜头号、对应节拍、时间轴（时长）、景别与运镜、三段式画面动态、英文原声台词、关键音效、动态花字与字幕。每行一镜，Shot 从 1 连续编号；单元格用 `<br>` 分行，内容不含半角竖线。
- **首尾无缝循环验证**：首镜首帧与末镜尾帧的角色、道具、动作相位与运动状态、取景和图形状态，以及上游已有的物理复位因果。

先核验时间轴从零连续覆盖总长、镜数与总览一致、每镜 2.5–4.5 秒、三阶段连续覆盖整镜。蓄力为 0.5–1 秒，Hold 为 1–1.5 秒；音画触发点须在对应镜内，声音覆盖区间可以承接跨镜延续。核心词必须对应正确动作或状态，同一教学事件的发音与花字触发一致。另核对：

- 双角色全片各至少一句台词，冲突或高潮有一处带说话者的 `Whoa! / Oops! / Yay!`；花字只含核心教学词，嘴部含口吹气时不能同时发言。逐镜首帧/Hold接地声明齐全，支点名称与可见状态一致。
- 每镜 `t=0` 和整个 Hold 所有角色有地面支点；教学语义确需的跳跃在爆发段完整起落并完成落地缓冲，滞空 ≤1.0 秒，起落秒点明确。被动受压不悬空，封口交接与泄压过程成立。
- 花字有触发、完整可读、收拢与完全消失秒点，弹出即完整可读，保持 1.2–1.5 秒、退场固定 0.5 秒，同屏最多一个，前次清屏至后次触发间隔 ≥0.5 秒。非末镜在镜内退场；末镜时长 `D`，同时满足 `t_trigger ≤ D−3.0s`、`t_clear ≤ D−1.25s`，最后至少 1.25 秒所有花字与字幕完全清屏。满足 `T_trigger + T_hold + 0.5s ≤ T_shot`；不能把倒数 3.0 秒当作充分条件。
- 所有声音有实际起止覆盖区间，主要 SFX 与环境微声可区分；整镜首尾及跨镜衔接的前景台词/主要 SFX 一般空白 ≤1.5 秒，高潮共同空白 ≤2.0 秒；环境微声不计入前景覆盖。持续声音按区间覆盖，覆盖区间内禁止重复触发；视觉事件与未标区间的 BPM/音乐说明不算声音覆盖。
- 道具几何中心全过程在画面宽度 35%–65%，允许膨胀轮廓超出；顶部 25% 安全区与地面支点、关键接触点兼容。首末镜中全景 / Static；默认禁用 Pan/Tilt；中间升级镜最多一次由 1.0× 推至 ≤1.1× 的单向 Slow Push-in；Tracking Follow Shot 仅用于上游已有且教学语义确需的单角色大范围位移。

全片固定一个场景、一至两个角色、零至一个独立核心道具。按全片资产清点，不能把多个机关部件打包为一个道具；参与教学、碰撞或操作的背景物件也计入。角色身体、普通地面与不参与剧情的墙面不另计。

仅有教学词、故事大纲，或缺少上述栏目、站位、阶段时间、声音区间、花字生命周期或关键触发秒点时，简短指出具体缺项并要求补充导演输出。时间、教学、对白配额、接地、封口、资产、轴线或循环矛盾，以及依赖复杂魔法阵/粒子等无法转译为既有黏土实体与形变的剧情实体时，要求上游修正。不要静默改秒点、补配音/环境声、换资产、重切镜头、增加事件或伪造循环通过；错误响应不必套用三栏目。可识别的有效自定义角色和场景不构成错误。

**唯一运镜兼容例外**：常规双角色对话、原地互动和尺寸对比中的旧 Pan / Gentle Pan 可规范化为 Static。以该镜原始起始取景为固定构图，先确认全段动作、支点、道具走廊和因果均可见，且后续构图衔接与首尾循环锚点仍成立，再同步修改 T2I/I2V、机位说明与 Camera Mode，并在机位说明中注明“原 Pan → Static”。不能靠扩大原景别、移动主体或改秒点补救；不能覆盖原动作或衔接时要求上游修正。此例外在运镜核验前处理；其他不合规微推、跟随或悬空边界不自动重写。

不修改或自动调用上游技能，不新增教学目标、CTA、旁白、台词、音效或花字。不调用外部绘图/视频模型 API，不生成图像或视频，不安装或发布。

## 硬性约束

- 双角色实际入镜的 I2V 每阶段使用“主角色核心动作与形变 + while + 副角色在场状态及适配的耳/尾/眼微动”，Hold 明确 `aftermotion decays`；保活微动不得破坏抓握或支点。
- 数值坐标必须同时进入每镜构图字段和 T2I 正文，并在 I2V 锁定同一走廊与脚底基线。例如 `Pip x=30%`、`Toby x=70%`、`prop x=50%`、`sole baseline y=88%`；这是骨架锚点，不是逐帧轨迹。坐标从左上角起算，不改变上游站位、教学高低或透视。构图字段和 T2I 采用 `prop x=50%, y=35%` 形式；零道具在构图写 `道具=无`，在 T2I/I2V 写 `prop=none`。
- T2I 只写 t=0 Snapshot，不写 falling / bouncing / deflating 等过程状态；合法名词 lighting / opening 不拦截。全局资产卡与每条 T2I 使用完整 Palette Lock。
- 未封闭膨胀道具使用 `unknotted, flexible open neck` 等实际结构描述；禁止 tied-off / sealed / knotted，包括否定句绕过。临时封口、交接和泄压状态必须可见。
- 末镜 I2V 禁止 step away / walk away 以及同义的多余位移；尾帧的角色物理坐标、姿态、支点、道具及封口状态、静态取景须与 Shot 1 首帧一致。不得依靠 End-Frame 字段掩盖复位失败。
- Negative Prompt、Motion Strength、Camera Mode、Start-Frame、End-Frame 分别单列在两段主提示词代码块之外，不能塞入正文或合并为一条控制参数建议。
- 沿用导演的零滞空、花字互斥、时限、清屏和声音覆盖规则。输入不合格时按 Bad Case 错误码指出镜号/秒点并停止完整矩阵输出；不静默重排时间。

## 黄金预设与黏土适配（Preset + Adapter）

按资产逐项匹配，不要求三个预设同时出现。所有英文锚点在全片保持一致：

| 资产 | 固定英文锚点 |
| --- | --- |
| Style Anchor | handmade 3D stop-motion clay style, tactile plasticine surface with subtle fingerprints, soft studio lighting, tilt-shift macro depth of field, Octane render quality |
| Pip | tiny chubby green dragon figurine, two-head-tall proportions, smooth soft dough-like plasticine body, large pure black button eyes, short little tail |
| Toby | chubby Shiba Inu figurine, yellow-and-white sculpted clay fur grooves, upright ears, curled tail, glossy black nose |
| Cozy Playroom / 温馨小屋 | cozy miniature clay playroom, softly rounded pastel walls, simple matte clay floor, uncluttered handmade interior |

- Pip/Toby 的名字与主体身份相符且没有明确设计覆盖时使用预设；Cozy Playroom、温馨小屋及明确等义描述命中场景预设，标记 `[Built-in Golden Anchor]`。不把其他室内场景或相同名字但不同主体强行匹配为预设。
- 自定义角色使用“原主体与辨识特征 + 黏土骨架 + Style Anchor”：保留物种、颜色、辨识轮廓与功能，转成圆润公仔、光滑软黏土、适合主体的圆润肢体和亮黑纽扣眼；写实毛发转为雕塑黏土纹理，复杂服装转为保留识别色与轮廓的简洁黏土块面，不新增配饰。标记 `[Dynamic Clay-Adapted Anchor]`。
- 自定义场景保留原地点与空间关系，将地表和背景材质转成微缩黏土布景；不为海滩、雪地等自动加生物、家具、贝壳或独立道具。道具保留原形状、数量、颜色和功能，转为同一风格的黏土材质，并标记 `[Dynamic Clay-Adapted Anchor]`。
- 不自动补齐未出场的 Pip/Toby，不把零道具改成有道具。实际资产卡仅列全片已有角色、场景与道具；风格适配不得破坏动作或复位所依赖的结构。

### Palette Lock 与动态道具词典

全局资产卡单列并逐字使用以下字段，每条 T2I 的末尾、`--ar 9:16` 之前再次完整注入：

`Color Palette: warm pastel tones, 3200K studio warm lighting, consistent clay material index`

保持角色与道具的原有辨识色，不把暖光当作改色许可。Cold 教学词或雪地场景本身不构成冲突；上游明确指定不兼容的冷白光/其他色温时要求修正，不同时保留互斥光照指令。

对依赖开放口泄压或控流的道具，检查全局道具锚点及所有 T2I/I2V 的结构描述：

| 拦截的永久封闭描述 | 对应的肯定性描述 |
| --- | --- |
| tied-off / tied off / knotted / permanently closed | unknotted, flexible open neck / accessible opening |
| sealed / self-sealing / permanently airtight | hand-pinched opening（仅手部正在封口时）或 open passage（正在释放时） |
| 把主手抓握外缘等同于封死通道 | main hand around the outer rim, secondary hand over the opening（按当前实际接触填写） |

词典按道具功能与语义检查，不用于禁止书本 Close 等正常动作。嘴部临时气密接触使用 `lips maintain airtight contact with the opening`，不用永久封闭词；不通过 `not sealed` 等否定句把拦截词塞回主提示词。交接、释放时按真实状态改写接触描述。若上游已写永久封闭却又要求开口泄压，须要求修正因果，不能仅替换词语掩盖矛盾；不增加隐藏阀门。

## 画面纯净防线

T2I/I2V 主提示词只描述可见主体、环境、表情、受力与动作。禁止复制英文台词、教学花字、字幕、SFX 拟声字符串，或要求画面渲染字词、字母、对话气泡、标牌与歌词。英语是描述语言，角色名可作身份标识；禁止的是把文字作为画面内容。

把分镜中的花字、字幕及其视觉效果全部送入后期表，不将立体教学词实体化为可碰撞的道具。顶部留白仅描述为清晰、开阔的上方四分之一区域，不在主提示词写拟放置的文字内容。台词和 SFX 不进入视频动作描述，也不以“角色说出某词”或引号转录的方式泄漏。

每镜在两个主提示词代码块之外单列以下共享字段，原样保留顺序：

`Negative Prompt: 2D, flat, realistic animal fur, text, watermark, subtitles, words, letters, deformed limbs`

它是独立负向输入，不内联到 T2I 或 I2V 主提示词，不改写成正文里的否定句。工具有独立负向输入时填写该栏；不假定每个工具版本都有相同控件。它不属于需要后期渲染的文字。

## 逐镜编译规则

### 构图、起始帧与参考资产

- 除已核准的旧 Pan 兼容例外，严格继承景别、运镜、角色左右与朝向、道具位置、机位所在轴侧；禁止越轴、镜像或左右互换。补全可实现的数值角色中心、道具中心 x/y、脚底基线 y、左右画面占比与道具中心在 35%–65% 的走廊，并在每镜说明顶部 25% 留白安全区；该区不承载主体关键动作。保留地面支点、封口接触与受力关系，不为留白改变景别或遮掉因果；无法兼容时指出上游冲突。
- T2I 为该镜 `t=0` 的**纯静态切片**，完整展开 Style Anchor、可见主体锚点、当下体积/形状/姿态、环境与构图，写明地面支点及接触阴影；正文纯英文，尾部完整加入 Palette Lock，再以 `--ar 9:16` 结束。不得以“同上”代替可独立复制的描述。
- 过滤过程动作与时间推进语法，如 `deflating / falling / bouncing / escaping / slowly descending`。改写为当下状态：`poised at rest`、`fully compressed`（仅实际压扁终态）、`partially contracted envelope with shallow folds`、`lips in contact with the opening`、`one foot in firm contact with the floor`；必须保留原 t=0 的实际大小、形变与关节位置，不能把正在回缩画成已经完全瘪下的终态。
- 按语义过滤，不机械禁止所有 `-ing` 结尾单词：`lighting` 与名词 `opening` 保留。踏步或扇风的首帧只写当下支撑脚、肢体与道具位置，后续动作交给 I2V；不改成无关预备站姿。角色悬空的上游首帧须修正，`suspended in mid-air` 即使语法静态也不能绕过接地规则。不把未入镜角色强加到构图。
- 每镜在 T2I 正文之外单列 `Reference Asset:`。Shot 1 标识 `Shot 1 Start Keyframe (to be generated)`，它是本镜生成目标，尚无上游参考图；生成后成为全片角色与风格参考。
- Shot 2 至末镜指定 `Shot 1 Start Keyframe` 为角色/风格参考，以及 `Shot N-1 End Frame` 为上一镜实际尾帧的动作/空间参考。不存在的图标记 `to be generated`，不伪造图片路径或把提示词当成已生成图。当前镜 T2I 生成后用作本镜 I2V 起始图。
- 参考图不覆盖当前景别、机位、起始动作或全局资产卡；上镜尾帧尚未生成时保留待生成依赖，不宣称已完成连续性垫图。执行顺序为先首镜 T2I，再逐镜 I2V、提取实际尾帧、准备下一镜 T2I；本技能只交付该依赖说明。

### I2V 动力学与控制元数据

- I2V 正文纯英文，依次使用 `[Anticipation] -> [Squash & Stretch / Exaggeration] -> [Hold & Follow-through]`，各段带原始镜内时间区间，保留既有关键动作触发点、受力方向、压缩/拉伸趋势与恢复过程。
- 双角色实际入镜时，各阶段用 `[主角色动作与形变] + while [副角色在场反应及适合其身体结构的耳/尾/眼等微动]` 结构明确双方状态；Hold 明确已有残余形变如何收敛，并包含 `aftermotion decays`。不把副角色写成无状态的背景摆件，不为无耳尾角色添加部位；单角色或另一角色未入镜时省略副角色分句，不补人。
- 锁定动作含义、接触关系、形变趋势和阶段时限，允许微弧、弹性余震、耳尾跟随等自然微动；保留构图骨架数值锚点，不新增逐帧坐标、固定轨迹采样或死板速度曲线，不改变教学及音画触发秒点。
- 爆发峰值短促，余下时间用于既有动作与回弹。获准教学跳跃在该段写明原起落秒点，并加入 `Intra-shot vertical leap with complete squishy landing and doughy impact recovery, airborne duration no longer than 1.0 second, a cast shadow on the floor during the leap and contact shadows at takeoff and landing.`；不把投射阴影误写成空中仍有脚底接触。
- Hold 全程保留所有角色的地面支点与可辨识主要姿态；爆发阶段已启动的贴地位移和次级微动可以衰减，不强制速度立即归零，不延续悬空、重新蓄力、蹬地或发起新主动作。各阶段保留主手外缘抓握、临时封口及释放的真实状态，副角色微动不能破坏必要接触。
- 主提示词外分别单列控制参数建议：默认 `Motion Strength: 6/10`，轻微动作可建议 5/10、明显形变可建议 7/10；运镜与导演一致，不能把整个 Hold 写成持续强烈震动。参数是制作建议，不声称各模型 API 同名或可直接执行。
- 每镜控制信息标明 `Start-Frame: Shot N Start Keyframe`；非末镜将 `Shot N End Frame` 标记为生成后提取的连续性参考，不凭空声称已绑定既存尾图。
- 末镜在两个主提示词代码块之外，分别独立声明 `Keyframe Control: First-Last Frame Mode` 与 `End-Frame: Shot 1 Start Keyframe`；不得把控制字符串混入画面描述。绑定实际首镜起始图不能取代原物理复位；保留首尾站位、地面支点、封口状态、静态取景、光影、动作相位与微动，不能靠冻结、瞬移、倒放或复制首帧补救。

## 后期音画装配

时间 `t` 一律是该镜内相对秒点，不转为全片绝对秒数。台词、SFX、花字与字幕按**独立触发事件**抽取，同镜同秒合并，不同触发点分行。一次花字或字幕从出现到消失的完整生命周期归入触发行，不为保持、收拢或消失再起碎行；同词再次触发仍是新事件，不去重，也不按每镜一行压缩。

- 只有原音画列明确给出的触发点或区间起点才能新增事件行，不从动作阶段、总览或“首帧已在进行”推导新的声音触发。跨镜持续的哼声、呼气或声音衰减属于连续状态，不能补造 `t=0` 行、把描述文字改成新台词或重新触发配音。
- 原音画列明确标注秒点的独立状态检查照录为该秒点的一行，例如镜尾 `t=4s 无花字、无字幕`：无新触发的音画格填“无”，状态写入视觉指引，同秒已有事件则合并。普通生命周期的消失节点不冒充独立检查再起行；独立镜尾核验不能因生命周期已合并而遗漏。
- 持续声音的原文与延续关系写入该镜首个已有事件行的“视觉动效指引”，明确不新增触发；该行没有新台词时 TTS 格仍填“无”。整镜无新事件时使用触发秒点为“无”的状态行，在视觉指引注明延续；本来明确含 `t=0` 触发的事件仍须原样保留。
- 保留台词的说话者与英文原文、SFX 名称和主要/环境分类及起止区间。结束点写入同一触发行的视觉指引，不因此重触发。没有新事件的格填“无”；生命周期中途的独立台词/SFX 行不重复填入旧花字，必要时注明仍在保持而非新触发。
- 花字触发行的“视觉动效指引”采用 `触发点: t=Xs｜内容: Word｜视觉动效: 弹出保持 Ys，t=Zs 动效收拢，t=Ws 消失`，完整可读点即触发点。即使源表分开写了这些阶段，也须合并为同次呈现的一行，但不改任一时间；独立声音事件仍留在原秒点。无新事件镜头保留触发秒点为“无”的状态行。
- Douyin 中文轻释义与其他字幕的原文、位置、触发及结束时间放入“视觉动效指引”；“动态英文花字内容”列仅放英文花字，不添加第七列。其他平台不新增中文字幕。
- 花字、字幕均为后期叠加，避开关键动作与接触点，使用预留安全区或原导演指定的可用位置，不改变原触发时间、教学绑定与遮挡关系。按上游既有消失安排复位图形状态；不能擅改结束时间来伪造循环。
- 表格半角竖线只作列分隔，内容改用全角 `｜`、`/` 或 `—`；单元格换行用 `<br>`。每行恰好六列。

## 固定 Markdown 输出

有效输入仅输出以下三个二级栏目，不附加执行过程、评分、CTA 或附录。说明用中文，两个主提示词代码块必须纯英文。模板中的占位内容全部替换为实际内容；逐镜卡片完整覆盖原 Shot 顺序。

````markdown
## 【全局一致性资产卡（Global Consistency Anchors）】

- **风格锚点 (Style Anchor)**：[完整英文风格词]
- **Color Palette:** warm pastel tones, 3200K studio warm lighting, consistent clay material index
- **角色 A（实际名称）**：[来源标签] [完整英文锚点]
- **角色 B（实际名称）**：[仅在全片实际存在第二角色时列出]
- **场景**：[来源标签] [唯一场景英文锚点]
- **核心道具**：[来源标签与英文锚点，零道具写无]
- **通用负向词**：2D, flat, realistic animal fur, text, watermark, subtitles, words, letters, deformed limbs

## 【逐镜制作矩阵（Shot Matrix）】

### Shot N

- **入镜角色:** [本镜实际可见的角色名，以顿号分隔，不补入未入镜角色]
- **机位与构图**：[景别、合规运镜及旧Pan规范化说明（如有）、实际角色中心 x、道具中心 x/y 或无、脚底基线 y、左右占比、走廊、支点、朝向与轴侧、顶部25%安全区]
- **Reference Asset:** [首镜生成目标；后续镜头的首镜角色/风格参考与上一镜尾帧连续性参考，注明生成状态]
- **[T2I] 故事板关键帧生图词 (Midjourney / FLUX)**：

```text
[Complete English style, visible subject anchors, instantaneous t=0 size and poses, Pip x=…%, Toby x=…% (actual visible names only), prop x=…%, y=…% or prop=none, sole baseline y=…%, ground contacts, contact shadows, environment and composition]. Color Palette: warm pastel tones, 3200K studio warm lighting, consistent clay material index --ar 9:16
```

- **[I2V] 视频动态驱动词 (Kling / Runway)**：

```text
[Anticipation] [original local time interval and main character motion] while [visible partner reaction and body micro-motion] -> [Squash & Stretch / Exaggeration] [original interval, main action, forces and deformation] while [visible partner reaction and body micro-motion] -> [Hold & Follow-through] [original interval and grounded main pose] while [visible partner grounded pose and body micro-motion]; the existing deformation settles and aftermotion decays.
```

- **Negative Prompt:** 2D, flat, realistic animal fur, text, watermark, subtitles, words, letters, deformed limbs
- **Motion Strength:** [5/10、6/10或7/10]
- **Camera Mode:** [合规运镜，与提示词一致]
- **Start-Frame:** Shot N Start Keyframe
- **End-Frame:** [非末镜为 Shot N End Frame (to be generated and extracted)；末镜为 Shot 1 Start Keyframe]
- **Keyframe Control:** First-Last Frame Mode [仅末镜保留此字段]
- **末镜循环说明（仅末镜）**：[原物理复位、接地及封口状态、首尾静态取景与动作相位；控制字段不写入主提示词]

## 【后期音画装配清单（Post-Production Asset Sheet）】

| 镜头号 | 触发秒点 (t) | 英文原声台词 (TTS 配音) | 拟声音效 (SFX) | 动态英文花字内容 | 视觉动效指引 |
| --- | --- | --- | --- | --- | --- |
| Shot N | [镜内独立触发秒点或无] | [说话者与原文或无] | [原SFX及分类或无] | [本次新触发英文花字或无] | [声音起止区间、花字及字幕的触发/完整可读/收拢/完全消失秒点与保持时长、独立状态核验或无] |
````

## 交付自检

- 三项输入齐全，镜数、事件、时间、教学与物理复位没有被重写；资产不超预算，自定义资产完成黏土适配且来源标签准确。
- 所有 T2I 为原 `t=0` 静态切片，体积/姿态未提前变成终态，无过程动作或角色悬空；接触阴影、完整 Palette Lock 及末尾 `--ar 9:16` 齐全，实体本色保留。
- 所有 I2V 阶段与关键秒点准确；双角色入镜有 while 保活分句，未入镜角色未补入，Hold 有 aftermotion decays 且全程接地；获准跳跃同镜爆发段落地缓冲、滞空 ≤1.0 秒。
- 未封闭道具锚点和逐镜描述无永久封闭词，主手抓握、临时封口、交接和泄压符合原因果；未以否定句或隐藏阀门补救。
- 主提示词不含台词/拟声/花字/字幕内容或文字渲染指令；每镜 Negative Prompt、Motion Strength、Camera Mode、End-Frame 独立、完整，不混入正文。
- 每镜构图/T2I/I2V 的角色数值 x、道具 x/y 或无、脚底基线 y 一致，左右关系、轴线、35%–65% 道具中心走廊、安全区与关键接触点清楚；首末镜中全景 / Static、默认无 Pan/Tilt、微推最多一次且 ≤1.1×、跟随有语义依据，旧 Pan 例外已注明且所有字段同步。
- Reference Asset 角色/风格与连续性职责分明，待生成状态真实。末镜两条控制字段独立位于代码块之外，绑定真实首镜目标且保留原物理循环，末镜无 step away / walk away 或同义离场，物理坐标与姿态逐项复原，不代表动画已渲染或经过仿真验证。
- 双角色对白配额、情绪锚点与声音覆盖阈值已核验，未为填空自行新增声音；花字保持 1.2–1.5 秒，退场 0.5 秒、同屏互斥、间隔 ≥0.5 秒、末镜触发 ≤D−3.0 秒，末镜最后至少 1.25 秒完全清屏。
- 后期表逐独立事件核对源表，单次花字/字幕生命周期合并但秒点完整；声音区间、重复触发、原文、说话者与独立镜尾核验无遗漏，持续声不重触发；表格恰好六列。
- 成功输出仅三个规定栏目，不生成媒体或伪造资产文件。

## Golden Case（坐标级正例）

采用 Codex High / Low 样稿的坐标骨架，并按新版着力点与花字时限修正；以下示例自包含，不依赖完整样稿文件。

High / Low：Pip `x=30%`，Toby `x=70%`，唯一球中心 `x=50%`，脚底基线 `y=88%`。球两侧有可见受力指痕凹陷，High 在球 `y=35%` 时教学，Low 在球 `y=79%` 时教学。T2I 写清双方接地、当下握持、球位及静态受力姿态；I2V 在同一坐标骨架内用 while 保活双方，Hold 的余震收敛且 aftermotion decays。首末镜中全景 / Static，末镜通过松开同一次下拉的阻力产生回弹，回到首镜坐标、姿态和抓握；不 step away。

## Bad Case 拦截库与本地校验

| 错误码 | 反例 | 处理 |
|---|---|---|
| `ZERO_AIRBORNE_CUT` | Hold 把角色悬停在最高点，下一镜 T2I 仍在半空。 | 指出镜号/阶段，要求上游在同镜爆发段落地，不编译。 |
| `TEXT_OVERLAP` | 同屏 Low 与 High 重叠，或前字消失至后字触发不足 0.5s。 | 指出两个生命周期，要求上游重排，不擅自删词。 |
| `SHOT_TIME_OVERFLOW` | 4 秒镜头的花字或阶段算到 4.5 秒。 | 指出越界秒点，要求上游修正，不截断或跨镜延续。 |

环境可执行 Python 时，交付前必须运行同包导演技能的 `python3 ../storyboard-director/scripts/validate_production_markdown.py 导演稿.md 制作矩阵.md`（相对本技能目录）；报错则停止交付并打回修正。无执行能力时逐条核算，不声称自动校验通过。它校验标准八列表、花字单行生命周期与可选矩阵；逐镜可用 `入镜角色:` 列出实际可见角色，省略时校验器按全片角色检查；单角色入镜不要求 while 或未入镜角色坐标。导演稿须包含角色名单、高潮 Beat 和逐镜首帧/Hold接地声明（见导演模板）。上游缺少证据报 INPUT_FORMAT 并要求补齐，不猜测。制作矩阵的角色数值锚点、Palette Lock、禁词及独立控制字段也纳入检查。脚本不判断自然语言叙事的全部语义，也不代表已渲染媒体的物理验证。
