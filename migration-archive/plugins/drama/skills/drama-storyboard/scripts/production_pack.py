#!/usr/bin/env python3
"""Prepare, validate, render, and export generic drama production packs."""

from __future__ import annotations

import argparse
import copy
import html
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


PRODUCTION_VERSION = "production-extension/v1"
PACK_VERSION = "drama-production-pack/v1"
TAG_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
SEGMENT_BREAK_CUTS = {"scene_change", "time_jump", "montage_break"}
REFERENCE_ROLES = {"style", "identity", "costume", "scene", "prop", "environment", "effect"}
SCENE_PURPOSES = {
    "scene_panorama": "场景身份与整体空间结构",
    "scene_coverage_grid": "机位与正反打空间连续性；只作参考，不复制九宫格或拼贴版式",
}

VALIDATOR_PATH = Path(__file__).with_name("validate_storyboard_manifest.py")
VALIDATOR_SPEC = importlib.util.spec_from_file_location("storyboard_validator", VALIDATOR_PATH)
assert VALIDATOR_SPEC and VALIDATOR_SPEC.loader
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
sys.modules[VALIDATOR_SPEC.name] = VALIDATOR
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


class ProductionError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProductionError(f"无法读取 UTF-8 JSON：{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProductionError(f"{path} 根节点必须是对象")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def resolve_local_uri(uri: str, base: Path) -> Path | None:
    if uri.startswith(("http://", "https://")):
        return None
    path = Path(uri)
    return path if path.is_absolute() else base / path


def tag_map(storyboard: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for entity in storyboard.get("entities", []):
        if not isinstance(entity, dict):
            continue
        name = str(entity.get("name") or entity.get("entity_id") or "未命名实体")
        description = str(entity.get("description") or "").strip()
        label = f"{name}（{description}）" if description else name
        if nonempty(entity.get("ref_tag")):
            result[entity["ref_tag"]] = label
        for variant in entity.get("variants", []):
            if not isinstance(variant, dict) or not nonempty(variant.get("ref_tag")):
                continue
            variant_name = str(variant.get("name") or variant.get("variant_id") or "造型")
            variant_description = str(variant.get("description") or "").strip()
            variant_label = f"{name}·{variant_name}"
            if variant_description:
                variant_label += f"（{variant_description}）"
            result[variant["ref_tag"]] = variant_label
    return result


def resolve_tags(value: str, mapping: dict[str, str]) -> tuple[str, list[str]]:
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        if tag not in mapping:
            missing.append(tag)
            return tag
        return mapping[tag]

    return TAG_RE.sub(replace, value), missing


def entity_names(storyboard: dict[str, Any]) -> dict[str, str]:
    return {
        entity.get("entity_id"): entity.get("name", entity.get("entity_id"))
        for entity in storyboard.get("entities", [])
        if isinstance(entity, dict) and nonempty(entity.get("entity_id"))
    }


def asset_prompt_index(assets: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not assets:
        return result
    for asset in assets.get("assets", []):
        if not isinstance(asset, dict):
            continue
        for version in asset.get("versions", []):
            if not isinstance(version, dict):
                continue
            for prompt in version.get("prompts", []):
                if isinstance(prompt, dict) and nonempty(prompt.get("id")):
                    result[prompt["id"]] = {
                        "asset": asset,
                        "version": version,
                        "prompt": prompt,
                    }
    return result


def asset_output_index(assets: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not assets or not isinstance(assets.get("production"), dict):
        return {}
    return {
        item.get("prompt_id"): item
        for item in assets["production"].get("outputs", [])
        if isinstance(item, dict) and nonempty(item.get("prompt_id"))
    }


def selected_core_missing(assets: dict[str, Any] | None) -> list[str]:
    if not assets or not isinstance(assets.get("production"), dict):
        return []
    outputs = asset_output_index(assets)
    return [
        entry.get("prompt_id")
        for entry in assets["production"].get("selection", [])
        if isinstance(entry, dict)
        and entry.get("selected")
        and entry.get("tier") == "core"
        and outputs.get(entry.get("prompt_id"), {}).get("status") != "succeeded"
    ]


def legacy_imports(storyboard: dict[str, Any], storyboard_path: Path) -> list[dict[str, Any]]:
    extensions = storyboard.get("extensions")
    if not isinstance(extensions, dict):
        return []
    existing = extensions.get("production_v1")
    if isinstance(existing, dict) and isinstance(existing.get("legacy_imports"), list):
        result = copy.deepcopy(existing["legacy_imports"])
        for item in result:
            if isinstance(item, dict):
                item.setdefault("source_base", str(storyboard_path.parent))
        return result
    result: list[dict[str, Any]] = []
    for index, item in enumerate(extensions.get("manual_continuity_assets", []), start=1):
        if not isinstance(item, dict) or not nonempty(item.get("uri")):
            continue
        result.append(
            {
                "legacy_asset_id": f"LEGACY-{index:03d}",
                "uri": item["uri"],
                "purpose": item.get("purpose", "旧版人工连续性资源"),
                "binding": "legacy_manual",
                "source_base": str(storyboard_path.parent),
            }
        )
    return result


def normalize_bindings(
    production: dict[str, Any],
    assets: dict[str, Any] | None,
    storyboard_path: Path,
    asset_path: Path | None,
) -> list[dict[str, Any]]:
    output_index = asset_output_index(assets)
    prompt_index = asset_prompt_index(assets)
    result: list[dict[str, Any]] = []
    for binding in production.get("shot_asset_bindings", []):
        if not isinstance(binding, dict) or not nonempty(binding.get("shot_id")):
            continue
        references: list[dict[str, Any]] = []
        for raw_reference in binding.get("references", []):
            if not isinstance(raw_reference, dict):
                continue
            reference = copy.deepcopy(raw_reference)
            prompt_id = reference.get("prompt_id")
            output = output_index.get(prompt_id, {})
            info = prompt_index.get(prompt_id, {})
            if not nonempty(reference.get("uri")) and output.get("status") == "succeeded":
                reference["uri"] = output.get("uri")
                reference["source_manifest"] = "assets"
            if not nonempty(reference.get("label")) and info:
                reference["label"] = info["prompt"].get("label", prompt_id)
            if not nonempty(reference.get("asset_id")) and info:
                reference["asset_id"] = info["asset"].get("id")
                reference["version"] = info["version"].get("id")
            production_role = info.get("prompt", {}).get("production_role") if info else None
            if production_role in SCENE_PURPOSES:
                reference.setdefault("production_role", production_role)
                reference.setdefault("role", "scene")
                reference.setdefault("purpose", SCENE_PURPOSES[production_role])
            reference.setdefault("role", "identity")
            reference.setdefault("source_manifest", "storyboard")
            if reference["source_manifest"] == "assets" and asset_path:
                reference.setdefault("source_base", str(asset_path.parent))
            else:
                reference.setdefault("source_base", str(storyboard_path.parent))
            references.append(reference)
        result.append({"shot_id": binding["shot_id"], "references": references})
    return result


def split_segments(shots: list[dict[str, Any]], max_seconds: float) -> list[list[dict[str, Any]]]:
    if max_seconds <= 0:
        raise ProductionError("max_segment_seconds 必须大于 0")
    result: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_duration = 0.0
    for shot in sorted(shots, key=lambda item: item.get("order", 0)):
        duration = shot.get("duration_s")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
            raise ProductionError(f"{shot.get('shot_id')} duration_s 不合法")
        if duration > max_seconds + 1e-9:
            raise ProductionError(
                f"{shot.get('shot_id')} 时长 {duration:g}s 超过视频段上限 {max_seconds:g}s"
            )
        cut_type = (shot.get("continuity") or {}).get("cut_type")
        explicit_break = cut_type in SEGMENT_BREAK_CUTS or "segment_break" in shot.get("risk_flags", [])
        incompatible = bool(
            current
            and (
                shot.get("scene_id") != current[-1].get("scene_id")
                or shot.get("generation_mode") != current[-1].get("generation_mode")
                or explicit_break
                or current_duration + float(duration) > max_seconds + 1e-9
            )
        )
        if incompatible:
            result.append(current)
            current = []
            current_duration = 0.0
        current.append(shot)
        current_duration += float(duration)
    if current:
        result.append(current)
    return result


def resolved_audio(audio: dict[str, Any], names: dict[str, str]) -> list[str]:
    result: list[str] = []
    if nonempty(audio.get("voiceover")):
        result.append(f"旁白：{audio['voiceover']}")
    for line in audio.get("dialogue", []):
        if isinstance(line, dict) and nonempty(line.get("text")):
            speaker = names.get(line.get("speaker_entity_id"), line.get("speaker_entity_id") or "角色")
            result.append(f"对白·{speaker}：{line['text']}")
    if audio.get("ambience"):
        result.append("环境声：" + "；".join(str(item) for item in audio["ambience"]))
    if audio.get("sfx"):
        result.append("拟音：" + "；".join(str(item) for item in audio["sfx"]))
    if nonempty(audio.get("music_intent")):
        result.append(f"音乐意图：{audio['music_intent']}")
    return result


def build_segments(
    storyboard: dict[str, Any],
    bindings: list[dict[str, Any]],
    max_seconds: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    mapping = tag_map(storyboard)
    names = entity_names(storyboard)
    binding_map = {item["shot_id"]: item.get("references", []) for item in bindings}
    segments: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for segment_index, group in enumerate(split_segments(storyboard.get("shots", []), max_seconds), start=1):
        segment_id = f"SEG-{segment_index:03d}"
        offset = 0.0
        cuts: list[dict[str, Any]] = []
        references: list[dict[str, Any]] = []
        seen_references: set[tuple[str, str]] = set()
        negatives: list[str] = []
        audio_cues: list[dict[str, Any]] = []
        for shot in group:
            prompt_layers = shot.get("prompt_layers")
            if not isinstance(prompt_layers, dict) or not nonempty(prompt_layers.get("delivery_prompt")):
                raise ProductionError(f"{shot.get('shot_id')} 尚未编译 delivery_prompt")
            resolved, missing = resolve_tags(prompt_layers["delivery_prompt"], mapping)
            unresolved.extend(f"{shot.get('shot_id')}:{tag}" for tag in missing)
            duration = float(shot["duration_s"])
            cuts.append(
                {
                    "shot_id": shot["shot_id"],
                    "start_s": round(offset, 3),
                    "end_s": round(offset + duration, 3),
                    "duration_s": duration,
                    "purpose": shot.get("purpose", ""),
                    "visual_prompt": resolved,
                }
            )
            audio_cues.append(
                {
                    "shot_id": shot["shot_id"],
                    "start_s": round(offset, 3),
                    "end_s": round(offset + duration, 3),
                    "lines": resolved_audio(shot.get("audio") or {}, names),
                }
            )
            for negative in prompt_layers.get("negative_constraints", []):
                resolved_negative, missing_negative = resolve_tags(str(negative), mapping)
                unresolved.extend(f"{shot.get('shot_id')}:{tag}" for tag in missing_negative)
                if resolved_negative not in negatives:
                    negatives.append(resolved_negative)
            for reference in binding_map.get(shot["shot_id"], []):
                key = (str(reference.get("prompt_id") or reference.get("asset_id") or ""), str(reference.get("uri") or ""))
                if key not in seen_references:
                    seen_references.add(key)
                    references.append(copy.deepcopy(reference))
            offset += duration
        timeline = "\n".join(
            f"{cut['start_s']:.2f}–{cut['end_s']:.2f}秒：{cut['visual_prompt']}"
            for cut in cuts
        )
        visual_prompt = (
            f"通用视频段 {segment_id}，总时长 {offset:.2f} 秒。\n"
            f"按以下时间顺序完成画面变化：\n{timeline}"
        )
        if negatives:
            visual_prompt += "\n共同限制：" + "；".join(negatives)
        segments.append(
            {
                "segment_id": segment_id,
                "scene_id": group[0].get("scene_id"),
                "generation_mode": group[0].get("generation_mode"),
                "shot_ids": [shot["shot_id"] for shot in group],
                "duration_s": round(offset, 3),
                "cut_starts_s": [cut["start_s"] for cut in cuts],
                "cuts": cuts,
                "visual_prompt": visual_prompt,
                "audio_cues": audio_cues,
                "references": references,
                "missing_references": [],
            }
        )
    return segments, sorted(set(unresolved))


def missing_references(
    segments: list[dict[str, Any]],
    storyboard_path: Path,
    asset_path: Path | None,
) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for segment in segments:
        segment_missing: list[str] = []
        for reference in segment.get("references", []):
            uri = reference.get("uri")
            label = reference.get("label") or reference.get("prompt_id") or reference.get("asset_id") or "未命名资源"
            if not nonempty(uri):
                segment_missing.append(str(label))
                missing.append({"segment_id": segment["segment_id"], "resource": label, "reason": "未登记 URI"})
                continue
            base = Path(reference.get("source_base")) if nonempty(reference.get("source_base")) else (asset_path.parent if reference.get("source_manifest") == "assets" and asset_path else storyboard_path.parent)
            local = resolve_local_uri(uri, base)
            if local is not None and not local.exists():
                segment_missing.append(str(label))
                missing.append({"segment_id": segment["segment_id"], "resource": label, "reason": f"文件不存在：{uri}"})
        segment["missing_references"] = segment_missing
    return missing


def prepare_manifest(
    storyboard: dict[str, Any],
    storyboard_path: Path,
    assets: dict[str, Any] | None,
    asset_path: Path | None,
    max_seconds: float,
) -> dict[str, Any]:
    base_errors = [issue for issue in VALIDATOR.validate_manifest(storyboard) if issue.severity == "error"]
    if base_errors:
        raise ProductionError(
            "Canonical Manifest 未通过验证：" + "; ".join(f"{issue.code}@{issue.path}" for issue in base_errors[:8])
        )
    if storyboard.get("workflow", {}).get("phase_status") != "compiled":
        raise ProductionError("只有 compiled 分镜才能生成生产包")
    result = copy.deepcopy(storyboard)
    extensions = result.setdefault("extensions", {})
    current = copy.deepcopy(extensions.get("production_v1")) if isinstance(extensions.get("production_v1"), dict) else {}
    current.setdefault("entity_asset_map", [])
    current.setdefault("shot_asset_bindings", [])
    current["version"] = PRODUCTION_VERSION
    current["asset_manifest_uri"] = str(asset_path) if asset_path else None
    current["max_segment_seconds"] = max_seconds
    current["legacy_imports"] = legacy_imports(result, storyboard_path)
    current["shot_asset_bindings"] = normalize_bindings(
        current, assets, storyboard_path, asset_path
    )
    segments, unresolved = build_segments(result, current["shot_asset_bindings"], max_seconds)
    missing = missing_references(segments, storyboard_path, asset_path)
    for prompt_id in selected_core_missing(assets):
        missing.append({"segment_id": None, "resource": prompt_id, "reason": "已选核心资产尚未成功生成"})
    for item in unresolved:
        missing.append({"segment_id": item.split(":", 1)[0], "resource": item, "reason": "Canonical 标签无法解析"})
    current["segments"] = segments
    current["missing_resources"] = missing
    current["status"] = "ready" if not missing else "incomplete"
    extensions["production_v1"] = current
    return result


def validate_production(
    storyboard: dict[str, Any], storyboard_path: Path, assets: dict[str, Any] | None, asset_path: Path | None
) -> tuple[list[str], list[str]]:
    errors = [f"{issue.code}@{issue.path}: {issue.message}" for issue in VALIDATOR.validate_manifest(storyboard) if issue.severity == "error"]
    warnings = [f"{issue.code}@{issue.path}: {issue.message}" for issue in VALIDATOR.validate_manifest(storyboard) if issue.severity == "warning"]
    production = (storyboard.get("extensions") or {}).get("production_v1")
    if not isinstance(production, dict):
        errors.append("缺少 extensions.production_v1；先运行 prepare")
        return errors, warnings
    if production.get("version") != PRODUCTION_VERSION:
        errors.append(f"production_v1.version 必须是 {PRODUCTION_VERSION}")
    max_seconds = production.get("max_segment_seconds")
    if isinstance(max_seconds, bool) or not isinstance(max_seconds, (int, float)) or max_seconds <= 0:
        errors.append("max_segment_seconds 必须是正数")
        max_seconds = 10
    shot_ids = [shot.get("shot_id") for shot in sorted(storyboard.get("shots", []), key=lambda item: item.get("order", 0))]
    covered: list[str] = []
    for segment in production.get("segments", []):
        if not isinstance(segment, dict):
            errors.append("segments 中存在非对象")
            continue
        duration = segment.get("duration_s")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration > max_seconds + 1e-9:
            errors.append(f"{segment.get('segment_id')} 超过 {max_seconds:g}s")
        covered.extend(segment.get("shot_ids", []))
        if TAG_RE.search(str(segment.get("visual_prompt") or "")):
            errors.append(f"{segment.get('segment_id')} 的用户提示词仍包含 Canonical 标签")
        if segment.get("missing_references"):
            warnings.append(f"{segment.get('segment_id')} 缺少资源：{', '.join(segment['missing_references'])}")
    if covered != shot_ids:
        errors.append("视频段必须按顺序且恰好覆盖全部镜头一次")
    valid_shots = set(shot_ids)
    seen_binding_shots: set[str] = set()
    prompt_index = asset_prompt_index(assets)
    asset_entities = {entity.get("id") for entity in (assets or {}).get("entities", []) if isinstance(entity, dict)}
    storyboard_entities = {entity.get("entity_id") for entity in storyboard.get("entities", []) if isinstance(entity, dict)}
    for mapping in production.get("entity_asset_map", []):
        if not isinstance(mapping, dict):
            errors.append("entity_asset_map 中存在非对象")
            continue
        if mapping.get("storyboard_entity_id") not in storyboard_entities:
            errors.append(f"实体映射引用未知分镜实体：{mapping.get('storyboard_entity_id')}")
        if assets and mapping.get("asset_entity_id") not in asset_entities:
            errors.append(f"实体映射引用未知资产实体：{mapping.get('asset_entity_id')}")
    for binding in production.get("shot_asset_bindings", []):
        if not isinstance(binding, dict):
            errors.append("shot_asset_bindings 中存在非对象")
            continue
        shot_id = binding.get("shot_id")
        if shot_id not in valid_shots:
            errors.append(f"资产绑定引用未知镜头：{shot_id}")
        if shot_id in seen_binding_shots:
            errors.append(f"镜头资产绑定重复：{shot_id}")
        seen_binding_shots.add(shot_id)
        seen_refs: set[tuple[str, str]] = set()
        for reference in binding.get("references", []):
            if not isinstance(reference, dict):
                errors.append(f"{shot_id} references 中存在非对象")
                continue
            prompt_id = reference.get("prompt_id")
            if prompt_id and assets and prompt_id not in prompt_index:
                errors.append(f"{shot_id} 引用了未知资产提示词：{prompt_id}")
            if reference.get("role") not in REFERENCE_ROLES:
                errors.append(f"{shot_id} 资产职责不合法：{reference.get('role')}")
            key = (str(prompt_id or reference.get("asset_id") or ""), str(reference.get("uri") or ""))
            if key in seen_refs:
                errors.append(f"{shot_id} 重复绑定资源：{key[0] or key[1]}")
            seen_refs.add(key)
    core_missing = selected_core_missing(assets)
    if core_missing:
        errors.append("核心资产未就绪：" + ", ".join(core_missing))
    if production.get("status") == "ready" and production.get("missing_resources"):
        errors.append("存在缺失资源时 production_v1.status 不能是 ready")
    return errors, warnings


def clean_file_name(value: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f/:\\]+", "-", value).strip("-.")
    return cleaned or "asset"


def human_audio(cue: dict[str, Any]) -> str:
    lines = cue.get("lines") or []
    return "；".join(str(line) for line in lines) if lines else "无"


def segment_markdown(segment: dict[str, Any]) -> str:
    lines = [
        f"# {segment['segment_id']}",
        "",
        f"- 时长：{segment['duration_s']:.2f} 秒",
        f"- 镜头：{', '.join(segment['shot_ids'])}",
        f"- 生成模式：{segment.get('generation_mode')}",
        "",
        "## 参考图片",
        "",
    ]
    if segment.get("references"):
        for reference in segment["references"]:
            lines.append(
                f"- {reference.get('label') or reference.get('asset_id') or reference.get('prompt_id') or '资源'}"
                f"（{reference.get('role', 'reference')}；{reference.get('purpose') or '未注明职责'}）：{reference.get('uri') or '缺失'}"
            )
    else:
        lines.append("- 本段没有显式绑定参考图片。")
    lines.extend(["", "## 视觉提示词", "", segment["visual_prompt"], "", "## 声音轨", ""])
    for cue in segment.get("audio_cues", []):
        lines.append(f"- {cue['start_s']:.2f}–{cue['end_s']:.2f}秒：{human_audio(cue)}")
    text = "\n".join(lines).rstrip() + "\n"
    if TAG_RE.search(text):
        raise ProductionError(f"{segment['segment_id']} prompt.md 仍包含 Canonical 标签")
    return text


def relative_href(uri: str, source_base: Path, output_dir: Path) -> tuple[str | None, bool]:
    if uri.startswith(("http://", "https://")):
        return uri, True
    source = resolve_local_uri(uri, source_base)
    if source is None:
        return None, False
    try:
        href = os.path.relpath(source, output_dir)
    except ValueError:
        href = str(source)
    return Path(href).as_posix(), source.exists()


def asset_cards(assets: dict[str, Any] | None, asset_path: Path | None, output_dir: Path) -> list[dict[str, Any]]:
    if not assets:
        return []
    selection = {
        entry.get("prompt_id"): entry
        for entry in (assets.get("production") or {}).get("selection", [])
        if isinstance(entry, dict)
    }
    outputs = asset_output_index(assets)
    cards: list[dict[str, Any]] = []
    for prompt_id, info in asset_prompt_index(assets).items():
        prompt = info["prompt"]
        if (prompt.get("output_spec") or {}).get("media_type") != "image":
            continue
        selected = selection.get(prompt_id, {})
        output = outputs.get(prompt_id, {})
        uri = output.get("uri") if output.get("status") == "succeeded" else None
        href, exists = relative_href(uri, asset_path.parent, output_dir) if uri and asset_path else (None, False)
        cards.append(
            {
                "prompt_id": prompt_id,
                "asset_id": info["asset"].get("id"),
                "asset_name": info["asset"].get("name"),
                "asset_type": info["asset"].get("type"),
                "label": prompt.get("label", prompt_id),
                "tier": selected.get("tier", "optional"),
                "selected": bool(selected.get("selected")),
                "reason": selected.get("reason", "未进入选择流程"),
                "status": output.get("status", "pending" if selected.get("selected") else "not_selected"),
                "production_role": prompt.get("production_role"),
                "uri": uri,
                "href": href,
                "image_exists": exists,
                "text": prompt.get("text", ""),
                "text_en": prompt.get("text_en", ""),
            }
        )
    return cards


def production_manifest(prepared: dict[str, Any]) -> dict[str, Any]:
    production = prepared["extensions"]["production_v1"]
    project = prepared.get("project", {})
    return {
        "schema_version": PACK_VERSION,
        "project": {
            "project_id": project.get("project_id"),
            "title": project.get("title"),
            "language": project.get("language"),
            "aspect_ratio": project.get("aspect_ratio"),
            "target_duration_s": project.get("target_duration_s"),
            "visual_style": project.get("visual_style"),
        },
        "status": production.get("status"),
        "max_segment_seconds": production.get("max_segment_seconds"),
        "segments": copy.deepcopy(production.get("segments", [])),
        "legacy_imports": copy.deepcopy(production.get("legacy_imports", [])),
        "missing_resources": copy.deepcopy(production.get("missing_resources", [])),
    }


def json_for_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def render_report_html(
    prepared: dict[str, Any],
    assets: dict[str, Any] | None,
    storyboard_path: Path,
    asset_path: Path | None,
    output_path: Path,
) -> str:
    pack = production_manifest(prepared)
    cards = asset_cards(assets, asset_path, output_path.parent)
    legacy = prepared["extensions"]["production_v1"].get("legacy_imports", [])
    total_duration = sum(float(segment.get("duration_s", 0)) for segment in pack["segments"]) or 1
    esc = lambda value: html.escape(str(value or ""), quote=True)
    asset_html: list[str] = []
    for card in cards:
        image = (
            f'<img loading="lazy" src="{esc(card["href"])}" alt="{esc(card["label"])}">'
            if card["href"] and card["image_exists"]
            else '<div class="missing-image">未生成</div>'
        )
        search = " ".join(str(card.get(key) or "") for key in ("prompt_id", "asset_name", "label", "reason"))
        asset_html.append(
            f'<article class="asset-card" data-tier="{esc(card["tier"])}" data-status="{esc(card["status"])}" data-search="{esc(search.lower())}">'
            f'<div class="asset-image">{image}</div><div class="asset-body">'
            f'<div class="eyebrow">{esc(card["asset_type"])} · {esc(card["asset_id"])} · {esc(card["tier"])}</div>'
            f'<h3>{esc(card["asset_name"])} · {esc(card["label"])}</h3>'
            f'<p class="status">{esc(card["status"])} · {esc(card["reason"])}</p>'
            f'{"<p class=status>" + esc(card.get("production_role")) + "</p>" if card.get("production_role") else ""}'
            f'<div class="prompt"><pre class="zh">{esc(card["text"])}</pre><pre class="en" hidden>{esc(card["text_en"])}</pre>'
            '<button class="copy">复制当前提示词</button></div></div></article>'
        )
    if not asset_html:
        asset_html.append('<div class="empty">未提供资产Manifest。</div>')
    legacy_html: list[str] = []
    for item in legacy:
        legacy_base = Path(item.get("source_base")) if nonempty(item.get("source_base")) else storyboard_path.parent
        href, exists = relative_href(item.get("uri", ""), legacy_base, output_path.parent)
        image = f'<img loading="lazy" src="{esc(href)}" alt="{esc(item.get("purpose"))}">' if href and exists else '<div class="missing-image">文件缺失</div>'
        legacy_html.append(
            f'<article class="legacy"><div>{image}</div><strong>{esc(item.get("purpose"))}</strong>'
            f'<small>{esc(item.get("uri"))} · legacy_manual</small></article>'
        )
    segment_html: list[str] = []
    timeline_html: list[str] = []
    for segment in pack["segments"]:
        width = max(3.0, float(segment["duration_s"]) / total_duration * 100)
        timeline_html.append(
            f'<a href="#{esc(segment["segment_id"])}" style="width:{width:.3f}%" title="{esc(segment["segment_id"])} {segment["duration_s"]:.2f}s">{esc(segment["segment_id"])}</a>'
        )
        refs: list[str] = []
        for reference in segment.get("references", []):
            base = Path(reference.get("source_base")) if nonempty(reference.get("source_base")) else (asset_path.parent if reference.get("source_manifest") == "assets" and asset_path else storyboard_path.parent)
            href, exists = relative_href(reference.get("uri", ""), base, output_path.parent) if reference.get("uri") else (None, False)
            image = f'<img loading="lazy" src="{esc(href)}" alt="{esc(reference.get("label"))}">' if href and exists else '<span class="ref-missing">缺图</span>'
            refs.append(
                f'<div class="reference">{image}<span>{esc(reference.get("label") or reference.get("asset_id") or reference.get("prompt_id"))}<small>{esc(reference.get("role"))} · {esc(reference.get("purpose"))}</small></span></div>'
            )
        cuts = "".join(
            f'<tr><td>{esc(cut["shot_id"])}</td><td>{cut["start_s"]:.2f}–{cut["end_s"]:.2f}s</td><td>{esc(cut.get("purpose"))}</td></tr>'
            for cut in segment.get("cuts", [])
        )
        audio = "".join(
            f'<li>{cue["start_s"]:.2f}–{cue["end_s"]:.2f}s · {esc(human_audio(cue))}</li>'
            for cue in segment.get("audio_cues", [])
        )
        segment_html.append(
            f'<article class="segment" id="{esc(segment["segment_id"])}" data-search="{esc((segment["segment_id"] + " " + segment["visual_prompt"]).lower())}">'
            f'<header><div><span>{esc(segment["scene_id"])}</span><h3>{esc(segment["segment_id"])}</h3></div><b>{segment["duration_s"]:.2f}s</b></header>'
            f'<div class="references">{"".join(refs) or "<p>未显式绑定参考图</p>"}</div>'
            f'<div class="prompt"><pre>{esc(segment["visual_prompt"])}</pre><button class="copy">复制视频提示词</button></div>'
            f'<details><summary>逐镜与声音</summary><table><thead><tr><th>镜头</th><th>时间</th><th>目的</th></tr></thead><tbody>{cuts}</tbody></table><ul>{audio}</ul></details>'
            f'{"<p class=warning>缺失：" + esc("、".join(segment.get("missing_references", []))) + "</p>" if segment.get("missing_references") else ""}'
            '</article>'
        )
    export_data = {"assets": assets or {}, "production": pack}
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(pack["project"].get("title"))} · 漫剧生产报告</title>
<style>
:root{{--bg:#0d1117;--panel:#161b22;--line:#30363d;--text:#e6edf3;--muted:#8b949e;--accent:#58a6ff;--ok:#3fb950;--warn:#d29922}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}button,input,select{{font:inherit}}header.top{{position:sticky;top:0;z-index:4;background:#0d1117ee;backdrop-filter:blur(12px);border-bottom:1px solid var(--line);padding:18px 24px}}h1{{margin:0;font-size:22px}}.meta{{color:var(--muted)}}nav{{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}}button,.tab{{border:1px solid var(--line);background:var(--panel);color:var(--text);border-radius:8px;padding:7px 11px;cursor:pointer}}button:hover,.tab.on{{border-color:var(--accent);color:var(--accent)}}main{{max-width:1500px;margin:auto;padding:24px}}.pane[hidden],.en[hidden]{{display:none}}.tools{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}}input{{min-width:260px}}input,select{{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:8px 10px}}.kpis{{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:12px;margin:18px 0}}.kpi{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}}.kpi b{{display:block;font-size:24px}}.kpi span,.eyebrow,small{{color:var(--muted)}}.asset-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:14px}}.asset-card{{display:grid;grid-template-columns:150px 1fr;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}}.asset-image{{min-height:150px;background:#090c10;display:grid;place-items:center}}img{{max-width:100%;height:auto;display:block}}.asset-image img{{width:100%;height:100%;object-fit:cover}}.asset-body{{padding:14px;min-width:0}}h3{{margin:2px 0 8px}}.status{{color:var(--muted)}}pre{{white-space:pre-wrap;word-break:break-word;background:#090c10;border:1px solid var(--line);padding:12px;border-radius:8px;max-height:300px;overflow:auto}}.copy{{float:right;margin-top:-4px}}.legacy-grid,.references{{display:flex;gap:10px;flex-wrap:wrap}}.legacy,.reference{{width:180px;background:var(--panel);border:1px solid var(--line);border-radius:9px;overflow:hidden}}.legacy>div,.reference>img,.ref-missing{{height:100px;width:100%;object-fit:cover;display:grid;place-items:center;background:#090c10}}.legacy strong,.legacy small,.reference span{{display:block;padding:7px}}.reference small{{display:block;padding:0}}.timeline{{display:flex;height:48px;margin:16px 0;overflow:hidden;border-radius:9px}}.timeline a{{display:grid;place-items:center;background:#1f6feb;color:white;text-decoration:none;border-right:2px solid var(--bg);min-width:38px;font-size:11px}}.segment{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin:14px 0;scroll-margin-top:130px}}.segment>header{{display:flex;justify-content:space-between}}.segment>header b{{font-size:20px;color:var(--accent)}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;border-bottom:1px solid var(--line);padding:8px}}.warning{{color:#ffd77a;background:#3b2b0b;padding:10px;border-radius:8px}}.missing-image,.empty{{color:var(--muted)}}@media(max-width:700px){{.kpis{{grid-template-columns:1fr 1fr}}.asset-grid{{grid-template-columns:1fr}}.asset-card{{grid-template-columns:1fr}}main{{padding:14px}}}}
</style></head><body>
<header class="top"><h1>{esc(pack["project"].get("title"))} · 漫剧生产报告</h1><div class="meta">{esc(pack["status"])} · {len(cards)} 条视觉资产提示词 · {len(pack["segments"])} 个视频段</div>
<nav><button class="tab on" data-pane="assets-pane">资产</button><button class="tab" data-pane="storyboard-pane">分镜</button><button id="lang">中 / EN</button><button data-export="assets">导出资产JSON</button><button data-export="production">导出生产JSON</button></nav></header>
<main><section class="pane" id="assets-pane"><div class="tools"><input class="search" placeholder="搜索资产"><select id="asset-filter"><option value="all">全部</option><option value="core">核心</option><option value="optional">可选</option><option value="succeeded">已生成</option><option value="missing">未生成</option></select></div>
<div class="kpis"><div class="kpi"><b>{len(cards)}</b><span>视觉提示词</span></div><div class="kpi"><b>{sum(c["tier"]=="core" for c in cards)}</b><span>核心</span></div><div class="kpi"><b>{sum(c["status"]=="succeeded" for c in cards)}</b><span>已生成</span></div><div class="kpi"><b>{len(legacy)}</b><span>旧版资源</span></div></div>
<div class="asset-grid">{"".join(asset_html)}</div><h2>旧版人工资源</h2><div class="legacy-grid">{"".join(legacy_html) or "<p>无</p>"}</div></section>
<section class="pane" id="storyboard-pane" hidden><div class="tools"><input class="search" placeholder="搜索视频段或提示词"></div><div class="kpis"><div class="kpi"><b>{len(pack["segments"])}</b><span>视频段</span></div><div class="kpi"><b>{sum(len(s["shot_ids"]) for s in pack["segments"])}</b><span>镜头</span></div><div class="kpi"><b>{total_duration:.1f}s</b><span>总时长</span></div><div class="kpi"><b>{len(pack["missing_resources"])}</b><span>缺失项</span></div></div><div class="timeline">{"".join(timeline_html)}</div>{"".join(segment_html)}</section></main>
<script type="application/json" id="report-data">{json_for_script(export_data)}</script>
<script>
const data=JSON.parse(document.getElementById('report-data').textContent);let english=false;
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x===b));document.querySelectorAll('.pane').forEach(p=>p.hidden=p.id!==b.dataset.pane)}});
document.getElementById('lang').onclick=()=>{{english=!english;document.querySelectorAll('.zh').forEach(x=>x.hidden=english);document.querySelectorAll('.en').forEach(x=>x.hidden=!english)}};
document.querySelectorAll('.copy').forEach(b=>b.onclick=async()=>{{const p=b.closest('.prompt');const text=[...p.querySelectorAll('pre')].find(x=>!x.hidden)?.textContent||'';try{{await navigator.clipboard.writeText(text)}}catch{{const t=document.createElement('textarea');t.value=text;document.body.append(t);t.select();document.execCommand('copy');t.remove()}}b.textContent='已复制';setTimeout(()=>b.textContent=b.closest('.segment')?'复制视频提示词':'复制当前提示词',900)}});
document.querySelectorAll('.search').forEach(input=>input.oninput=()=>{{const pane=input.closest('.pane');const q=input.value.trim().toLowerCase();pane.querySelectorAll('[data-search]').forEach(x=>x.hidden=q&&!x.dataset.search.includes(q))}});
document.getElementById('asset-filter').onchange=e=>{{const v=e.target.value;document.querySelectorAll('.asset-card').forEach(x=>x.hidden=v!=='all'&&!((v==='core'||v==='optional')?x.dataset.tier===v:v==='succeeded'?x.dataset.status==='succeeded':x.dataset.status!=='succeeded'))}};
document.querySelectorAll('[data-export]').forEach(b=>b.onclick=()=>{{const kind=b.dataset.export;const blob=new Blob([JSON.stringify(data[kind],null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=kind+'.json';a.click();URL.revokeObjectURL(a.href)}});
</script></body></html>'''


def copy_asset(uri: str, base: Path, asset_dir: Path, used_names: set[str]) -> str:
    if uri.startswith(("http://", "https://")):
        return uri
    source = resolve_local_uri(uri, base)
    if source is None or not source.exists():
        return uri
    name = clean_file_name(source.name)
    stem, suffix = Path(name).stem, Path(name).suffix
    counter = 2
    while name in used_names:
        name = f"{stem}-{counter}{suffix}"
        counter += 1
    used_names.add(name)
    shutil.copy2(source, asset_dir / name)
    return f"assets/{name}"


def export_pack(
    prepared: dict[str, Any],
    assets: dict[str, Any] | None,
    storyboard_path: Path,
    asset_path: Path | None,
    out_dir: Path,
) -> None:
    if out_dir.exists():
        raise ProductionError(f"输出目录已存在，拒绝覆盖：{out_dir}")
    out_dir.mkdir(parents=True)
    asset_dir = out_dir / "assets"
    segment_dir = out_dir / "segments"
    asset_dir.mkdir()
    segment_dir.mkdir()
    used_names: set[str] = set()
    copied_assets = copy.deepcopy(assets) if assets else None
    uri_map: dict[tuple[str, str], str] = {}
    if copied_assets and asset_path:
        for output in (copied_assets.get("production") or {}).get("outputs", []):
            if not isinstance(output, dict) or output.get("status") != "succeeded" or not nonempty(output.get("uri")):
                continue
            old = output["uri"]
            new = copy_asset(old, asset_path.parent, asset_dir, used_names)
            output["uri"] = new
            uri_map[("assets", old)] = new
    production = prepared["extensions"]["production_v1"]
    for legacy in production.get("legacy_imports", []):
        if nonempty(legacy.get("uri")):
            old = legacy["uri"]
            legacy_base = Path(legacy.get("source_base")) if nonempty(legacy.get("source_base")) else storyboard_path.parent
            new = copy_asset(old, legacy_base, asset_dir, used_names)
            legacy["uri"] = new
            legacy.pop("source_base", None)
            uri_map[("storyboard", old)] = new
    for segment in production.get("segments", []):
        for reference in segment.get("references", []):
            source = reference.get("source_manifest", "storyboard")
            old = reference.get("uri")
            if not nonempty(old):
                continue
            key = (source, old)
            if key not in uri_map:
                base = Path(reference.get("source_base")) if nonempty(reference.get("source_base")) else (asset_path.parent if source == "assets" and asset_path else storyboard_path.parent)
                uri_map[key] = copy_asset(old, base, asset_dir, used_names)
            reference["uri"] = uri_map[key]
            reference["source_manifest"] = "storyboard"
            reference.pop("source_base", None)
    pack = production_manifest(prepared)
    pack["report"] = "report.html"
    for segment in pack["segments"]:
        folder = segment_dir / segment["segment_id"]
        folder.mkdir()
        prompt_path = folder / "prompt.md"
        prompt_path.write_text(segment_markdown(segment), encoding="utf-8")
        segment["prompt_file"] = f"segments/{segment['segment_id']}/prompt.md"
    write_json(out_dir / "manifest.json", pack)
    html_text = render_report_html(prepared, copied_assets, out_dir / "manifest.json", out_dir / "asset-manifest.json" if copied_assets else None, out_dir / "report.html")
    (out_dir / "report.html").write_text(html_text, encoding="utf-8")
    if copied_assets:
        write_json(out_dir / "asset-manifest.json", copied_assets)
    for path in [out_dir / "manifest.json", *segment_dir.glob("*/prompt.md")]:
        if "{{" in path.read_text(encoding="utf-8"):
            raise ProductionError(f"用户交付物仍包含 Canonical 标签：{path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "validate", "render", "export"):
        command = sub.add_parser(name)
        command.add_argument("storyboard", type=Path)
        command.add_argument("--assets", type=Path)
    sub.choices["prepare"].add_argument("--output", type=Path, required=True)
    sub.choices["prepare"].add_argument("--max-segment-seconds", type=float, default=10.0)
    sub.choices["validate"].add_argument("--strict", action="store_true")
    sub.choices["render"].add_argument("--output", type=Path, required=True)
    sub.choices["export"].add_argument("--out-dir", type=Path, required=True)
    sub.choices["render"].add_argument("--max-segment-seconds", type=float, default=10.0)
    sub.choices["export"].add_argument("--max-segment-seconds", type=float, default=10.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        storyboard = load_json(args.storyboard)
        assets = load_json(args.assets) if args.assets else None
        if args.command == "prepare":
            prepared = prepare_manifest(storyboard, args.storyboard, assets, args.assets, args.max_segment_seconds)
            write_json(args.output, prepared)
            print(args.output.resolve())
        elif args.command == "validate":
            errors, warnings = validate_production(storyboard, args.storyboard, assets, args.assets)
            print(json.dumps({"valid": not errors and not (args.strict and warnings), "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
            return 1 if errors or (args.strict and warnings) else 0
        elif args.command == "render":
            prepared = prepare_manifest(storyboard, args.storyboard, assets, args.assets, args.max_segment_seconds)
            if args.output.exists():
                raise ProductionError(f"输出文件已存在，拒绝覆盖：{args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render_report_html(prepared, assets, args.storyboard, args.assets, args.output), encoding="utf-8")
            print(args.output.resolve())
        elif args.command == "export":
            prepared = prepare_manifest(storyboard, args.storyboard, assets, args.assets, args.max_segment_seconds)
            export_pack(prepared, assets, args.storyboard, args.assets, args.out_dir)
            print(args.out_dir.resolve())
    except ProductionError as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
