#!/usr/bin/env python3

import copy
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_prompt_report as renderer


def fact(key, value, *, source="source_text", status="confirmed", unit=None):
    item = {
        "key": key,
        "value": value,
        "source": source,
        "status": status,
        "evidence": "测试依据",
    }
    if unit:
        item["unit"] = unit
    if source == "source_text":
        item["source_locator"] = "第一章"
    return item


def input_ref(source_kind, ref_id, role):
    return {"source_kind": source_kind, "ref_id": ref_id, "role": role}


def image_prompt(prompt_id, label, text, *, mode="generate", inputs=None):
    return {
        "id": prompt_id,
        "label": label,
        "mode": mode,
        "input_refs": inputs or [],
        "output_spec": {
            "media_type": "image",
            "count": 1,
            "layout": "单图" if "fullbody" not in prompt_id else "横向四视图",
            "aspect_ratio": "4:5" if "fullbody" not in prompt_id else "2:1",
        },
        "text": f"{text}。风格：二维漫剧统一线稿与赛璐璐着色。负面约束：禁止结构漂移、文字和水印。",
        "text_en": f"English prompt for {prompt_id}. Style: unified 2D comic linework and cel shading. Negative constraints: no structural drift, text, or watermark.",
    }


def audio_prompt(prompt_id, label, text):
    return {
        "id": prompt_id,
        "label": label,
        "mode": "generate",
        "input_refs": [],
        "output_spec": {
            "media_type": "audio",
            "count": 1,
            "duration_seconds": 12,
            "loopable": False,
        },
        "text": f"{text}。风格：写实分层声音设计。负面约束：禁止削波、底噪和突兀循环接缝。",
        "text_en": f"English prompt for {prompt_id}. Style: realistic layered sound design. Negative constraints: no clipping, noise floor, or abrupt loop seam.",
    }


def version(version_id, label, prompts, *, facts=None):
    return {
        "id": version_id,
        "label": label,
        "story_stage": label,
        "changes": "测试变化",
        "facts": facts or [],
        "prompts": prompts,
        "prohibitions": ["禁止身份漂移"],
    }


def asset(asset_id, asset_type, name, versions, *, facts=None, importance=None, subtype=None):
    item = {
        "id": asset_id,
        "type": asset_type,
        "name": name,
        "first_appearance": "阶段01",
        "definition": "测试资产定义",
        "anchors": ["保持身份与结构一致"],
        "facts": facts or [],
        "versions": versions,
    }
    if importance:
        item["importance_level"] = importance
    if subtype:
        item["subtype"] = subtype
    return item


def ref(asset_id, version_id, relation):
    return {"asset_id": asset_id, "version": version_id, "relation_label": relation}


def coverage(assets):
    counts = {asset_type: 0 for asset_type in renderer.ASSET_TYPES}
    for item in assets:
        counts[item["type"]] += 1
    return [
        {
            "type": asset_type,
            "status": "present" if counts[asset_type] else "none",
            "count": counts[asset_type],
            "note": "测试覆盖",
        }
        for asset_type in sorted(renderer.ASSET_TYPES)
    ]


def sample_manifest():
    assets = [
        asset(
            "G01",
            "G",
            "全局视觉圣经",
            [
                version(
                    "v1",
                    "锁定风格",
                    [
                        image_prompt(
                            "G01-v1-style",
                            "全局风格提示词",
                            "全局风格提示词",
                            inputs=[input_ref("reference_input", "R01", "只参考线条与色彩")],
                        )
                    ],
                )
            ],
            facts=[fact("render_mode", "2d_comic", source="user")],
        ),
        asset(
            "C01",
            "C",
            "主角A",
            [
                version(
                    "v1",
                    "正常",
                    [
                        image_prompt("C01-v1-face", "面部身份", "面部身份提示词"),
                        image_prompt(
                            "C01-v1-fullbody",
                            "完整人物四视图",
                            "完整人物四视图提示词",
                            mode="edit",
                            inputs=[input_ref("prompt_output", "C01-v1-face", "唯一面部身份来源")],
                        ),
                    ],
                ),
                version(
                    "v2",
                    "受伤",
                    [
                        image_prompt(
                            "C01-v2-injured",
                            "受伤编辑",
                            "受伤状态提示词",
                            mode="edit",
                            inputs=[input_ref("prompt_output", "C01-v1-fullbody", "角色身体与身份母版")],
                        )
                    ],
                    facts=[fact("injury", "左前臂擦伤")],
                ),
                version(
                    "v3",
                    "变身",
                    [
                        image_prompt(
                            "C01-v3-transformed",
                            "变身编辑",
                            "变身状态提示词",
                            mode="edit",
                            inputs=[input_ref("prompt_output", "C01-v1-fullbody", "角色身份母版")],
                        )
                    ],
                ),
            ],
            facts=[
                fact("height_cm", 172, source="inference", status="estimated", unit="cm"),
                fact("weight_kg", 62, source="inference", status="estimated", unit="kg"),
            ],
            importance="A",
        ),
        asset(
            "W01",
            "W",
            "主角外套",
            [version("v1", "日常", [image_prompt("W01-v1-costume", "服装结构", "主角外套提示词")])],
            subtype="costume",
        ),
        asset(
            "W02",
            "W",
            "主角发型",
            [version("v1", "日常", [image_prompt("W02-v1-hair", "发型", "主角发型提示词")])],
            subtype="hair",
        ),
        asset(
            "W03",
            "W",
            "主角妆容",
            [version("v1", "日常", [image_prompt("W03-v1-makeup", "妆容", "主角妆容提示词")])],
            subtype="makeup",
        ),
        asset(
            "S01",
            "S",
            "旧宅",
            [version("v1", "完整", [image_prompt("S01-v1-master", "场景母版", "旧宅场景提示词")])],
            importance="A",
        ),
        asset(
            "P01",
            "P",
            "铜钥匙",
            [version("v1", "完好", [image_prompt("P01-v1-isolated", "道具图", "共享钥匙唯一提示词")])],
        ),
        asset(
            "V01",
            "V",
            "送货摩托",
            [version("v1", "完好", [image_prompt("V01-v1-vehicle", "载具图", "送货摩托提示词")])],
        ),
        asset(
            "E01",
            "E",
            "旧宅夜间环境",
            [version("v1", "夜间", [image_prompt("E01-v1-environment", "环境状态", "夜间环境提示词")])],
        ),
        asset(
            "L01",
            "L",
            "旧宅夜间灯光",
            [
                version(
                    "v1",
                    "夜间",
                    [image_prompt("L01-v1-light", "灯光模块", "灯光提示词 </script><img src=x onerror=alert(1)>")],
                )
            ],
        ),
        asset(
            "F01",
            "F",
            "旧宅灰尘",
            [version("v1", "扬起", [image_prompt("F01-v1-dust", "灰尘特效", "灰尘特效提示词")])],
        ),
        asset(
            "A-VO-01",
            "A",
            "主角声音",
            [version("v1", "日常", [audio_prompt("A-VO-01-v1-voice", "角色声音", "主角声音提示词")])],
        ),
        asset(
            "A-AMB-01",
            "A",
            "旧宅环境声",
            [version("v1", "夜间", [audio_prompt("A-AMB-01-v1-ambience", "环境声音", "旧宅环境声提示词")])],
        ),
    ]
    return {
        "schema_version": renderer.SCHEMA_VERSION,
        "title": "测试故事资产报告",
        "input_summary": "主角A在旧宅经历正常、受伤与变身。",
        "constraints": ["二维漫剧"],
        "aliases": [{"alias": "阿A", "canonical": "主角A", "note": "同一角色"}],
        "pending_questions": [],
        "reference_inputs": [
            {
                "id": "R01",
                "media_type": "image",
                "source_ref": "reference-style.png",
                "role": "style",
                "description": "用户提供的线条风格参考",
                "allowed_influence": ["线条粗细", "色彩关系"],
                "prohibited_influence": ["人物身份", "服装结构"],
            }
        ],
        "asset_type_coverage": coverage(assets),
        "assets": assets,
        "entities": [
            {
                "id": "character:C01",
                "type": "character",
                "name": "主角A",
                "description": "核心角色",
                "common_asset_refs": [
                    ref("C01", "v1", "身份锚点"),
                    ref("W02", "v1", "当前发型"),
                    ref("W03", "v1", "当前妆容"),
                    ref("A-VO-01", "v1", "角色声音"),
                ],
                "states": [
                    {
                        "id": "normal",
                        "label": "正常",
                        "story_stage": "阶段01",
                        "asset_refs": [ref("W01", "v1", "当前服装"), ref("P01", "v1", "随身道具")],
                    },
                    {"id": "injured", "label": "受伤", "story_stage": "阶段02", "asset_refs": [ref("C01", "v2", "角色状态")]},
                    {"id": "transformed", "label": "变身", "story_stage": "阶段03", "asset_refs": [ref("C01", "v3", "角色状态")]},
                ],
            },
            {
                "id": "scene:S01",
                "type": "scene",
                "name": "旧宅",
                "description": "主要场景",
                "common_asset_refs": [ref("S01", "v1", "空间锚点"), ref("P01", "v1", "场景道具")],
                "states": [
                    {
                        "id": "night",
                        "label": "夜间",
                        "story_stage": "阶段02",
                        "asset_refs": [
                            ref("E01", "v1", "当前环境"),
                            ref("L01", "v1", "当前灯光"),
                            ref("F01", "v1", "当前特效"),
                            ref("A-AMB-01", "v1", "环境声音"),
                        ],
                    }
                ],
            },
        ],
        "standalone_asset_refs": [
            ref("G01", "v1", "项目全局"),
            ref("V01", "v1", "独立载具"),
        ],
        "continuity": [
            {
                "stage_id": "stage-02",
                "label": "旧宅夜间受伤",
                "source_locator": "第二章",
                "asset_refs": [
                    ref("C01", "v2", "角色状态"),
                    ref("S01", "v1", "场景"),
                    ref("L01", "v1", "灯光"),
                ],
            }
        ],
        "quality_checks": [{"label": "语义检查", "status": "pass", "note": "全部覆盖"}],
    }


def find_prompt(manifest, prompt_id):
    for item in manifest["assets"]:
        for item_version in item["versions"]:
            for prompt in item_version["prompts"]:
                if prompt["id"] == prompt_id:
                    return prompt
    raise AssertionError(prompt_id)


class RendererTests(unittest.TestCase):
    def test_v2_manifest_renders_once_and_escapes_script_end(self):
        manifest = sample_manifest()
        output = renderer.build_html(manifest)
        self.assertEqual(output.count("共享钥匙唯一提示词"), 1)
        self.assertNotIn("</script><img src=x", output)
        self.assertIn("\\u003c/script\\u003e", output)
        marker = '<script id="report-data" type="application/json">'
        start = output.index(marker) + len(marker)
        payload = output[start:output.index("</script>", start)]
        restored = json.loads(payload)
        self.assertEqual(restored["schema_version"], renderer.SCHEMA_VERSION)
        self.assertEqual(restored["assets"][1]["facts"][0]["value"], 172)
        self.assertEqual(find_prompt(restored, "C01-v1-fullbody")["input_refs"][0]["ref_id"], "C01-v1-face")

    def test_wrong_schema_version_is_rejected(self):
        manifest = sample_manifest()
        manifest["schema_version"] = "story-asset-manifest/unsupported"
        with self.assertRaisesRegex(renderer.ManifestError, renderer.SCHEMA_VERSION):
            renderer.validate_manifest(manifest)

    def test_fact_source_and_evidence_are_validated(self):
        invalid_source = sample_manifest()
        invalid_source["assets"][1]["facts"][0]["source"] = "原文明确"
        with self.assertRaisesRegex(renderer.ManifestError, "source 必须是"):
            renderer.validate_manifest(invalid_source)

        missing_evidence = sample_manifest()
        missing_evidence["assets"][1]["facts"][0].pop("evidence")
        with self.assertRaisesRegex(renderer.ManifestError, "evidence"):
            renderer.validate_manifest(missing_evidence)

    def test_alias_shape_and_subtype_scope_are_validated(self):
        bad_alias = sample_manifest()
        bad_alias["aliases"][0] = {"canonical": "主角A", "variants": ["阿A"]}
        with self.assertRaisesRegex(renderer.ManifestError, "alias"):
            renderer.validate_manifest(bad_alias)

        bad_audio_subtype = sample_manifest()
        next(item for item in bad_audio_subtype["assets"] if item["id"] == "A-VO-01")["subtype"] = "voice"
        with self.assertRaisesRegex(renderer.ManifestError, "subtype 只适用于 W"):
            renderer.validate_manifest(bad_audio_subtype)

    def test_duplicate_prompt_id_is_rejected(self):
        manifest = sample_manifest()
        find_prompt(manifest, "P01-v1-isolated")["id"] = "C01-v1-face"
        with self.assertRaisesRegex(renderer.ManifestError, "id 重复"):
            renderer.validate_manifest(manifest)

    def test_duplicate_prompt_text_must_be_merged_or_distinguished(self):
        duplicate_chinese = sample_manifest()
        find_prompt(duplicate_chinese, "P01-v1-isolated")["text"] = find_prompt(
            duplicate_chinese, "C01-v1-face"
        )["text"]
        with self.assertRaisesRegex(renderer.ManifestError, "请合并或明确区分"):
            renderer.validate_manifest(duplicate_chinese)

        duplicate_english = sample_manifest()
        find_prompt(duplicate_english, "P01-v1-isolated")["text_en"] = find_prompt(
            duplicate_english, "C01-v1-face"
        )["text_en"]
        with self.assertRaisesRegex(renderer.ManifestError, "请合并或明确区分"):
            renderer.validate_manifest(duplicate_english)

    def test_prompt_style_and_negative_sections_are_required(self):
        missing_style = sample_manifest()
        find_prompt(missing_style, "C01-v1-face")["text"] = "面部身份提示词。负面约束：禁止身份漂移。"
        with self.assertRaisesRegex(renderer.ManifestError, "风格："):
            renderer.validate_manifest(missing_style)

        missing_negative = sample_manifest()
        find_prompt(missing_negative, "C01-v1-face")["text_en"] = "Face identity prompt. Style: 2D comic."
        with self.assertRaisesRegex(renderer.ManifestError, "Negative constraints:"):
            renderer.validate_manifest(missing_negative)

    def test_english_prompts_are_required(self):
        bilingual = sample_manifest()
        find_prompt(bilingual, "C01-v1-face")["text_en"] = "English </script><img src=x onerror=alert(2)>. Style: 2D comic. Negative constraints: no text or watermark."
        renderer.validate_manifest(bilingual)
        output = renderer.build_html(bilingual)
        self.assertNotIn("English </script><img", output)
        self.assertIn("English \\u003c/script\\u003e", output)

        partial = sample_manifest()
        find_prompt(partial, "C01-v1-face").pop("text_en")
        with self.assertRaisesRegex(renderer.ManifestError, "text_en"):
            renderer.validate_manifest(partial)

        empty = sample_manifest()
        find_prompt(empty, "C01-v1-face")["text_en"] = ""
        with self.assertRaisesRegex(renderer.ManifestError, "text_en"):
            renderer.validate_manifest(empty)

        wrong_type = sample_manifest()
        find_prompt(wrong_type, "C01-v1-face")["text_en"] = ["not", "text"]
        with self.assertRaisesRegex(renderer.ManifestError, "text_en"):
            renderer.validate_manifest(wrong_type)

    def test_dangling_and_cyclic_prompt_dependencies_are_rejected(self):
        dangling = sample_manifest()
        find_prompt(dangling, "C01-v1-fullbody")["input_refs"][0]["ref_id"] = "missing"
        with self.assertRaisesRegex(renderer.ManifestError, "不存在的提示词产物"):
            renderer.validate_manifest(dangling)

        cyclic = sample_manifest()
        find_prompt(cyclic, "C01-v1-face")["input_refs"] = [
            input_ref("prompt_output", "C01-v1-fullbody", "错误反向依赖")
        ]
        with self.assertRaisesRegex(renderer.ManifestError, "依赖存在循环"):
            renderer.validate_manifest(cyclic)

    def test_dangling_unreferenced_and_duplicate_asset_refs_are_rejected(self):
        dangling = sample_manifest()
        dangling["entities"][0]["states"][0]["asset_refs"][0]["asset_id"] = "P99"
        with self.assertRaisesRegex(renderer.ManifestError, "不存在的资产版本"):
            renderer.validate_manifest(dangling)

        unreferenced = sample_manifest()
        unreferenced["entities"][0]["states"][2]["asset_refs"] = []
        with self.assertRaisesRegex(renderer.ManifestError, "未被实体、状态或独立资产区引用"):
            renderer.validate_manifest(unreferenced)

        duplicate = sample_manifest()
        duplicate["entities"][0]["states"][0]["asset_refs"].append(ref("C01", "v1", "重复身份"))
        with self.assertRaisesRegex(renderer.ManifestError, "与共用资产重复引用"):
            renderer.validate_manifest(duplicate)

    def test_coverage_and_output_spec_are_validated(self):
        bad_coverage = sample_manifest()
        next(item for item in bad_coverage["asset_type_coverage"] if item["type"] == "C")["count"] = 2
        with self.assertRaisesRegex(renderer.ManifestError, "count 应为 1"):
            renderer.validate_manifest(bad_coverage)

        bad_output = sample_manifest()
        find_prompt(bad_output, "C01-v1-face")["output_spec"].pop("aspect_ratio")
        with self.assertRaisesRegex(renderer.ManifestError, "aspect_ratio"):
            renderer.validate_manifest(bad_output)

    def test_render_mode_reference_roles_and_scene_state_are_validated(self):
        bad_mode = sample_manifest()
        bad_mode["assets"][0]["facts"][0]["value"] = "photorealistic"
        with self.assertRaisesRegex(renderer.ManifestError, "render_mode 必须是"):
            renderer.validate_manifest(bad_mode)

        empty_reference_rule = sample_manifest()
        empty_reference_rule["reference_inputs"][0]["allowed_influence"] = []
        with self.assertRaisesRegex(renderer.ManifestError, "分别声明允许影响和禁止影响"):
            renderer.validate_manifest(empty_reference_rule)

        missing_scene_anchor = sample_manifest()
        missing_scene_anchor["entities"][1]["common_asset_refs"] = [ref("P01", "v1", "场景道具")]
        missing_scene_anchor["standalone_asset_refs"].append(ref("S01", "v1", "独立场景"))
        with self.assertRaisesRegex(renderer.ManifestError, "至少一个 S 资产版本"):
            renderer.validate_manifest(missing_scene_anchor)

        empty_stage = sample_manifest()
        empty_stage["continuity"][0]["asset_refs"] = []
        with self.assertRaisesRegex(renderer.ManifestError, "至少包含一个资产版本"):
            renderer.validate_manifest(empty_stage)

    def test_validate_only_cli_and_file_preservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.json"
            output_path = root / "report.html"
            manifest_path.write_text(json.dumps(sample_manifest(), ensure_ascii=False), encoding="utf-8")
            with redirect_stdout(StringIO()) as stdout:
                self.assertEqual(renderer.main(["--input", str(manifest_path), "--validate-only"]), 0)
            self.assertIn("验证通过", stdout.getvalue())
            self.assertFalse(output_path.exists())

            rendered_path = root / "rendered.html"
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    renderer.main(["--input", str(manifest_path), "--output", str(rendered_path)]),
                    0,
                )
            self.assertIn("<!doctype html>", rendered_path.read_text(encoding="utf-8"))

            output_path.write_text("保留旧文件", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                renderer.render_file(manifest_path, output_path)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "保留旧文件")


if __name__ == "__main__":
    unittest.main()
