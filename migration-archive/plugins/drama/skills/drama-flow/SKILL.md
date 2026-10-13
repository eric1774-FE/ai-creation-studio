---
name: drama-flow
description: 编排中文漫剧从素材到可投产提示词包的完整流水线：画面化扩写、高留存重排、固定资产提取与自动生图、导演分镜、资产绑定、视频段、离线HTML报告和无变量生产包。适用于一站式处理、完整流程、从故事到分镜或生产交付，也可路由单个阶段；不替代各专业 Skill 的内部规则。
---

# 漫剧全流程

统一路由 `$drama-expand`、`$drama-retention`、`$drama-assets` 和 `$drama-storyboard`，保存阶段来源，避免新增内容在交接时变成原文事实。

## 选择运行模式

- 用户明确要求完整制作、一站式处理或从故事到分镜时，运行完整流水线。
- 用户只要求扩写、画面化或情绪细节时，仅使用 `$drama-expand`。
- 用户只要求爆点前置、高留存或解说节奏时，仅使用 `$drama-retention`。
- 用户只要求角色定妆、场景设定、固定资源或资产提示词时，仅使用 `$drama-assets`。
- 用户只要求分镜、镜头提示词或 Manifest 时，仅使用 `$drama-storyboard`。
- 用户明确指定阶段时服从指定，不为凑流程调用无关 Skill。

## 完整流水线预检

开始正式流水线前，一次性确认画幅、目标总时长、媒介与视觉风格、生成路径和现有参考资产。信息缺失时集中询问，不先生成正式结果再返工。

默认采用：

- `$drama-expand` 的“改写+扩写”模式；
- `$drama-retention` 的“保真优化”模式；
- 扩写与留存之间不暂停确认；
- `$drama-assets` 完成核心资产预选后暂停，用户可增删；这是第一次确认。
- `$drama-storyboard` Phase 1 完成后暂停，用户确认当前骨架版本才进入 Phase 2；这是第二次确认。

用户要求严格不新增、自由改编、逐阶段确认或跳过某阶段时，以用户要求为准。

## 来源账本

全程维护三类信息，不互相覆盖：

1. `original_facts`：原始文本明确给出的事实、关系、因果、顺序和结局。
2. `creative_additions`：`$drama-expand` 新增的动作、环境、物品或候选联想。
3. `retention_copy`：`$drama-retention` 重排后的最终文案。

将原文和 `creative_additions` 一并交给 `$drama-retention`，要求它保留二者边界。新增内容被选入成稿时仍列入创作补充，不因重新排序而升级为原文事实。

把 `retention_copy` 作为 `$drama-storyboard` 的直接来源，并用它计算 `source_digest`。同时把来源账本传入分镜阶段；创作补充在 Phase 1 中标记为 `visual_inference`，直到用户确认骨架。

## 阶段执行

1. 使用 `$drama-expand` 生成画面化稿和创作补充。
2. 使用 `$drama-retention` 从扩写结果中选择并重排，输出高留存稿，继续保留创作补充。
3. 使用 `$drama-assets` 从 `retention_copy` 和来源账本生成资产Manifest与核心预选，展示调用数和依赖，等待第一次确认。
4. 用户确认资产清单后，按依赖调用内置 `imagegen`，把成功图片保存到项目目录并登记；A/B级场景先生成无人全景定场图，再以它为输入生成包含正拍、反打和侧向机位的九宫格空间参考；失败项最多修正重试一次。资产阶段结束立即导出离线资产HTML报告，不等待分镜。
5. 使用 `$drama-storyboard` 完成 Phase 0 核对和 Phase 1 骨架，保存当前 `source_digest` 与 `skeleton_revision`，展示骨架等待第二次确认。
6. 用户确认后，使用同一版本进入 Phase 2，编译提示词、按画面可见性绑定固定资产、组合视频段并运行生产验证。
7. 交付 Canonical Manifest、单页双面板HTML和无变量生产包。

如果用户修改原文、高留存稿、实体、时长或分镜结构，递增骨架版本并返回 Phase 1，不沿用旧确认结果。

## 默认交付

- 第一次确认：高留存成稿、来源账本摘要、资产Manifest、核心/可选清单和预计生图调用数。
- 第二次确认：已生成固定资源、资产HTML报告、失败摘要、分镜 Phase 1 文件和待确认版本。
- 最终交付：Canonical Manifest、HTML生产报告、生产包、验证结果和风险摘要。
- 单阶段请求遵循对应专业 Skill 的默认交付格式。
