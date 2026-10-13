#!/usr/bin/env python3
"""Validate storyboard-manifest/v1 without third-party dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


TAG_RE = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
ANY_TAG_RE = re.compile(r"\{\{[^{}]+\}\}")
VENDOR_TOKEN_RE = re.compile(r"@[A-Za-z_][A-Za-z0-9_.-]*")
SHOT_SIZE_RANK = {
    "extreme_wide": 0,
    "wide": 1,
    "full": 2,
    "medium_full": 3,
    "medium": 4,
    "medium_close": 5,
    "close_up": 6,
    "extreme_close_up": 7,
}
ENTITY_PREFIX = {"character": "CHAR_", "location": "LOC_", "prop": "PROP_"}
COMPILED_PROMPT_FIELDS = ("keyframe_prompt", "motion_prompt", "delivery_prompt")


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    path: str
    message: str


def add(issues: list[Issue], severity: str, code: str, path: str, message: str) -> None:
    issues.append(Issue(severity, code, path, message))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def as_object(
    value: Any, issues: list[Issue], path: str, required: tuple[str, ...] = ()
) -> dict[str, Any]:
    if not isinstance(value, dict):
        add(issues, "error", "TYPE_OBJECT", path, "must be an object")
        return {}
    for key in required:
        if key not in value:
            add(issues, "error", "REQUIRED_FIELD", f"{path}.{key}", "is required")
    return value


def as_list(value: Any, issues: list[Issue], path: str) -> list[Any]:
    if not isinstance(value, list):
        add(issues, "error", "TYPE_ARRAY", path, "must be an array")
        return []
    return value


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def angular_difference(a: Any, b: Any) -> float | None:
    if not is_number(a) or not is_number(b):
        return None
    raw = abs(float(a) - float(b)) % 360
    return min(raw, 360 - raw)


def effective_entity_tag(
    use: dict[str, Any], entities: dict[str, dict[str, Any]]
) -> tuple[str | None, str | None]:
    entity_id = use.get("entity_id")
    entity = entities.get(entity_id)
    if not entity:
        return None, f"unknown entity {entity_id!r}"
    variant_id = use.get("variant_id")
    if variant_id is None:
        return entity.get("ref_tag"), None
    for variant in entity.get("variants", []):
        if isinstance(variant, dict) and variant.get("variant_id") == variant_id:
            return variant.get("ref_tag"), None
    return None, f"unknown variant {variant_id!r} for entity {entity_id!r}"


def validate_manifest(data: Any) -> list[Issue]:
    issues: list[Issue] = []
    root = as_object(
        data,
        issues,
        "$",
        ("schema_version", "project", "workflow", "entities", "scenes", "shots"),
    )
    if root.get("schema_version") != "storyboard-manifest/v1":
        add(
            issues,
            "error",
            "SCHEMA_VERSION",
            "$.schema_version",
            "must equal storyboard-manifest/v1",
        )

    project = as_object(
        root.get("project"),
        issues,
        "$.project",
        (
            "project_id",
            "title",
            "language",
            "aspect_ratio",
            "target_duration_s",
            "visual_style",
            "generation_path",
            "capabilities",
        ),
    )
    target_duration = project.get("target_duration_s")
    if not is_number(target_duration) or target_duration <= 0:
        add(issues, "error", "DURATION", "$.project.target_duration_s", "must be positive")
    page_size = project.get("chat_page_size", 10)
    if not isinstance(page_size, int) or isinstance(page_size, bool) or not 1 <= page_size <= 10:
        add(issues, "error", "PAGE_SIZE", "$.project.chat_page_size", "must be 1..10")
    generation_path = project.get("generation_path")
    allowed_paths = {"t2v", "i2v_start", "i2v_start_end", "video_extend", "mixed"}
    if generation_path not in allowed_paths:
        add(issues, "error", "GENERATION_PATH", "$.project.generation_path", "is invalid")
    capabilities = as_object(
        project.get("capabilities"),
        issues,
        "$.project.capabilities",
        ("supports_input_image", "supports_end_frame", "supports_video_extend"),
    )

    workflow = as_object(
        root.get("workflow"),
        issues,
        "$.workflow",
        (
            "phase_status",
            "source_digest",
            "skeleton_revision",
            "approved_revision",
            "compiled_from_revision",
        ),
    )
    phase = workflow.get("phase_status")
    revision = workflow.get("skeleton_revision")
    approved_revision = workflow.get("approved_revision")
    compiled_revision = workflow.get("compiled_from_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        add(issues, "error", "REVISION", "$.workflow.skeleton_revision", "must be >= 1")
    digest = workflow.get("source_digest")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        add(issues, "error", "SOURCE_DIGEST", "$.workflow.source_digest", "must be sha256:<64 lowercase hex>")
    if phase == "draft_skeleton":
        if approved_revision is not None or compiled_revision is not None:
            add(issues, "error", "PHASE_REVISION", "$.workflow", "draft skeleton cannot be approved or compiled")
    elif phase == "approved_skeleton":
        if approved_revision != revision or compiled_revision is not None:
            add(issues, "error", "PHASE_REVISION", "$.workflow", "approved revision must equal skeleton revision and compiled revision must be null")
    elif phase == "compiled":
        if approved_revision != revision or compiled_revision != approved_revision:
            add(issues, "error", "PHASE_REVISION", "$.workflow", "compiled output must use the currently approved skeleton revision")
    else:
        add(issues, "error", "PHASE_STATUS", "$.workflow.phase_status", "is invalid")

    entity_items = as_list(root.get("entities"), issues, "$.entities")
    entities: dict[str, dict[str, Any]] = {}
    declared_tags: set[str] = set()
    variant_ids: set[str] = set()
    asset_ids: set[str] = set()
    for index, raw_entity in enumerate(entity_items):
        path = f"$.entities[{index}]"
        entity = as_object(
            raw_entity,
            issues,
            path,
            ("entity_id", "entity_type", "name", "ref_tag", "description", "asset_refs", "variants"),
        )
        entity_id = entity.get("entity_id")
        entity_type = entity.get("entity_type")
        if not nonempty(entity_id):
            add(issues, "error", "ENTITY_ID", f"{path}.entity_id", "must be non-empty")
        elif entity_id in entities:
            add(issues, "error", "DUPLICATE_ENTITY_ID", f"{path}.entity_id", f"duplicate {entity_id}")
        else:
            entities[entity_id] = entity
        expected_prefix = ENTITY_PREFIX.get(entity_type)
        if expected_prefix and isinstance(entity_id, str) and not entity_id.startswith(expected_prefix):
            add(issues, "warning", "ENTITY_PREFIX", f"{path}.entity_id", f"{entity_type} IDs should start with {expected_prefix}")
        tag = entity.get("ref_tag")
        if not isinstance(tag, str) or not TAG_RE.fullmatch(tag):
            add(issues, "error", "REF_TAG_FORMAT", f"{path}.ref_tag", "must use {{UPPER_SNAKE_CASE}}")
        elif tag in declared_tags:
            add(issues, "error", "DUPLICATE_REF_TAG", f"{path}.ref_tag", f"duplicate {tag}")
        else:
            declared_tags.add(tag)
        for asset_index, asset in enumerate(as_list(entity.get("asset_refs"), issues, f"{path}.asset_refs")):
            asset_path = f"{path}.asset_refs[{asset_index}]"
            asset_obj = as_object(asset, issues, asset_path, ("asset_id", "role", "uri"))
            asset_id = asset_obj.get("asset_id")
            if asset_id in asset_ids:
                add(issues, "error", "DUPLICATE_ASSET_ID", f"{asset_path}.asset_id", f"duplicate {asset_id}")
            elif nonempty(asset_id):
                asset_ids.add(asset_id)
        for variant_index, raw_variant in enumerate(as_list(entity.get("variants"), issues, f"{path}.variants")):
            variant_path = f"{path}.variants[{variant_index}]"
            variant = as_object(raw_variant, issues, variant_path, ("variant_id", "name", "ref_tag", "description", "asset_refs"))
            variant_id = variant.get("variant_id")
            if variant_id in variant_ids:
                add(issues, "error", "DUPLICATE_VARIANT_ID", f"{variant_path}.variant_id", f"duplicate {variant_id}")
            elif nonempty(variant_id):
                variant_ids.add(variant_id)
            variant_tag = variant.get("ref_tag")
            if not isinstance(variant_tag, str) or not TAG_RE.fullmatch(variant_tag):
                add(issues, "error", "REF_TAG_FORMAT", f"{variant_path}.ref_tag", "must use {{UPPER_SNAKE_CASE}}")
            elif variant_tag in declared_tags:
                add(issues, "error", "DUPLICATE_REF_TAG", f"{variant_path}.ref_tag", f"duplicate {variant_tag}")
            else:
                declared_tags.add(variant_tag)
            for asset_index, asset in enumerate(as_list(variant.get("asset_refs"), issues, f"{variant_path}.asset_refs")):
                asset_path = f"{variant_path}.asset_refs[{asset_index}]"
                asset_obj = as_object(asset, issues, asset_path, ("asset_id", "role", "uri"))
                asset_id = asset_obj.get("asset_id")
                if asset_id in asset_ids:
                    add(issues, "error", "DUPLICATE_ASSET_ID", f"{asset_path}.asset_id", f"duplicate {asset_id}")
                elif nonempty(asset_id):
                    asset_ids.add(asset_id)

    scene_items = as_list(root.get("scenes"), issues, "$.scenes")
    scenes: dict[str, dict[str, Any]] = {}
    for index, raw_scene in enumerate(scene_items):
        path = f"$.scenes[{index}]"
        scene = as_object(
            raw_scene,
            issues,
            path,
            ("scene_id", "location_entity_id", "summary", "time_of_day", "weather", "axis", "lighting", "spatial_relations"),
        )
        scene_id = scene.get("scene_id")
        if scene_id in scenes:
            add(issues, "error", "DUPLICATE_SCENE_ID", f"{path}.scene_id", f"duplicate {scene_id}")
        elif nonempty(scene_id):
            scenes[scene_id] = scene
        location_id = scene.get("location_entity_id")
        location = entities.get(location_id)
        if not location:
            add(issues, "error", "UNKNOWN_LOCATION", f"{path}.location_entity_id", f"unknown entity {location_id!r}")
        elif location.get("entity_type") != "location":
            add(issues, "error", "LOCATION_TYPE", f"{path}.location_entity_id", "must reference a location entity")
        lighting = as_object(scene.get("lighting"), issues, f"{path}.lighting", ("key_direction_world", "color_temperature_k", "quality", "ambient"))
        kelvin = lighting.get("color_temperature_k")
        if not isinstance(kelvin, int) or isinstance(kelvin, bool) or not 1000 <= kelvin <= 20000:
            add(issues, "error", "COLOR_TEMPERATURE", f"{path}.lighting.color_temperature_k", "must be 1000..20000")

    shot_items = as_list(root.get("shots"), issues, "$.shots")
    shots: dict[str, dict[str, Any]] = {}
    orders: set[int] = set()
    total_duration = 0.0
    for index, raw_shot in enumerate(shot_items):
        path = f"$.shots[{index}]"
        shot = as_object(
            raw_shot,
            issues,
            path,
            (
                "shot_id",
                "scene_id",
                "order",
                "source_text",
                "duration_s",
                "purpose",
                "generation_mode",
                "entity_refs",
                "composition",
                "camera",
                "motion",
                "audio",
                "continuity",
                "visual_inference",
                "prompt_layers",
                "risk_flags",
            ),
        )
        shot_id = shot.get("shot_id")
        if shot_id in shots:
            add(issues, "error", "DUPLICATE_SHOT_ID", f"{path}.shot_id", f"duplicate {shot_id}")
        elif nonempty(shot_id):
            shots[shot_id] = shot
        scene_id = shot.get("scene_id")
        if scene_id not in scenes:
            add(issues, "error", "UNKNOWN_SCENE", f"{path}.scene_id", f"unknown scene {scene_id!r}")
        order = shot.get("order")
        if not isinstance(order, int) or isinstance(order, bool) or order < 1:
            add(issues, "error", "SHOT_ORDER", f"{path}.order", "must be a positive integer")
        elif order in orders:
            add(issues, "error", "DUPLICATE_SHOT_ORDER", f"{path}.order", f"duplicate order {order}")
        else:
            orders.add(order)
        duration = shot.get("duration_s")
        if not is_number(duration) or duration <= 0:
            add(issues, "error", "DURATION", f"{path}.duration_s", "must be positive")
        else:
            total_duration += float(duration)

        mode = shot.get("generation_mode")
        if generation_path != "mixed" and mode != generation_path:
            add(issues, "error", "GENERATION_MODE", f"{path}.generation_mode", f"must match project path {generation_path!r}")
        if mode in {"i2v_start", "i2v_start_end"} and capabilities.get("supports_input_image") is not True:
            add(issues, "error", "CAPABILITY_INPUT_IMAGE", f"{path}.generation_mode", "requires input-image support")
        if mode == "i2v_start_end" and capabilities.get("supports_end_frame") is not True:
            add(issues, "error", "CAPABILITY_END_FRAME", f"{path}.generation_mode", "requires end-frame support")
        if mode == "video_extend" and capabilities.get("supports_video_extend") is not True:
            add(issues, "error", "CAPABILITY_EXTEND", f"{path}.generation_mode", "requires video-extension support")

        entity_uses = as_list(shot.get("entity_refs"), issues, f"{path}.entity_refs")
        effective_tags: set[str] = set()
        motion_required_tags: set[str] = set()
        primary_entities: set[str] = set()
        seen_uses: set[tuple[Any, Any]] = set()
        for use_index, raw_use in enumerate(entity_uses):
            use_path = f"{path}.entity_refs[{use_index}]"
            use = as_object(raw_use, issues, use_path, ("entity_id", "variant_id", "role"))
            key = (use.get("entity_id"), use.get("variant_id"))
            if key in seen_uses:
                add(issues, "warning", "DUPLICATE_ENTITY_USE", use_path, f"duplicate entity use {key}")
            seen_uses.add(key)
            tag, error = effective_entity_tag(use, entities)
            if error:
                add(issues, "error", "ENTITY_REFERENCE", use_path, error)
            elif tag:
                effective_tags.add(tag)
                if use.get("role") in {"primary", "prop"}:
                    motion_required_tags.add(tag)
            if use.get("role") == "primary" and nonempty(use.get("entity_id")):
                primary_entities.add(use["entity_id"])

        scene = scenes.get(scene_id, {})
        location = entities.get(scene.get("location_entity_id"), {})
        location_tag = location.get("ref_tag")
        if isinstance(location_tag, str):
            effective_tags.add(location_tag)

        motion = as_object(
            shot.get("motion"),
            issues,
            f"{path}.motion",
            ("primary_action_goal", "complex_action_subjects", "motion_bounds", "motion_beats"),
        )
        complex_subjects = motion.get("complex_action_subjects")
        if not isinstance(complex_subjects, int) or isinstance(complex_subjects, bool) or complex_subjects < 0:
            add(issues, "error", "COMPLEX_SUBJECTS", f"{path}.motion.complex_action_subjects", "must be a non-negative integer")
        elif complex_subjects > 2:
            add(issues, "error", "MULTI_SUBJECT_ACTION", f"{path}.motion.complex_action_subjects", "a generative shot cannot choreograph more than two independent complex actors")
        bounds = as_object(motion.get("motion_bounds"), issues, f"{path}.motion.motion_bounds", ("start_state", "end_state"))
        for state_name in ("start_state", "end_state"):
            state_path = f"{path}.motion.motion_bounds.{state_name}"
            state = as_object(
                bounds.get(state_name),
                issues,
                state_path,
                ("frame_zone", "body_pose", "facing", "center_of_gravity", "hand_prop_state", "world_vector", "screen_vector", "summary"),
            )
            for key in ("body_pose", "facing", "center_of_gravity", "hand_prop_state", "world_vector", "summary"):
                if not nonempty(state.get(key)):
                    add(issues, "error", "MOTION_STATE", f"{state_path}.{key}", "must be non-empty")
        beats = as_list(motion.get("motion_beats"), issues, f"{path}.motion.motion_beats")
        beat_orders: set[int] = set()
        for beat_index, raw_beat in enumerate(beats):
            beat_path = f"{path}.motion.motion_beats[{beat_index}]"
            beat = as_object(raw_beat, issues, beat_path, ("order", "description"))
            beat_order = beat.get("order")
            if beat_order in beat_orders:
                add(issues, "error", "DUPLICATE_BEAT_ORDER", f"{beat_path}.order", f"duplicate beat order {beat_order}")
            elif isinstance(beat_order, int) and not isinstance(beat_order, bool):
                beat_orders.add(beat_order)
        if len(beats) > 5:
            add(issues, "warning", "ACTION_OVERLOAD", f"{path}.motion.motion_beats", "more than five beats may overload one generated clip")

        audio = as_object(shot.get("audio"), issues, f"{path}.audio", ("voiceover", "dialogue", "ambience", "sfx", "music_intent"))
        for line_index, raw_line in enumerate(as_list(audio.get("dialogue"), issues, f"{path}.audio.dialogue")):
            line_path = f"{path}.audio.dialogue[{line_index}]"
            line = as_object(raw_line, issues, line_path, ("speaker_entity_id", "text"))
            speaker = entities.get(line.get("speaker_entity_id"))
            if not speaker:
                add(issues, "error", "DIALOGUE_SPEAKER", f"{line_path}.speaker_entity_id", "must reference an entity")
            elif speaker.get("entity_type") != "character":
                add(issues, "error", "DIALOGUE_SPEAKER", f"{line_path}.speaker_entity_id", "must reference a character")

        inference = as_object(shot.get("visual_inference"), issues, f"{path}.visual_inference", ("is_inference", "additions", "rationale"))
        additions = as_list(inference.get("additions"), issues, f"{path}.visual_inference.additions")
        is_inference = inference.get("is_inference")
        risk_flags = as_list(shot.get("risk_flags"), issues, f"{path}.risk_flags")
        if is_inference is True:
            if not additions or not nonempty(inference.get("rationale")):
                add(issues, "error", "VISUAL_INFERENCE", f"{path}.visual_inference", "inference requires additions and rationale")
            if "visual_inference" not in risk_flags:
                add(issues, "warning", "INFERENCE_FLAG", f"{path}.risk_flags", "visual inference should be flagged")
        elif additions:
            add(issues, "error", "VISUAL_INFERENCE", f"{path}.visual_inference.additions", "must be empty when is_inference is false")

        continuity = as_object(
            shot.get("continuity"),
            issues,
            f"{path}.continuity",
            ("previous_shot_id", "axis_crossing", "axis_strategy", "entry_exit", "eyeline", "action_match", "wardrobe_state", "prop_state", "lighting_override", "cut_type"),
        )
        if continuity.get("axis_crossing") is True and continuity.get("axis_strategy") == "none":
            add(issues, "error", "AXIS_CROSSING", f"{path}.continuity.axis_strategy", "axis crossing requires an explicit strategy")
        if continuity.get("axis_crossing") is False and continuity.get("axis_strategy") not in {"none", None}:
            add(issues, "warning", "AXIS_STRATEGY", f"{path}.continuity.axis_strategy", "strategy is set although axis_crossing is false")
        for field in ("entry_exit", "eyeline", "action_match", "wardrobe_state", "prop_state"):
            if not nonempty(continuity.get(field)):
                add(issues, "error", "CONTINUITY_STATE", f"{path}.continuity.{field}", "must be non-empty")
        lighting_override = continuity.get("lighting_override")
        if lighting_override is not None:
            override = as_object(lighting_override, issues, f"{path}.continuity.lighting_override", ("reason", "anchor"))
            if not nonempty(override.get("reason")):
                add(issues, "error", "LIGHTING_OVERRIDE", f"{path}.continuity.lighting_override.reason", "must explain the story-motivated light change")
            anchor = as_object(override.get("anchor"), issues, f"{path}.continuity.lighting_override.anchor", ("key_direction_world", "color_temperature_k", "quality", "ambient"))
            override_kelvin = anchor.get("color_temperature_k")
            if not isinstance(override_kelvin, int) or isinstance(override_kelvin, bool) or not 1000 <= override_kelvin <= 20000:
                add(issues, "error", "COLOR_TEMPERATURE", f"{path}.continuity.lighting_override.anchor.color_temperature_k", "must be 1000..20000")
            if "lighting_override" not in risk_flags:
                add(issues, "warning", "LIGHTING_OVERRIDE_FLAG", f"{path}.risk_flags", "lighting override should be flagged")

        prompts = shot.get("prompt_layers")
        if phase == "compiled":
            prompt_obj = as_object(
                prompts,
                issues,
                f"{path}.prompt_layers",
                ("keyframe_prompt", "motion_prompt", "end_keyframe_prompt", "delivery_prompt", "negative_constraints"),
            )
            for field in COMPILED_PROMPT_FIELDS:
                if not nonempty(prompt_obj.get(field)):
                    add(issues, "error", "EMPTY_PROMPT", f"{path}.prompt_layers.{field}", "must be non-empty in compiled phase")
            end_prompt = prompt_obj.get("end_keyframe_prompt")
            if mode == "i2v_start_end":
                if not nonempty(end_prompt):
                    add(issues, "error", "END_FRAME_PROMPT", f"{path}.prompt_layers.end_keyframe_prompt", "is required for i2v_start_end")
            elif end_prompt is not None:
                if capabilities.get("supports_end_frame") is not True:
                    add(issues, "error", "UNSUPPORTED_END_FRAME", f"{path}.prompt_layers.end_keyframe_prompt", "end-frame prompt is unsupported by this capability profile")
                else:
                    add(issues, "warning", "UNUSED_END_FRAME", f"{path}.prompt_layers.end_keyframe_prompt", "end-frame prompt is present but generation mode does not consume it")
            combined = "\n".join(str(prompt_obj.get(field) or "") for field in ("keyframe_prompt", "motion_prompt", "end_keyframe_prompt", "delivery_prompt"))
            if VENDOR_TOKEN_RE.search(combined):
                add(issues, "error", "VENDOR_TOKEN", f"{path}.prompt_layers", "canonical prompts cannot contain @vendor tokens")
            found_tags = set(ANY_TAG_RE.findall(combined))
            for tag in sorted(found_tags - declared_tags):
                add(issues, "error", "UNDECLARED_REF_TAG", f"{path}.prompt_layers", f"undeclared tag {tag}")
            for tag in sorted(effective_tags):
                if tag not in str(prompt_obj.get("keyframe_prompt", "")):
                    add(issues, "error", "MISSING_REF_TAG", f"{path}.prompt_layers.keyframe_prompt", f"missing {tag}")
                if tag not in str(prompt_obj.get("delivery_prompt", "")):
                    add(issues, "error", "MISSING_REF_TAG", f"{path}.prompt_layers.delivery_prompt", f"missing {tag}")
            for tag in sorted(motion_required_tags):
                if tag not in str(prompt_obj.get("motion_prompt", "")):
                    add(issues, "error", "MISSING_REF_TAG", f"{path}.prompt_layers.motion_prompt", f"missing {tag}")
            if mode == "i2v_start_end":
                for tag in sorted(effective_tags):
                    if tag not in str(prompt_obj.get("end_keyframe_prompt", "")):
                        add(issues, "error", "MISSING_REF_TAG", f"{path}.prompt_layers.end_keyframe_prompt", f"missing {tag}")
            active_lighting = scene.get("lighting") if isinstance(scene.get("lighting"), dict) else {}
            if isinstance(lighting_override, dict) and isinstance(lighting_override.get("anchor"), dict):
                active_lighting = lighting_override["anchor"]
            light_direction = active_lighting.get("key_direction_world")
            kelvin_token = str(active_lighting.get("color_temperature_k", ""))
            lighting_fields = ["keyframe_prompt", "motion_prompt", "delivery_prompt"]
            if mode == "i2v_start_end":
                lighting_fields.append("end_keyframe_prompt")
            for field in lighting_fields:
                prompt_text = str(prompt_obj.get(field) or "")
                if nonempty(light_direction) and light_direction not in prompt_text:
                    add(issues, "error", "MISSING_LIGHT_ANCHOR", f"{path}.prompt_layers.{field}", f"missing world-space light anchor {light_direction!r}")
                if kelvin_token and kelvin_token not in prompt_text:
                    add(issues, "error", "MISSING_LIGHT_ANCHOR", f"{path}.prompt_layers.{field}", f"missing color temperature {kelvin_token}K")
        elif prompts is not None:
            add(issues, "warning", "EARLY_PROMPTS", f"{path}.prompt_layers", "Phase 1 should avoid compiling full prompts before skeleton approval")

    if orders and orders != set(range(1, len(orders) + 1)):
        add(issues, "warning", "SHOT_ORDER_GAPS", "$.shots", "shot orders should be consecutive starting at 1")
    if is_number(target_duration) and abs(total_duration - float(target_duration)) > 0.5:
        add(
            issues,
            "warning",
            "TOTAL_DURATION",
            "$.shots",
            f"shot duration sum {total_duration:.3f}s differs from target {float(target_duration):.3f}s by more than 0.5s",
        )

    ordered_shots = sorted(
        (shot for shot in shots.values() if isinstance(shot.get("order"), int)),
        key=lambda item: item["order"],
    )
    for current in ordered_shots:
        shot_id = current.get("shot_id", "?")
        path = f"$.shots[{shot_id}]"
        continuity = current.get("continuity") if isinstance(current.get("continuity"), dict) else {}
        previous_id = continuity.get("previous_shot_id")
        if previous_id is None:
            if current.get("order") != 1:
                add(issues, "warning", "PREVIOUS_SHOT", f"{path}.continuity.previous_shot_id", "is null after the first shot")
            continue
        previous = shots.get(previous_id)
        if not previous:
            add(issues, "error", "UNKNOWN_PREVIOUS_SHOT", f"{path}.continuity.previous_shot_id", f"unknown shot {previous_id!r}")
            continue
        if isinstance(previous.get("order"), int) and previous["order"] >= current.get("order", 0):
            add(issues, "error", "PREVIOUS_SHOT_ORDER", f"{path}.continuity.previous_shot_id", "must reference an earlier shot")
        if previous.get("scene_id") != current.get("scene_id"):
            continue
        previous_motion = previous.get("motion") if isinstance(previous.get("motion"), dict) else {}
        current_motion = current.get("motion") if isinstance(current.get("motion"), dict) else {}
        previous_bounds = previous_motion.get("motion_bounds") if isinstance(previous_motion.get("motion_bounds"), dict) else {}
        current_bounds = current_motion.get("motion_bounds") if isinstance(current_motion.get("motion_bounds"), dict) else {}
        previous_end = previous_bounds.get("end_state") if isinstance(previous_bounds.get("end_state"), dict) else {}
        current_start = current_bounds.get("start_state") if isinstance(current_bounds.get("start_state"), dict) else {}
        previous_world = previous_end.get("world_vector")
        current_world = current_start.get("world_vector")
        if nonempty(previous_world) and nonempty(current_world) and previous_world != current_world and previous_world not in {"static", "none"} and current_world not in {"static", "none"}:
            add(issues, "warning", "WORLD_VECTOR_MISMATCH", f"{path}.motion.motion_bounds.start_state.world_vector", f"does not match {previous_id} end vector")
        previous_screen = previous_end.get("screen_vector")
        current_screen = current_start.get("screen_vector")
        if continuity.get("axis_crossing") is False and previous_screen != current_screen and previous_screen not in {None, "static", "mixed"} and current_screen not in {None, "static", "mixed"}:
            add(issues, "warning", "SCREEN_VECTOR_MISMATCH", f"{path}.motion.motion_bounds.start_state.screen_vector", f"reverses {previous_id} without an axis crossing")

        previous_primary = {
            use.get("entity_id")
            for use in previous.get("entity_refs", [])
            if isinstance(use, dict) and use.get("role") == "primary"
        }
        current_primary = {
            use.get("entity_id")
            for use in current.get("entity_refs", [])
            if isinstance(use, dict) and use.get("role") == "primary"
        }
        previous_comp = previous.get("composition") if isinstance(previous.get("composition"), dict) else {}
        current_comp = current.get("composition") if isinstance(current.get("composition"), dict) else {}
        angle_change = angular_difference(previous_comp.get("azimuth_deg"), current_comp.get("azimuth_deg"))
        previous_rank = SHOT_SIZE_RANK.get(previous_comp.get("shot_size"))
        current_rank = SHOT_SIZE_RANK.get(current_comp.get("shot_size"))
        cut_type = continuity.get("cut_type")
        if (
            previous_primary & current_primary
            and angle_change is not None
            and angle_change < 30
            and previous_rank is not None
            and current_rank is not None
            and abs(previous_rank - current_rank) < 2
            and cut_type == "standard"
        ):
            add(issues, "warning", "JUMP_CUT_RISK", f"{path}.continuity.cut_type", "same subject changes less than 30 degrees and fewer than two shot-size levels")

    return issues


def digest_source(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable issues")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failure")
    args = parser.parse_args(argv)

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.manifest}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
        return 1

    issues = validate_manifest(data)
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    if args.json_output:
        print(json.dumps({"valid": not errors, "errors": len(errors), "warnings": len(warnings), "issues": [asdict(issue) for issue in issues]}, ensure_ascii=False, indent=2))
    else:
        for issue in issues:
            print(f"[{issue.severity.upper()}] {issue.code} {issue.path}: {issue.message}")
        print(f"Validation complete: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
