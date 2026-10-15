## 【全局一致性资产卡（Global Consistency Anchors）】

- **风格锚点 (Style Anchor)**：handmade 3D stop-motion clay style, tactile plasticine surface with subtle fingerprints, soft studio lighting, tilt-shift macro depth of field, Octane render quality
- **Color Palette:** warm pastel tones, 3200K studio warm lighting, consistent clay material index
- **角色 A（Pip）**：[Built-in Golden Anchor] tiny chubby green dragon figurine, two-head-tall proportions, smooth soft dough-like plasticine body, large pure black button eyes, short little tail
- **角色 B（Toby）**：[Built-in Golden Anchor] chubby Shiba Inu figurine, yellow-and-white sculpted clay fur grooves, upright ears, curled tail, glossy black nose
- **场景**：[Built-in Golden Anchor] cozy miniature clay playroom, softly rounded pastel walls, simple matte clay floor, uncluttered handmade interior
- **核心道具**：[Dynamic Clay-Adapted Anchor] one clay ball with integral rounded grip recesses and soft clay compressed beneath the fingers
- **通用负向词**：2D, flat, realistic animal fur, text, watermark, subtitles, words, letters, deformed limbs

## 【逐镜制作矩阵（Shot Matrix）】

### Shot 1

- **入镜角色:** Pip、Toby
- **机位与构图**：中全景 / Static，Pip x=30%，y=65%，Toby x=70%，y=68%，prop x=50%，y=35%，sole baseline y=88%。
- **Reference Asset:** Shot 1 Start Keyframe (to be generated)
- **[T2I] 故事板关键帧生图词**：

```text
handmade 3D stop-motion clay style, tactile plasticine surface with subtle fingerprints, soft studio lighting, tilt-shift macro depth of field, Octane render quality. Nominal character identities: Pip is a tiny chubby green dragon figurine, two-head-tall proportions, smooth soft dough-like plasticine body, large pure black button eyes, short little tail; Toby is a chubby Shiba Inu figurine, yellow-and-white sculpted clay fur grooves, upright ears, curled tail, glossy black nose. Current snapshot: Pip x=30%, y=65%, Toby x=70%, y=68%, prop x=50%, y=35%, sole baseline y=88%. cozy miniature clay playroom, softly rounded pastel walls, simple matte clay floor, uncluttered handmade interior. Both soles rest firmly on the floor with contact shadows; both characters face inward with their fingers wrapped around integral rounded grip recesses on opposite sides of one clay ball, the soft clay compressed beneath their fingertips. Pip has a normal torso, Toby has bent knees and a curled tail, poised at rest. The upper quarter is clear. Color Palette: warm pastel tones, 3200K studio warm lighting, consistent clay material index --ar 9:16
```

- **[I2V] 视频动态驱动词**：

```text
[Anticipation] t=0-0.75s: Pip maintains the grounded grip and elastic tension while Toby braces with bent knees and a tiny ear twitch. -> [Squash & Stretch / Exaggeration] t=0.75-2.75s: At t=0.75s Pip stabilizes the overhead ball at y=35% and keeps the existing upward effort while Toby maintains the firm grip and flat soles with a small eye response. Start anchors: Pip x=30%, y=65%, Toby x=70%, y=68%, prop x=50%, sole baseline y=88%. -> [Hold & Follow-through] t=2.75-4s: Pip maintains the grounded supported grip while Toby keeps the grounded stance with tiny ear and tail motion; aftermotion decays.
```

- **Negative Prompt:** 2D, flat, realistic animal fur, text, watermark, subtitles, words, letters, deformed limbs
- **Motion Strength:** 6/10
- **Camera Mode:** Static
- **Start-Frame:** Shot 1 Start Keyframe
- **End-Frame:** Shot 1 End Frame (to be generated and extracted)



### Shot 2

- **入镜角色:** Pip、Toby
- **机位与构图**：中全景 / Static，Pip x=30%，y=65%，Toby x=70%，y=68%，prop x=50%，y=35%，sole baseline y=88%。
- **Reference Asset:** Shot 1 Start Keyframe (character/style reference, to be generated); Shot 1 End Frame (to be generated and extracted)
- **[T2I] 故事板关键帧生图词**：

```text
handmade 3D stop-motion clay style, tactile plasticine surface with subtle fingerprints, soft studio lighting, tilt-shift macro depth of field, Octane render quality. Nominal character identities: Pip is a tiny chubby green dragon figurine, two-head-tall proportions, smooth soft dough-like plasticine body, large pure black button eyes, short little tail; Toby is a chubby Shiba Inu figurine, yellow-and-white sculpted clay fur grooves, upright ears, curled tail, glossy black nose. Current snapshot: Pip x=30%, y=65%, Toby x=70%, y=68%, prop x=50%, y=35%, sole baseline y=88%. cozy miniature clay playroom, softly rounded pastel walls, simple matte clay floor, uncluttered handmade interior. Both soles rest firmly on the floor with contact shadows; both characters face inward with their fingers wrapped around integral rounded grip recesses on opposite sides of one clay ball, the soft clay compressed beneath their fingertips. Pip has a normal torso, Toby has bent knees and a curled tail, poised at rest. The upper quarter is clear. Color Palette: warm pastel tones, 3200K studio warm lighting, consistent clay material index --ar 9:16
```

- **[I2V] 视频动态驱动词**：

```text
[Anticipation] t=0-0.75s: Pip maintains the grounded grip and elastic tension while Toby braces with bent knees and a tiny ear twitch. -> [Squash & Stretch / Exaggeration] t=0.75-2.75s: At t=0.75s Toby begins one continuous downward pull through the shared grip; the supported ball reaches y=79% at t=1.25s and Pip enters a partial crouch while Toby maintains the firm grip and flat soles with a small eye response. Start anchors: Pip x=30%, y=65%, Toby x=70%, y=68%, prop x=50%, sole baseline y=88%. -> [Hold & Follow-through] t=2.75-4s: Pip maintains the grounded supported grip while Toby keeps the grounded stance with tiny ear and tail motion; aftermotion decays.
```

- **Negative Prompt:** 2D, flat, realistic animal fur, text, watermark, subtitles, words, letters, deformed limbs
- **Motion Strength:** 6/10
- **Camera Mode:** Static
- **Start-Frame:** Shot 2 Start Keyframe
- **End-Frame:** Shot 2 End Frame (to be generated and extracted)



### Shot 3

- **入镜角色:** Pip、Toby
- **机位与构图**：中全景 / Static，Pip x=30%，y=72%，Toby x=70%，y=72%，prop x=50%，y=79%，sole baseline y=88%。
- **Reference Asset:** Shot 1 Start Keyframe (character/style reference, to be generated); Shot 2 End Frame (to be generated and extracted)
- **[T2I] 故事板关键帧生图词**：

```text
handmade 3D stop-motion clay style, tactile plasticine surface with subtle fingerprints, soft studio lighting, tilt-shift macro depth of field, Octane render quality. Nominal character identities: Pip is a tiny chubby green dragon figurine, two-head-tall proportions, smooth soft dough-like plasticine body, large pure black button eyes, short little tail; Toby is a chubby Shiba Inu figurine, yellow-and-white sculpted clay fur grooves, upright ears, curled tail, glossy black nose. Current snapshot: Pip x=30%, y=72%, Toby x=70%, y=72%, prop x=50%, y=79%, sole baseline y=88%. cozy miniature clay playroom, softly rounded pastel walls, simple matte clay floor, uncluttered handmade interior. Both soles rest firmly on the floor with contact shadows; both characters face inward with their fingers wrapped around integral rounded grip recesses on opposite sides of one clay ball, the soft clay compressed beneath their fingertips. Pip has a partially compressed torso, Toby has bent knees and a curled tail, poised at rest. The upper quarter is clear. Color Palette: warm pastel tones, 3200K studio warm lighting, consistent clay material index --ar 9:16
```

- **[I2V] 视频动态驱动词**：

```text
[Anticipation] t=0-0.75s: Pip maintains the grounded grip and elastic tension while Toby braces with bent knees and a tiny ear twitch. -> [Squash & Stretch / Exaggeration] t=0.75-2.75s: At t=0.75s the same downward pressure fully compresses Pip into an accordion shape, with both feet planted and the ball supported at y=79% while Toby maintains the firm grip and flat soles with a small eye response. Start anchors: Pip x=30%, y=72%, Toby x=70%, y=72%, prop x=50%, sole baseline y=88%. -> [Hold & Follow-through] t=2.75-4s: Pip maintains the grounded supported grip while Toby keeps the grounded stance with tiny ear and tail motion; aftermotion decays.
```

- **Negative Prompt:** 2D, flat, realistic animal fur, text, watermark, subtitles, words, letters, deformed limbs
- **Motion Strength:** 6/10
- **Camera Mode:** Static
- **Start-Frame:** Shot 3 Start Keyframe
- **End-Frame:** Shot 3 End Frame (to be generated and extracted)



### Shot 4

- **入镜角色:** Pip、Toby
- **机位与构图**：中全景 / Static，Pip x=30%，y=77%，Toby x=70%，y=72%，prop x=50%，y=79%，sole baseline y=88%。
- **Reference Asset:** Shot 1 Start Keyframe (character/style reference, to be generated); Shot 3 End Frame (to be generated and extracted)
- **[T2I] 故事板关键帧生图词**：

```text
handmade 3D stop-motion clay style, tactile plasticine surface with subtle fingerprints, soft studio lighting, tilt-shift macro depth of field, Octane render quality. Nominal character identities: Pip is a tiny chubby green dragon figurine, two-head-tall proportions, smooth soft dough-like plasticine body, large pure black button eyes, short little tail; Toby is a chubby Shiba Inu figurine, yellow-and-white sculpted clay fur grooves, upright ears, curled tail, glossy black nose. Current snapshot: Pip x=30%, y=77%, Toby x=70%, y=72%, prop x=50%, y=79%, sole baseline y=88%. cozy miniature clay playroom, softly rounded pastel walls, simple matte clay floor, uncluttered handmade interior. Both soles rest firmly on the floor with contact shadows; both characters face inward with their fingers wrapped around integral rounded grip recesses on opposite sides of one clay ball, the soft clay compressed beneath their fingertips. Pip has a fully compressed torso, Toby has bent knees and a curled tail, poised at rest. The upper quarter is clear. Color Palette: warm pastel tones, 3200K studio warm lighting, consistent clay material index --ar 9:16
```

- **[I2V] 视频动态驱动词**：

```text
[Anticipation] t=0-0.5s: Pip maintains the grounded grip and elastic tension while Toby braces with bent knees and a tiny ear twitch. -> [Squash & Stretch / Exaggeration] t=0.5-2.75s: The existing upward tension restores Pip and the ball to the opening high position while Toby maintains the firm grip and flat soles with a small eye response. Start anchors: Pip x=30%, y=77%, Toby x=70%, y=72%, prop x=50%, sole baseline y=88%. -> [Hold & Follow-through] t=2.75-4s: Pip maintains the grounded opening high grip while Toby keeps the grounded stance with tiny ear and tail motion; aftermotion decays.
```

- **Negative Prompt:** 2D, flat, realistic animal fur, text, watermark, subtitles, words, letters, deformed limbs
- **Motion Strength:** 6/10
- **Camera Mode:** Static
- **Start-Frame:** Shot 4 Start Keyframe
- **End-Frame:** Shot 1 Start Keyframe
- **Keyframe Control:** First-Last Frame Mode
- **末镜循环说明**：末镜起始球位为 y=79%，Pip 为压缩姿态；复位过程允许移动，终态球位回到 y=35%。首尾坐标、姿态、双脚支点与球高位复原，撤去同一次下拉阻力后的回弹驱动复位。


```json
{
  "first_start": {
    "characters": {
      "Pip": {
        "position": [
          30,
          65
        ],
        "facing": "right",
        "pose": "upright-overhead-grip",
        "contacts": [
          "feet:floor",
          "hands:ball-left-grip"
        ],
        "velocity": [
          0,
          0
        ],
        "phase": "upper-turning-point",
        "secondary_motion": "settled"
      },
      "Toby": {
        "position": [
          70,
          68
        ],
        "facing": "left",
        "pose": "bent-knees-overhead-grip",
        "contacts": [
          "feet:floor",
          "hands:ball-right-grip"
        ],
        "velocity": [
          0,
          0
        ],
        "phase": "upper-turning-point",
        "secondary_motion": "settled"
      }
    },
    "prop": {
      "position": [
        50,
        35
      ],
      "orientation": "upright",
      "shape": "round",
      "integrity": "intact",
      "contacts": [
        "Pip:hands",
        "Toby:hands"
      ],
      "velocity": [
        0,
        0
      ],
      "phase": "upper-turning-point"
    },
    "view": {
      "framing": "中全景",
      "camera": "Static",
      "lighting": "warm-pastel-3200K",
      "graphics": "clear"
    }
  },
  "last_end": {
    "characters": {
      "Pip": {
        "position": [
          30,
          65
        ],
        "facing": "right",
        "pose": "upright-overhead-grip",
        "contacts": [
          "feet:floor",
          "hands:ball-left-grip"
        ],
        "velocity": [
          0,
          0
        ],
        "phase": "upper-turning-point",
        "secondary_motion": "settled"
      },
      "Toby": {
        "position": [
          70,
          68
        ],
        "facing": "left",
        "pose": "bent-knees-overhead-grip",
        "contacts": [
          "feet:floor",
          "hands:ball-right-grip"
        ],
        "velocity": [
          0,
          0
        ],
        "phase": "upper-turning-point",
        "secondary_motion": "settled"
      }
    },
    "prop": {
      "position": [
        50,
        35
      ],
      "orientation": "upright",
      "shape": "round",
      "integrity": "intact",
      "contacts": [
        "Pip:hands",
        "Toby:hands"
      ],
      "velocity": [
        0,
        0
      ],
      "phase": "upper-turning-point"
    },
    "view": {
      "framing": "中全景",
      "camera": "Static",
      "lighting": "warm-pastel-3200K",
      "graphics": "clear"
    }
  }
}
```

## 【后期音画装配清单（Post-Production Asset Sheet）】

| 镜头号 | 触发秒点 (t) | 英文原声台词 (TTS 配音) | 拟声音效 (SFX) | 动态英文花字内容 | 视觉动效指引 |
|---|---|---|---|---|---|
| Shot 1 | t=0s | 无 | 主要 SFX：Squeak t=0–2.75s | 无 | 原动作弹性声 |
| Shot 1 | t=0.75s | Pip: High! t=0.75–1.15s | 无 | High | 触发点: t=0.75s｜内容: High｜视觉动效: 弹出保持 1.5s，t=2.25s 动效收拢，t=2.75s 消失 |
| Shot 2 | t=0s | 无 | 主要 SFX：Squeak t=0–4s | 无 | 下拉声 |
| Shot 2 | t=1.25s | Toby: Low! t=1.25–1.65s | 无 | Low | 触发点: t=1.25s｜内容: Low｜视觉动效: 弹出保持 1.2s，t=2.45s 动效收拢，t=2.95s 消失 |
| Shot 3 | t=0s | 无 | 主要 SFX：Squish t=0–3s | 无 | 压扁声 |
| Shot 3 | t=1s | Pip: Oops! t=1–1.5s | 无 | 无 | Level-0，不配花字 |
| Shot 4 | t=0s | 无 | 主要 SFX：Boing t=0–3.25s | 无 | 回弹声 |
| Shot 4 | t=0.75s | Pip: High! t=0.75–1.15s | 无 | High | 触发点: t=0.75s｜内容: High｜视觉动效: 弹出保持 1.5s，t=2.25s 动效收拢，t=2.75s 消失 |
