# Reviewer Bad Cases

以下均为本地手写契约夹具，不是实际模型试跑结果。Python 只检查栏目、状态行和拒绝分支，不判断这些故事的语义是否成立。`变体` 以 golden-review.md 为基底应用一次文本替换。

### missing-planner-input

- 类型：planner
- 预期：invalid

```markdown
## 【规格设定】

- 节奏模式：standard
- 建议总时长：16 秒
- 节拍数量：4 拍
- 场景：Cozy Playroom
- 出场角色：Pip、Toby
- 核心道具：方向盘

## 【选定戏剧母题】

双雄相克，左右较劲后回弹。

## 【教学与 TPR 映射】

Left / Right 绑定指针左右偏转；亲子面朝同向指认。

## 【剧情节拍大纲（Beat Outline）】

Beat 1 左转示范，Beat 2 右转加码，Beat 3 较劲，Beat 4 回弹。
```

缺少 `【家长端动作指引（CTA）】`，应要求补齐，不生成完整评审。

### vocab-grounding

- 类型：review
- 预期：blocked

```markdown
## 【剧本硬线与雷达体检】

- **红线筛查**：未通过 - 触发错误码: `VOCAB_GROUNDING_MISMATCH`
- **红线定位**：Beat 2 指针居中、角色直立，却喊 “Right!”，缺少右偏证据。
- **四维评分与扣分项**：
  - 道具玩具化：合格。
  - 橡皮泥身体喜剧：合格。
  - 教学无歧义：扣分，词义与状态脱节。
  - 四拍递进因果：合格。

## 【手术级打磨建议（Surgery Notes）】

- **道具升级方案**：保持同一软轴和握把。
- **包袱强化方案**：保留贴地麻花形变。
- **时序与教学防呆**：只在指针确实右偏时喊词。

## 【重写润色后的 4 拍大纲（Polished Version）】

- **状态**：拒绝下游稿，未生成 Golden 4 拍。
- **下一步**：请将本体检报告与手术建议补充给 `kids-story-planner` 重写，再重新提交 `kids-story-reviewer`。
```

### unclosed-airborne

- 类型：review
- 预期：blocked

```markdown
## 【剧本硬线与雷达体检】

- **红线筛查**：未通过 - 触发错误码: `UNCLOSED_AIRBORNE_ACTION`
- **红线定位**：Beat 3 的 Jump 示范让 Pip 在半空等待，Beat 4 才落地，且缺缓冲。
- **四维评分与扣分项**：
  - 道具玩具化：合格（零道具）。
  - 橡皮泥身体喜剧：扣分，依赖跨拍悬空。
  - 教学无歧义：合格。
  - 四拍递进因果：扣分，动作未闭环。

## 【手术级打磨建议（Surgery Notes）】

- **道具升级方案**：不新增道具。
- **包袱强化方案**：用落地后的黏土压缩制造笑点。
- **时序与教学防呆**：Beat 3 内完成起跳、落地与缓冲，Beat 4 仅收敛余动。

## 【重写润色后的 4 拍大纲（Polished Version）】

- **状态**：拒绝下游稿，未生成 Golden 4 拍。
- **下一步**：请将本体检报告与手术建议补充给 `kids-story-planner` 重写，再重新提交 `kids-story-reviewer`。
```

### end-pollution-v1

- 类型：review
- 预期：blocked

```markdown
## 【剧本硬线与雷达体检】

- **红线筛查**：未通过 - 触发错误码: `TEACHING_POLLUTION_AT_END`
- **红线定位**：Beat 4 / Shot 4 的方向盘在回中复位时，Toby 再喊 “Right!” 并新弹出 Right 花字。
- **四维评分与扣分项**：
  - 道具玩具化：合格。
  - 橡皮泥身体喜剧：合格。
  - 教学无歧义：扣分，复位拍被教学污染。
  - 四拍递进因果：扣分，收尾还在教词。

## 【手术级打磨建议（Surgery Notes）】

- **道具升级方案**：保留已有回弹机构。
- **包袱强化方案**：回中只保留互看一眼。
- **时序与教学防呆**：将 Right 的示范留在 Beat 2，Beat 4 不触发教学。

## 【重写润色后的 4 拍大纲（Polished Version）】

- **状态**：拒绝下游稿，未生成 Golden 4 拍。
- **下一步**：请将本体检报告与手术建议补充给 `kids-story-planner` 重写，再重新提交 `kids-story-reviewer`。
```

Gemini v1 来源为仓库提交 `4195c6a` 中 `story-gemini.md` 的 Shot 4：方向盘回正至中心，但 `t=0.75–1.15s Toby: Right!`，并新弹 Right 花字。此处隔离末拍污染；原始片段同时可能触发 `VOCAB_GROUNDING_MISMATCH`，完整语义评审必须列全命中码。

### end-pollution-v2

- 类型：review
- 预期：blocked

```markdown
## 【剧本硬线与雷达体检】

- **红线筛查**：未通过 - 触发错误码: `TEACHING_POLLUTION_AT_END`
- **红线定位**：Beat 4 / Shot 4 先在右偏静态下再次喊 “Right!” 并弹字，再释放扭力回中。词义成立，仍违反清白复位拍。
- **四维评分与扣分项**：
  - 道具玩具化：合格。
  - 橡皮泥身体喜剧：合格。
  - 教学无歧义：扣分，收尾新增教学事件。
  - 四拍递进因果：扣分，复位承担了额外教学。

## 【手术级打磨建议（Surgery Notes）】

- **道具升级方案**：不新增机构。
- **包袱强化方案**：卸力回弹后面面相觑。
- **时序与教学防呆**：把正确的右偏教学移回 Beat 2，Beat 4 保持无字。

## 【重写润色后的 4 拍大纲（Polished Version）】

- **状态**：拒绝下游稿，未生成 Golden 4 拍。
- **下一步**：请将本体检报告与手术建议补充给 `kids-story-planner` 重写，再重新提交 `kids-story-reviewer`。
```

Gemini v2 是针对 v1 构造的回归变体，用于隔离“词义正确但末拍仍被污染”的情况，不冒称可追溯的第二份真实模型产物。

### magic-reset

- 类型：review
- 预期：blocked

```markdown
## 【剧本硬线与雷达体检】

- **红线筛查**：未通过 - 触发错误码: `MAGIC_RESET`
- **红线定位**：Beat 3 拉断握把，Beat 4 复制首帧让握把凭空完好。
- **四维评分与扣分项**：
  - 道具玩具化：扣分，断裂不能回弹修复。
  - 橡皮泥身体喜剧：扣分，使用不可逆损坏。
  - 教学无歧义：合格。
  - 四拍递进因果：扣分，依赖复制首帧。

## 【手术级打磨建议（Surgery Notes）】

- **道具升级方案**：改为现有轮缘的弹性形变，取消断裂。
- **包袱强化方案**：用可回弹的身体扭转代替损坏。
- **时序与教学防呆**：让角色卸力、软轴释放储能并自然复位。

## 【重写润色后的 4 拍大纲（Polished Version）】

- **状态**：拒绝下游稿，未生成 Golden 4 拍。
- **下一步**：请将本体检报告与手术建议补充给 `kids-story-planner` 重写，再重新提交 `kids-story-reviewer`。
```

### failed-with-golden

- 类型：variant
- 预期：invalid

```json
{"old": "- **红线筛查**：全部通过", "new": "- **红线筛查**：未通过 - 触发错误码: `MAGIC_RESET`"}
```

该变体保留 Golden 的完整第三栏，是红线失败后仍泄漏下游大纲的违规例。

### status-drift

- 类型：variant
- 预期：invalid

```json
{"old": "- **红线筛查**：全部通过", "new": "- **红线筛查**：PASS（全部通过）"}
```

### heading-drift

- 类型：variant
- 预期：invalid

```json
{"old": "### 【教学与 TPR 映射】", "new": "### 【教学映射】"}
```

### beat-gap

- 类型：variant
- 预期：invalid

```json
{"old": "#### Beat 3（失控破功）", "new": "#### Beat 4（失控破功）"}
```

### extra-section

- 类型：variant
- 预期：invalid

```json
{"old": "## 【手术级打磨建议（Surgery Notes）】", "new": "## 附加总结\n\n多余栏目。\n\n## 【手术级打磨建议（Surgery Notes）】"}
```
