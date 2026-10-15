# 首尾状态 JSON 契约（0.2.0-draft）

导演在现有 `Loop Check` 中输出且仅输出一个 `json` 围栏代码块。编译器在末镜控制区完整复制该块，放在两个 `text` 提示词代码块之外。其他说明可用自然语言，不另增 JSON 块。

`first_start` 表示 Shot 1 的起始帧，`last_end` 表示末镜的结束帧；不记录末镜起点。末镜可以从另一位置出发，通过已有因果回位。首尾允许相同的非零运动，但速度、方向、动作相位及次级微动都须匹配，不能只匹配坐标。

## 字段与单位

根对象恰有 `first_start`、`last_end`。两端各恰有 `characters`、`prop`、`view`，不能省略或增加字段。

| 对象 | 必填字段 | 类型与含义 |
|---|---|---|
| `characters` | 导演名单中的每个实际角色名 | 对象；名单与导演总览完全一致，不使用 A/B 代号，不增加未出场角色。 |
| 每个角色 | `position` | `[x, y]`；身体中心在统一画面上的百分比，左上角为 `[0, 0]`，两轴均为 0–100。 |
| 每个角色 | `facing`, `pose` | 非空字符串；身体朝向、主要姿态标签。 |
| 每个角色 | `contacts` | 字符串数组，记录地面支点及手/身体与道具的实际接触；无接触用 `[]`，不得用数组替代接触说明的缺失。 |
| 每个角色 | `velocity` | `[vx, vy]`；画面百分比每秒，正向为右/下，可为非零或负值。 |
| 每个角色 | `phase`, `secondary_motion` | 非空字符串；动作相位及耳、尾等次级微动状态；无相应部位用同一明确标签，如 `none`。 |
| `prop` | 零道具时为 `null` | 一个道具时为对象，不以空对象代替。 |
| 道具对象 | `position`, `velocity` | 与角色同一坐标和速度单位，记录道具中心。 |
| 道具对象 | `orientation`, `shape`, `integrity`, `phase` | 非空字符串；朝向、形变、完整性及运动相位，不能仅写“已复位”。 |
| 道具对象 | `contacts` | 字符串数组，记录与角色、地面等接触，语义与角色的接触描述相互一致。 |
| `view` | `framing`, `camera`, `lighting`, `graphics` | 非空字符串；取景、机位、光照与图形状态。取景/机位须与首末镜表格列一致；无字状态可用 `clear`。 |

数值使用有限 JSON 数字，不用百分号字符串、NaN、Infinity 或布尔值。字段名与角色名区分大小写。语义标签在两端重复填写同一标签，不使用 `same`、`同上`、JSON 引用或不同的同义词。比较语义字符串时仅规范化大小写与空白；`contacts` 按无序列表比较，坐标数组按轴顺序比较。编译器复制全部字段和值；其首镜构图/T2I 的坐标须匹配 `first_start`。

## 完整示例

下面是 High / Low 单球故事的首尾声明；身体中心、脚底基线和球中心是不同锚点。角色双脚接地、手握一体凹槽，球位于高处；末镜从低位起始，通过回弹恢复此状态。将此块原样放入导演输出和编译稿末镜控制区。

```json
{
  "first_start": {
    "characters": {
      "Pip": {"position": [30, 65], "facing": "right", "pose": "upright-overhead-grip", "contacts": ["feet:floor", "hands:ball-left-grip"], "velocity": [0, 0], "phase": "upper-turning-point", "secondary_motion": "settled"},
      "Toby": {"position": [70, 68], "facing": "left", "pose": "bent-knees-overhead-grip", "contacts": ["feet:floor", "hands:ball-right-grip"], "velocity": [0, 0], "phase": "upper-turning-point", "secondary_motion": "settled"}
    },
    "prop": {"position": [50, 35], "orientation": "upright", "shape": "round", "integrity": "intact", "contacts": ["Pip:hands", "Toby:hands"], "velocity": [0, 0], "phase": "upper-turning-point"},
    "view": {"framing": "中全景", "camera": "Static", "lighting": "warm-pastel-3200K", "graphics": "clear"}
  },
  "last_end": {
    "characters": {
      "Pip": {"position": [30, 65], "facing": "right", "pose": "upright-overhead-grip", "contacts": ["feet:floor", "hands:ball-left-grip"], "velocity": [0, 0], "phase": "upper-turning-point", "secondary_motion": "settled"},
      "Toby": {"position": [70, 68], "facing": "left", "pose": "bent-knees-overhead-grip", "contacts": ["feet:floor", "hands:ball-right-grip"], "velocity": [0, 0], "phase": "upper-turning-point", "secondary_motion": "settled"}
    },
    "prop": {"position": [50, 35], "orientation": "upright", "shape": "round", "integrity": "intact", "contacts": ["Pip:hands", "Toby:hands"], "velocity": [0, 0], "phase": "upper-turning-point"},
    "view": {"framing": "中全景", "camera": "Static", "lighting": "warm-pastel-3200K", "graphics": "clear"}
  }
}
```

缺项、未知字段、名单或类型错误报 `INPUT_FORMAT`；首尾任一状态不同、首镜坐标冲突或编译稿改写导演声明报 `LOOP_STATE_MISMATCH`。脚本检查结构、时序与显式声明的一致性，不识别画面姿态，不推断标签背后的物理关系；自由文本因果、接触合理性与实际生成的帧仍须复核。
