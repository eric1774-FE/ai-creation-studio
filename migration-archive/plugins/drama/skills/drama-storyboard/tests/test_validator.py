#!/usr/bin/env python3
"""Small dependency-free regression suite for storyboard validation."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SPEC = importlib.util.spec_from_file_location(
    "storyboard_validator", ROOT / "scripts" / "validate_storyboard_manifest.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def issue_codes(data: dict, severity: str | None = None) -> set[str]:
    return {
        issue.code
        for issue in VALIDATOR.validate_manifest(data)
        if severity is None or issue.severity == severity
    }


class ValidatorTests(unittest.TestCase):
    def test_schema_is_parseable_and_internal_refs_resolve(self) -> None:
        schema = json.loads(
            (ROOT / "references" / "storyboard-manifest-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            "https://json-schema.org/draft/2020-12/schema", schema["$schema"]
        )
        refs = []

        def walk(value: object) -> None:
            if isinstance(value, dict):
                if isinstance(value.get("$ref"), str):
                    refs.append(value["$ref"])
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(schema)
        for ref in refs:
            self.assertTrue(ref.startswith("#/$defs/"))
            self.assertIn(ref.removeprefix("#/$defs/"), schema["$defs"])

    def test_valid_compiled_manifest(self) -> None:
        data = load("valid_manifest.json")
        self.assertEqual([], VALIDATOR.validate_manifest(data))
        self.assertTrue(data["shots"][0]["visual_inference"]["is_inference"])
        self.assertIn("visual_inference", data["shots"][0]["risk_flags"])

    def test_invalid_manifest_reports_production_errors(self) -> None:
        codes = issue_codes(load("invalid_manifest.json"), "error")
        self.assertTrue(
            {
                "SCHEMA_VERSION",
                "PAGE_SIZE",
                "PHASE_REVISION",
                "DUPLICATE_ENTITY_ID",
                "DUPLICATE_REF_TAG",
                "UNKNOWN_LOCATION",
                "COLOR_TEMPERATURE",
                "DURATION",
                "ENTITY_REFERENCE",
                "MULTI_SUBJECT_ACTION",
                "AXIS_CROSSING",
                "EMPTY_PROMPT",
                "VENDOR_TOKEN",
            }.issubset(codes)
        )

    def test_end_frame_capability_is_enforced(self) -> None:
        data = load("valid_manifest.json")
        data["project"]["generation_path"] = "i2v_start_end"
        for shot in data["shots"]:
            shot["generation_mode"] = "i2v_start_end"
            shot["prompt_layers"]["end_keyframe_prompt"] = (
                "{{CHAR_SHENLING_BLACK_COAT}}与{{PROP_CANDLE}}位于"
                "{{LOC_GRAVEYARD}}，动作到达结束状态；保持墓碑左后方四十五度，"
                "高于人物视线的4300K主光"
            )
        data["project"]["capabilities"]["supports_end_frame"] = True
        self.assertEqual(set(), issue_codes(data, "error"))
        data["project"]["capabilities"]["supports_end_frame"] = False
        self.assertIn("CAPABILITY_END_FRAME", issue_codes(data, "error"))

    def test_jump_cut_warning_and_explicit_exemption(self) -> None:
        data = load("valid_manifest.json")
        second = data["shots"][1]
        second["composition"]["azimuth_deg"] = 10
        second["composition"]["shot_size"] = "medium_close"
        self.assertIn("JUMP_CUT_RISK", issue_codes(data, "warning"))
        second["continuity"]["cut_type"] = "match_cut"
        self.assertNotIn("JUMP_CUT_RISK", issue_codes(data, "warning"))

    def test_three_phase_revision_lock(self) -> None:
        data = load("valid_manifest.json")
        for shot in data["shots"]:
            shot["prompt_layers"] = None
        data["workflow"].update(
            phase_status="draft_skeleton",
            approved_revision=None,
            compiled_from_revision=None,
        )
        self.assertNotIn("PHASE_REVISION", issue_codes(data, "error"))
        data["workflow"].update(
            phase_status="approved_skeleton",
            approved_revision=1,
            compiled_from_revision=None,
        )
        self.assertNotIn("PHASE_REVISION", issue_codes(data, "error"))
        data["workflow"]["skeleton_revision"] = 2
        self.assertIn("PHASE_REVISION", issue_codes(data, "error"))

    def test_sixty_second_twenty_five_shot_draft_and_paging(self) -> None:
        data = load("valid_manifest.json")
        data["project"]["target_duration_s"] = 60
        data["project"]["generation_path"] = "t2v"
        data["project"]["capabilities"] = {
            "supports_input_image": False,
            "supports_end_frame": False,
            "supports_video_extend": False,
            "profile_note": "文本生视频",
        }
        data["workflow"]["phase_status"] = "draft_skeleton"
        data["workflow"]["approved_revision"] = None
        data["workflow"]["compiled_from_revision"] = None
        template = data["shots"][0]
        shots = []
        for index in range(25):
            shot = copy.deepcopy(template)
            shot["shot_id"] = f"SHOT_{index + 1:03d}"
            shot["order"] = index + 1
            shot["duration_s"] = 2.4
            shot["generation_mode"] = "t2v"
            shot["prompt_layers"] = None
            shot["continuity"]["previous_shot_id"] = (
                None if index == 0 else f"SHOT_{index:03d}"
            )
            shot["continuity"]["cut_type"] = "match_cut"
            shots.append(shot)
        data["shots"] = shots
        self.assertEqual([], VALIDATOR.validate_manifest(data))
        self.assertEqual(3, (len(shots) + data["project"]["chat_page_size"] - 1) // data["project"]["chat_page_size"])

    def test_world_and_screen_vector_mismatches_are_separate(self) -> None:
        data = load("valid_manifest.json")
        first_end = data["shots"][0]["motion"]["motion_bounds"]["end_state"]
        second_start = data["shots"][1]["motion"]["motion_bounds"]["start_state"]
        first_end["world_vector"] = "toward_window"
        second_start["world_vector"] = "toward_door"
        first_end["screen_vector"] = "left_to_right"
        second_start["screen_vector"] = "right_to_left"
        codes = issue_codes(data, "warning")
        self.assertIn("WORLD_VECTOR_MISMATCH", codes)
        self.assertIn("SCREEN_VECTOR_MISMATCH", codes)

    def test_compiled_prompts_inherit_world_space_light_anchor(self) -> None:
        data = load("valid_manifest.json")
        data["shots"][0]["prompt_layers"]["motion_prompt"] = (
            "{{CHAR_SHENLING_BLACK_COAT}}靠近{{PROP_CANDLE}}，保持原有光线"
        )
        self.assertIn("MISSING_LIGHT_ANCHOR", issue_codes(data, "error"))

    def test_three_person_establishing_shot_is_allowed_but_three_actions_are_not(self) -> None:
        data = load("valid_manifest.json")
        for suffix, name in (("B", "角色乙"), ("C", "角色丙")):
            data["entities"].append(
                {
                    "entity_id": f"CHAR_{suffix}",
                    "entity_type": "character",
                    "name": name,
                    "ref_tag": f"{{{{CHAR_{suffix}}}}}",
                    "description": name,
                    "asset_refs": [],
                    "variants": [],
                }
            )
        shot = data["shots"][0]
        shot["entity_refs"].extend(
            [
                {"entity_id": "CHAR_B", "variant_id": None, "role": "secondary"},
                {"entity_id": "CHAR_C", "variant_id": None, "role": "secondary"},
            ]
        )
        shot["prompt_layers"]["keyframe_prompt"] += " {{CHAR_B}}与{{CHAR_C}}静止站在后景。"
        shot["prompt_layers"]["delivery_prompt"] += " {{CHAR_B}}与{{CHAR_C}}静止站在后景。"
        shot["motion"]["complex_action_subjects"] = 0
        self.assertNotIn("MULTI_SUBJECT_ACTION", issue_codes(data, "error"))
        shot["motion"]["complex_action_subjects"] = 3
        self.assertIn("MULTI_SUBJECT_ACTION", issue_codes(data, "error"))

    def test_representative_story_types_fit_the_contract(self) -> None:
        cases = {
            "ordinary_narrative": ("他推门回到客栈。", 1, []),
            "two_person_dialogue": (
                "你来迟了。门外的人没有回答。",
                1,
                [{"speaker_entity_id": "CHAR_SHENLING", "text": "你来迟了。"}],
            ),
            "emotion": ("他低下头，把信纸攥出折痕。", 1, []),
            "suspense": ("门缝下缓慢渗进一线红光。", 1, []),
            "close_combat": ("两人同时近身，一人横挡，一人收刀。", 2, []),
            "large_vfx": ("城外雷云合拢，光柱贯穿地面。", 1, []),
        }
        for label, (source_text, complex_subjects, dialogue) in cases.items():
            with self.subTest(label=label):
                data = load("valid_manifest.json")
                shot = data["shots"][0]
                shot["source_text"] = source_text
                shot["motion"]["complex_action_subjects"] = complex_subjects
                shot["audio"]["dialogue"] = dialogue
                self.assertEqual(set(), issue_codes(data, "error"))


if __name__ == "__main__":
    unittest.main()
