## 【导演总览（Director's Notes）】

- 规格确认：标准版 standard，总镜头数：4 镜，总时长：16 秒
- 出场角色：Pip、Toby
- 高潮节拍：Beat 2
- 视听基调：115–120 BPM，暖粉彩、3200K 柔和摄影棚光照，保留主体本色。
- 空间与站位：Pip x=30%，Toby x=70%，球中心 x=50%，脚底基线 y=88%。球两侧有一体可抓握凹槽，双方手指包覆槽缘，软黏土接触处受力下陷，拉力经槽缘传递。High 对应球 y=35%，Low 对应球 y=79%。顶部 25% 留白，首末镜中全景 / Static。
- 平台与字幕：通用英文花字，无额外字幕。

## 【秒级视听分镜表】

| 镜头号 | 对应节拍 | 时间轴 (时长) | 景别与运镜 | 画面动态与黏土动力学（三段式） | 英文原声台词 | 关键音效 (SFX) | 动态花字与字幕 |
|---|---|---|---|---|---|---|---|
| Shot 1 | Beat 1 | 00:00–00:04 (4s) | 中全景 / Static | [蓄力 Anticipation] t=0–0.75s：Pip 左、Toby 右，双脚接地，握住球两侧指痕凹陷，高位拉扯。<br>[爆发 Squash & Stretch] t=0.75–2.75s：球保持高处，Toby 前肢短促拉长回稳。<br>[定格 Hold & Follow Through] t=2.75–4s：保持高位握持，耳尾余震收敛。<br>跳跃声明：无<br>首帧接地：Pip=双脚，Toby=双脚；Hold接地：Pip=双脚，Toby=双脚 | t=0.75–1.15s Pip: High! | 主要 SFX：Squeak，t=0–2.75s | 触发点: t=0.75s｜内容: High｜视觉动效: 弹出保持 1.5s，t=2.25s 动效收拢，t=2.75s 消失 |
| Shot 2 | Beat 2 | 00:04–00:08 (4s) | 中全景 / Static | [蓄力 Anticipation] t=0–0.75s：Toby 屈膝蓄势，Pip 维持同一上举张力。<br>[爆发 Squash & Stretch] t=0.75–2.75s：Toby 发动一次下拉，球于 t=1.25s 到低位 y=79%。<br>[定格 Hold & Follow Through] t=2.75–4s：维持低位抓握，双方贴地，耳尾余震收敛。<br>跳跃声明：无<br>首帧接地：Pip=双脚，Toby=双脚；Hold接地：Pip=双脚，Toby=双脚 | t=1.25–1.65s Toby: Low! | 主要 SFX：Squeak，t=0–4s | 触发点: t=1.25s｜内容: Low｜视觉动效: 弹出保持 1.2s，t=2.45s 动效收拢，t=2.95s 消失 |
| Shot 3 | Beat 2 | 00:08–00:12 (4s) | 中全景 / Static | [蓄力 Anticipation] t=0–0.75s：延续同一次下拉压力，Pip 微反向蓄势。<br>[爆发 Squash & Stretch] t=0.75–2.75s：Pip 压成手风琴，Toby 耳尖反应，球保持低位。<br>[定格 Hold & Follow Through] t=2.75–4s：保持贴地压缩，余震收敛。<br>跳跃声明：无<br>首帧接地：Pip=双脚，Toby=双脚；Hold接地：Pip=双脚，Toby=双脚 | t=1–1.5s Pip: Oops!（唯一 Level-0 情绪锚点，不配花字） | 主要 SFX：Squish，t=0–3s | 无花字、无字幕 |
| Shot 4 | Beat 3 | 00:12–00:16 (4s) | 中全景 / Static | [蓄力 Anticipation] t=0–0.5s：Toby 减弱同一次下拉阻力。<br>[爆发 Squash & Stretch] t=0.5–2.75s：Pip 受压身体沿原上举张力回弹，t=0.75s 球恢复高位。<br>[定格 Hold & Follow Through] t=2.75–4s：双方恢复开场坐标、指痕抓握和姿态，余震收敛。<br>跳跃声明：无<br>首帧接地：Pip=双脚，Toby=双脚；Hold接地：Pip=双脚，Toby=双脚 | t=0.75–1.15s Pip: High! | 主要 SFX：Boing，t=0–3.25s | 触发点: t=0.75s｜内容: High｜视觉动效: 弹出保持 1.5s，t=2.25s 动效收拢，t=2.75s 消失 |

## 【首尾无缝循环衔接验证（Loop Check）】

- 末镜尾帧与首镜首帧：Pip x=30%，Toby x=70%，球中心 x=50%、y=35%，脚底基线 y=88%，相向抓握球两侧指痕凹陷；两名角色双脚接地，耳尾余震归零。
- 复位来自同一次下拉阻力撤去后的黏土回弹，无额外动作或道具。首末中全景 / Static，末镜 t=2.75–4s 完全无花字、无字幕。

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
