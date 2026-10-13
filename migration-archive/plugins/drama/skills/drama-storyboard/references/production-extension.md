# 分镜生产扩展 v1

Canonical 分镜继续使用 `storyboard-manifest/v1`。下游生产数据只写入 `extensions.production_v1`：

```json
{
  "extensions": {
    "production_v1": {
      "version": "production-extension/v1",
      "asset_manifest_uri": "project-asset-approved.json",
      "max_segment_seconds": 10,
      "entity_asset_map": [
        {
          "storyboard_entity_id": "CHAR_HERO",
          "asset_entity_id": "character:C01",
          "state_id": "default"
        }
      ],
      "shot_asset_bindings": [
        {
          "shot_id": "SHOT_001",
          "references": [
            {
              "prompt_id": "C01-v1-fullbody",
              "asset_id": "C01",
              "version": "v1",
              "role": "identity",
              "purpose": "角色身份一致性",
              "label": "主角完整人物",
              "uri": "assets/C01-v1-fullbody.png",
              "source_manifest": "assets"
            }
          ]
        }
      ]
    }
  }
}
```

## 绑定规则

- `entity_asset_map` 只做身份和状态对账，不代替逐镜可见性判断。
- `shot_asset_bindings` 只绑定镜头中实际可见、并且生成模型需要上传的图片。
- `role` 只使用 `style/identity/costume/scene/prop/environment/effect`；`purpose` 用自然语言说明该图在本镜中的职责。
- 人物定妆、当前服装、场景主视图和画面中清晰可见的关键道具分别绑定；不因剧情提到某物就上传它。
- A/B 级场景有两类固定图：全景图的 `purpose` 写“场景身份与整体空间结构”；九宫格图写“机位与正反打空间连续性，只作参考，不复制拼贴版式”。全景或大全景优先绑定全景图；对话正反打、侧拍和空间转向优先绑定九宫格图。模型允许且镜头风险高时可同时绑定。
- `prompt_id` 存在成功输出时，`prepare` 自动补齐 `uri`、资产ID和标签。
- 旧 `manual_continuity_assets` 导入 `legacy_imports`，统一标为 `legacy_manual`；无法确定归属时不得猜测镜头绑定。

## 视频段

- `prepare` 按镜头顺序贪心组合，默认最多10秒。
- 场景、`generation_mode` 改变，当前镜声明 `segment_break`，或剪辑类型为 `scene_change/time_jump/montage_break` 时另起一段。
- 每段保存累计切点、逐镜自然语言提示词、独立声音轨和参考图片清单。
- Canonical 标签只留在原始 Manifest；视频段、HTML和 `prompt.md` 中不得出现 `{{...}}`。
