#!/usr/bin/env python3

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "production_pack", ROOT / "scripts" / "production_pack.py"
)
assert SPEC and SPEC.loader
PACK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PACK
SPEC.loader.exec_module(PACK)


def storyboard() -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / "valid_manifest.json").read_text(encoding="utf-8"))


def assets(uri: str | None = None) -> dict:
    output = [] if uri is None else [{"prompt_id": "C01-v1-fullbody", "status": "succeeded", "uri": uri}]
    return {
        "schema_version": "story-asset-manifest/v2",
        "title": "assets",
        "assets": [
            {
                "id": "C01",
                "type": "C",
                "name": "沈凌",
                "versions": [
                    {
                        "id": "v1",
                        "prompts": [
                            {
                                "id": "C01-v1-fullbody",
                                "label": "沈凌完整人物",
                                "mode": "generate",
                                "input_refs": [],
                                "output_spec": {"media_type": "image", "count": 1, "layout": "single", "aspect_ratio": "1:1"},
                                "text": "生成人物。风格：二维漫剧。负面约束：无文字。",
                                "text_en": "Generate character. Style: 2D comic. Negative constraints: no text.",
                            }
                        ],
                    }
                ],
            }
        ],
        "entities": [{"id": "character:C01", "type": "character"}],
        "production": {
            "selection_status": "approved",
            "selection": [
                {
                    "prompt_id": "C01-v1-fullbody",
                    "asset_id": "C01",
                    "version": "v1",
                    "label": "沈凌完整人物",
                    "selected": True,
                    "tier": "core",
                    "reason": "A级角色",
                }
            ],
            "outputs": output,
        },
    }


def add_binding(data: dict) -> None:
    data["extensions"] = {
        "production_v1": {
            "entity_asset_map": [
                {
                    "storyboard_entity_id": "CHAR_SHENLING",
                    "asset_entity_id": "character:C01",
                    "state_id": "default",
                }
            ],
            "shot_asset_bindings": [
                {
                    "shot_id": shot["shot_id"],
                    "references": [
                        {
                            "prompt_id": "C01-v1-fullbody",
                            "role": "identity",
                        }
                    ],
                }
                for shot in data["shots"]
            ],
        }
    }


class ProductionPackTests(unittest.TestCase):
    def test_prepare_groups_and_resolves_canonical_tags(self) -> None:
        data = storyboard()
        prepared = PACK.prepare_manifest(data, Path("storyboard.json"), None, None, 10)
        production = prepared["extensions"]["production_v1"]
        self.assertEqual(1, len(production["segments"]))
        self.assertEqual(6, production["segments"][0]["duration_s"])
        self.assertNotIn("{{", production["segments"][0]["visual_prompt"])
        self.assertEqual([0, 3], production["segments"][0]["cut_starts_s"])

    def test_segment_break_and_duration_limit_are_deterministic(self) -> None:
        data = storyboard()
        data["shots"][1]["risk_flags"].append("segment_break")
        prepared = PACK.prepare_manifest(data, Path("storyboard.json"), None, None, 10)
        self.assertEqual(2, len(prepared["extensions"]["production_v1"]["segments"]))
        data = storyboard()
        data["shots"][0]["duration_s"] = 11
        data["project"]["target_duration_s"] = 14
        with self.assertRaises(PACK.ProductionError):
            PACK.prepare_manifest(data, Path("storyboard.json"), None, None, 10)

    def test_legacy_assets_are_imported_without_fake_bindings(self) -> None:
        data = storyboard()
        data["extensions"] = {
            "manual_continuity_assets": [
                {"uri": "assets/hero.png", "purpose": "角色连续性", "binding": "manual_only"}
            ]
        }
        prepared = PACK.prepare_manifest(data, Path("storyboard.json"), None, None, 10)
        production = prepared["extensions"]["production_v1"]
        self.assertEqual("legacy_manual", production["legacy_imports"][0]["binding"])
        self.assertEqual([], production["shot_asset_bindings"])

    def test_binding_validation_catches_unknown_entities_prompts_and_duplicates(self) -> None:
        data = storyboard()
        add_binding(data)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "hero.png"
            image.write_bytes(b"png")
            asset_data = assets(image.name)
            prepared = PACK.prepare_manifest(data, root / "storyboard.json", asset_data, root / "assets.json", 10)
            production = prepared["extensions"]["production_v1"]
            production["entity_asset_map"][0]["asset_entity_id"] = "missing"
            production["shot_asset_bindings"][0]["references"][0]["prompt_id"] = "missing"
            production["shot_asset_bindings"].append(copy.deepcopy(production["shot_asset_bindings"][0]))
            errors, _ = PACK.validate_production(prepared, root / "storyboard.json", asset_data, root / "assets.json")
            self.assertTrue(any("未知资产实体" in error for error in errors))
            self.assertTrue(any("未知资产提示词" in error for error in errors))
            self.assertTrue(any("绑定重复" in error for error in errors))

    def test_missing_core_output_prevents_ready(self) -> None:
        data = storyboard()
        prepared = PACK.prepare_manifest(data, Path("storyboard.json"), assets(), Path("assets.json"), 10)
        self.assertEqual("incomplete", prepared["extensions"]["production_v1"]["status"])
        errors, _ = PACK.validate_production(prepared, Path("storyboard.json"), assets(), Path("assets.json"))
        self.assertTrue(any("核心资产未就绪" in error for error in errors))

    def test_scene_grid_binding_gets_spatial_reference_purpose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hero = root / "hero.png"
            grid = root / "grid.png"
            hero.write_bytes(b"png")
            grid.write_bytes(b"png")
            asset_data = assets(hero.name)
            asset_data["assets"].append(
                {
                    "id": "S01",
                    "type": "S",
                    "name": "地下室",
                    "versions": [
                        {
                            "id": "v1",
                            "prompts": [
                                {
                                    "id": "S01-v1-coverage-grid",
                                    "label": "地下室九宫格机位图",
                                    "production_role": "scene_coverage_grid",
                                    "mode": "edit",
                                    "input_refs": [],
                                    "output_spec": {"media_type": "image", "count": 1, "layout": "nine_grid", "aspect_ratio": "16:9"},
                                    "text": "生成九宫格。风格：二维漫剧。负面约束：无文字。",
                                    "text_en": "Generate a grid. Style: 2D comic. Negative constraints: no text.",
                                }
                            ],
                        }
                    ],
                }
            )
            asset_data["production"]["outputs"].append(
                {"prompt_id": "S01-v1-coverage-grid", "status": "succeeded", "uri": grid.name}
            )
            data = storyboard()
            data["extensions"] = {
                "production_v1": {
                    "entity_asset_map": [],
                    "shot_asset_bindings": [
                        {
                            "shot_id": data["shots"][0]["shot_id"],
                            "references": [{"prompt_id": "S01-v1-coverage-grid"}],
                        }
                    ],
                }
            }
            prepared = PACK.prepare_manifest(
                data, root / "storyboard.json", asset_data, root / "assets.json", 10
            )
            reference = prepared["extensions"]["production_v1"]["shot_asset_bindings"][0]["references"][0]
            self.assertEqual("scene", reference["role"])
            self.assertEqual("scene_coverage_grid", reference["production_role"])
            self.assertIn("不复制九宫格", reference["purpose"])

    def test_report_and_export_are_offline_and_variable_free(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "hero.png"
            image.write_bytes(b"png")
            data = storyboard()
            add_binding(data)
            asset_data = assets(image.name)
            story_path = root / "storyboard.json"
            asset_path = root / "assets.json"
            prepared = PACK.prepare_manifest(data, story_path, asset_data, asset_path, 10)
            report_path = root / "report.html"
            report = PACK.render_report_html(prepared, asset_data, story_path, asset_path, report_path)
            self.assertIn('id="assets-pane"', report)
            self.assertIn('id="storyboard-pane"', report)
            self.assertNotIn("<script src=", report)
            self.assertNotIn("<link ", report)
            self.assertNotIn("{{", report)
            out_dir = root / "production"
            PACK.export_pack(prepared, asset_data, story_path, asset_path, out_dir)
            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("drama-production-pack/v1", manifest["schema_version"])
            self.assertTrue((out_dir / "assets" / "hero.png").exists())
            self.assertTrue((out_dir / "segments" / "SEG-001" / "prompt.md").exists())
            self.assertNotIn("{{", (out_dir / "segments" / "SEG-001" / "prompt.md").read_text(encoding="utf-8"))

    def test_report_escapes_model_generated_html_and_embedded_json(self) -> None:
        data = storyboard()
        asset_data = assets()
        asset_data["assets"][0]["name"] = '</script><img src=x onerror="boom">'
        prepared = PACK.prepare_manifest(data, Path("storyboard.json"), asset_data, Path("assets.json"), 10)
        report = PACK.render_report_html(
            prepared, asset_data, Path("storyboard.json"), Path("assets.json"), Path("report.html")
        )
        self.assertNotIn('<img src=x onerror="boom">', report)
        self.assertNotIn("</script><img", report)
        self.assertIn("\\u003c/script>", report)


if __name__ == "__main__":
    unittest.main()
