# 资产生产扩展

`story-asset-manifest/v2` 的原始资产、事实、实体和提示词字段保持不变。自动生图状态写在根节点 `production`：

```json
{
  "production": {
    "selection_status": "draft | approved",
    "selection": [
      {
        "prompt_id": "C01-v1-fullbody",
        "asset_id": "C01",
        "version": "v1",
        "label": "完整人物四视图",
        "selected": true,
        "tier": "core",
        "reason": "A级角色"
      }
    ],
    "outputs": [
      {
        "prompt_id": "C01-v1-fullbody",
        "status": "succeeded",
        "uri": "assets/C01-v1-fullbody.png",
        "dependencies": ["C01-v1-face"]
      }
    ],
    "readiness": "awaiting_approval | generating | blocked | ready"
  }
}
```

场景提示词可增加兼容字段 `production_role`：

- `scene_panorama`：同一场景的无人全景空间母版，`output_spec.layout=single_panorama`。
- `scene_coverage_grid`：依赖全景母版的 3×3 正拍、反打与侧向机位参考，`output_spec.layout=nine_grid`。

字段用于选择、报告和分镜绑定，不改变 `story-asset-manifest/v2` 的资产引用关系。新建 A/B 级场景必须同时具备两种职责；旧 Manifest 未包含该字段时仍可读取，但不得把旧单张场景图误报为已完成机位覆盖。

## 不变量

- `selection` 只登记 `output_spec.media_type=image` 的提示词。
- `tier=core` 表示生产就绪所必需；用户可在第一次确认时排除它，排除后不再视为必需。
- 选择一个编辑提示词时，所有 `prompt_output` 依赖必须自动加入选择。
- 每个提示词最多一个当前输出记录。重生成时替换记录，图片文件使用新版本名，不覆盖旧文件。
- `succeeded` 必须有可访问的 `uri`；`failed` 必须有失败原因；依赖失败的下游记录为 `skipped`。
- 仅当全部已选核心提示词成功时才允许 `readiness=ready`。
- A/B 级场景的九宫格提示词必须依赖同版本全景图；全景失败时九宫格登记为 `skipped`。
