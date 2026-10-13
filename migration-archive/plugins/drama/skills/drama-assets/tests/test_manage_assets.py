#!/usr/bin/env python3

from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "manage_assets", ROOT / "scripts" / "manage_assets.py"
)
assert SPEC and SPEC.loader
MANAGER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MANAGER
SPEC.loader.exec_module(MANAGER)


def prompt(
    prompt_id: str,
    media: str = "image",
    deps: tuple[str, ...] = (),
    production_role: str | None = None,
    layout: str = "single",
    dep_role: str = "identity",
) -> dict:
    value = {
        "id": prompt_id,
        "label": prompt_id,
        "mode": "edit" if deps else "generate",
        "input_refs": [
            {"source_kind": "prompt_output", "ref_id": dep, "role": dep_role}
            for dep in deps
        ],
        "output_spec": {
            "media_type": media,
            "count": 1,
            **({"layout": layout, "aspect_ratio": "16:9"} if media == "image" else {}),
        },
        "text": "生成资产。风格：二维漫剧。负面约束：无文字。",
        "text_en": "Generate asset. Style: 2D comic. Negative constraints: no text.",
    }
    if production_role:
        value["production_role"] = production_role
    return value


def asset(asset_id: str, asset_type: str, prompts: list[dict], importance: str | None = None) -> dict:
    value = {
        "id": asset_id,
        "type": asset_type,
        "name": asset_id,
        "definition": asset_id,
        "anchors": [],
        "facts": [],
        "versions": [
            {
                "id": "v1",
                "label": "default",
                "story_stage": "stage-01",
                "changes": "none",
                "facts": [],
                "prompts": prompts,
                "prohibitions": [],
            }
        ],
    }
    if importance:
        value["importance_level"] = importance
    return value


def manifest() -> dict:
    assets = [
        asset("G01", "G", [prompt("G01-v1-style")]),
        asset(
            "C01",
            "C",
            [prompt("C01-v1-face"), prompt("C01-v1-fullbody", deps=("C01-v1-face",))],
            "A",
        ),
        asset("W01", "W", [prompt("W01-v1-costume")]),
        asset("S01", "S", [prompt("S01-v1-master")], "B"),
        asset("P01", "P", [prompt("P01-v1-prop")]),
        asset("P02", "P", [prompt("P02-v1-optional")]),
        asset("A-VO-01", "A", [prompt("A-VO-01-v1", media="audio")]),
    ]
    return {
        "schema_version": "story-asset-manifest/v2",
        "title": "fixture",
        "input_summary": "",
        "constraints": [],
        "aliases": [],
        "pending_questions": [],
        "reference_inputs": [],
        "asset_type_coverage": [],
        "assets": assets,
        "entities": [
            {
                "id": "character:C01",
                "type": "character",
                "name": "主角",
                "description": "主角",
                "common_asset_refs": [
                    {"asset_id": "C01", "version": "v1", "relation_label": "identity"},
                    {"asset_id": "W01", "version": "v1", "relation_label": "costume"},
                ],
                "states": [],
            }
        ],
        "standalone_asset_refs": [],
        "continuity": [
            {
                "stage_id": "stage-01",
                "label": "one",
                "source_locator": "one",
                "asset_refs": [{"asset_id": "P01", "version": "v1", "relation_label": "prop"}],
            },
            {
                "stage_id": "stage-02",
                "label": "two",
                "source_locator": "two",
                "asset_refs": [{"asset_id": "P01", "version": "v1", "relation_label": "prop"}],
            },
        ],
        "quality_checks": [],
    }


class AssetManagerTests(unittest.TestCase):
    def test_default_selection_uses_core_assets_and_dependency_closure(self) -> None:
        data = MANAGER.plan(manifest())
        selected = {
            entry["prompt_id"]
            for entry in data["production"]["selection"]
            if entry["selected"]
        }
        self.assertEqual(
            {
                "G01-v1-style",
                "C01-v1-face",
                "C01-v1-fullbody",
                "W01-v1-costume",
                "S01-v1-master",
                "P01-v1-prop",
            },
            selected,
        )
        self.assertNotIn("P02-v1-optional", selected)
        self.assertTrue(all("A-VO" not in entry["prompt_id"] for entry in data["production"]["selection"]))

    def test_approve_can_add_optional_and_queue_is_topological(self) -> None:
        data = MANAGER.approve(MANAGER.plan(manifest()), {"P02-v1-optional"}, set())
        queue = MANAGER.queue(data)
        positions = {entry["prompt_id"]: index for index, entry in enumerate(queue)}
        self.assertLess(positions["C01-v1-face"], positions["C01-v1-fullbody"])
        self.assertIn("P02-v1-optional", positions)
        self.assertEqual("approved", data["production"]["selection_status"])

    def test_failure_blocks_dependents_and_ready_requires_core_outputs(self) -> None:
        data = MANAGER.approve(MANAGER.plan(manifest()), set(), set())
        data = MANAGER.record(data, "C01-v1-face", "failed", None, "generation failed")
        states = {entry["prompt_id"]: entry["state"] for entry in MANAGER.queue(data)}
        self.assertEqual("failed", states["C01-v1-face"])
        self.assertEqual("blocked", states["C01-v1-fullbody"])
        self.assertEqual("blocked", MANAGER.readiness(data)[0])

    def test_succeeded_uri_is_checked_and_complete_selection_becomes_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "assets.json"
            data = MANAGER.approve(MANAGER.plan(manifest()), set(), set())
            for entry in MANAGER.selected_entries(data):
                path = root / f"{entry['prompt_id']}.png"
                path.write_bytes(b"png")
                data = MANAGER.record(
                    data, entry["prompt_id"], "succeeded", path.name, None
                )
            self.assertEqual("ready", MANAGER.readiness(data)[0])
            self.assertEqual([], MANAGER.validate_production(data, manifest_path, True))

    def test_unknown_dependency_and_duplicate_outputs_are_rejected(self) -> None:
        data = manifest()
        data["assets"][0]["versions"][0]["prompts"][0]["input_refs"] = [
            {"source_kind": "prompt_output", "ref_id": "MISSING", "role": "style"}
        ]
        with self.assertRaises(MANAGER.AssetError):
            MANAGER.index_manifest(data)

    def test_scene_coverage_gate_requires_panorama_and_dependent_nine_grid(self) -> None:
        data = manifest()
        scene = next(item for item in data["assets"] if item["id"] == "S01")
        scene["versions"][0]["prompts"] = [
            prompt(
                "S01-v1-panorama",
                production_role="scene_panorama",
                layout="single_panorama",
            ),
            prompt(
                "S01-v1-coverage-grid",
                deps=("S01-v1-panorama",),
                production_role="scene_coverage_grid",
                layout="nine_grid",
                dep_role="scene_geometry",
            ),
        ]
        self.assertEqual([], MANAGER.scene_coverage_issues(data))
        broken = copy.deepcopy(data)
        broken_scene = next(item for item in broken["assets"] if item["id"] == "S01")
        broken_scene["versions"][0]["prompts"][1]["input_refs"] = []
        self.assertTrue(any("scene_geometry" in issue for issue in MANAGER.scene_coverage_issues(broken)))

    def test_asset_report_is_offline_searchable_and_exportable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "assets.json"
            report_path = root / "assets-report.html"
            data = MANAGER.plan(manifest())
            report = MANAGER.render_asset_report_html(data, manifest_path, report_path)
            self.assertIn("<!doctype html>", report)
            self.assertIn('id="search"', report)
            self.assertIn('id="export"', report)
            self.assertIn('id="report-data"', report)
            self.assertNotIn("<script src=", report)
            self.assertNotIn("<link ", report)
            self.assertNotIn("{{", report)


if __name__ == "__main__":
    unittest.main()
