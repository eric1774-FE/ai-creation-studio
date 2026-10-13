#!/usr/bin/env python3
"""Plan, approve, record, validate, and report drama asset generation."""

from __future__ import annotations

import argparse
import html
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "story-asset-manifest/v2"
OUTPUT_STATUSES = {"succeeded", "failed", "skipped"}
SCENE_ROLES = {"scene_panorama", "scene_coverage_grid"}


class AssetError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssetError(f"无法读取 UTF-8 JSON：{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AssetError("Manifest 根节点必须是对象")
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


def as_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise AssetError(f"{path} 必须是数组")
    return value


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def index_manifest(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise AssetError(f"schema_version 必须是 {SCHEMA_VERSION}")
    for key in (
        "reference_inputs",
        "asset_type_coverage",
        "assets",
        "entities",
        "standalone_asset_refs",
        "continuity",
        "quality_checks",
    ):
        as_list(data.get(key), f"$.{key}")

    assets: dict[str, dict[str, Any]] = {}
    versions: set[tuple[str, str]] = set()
    prompts: dict[str, dict[str, Any]] = {}
    prompt_order: list[str] = []
    dependencies: dict[str, set[str]] = {}
    asset_prompts: dict[str, list[str]] = defaultdict(list)

    for asset_index, raw_asset in enumerate(data["assets"]):
        path = f"$.assets[{asset_index}]"
        if not isinstance(raw_asset, dict):
            raise AssetError(f"{path} 必须是对象")
        asset_id = raw_asset.get("id")
        if not nonempty(asset_id):
            raise AssetError(f"{path}.id 必须是非空字符串")
        if asset_id in assets:
            raise AssetError(f"重复资产 ID：{asset_id}")
        asset_type = raw_asset.get("type")
        if asset_type not in {"G", "C", "W", "S", "P", "V", "E", "L", "F", "A"}:
            raise AssetError(f"{path}.type 不合法：{asset_type}")
        assets[asset_id] = raw_asset
        raw_versions = as_list(raw_asset.get("versions"), f"{path}.versions")
        for version_index, raw_version in enumerate(raw_versions):
            version_path = f"{path}.versions[{version_index}]"
            if not isinstance(raw_version, dict):
                raise AssetError(f"{version_path} 必须是对象")
            version_id = raw_version.get("id")
            if not nonempty(version_id):
                raise AssetError(f"{version_path}.id 必须是非空字符串")
            version_key = (asset_id, version_id)
            if version_key in versions:
                raise AssetError(f"重复资产版本：{asset_id}-{version_id}")
            versions.add(version_key)
            for prompt_index, raw_prompt in enumerate(
                as_list(raw_version.get("prompts"), f"{version_path}.prompts")
            ):
                prompt_path = f"{version_path}.prompts[{prompt_index}]"
                if not isinstance(raw_prompt, dict):
                    raise AssetError(f"{prompt_path} 必须是对象")
                prompt_id = raw_prompt.get("id")
                if not nonempty(prompt_id):
                    raise AssetError(f"{prompt_path}.id 必须是非空字符串")
                if prompt_id in prompts:
                    raise AssetError(f"重复提示词 ID：{prompt_id}")
                output_spec = raw_prompt.get("output_spec")
                if not isinstance(output_spec, dict) or output_spec.get("media_type") not in {
                    "image",
                    "audio",
                }:
                    raise AssetError(f"{prompt_path}.output_spec.media_type 必须是 image 或 audio")
                if not nonempty(raw_prompt.get("text")) or not nonempty(raw_prompt.get("text_en")):
                    raise AssetError(f"{prompt_path} 必须同时包含中文和英文提示词")
                deps: set[str] = set()
                for input_index, raw_input in enumerate(
                    as_list(raw_prompt.get("input_refs"), f"{prompt_path}.input_refs")
                ):
                    input_path = f"{prompt_path}.input_refs[{input_index}]"
                    if not isinstance(raw_input, dict):
                        raise AssetError(f"{input_path} 必须是对象")
                    if raw_input.get("source_kind") == "prompt_output":
                        ref_id = raw_input.get("ref_id")
                        if not nonempty(ref_id):
                            raise AssetError(f"{input_path}.ref_id 必须是非空字符串")
                        deps.add(ref_id)
                prompts[prompt_id] = {
                    "prompt": raw_prompt,
                    "asset": raw_asset,
                    "version": raw_version,
                    "asset_id": asset_id,
                    "version_id": version_id,
                }
                prompt_order.append(prompt_id)
                dependencies[prompt_id] = deps
                asset_prompts[asset_id].append(prompt_id)

    for prompt_id, deps in dependencies.items():
        missing = sorted(deps - prompts.keys())
        if missing:
            raise AssetError(f"{prompt_id} 引用了不存在的提示词输出：{', '.join(missing)}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(prompt_id: str) -> None:
        if prompt_id in visited:
            return
        if prompt_id in visiting:
            raise AssetError(f"提示词依赖存在循环：{prompt_id}")
        visiting.add(prompt_id)
        for dependency in dependencies[prompt_id]:
            visit(dependency)
        visiting.remove(prompt_id)
        visited.add(prompt_id)

    for prompt_id in prompt_order:
        visit(prompt_id)

    return {
        "assets": assets,
        "versions": versions,
        "prompts": prompts,
        "prompt_order": prompt_order,
        "dependencies": dependencies,
        "asset_prompts": asset_prompts,
    }


def referenced_assets(entity: dict[str, Any]) -> set[str]:
    refs: list[Any] = []
    refs.extend(entity.get("common_asset_refs", []))
    for state in entity.get("states", []):
        if isinstance(state, dict):
            refs.extend(state.get("asset_refs", []))
    return {
        ref.get("asset_id")
        for ref in refs
        if isinstance(ref, dict) and nonempty(ref.get("asset_id"))
    }


def dependency_closure(selected: set[str], dependencies: dict[str, set[str]]) -> set[str]:
    result = set(selected)
    pending = list(selected)
    while pending:
        prompt_id = pending.pop()
        for dependency in dependencies[prompt_id]:
            if dependency not in result:
                result.add(dependency)
                pending.append(dependency)
    return result


def terminal_image_prompts(asset_id: str, index: dict[str, Any]) -> set[str]:
    candidates = {
        prompt_id
        for prompt_id in index["asset_prompts"].get(asset_id, [])
        if index["prompts"][prompt_id]["prompt"]["output_spec"]["media_type"] == "image"
    }
    consumed = {
        dependency
        for prompt_id in candidates
        for dependency in index["dependencies"][prompt_id]
        if dependency in candidates
    }
    return candidates - consumed or candidates


def core_asset_ids(data: dict[str, Any], index: dict[str, Any]) -> tuple[set[str], dict[str, str]]:
    core: set[str] = set()
    reasons: dict[str, str] = {}
    for asset_id, asset in index["assets"].items():
        asset_type = asset.get("type")
        if asset_type == "G":
            core.add(asset_id)
            reasons[asset_id] = "全局视觉圣经"
        elif asset_type in {"C", "S"} and asset.get("importance_level") in {"A", "B"}:
            core.add(asset_id)
            reasons[asset_id] = f"{asset.get('importance_level')}级{'角色' if asset_type == 'C' else '场景'}"

    recurrence: Counter[str] = Counter()
    for stage in data.get("continuity", []):
        if isinstance(stage, dict):
            recurrence.update(
                ref.get("asset_id")
                for ref in stage.get("asset_refs", [])
                if isinstance(ref, dict) and nonempty(ref.get("asset_id"))
            )
    for asset_id, count in recurrence.items():
        asset = index["assets"].get(asset_id)
        if asset and asset.get("type") == "P" and count >= 2:
            core.add(asset_id)
            reasons[asset_id] = f"连续性阶段重复出现 {count} 次的关键道具"

    # Character presentation assets are part of character continuity, but scene weather,
    # lighting and effects remain optional until the user selects them.
    for entity in data.get("entities", []):
        if not isinstance(entity, dict) or entity.get("type") != "character":
            continue
        refs = referenced_assets(entity)
        if any(index["assets"].get(ref, {}).get("type") == "C" and ref in core for ref in refs):
            for ref in refs:
                if index["assets"].get(ref, {}).get("type") == "W":
                    core.add(ref)
                    reasons[ref] = "主要角色关联的服装妆发"
    return core, reasons


def build_selection(data: dict[str, Any]) -> list[dict[str, Any]]:
    index = index_manifest(data)
    core_assets, reasons = core_asset_ids(data, index)
    directly_selected = {
        prompt_id
        for asset_id in core_assets
        for prompt_id in terminal_image_prompts(asset_id, index)
    }
    selected = dependency_closure(directly_selected, index["dependencies"])
    entries: list[dict[str, Any]] = []
    for prompt_id in index["prompt_order"]:
        info = index["prompts"][prompt_id]
        if info["prompt"]["output_spec"]["media_type"] != "image":
            continue
        asset_id = info["asset_id"]
        if prompt_id in directly_selected:
            reason = reasons.get(asset_id, "核心连续性资产")
        elif prompt_id in selected:
            reason = "被已选核心资产依赖"
        else:
            reason = "可选视觉资产"
        entries.append(
            {
                "prompt_id": prompt_id,
                "asset_id": asset_id,
                "version": info["version_id"],
                "label": info["prompt"].get("label", prompt_id),
                "selected": prompt_id in selected,
                "tier": "core" if prompt_id in selected else "optional",
                "reason": reason,
            }
        )
    return entries


def selected_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    production = data.get("production")
    if not isinstance(production, dict):
        return []
    return [entry for entry in production.get("selection", []) if isinstance(entry, dict) and entry.get("selected")]


def output_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    production = data.get("production")
    if not isinstance(production, dict):
        return {}
    return {
        output.get("prompt_id"): output
        for output in production.get("outputs", [])
        if isinstance(output, dict) and nonempty(output.get("prompt_id"))
    }


def readiness(data: dict[str, Any]) -> tuple[str, list[str]]:
    production = data.get("production")
    if not isinstance(production, dict) or production.get("selection_status") != "approved":
        return "awaiting_approval", []
    outputs = output_map(data)
    missing_core = [
        entry["prompt_id"]
        for entry in selected_entries(data)
        if entry.get("tier") == "core"
        and outputs.get(entry["prompt_id"], {}).get("status") != "succeeded"
    ]
    selected_ids = {entry["prompt_id"] for entry in selected_entries(data)}
    if missing_core:
        if any(outputs.get(prompt_id, {}).get("status") == "failed" for prompt_id in missing_core):
            return "blocked", missing_core
        return "generating", missing_core
    if all(outputs.get(prompt_id, {}).get("status") == "succeeded" for prompt_id in selected_ids):
        return "ready", []
    return "generating", []


def scene_coverage_issues(data: dict[str, Any]) -> list[str]:
    """Check the spatial-lock pair required for recurring scenes."""
    issues: list[str] = []
    for asset in data.get("assets", []):
        if not isinstance(asset, dict) or asset.get("type") != "S":
            continue
        if asset.get("importance_level") not in {"A", "B"}:
            continue
        for version in asset.get("versions", []):
            if not isinstance(version, dict):
                continue
            prompts = [prompt for prompt in version.get("prompts", []) if isinstance(prompt, dict)]
            by_role = {prompt.get("production_role"): prompt for prompt in prompts}
            prefix = f"{asset.get('id')}-{version.get('id')}"
            missing = sorted(SCENE_ROLES - by_role.keys())
            if missing:
                issues.append(f"{prefix} 缺少场景定场提示词：{', '.join(missing)}")
                continue
            panorama = by_role["scene_panorama"]
            coverage = by_role["scene_coverage_grid"]
            if (panorama.get("output_spec") or {}).get("layout") != "single_panorama":
                issues.append(f"{prefix} 全景图 layout 必须是 single_panorama")
            if (coverage.get("output_spec") or {}).get("layout") != "nine_grid":
                issues.append(f"{prefix} 机位图 layout 必须是 nine_grid")
            if coverage.get("mode") != "edit":
                issues.append(f"{prefix} 九宫格机位图必须使用 edit 锁定全景图空间")
            dependencies = {
                ref.get("ref_id")
                for ref in coverage.get("input_refs", [])
                if isinstance(ref, dict)
                and ref.get("source_kind") == "prompt_output"
                and ref.get("role") == "scene_geometry"
            }
            if panorama.get("id") not in dependencies:
                issues.append(f"{prefix} 九宫格机位图必须以 scene_geometry 职责依赖同版本全景图")
    return issues


def validate_production(
    data: dict[str, Any],
    manifest_path: Path,
    require_ready: bool = False,
    require_scene_coverage: bool = False,
) -> list[str]:
    index = index_manifest(data)
    production = data.get("production")
    if production is None:
        issues = ["缺少 production；先运行 plan"] if require_ready else []
        if require_scene_coverage:
            issues.extend(scene_coverage_issues(data))
        return issues
    if not isinstance(production, dict):
        return ["production 必须是对象"]
    issues: list[str] = []
    selection = production.get("selection")
    if not isinstance(selection, list):
        return ["production.selection 必须是数组"]
    seen: set[str] = set()
    tiers: dict[str, str] = {}
    for pos, entry in enumerate(selection):
        if not isinstance(entry, dict):
            issues.append(f"selection[{pos}] 必须是对象")
            continue
        prompt_id = entry.get("prompt_id")
        if prompt_id not in index["prompts"]:
            issues.append(f"selection[{pos}] 引用了不存在的提示词 {prompt_id}")
            continue
        if index["prompts"][prompt_id]["prompt"]["output_spec"]["media_type"] != "image":
            issues.append(f"selection[{pos}] 只能选择图片提示词 {prompt_id}")
        if prompt_id in seen:
            issues.append(f"selection 重复提示词 {prompt_id}")
        seen.add(prompt_id)
        if not isinstance(entry.get("selected"), bool):
            issues.append(f"selection[{pos}].selected 必须是布尔值")
        if entry.get("tier") not in {"core", "optional"}:
            issues.append(f"selection[{pos}].tier 必须是 core 或 optional")
        tiers[prompt_id] = entry.get("tier")

    outputs = production.get("outputs", [])
    if not isinstance(outputs, list):
        issues.append("production.outputs 必须是数组")
        outputs = []
    seen_outputs: set[str] = set()
    for pos, output in enumerate(outputs):
        if not isinstance(output, dict):
            issues.append(f"outputs[{pos}] 必须是对象")
            continue
        prompt_id = output.get("prompt_id")
        if prompt_id not in index["prompts"]:
            issues.append(f"outputs[{pos}] 引用了不存在的提示词 {prompt_id}")
        if prompt_id in seen_outputs:
            issues.append(f"outputs 重复提示词 {prompt_id}")
        seen_outputs.add(prompt_id)
        status = output.get("status")
        if status not in OUTPUT_STATUSES:
            issues.append(f"outputs[{pos}].status 不合法：{status}")
        if status == "succeeded":
            uri = output.get("uri")
            if not nonempty(uri):
                issues.append(f"outputs[{pos}] 成功状态必须包含 uri")
            elif not uri.startswith(("http://", "https://")):
                candidate = Path(uri)
                if not candidate.is_absolute():
                    candidate = manifest_path.parent / candidate
                if not candidate.exists():
                    issues.append(f"outputs[{pos}] 图片不存在：{uri}")
        elif status == "failed" and not nonempty(output.get("error")):
            issues.append(f"outputs[{pos}] 失败状态必须包含 error")

    selected_ids = {entry["prompt_id"] for entry in selected_entries(data)}
    for prompt_id in selected_ids:
        missing_deps = index["dependencies"][prompt_id] - selected_ids
        if missing_deps:
            issues.append(f"已选提示词 {prompt_id} 缺少依赖：{', '.join(sorted(missing_deps))}")
    state, missing_core = readiness(data)
    production["readiness"] = state
    if state == "ready" and missing_core:
        issues.append("ready 状态不能存在缺失核心资产")
    if require_ready and state != "ready":
        issues.append(f"生产资产尚未 ready：{state}; 缺失核心资产 {', '.join(missing_core) or '无'}")
    if require_scene_coverage:
        issues.extend(scene_coverage_issues(data))
    return issues


def plan(data: dict[str, Any]) -> dict[str, Any]:
    index_manifest(data)
    previous = data.get("production") if isinstance(data.get("production"), dict) else {}
    data["production"] = {
        "selection_status": "draft",
        "selection": build_selection(data),
        "outputs": previous.get("outputs", []),
        "readiness": "awaiting_approval",
    }
    return data


def approve(data: dict[str, Any], include: set[str], exclude: set[str]) -> dict[str, Any]:
    if not isinstance(data.get("production"), dict):
        plan(data)
    index = index_manifest(data)
    selection = data["production"]["selection"]
    known = {entry["prompt_id"] for entry in selection}
    unknown = (include | exclude) - known
    if unknown:
        raise AssetError(f"未知图片提示词：{', '.join(sorted(unknown))}")
    requested = {
        entry["prompt_id"]
        for entry in selection
        if entry.get("selected") and entry["prompt_id"] not in exclude
    } | include
    selected = dependency_closure(requested, index["dependencies"])
    for entry in selection:
        prompt_id = entry["prompt_id"]
        entry["selected"] = prompt_id in selected
        if prompt_id in include and entry.get("tier") != "core":
            entry["reason"] = "用户在确认时加入"
        if prompt_id in selected and prompt_id not in requested:
            entry["reason"] = "被已选资产依赖"
    data["production"]["selection_status"] = "approved"
    data["production"]["readiness"] = readiness(data)[0]
    return data


def queue(data: dict[str, Any]) -> list[dict[str, Any]]:
    index = index_manifest(data)
    production = data.get("production")
    if not isinstance(production, dict) or production.get("selection_status") != "approved":
        raise AssetError("资产清单尚未确认")
    selected = {entry["prompt_id"]: entry for entry in selected_entries(data)}
    outputs = output_map(data)
    ordered: list[str] = []
    visited: set[str] = set()

    def visit(prompt_id: str) -> None:
        if prompt_id in visited:
            return
        for dependency in index["dependencies"][prompt_id]:
            if dependency in selected:
                visit(dependency)
        visited.add(prompt_id)
        ordered.append(prompt_id)

    for prompt_id in index["prompt_order"]:
        if prompt_id in selected:
            visit(prompt_id)

    result: list[dict[str, Any]] = []
    for prompt_id in ordered:
        deps = index["dependencies"][prompt_id]
        output = outputs.get(prompt_id, {})
        if output.get("status") in OUTPUT_STATUSES:
            state = output["status"]
        elif any(outputs.get(dep, {}).get("status") in {"failed", "skipped"} for dep in deps):
            state = "blocked"
        elif all(outputs.get(dep, {}).get("status") == "succeeded" for dep in deps):
            state = "ready"
        else:
            state = "waiting"
        prompt = index["prompts"][prompt_id]["prompt"]
        result.append(
            {
                "prompt_id": prompt_id,
                "asset_id": index["prompts"][prompt_id]["asset_id"],
                "label": prompt.get("label", prompt_id),
                "mode": prompt.get("mode"),
                "dependencies": sorted(deps),
                "state": state,
                "text": prompt.get("text"),
            }
        )
    return result


def record(
    data: dict[str, Any], prompt_id: str, status: str, uri: str | None, error: str | None
) -> dict[str, Any]:
    index = index_manifest(data)
    selected = {entry["prompt_id"] for entry in selected_entries(data)}
    if prompt_id not in selected:
        raise AssetError(f"提示词未被选择：{prompt_id}")
    if status not in OUTPUT_STATUSES:
        raise AssetError(f"不支持的状态：{status}")
    if status == "succeeded" and not nonempty(uri):
        raise AssetError("成功状态必须提供 --uri")
    if status == "failed" and not nonempty(error):
        raise AssetError("失败状态必须提供 --error")
    output: dict[str, Any] = {"prompt_id": prompt_id, "status": status}
    if uri:
        output["uri"] = uri
    if error:
        output["error"] = error
    output["dependencies"] = sorted(index["dependencies"][prompt_id])
    outputs = data["production"].setdefault("outputs", [])
    for pos, existing in enumerate(outputs):
        if existing.get("prompt_id") == prompt_id:
            outputs[pos] = output
            break
    else:
        outputs.append(output)
    data["production"]["readiness"] = readiness(data)[0]
    return data


def relative_href(uri: str, manifest_path: Path, output_path: Path) -> tuple[str | None, bool]:
    if uri.startswith(("http://", "https://")):
        return uri, True
    source = Path(uri)
    if not source.is_absolute():
        source = manifest_path.parent / source
    try:
        href = os.path.relpath(source, output_path.parent)
    except ValueError:
        href = str(source)
    return Path(href).as_posix(), source.exists()


def json_for_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def render_asset_report_html(data: dict[str, Any], manifest_path: Path, output_path: Path) -> str:
    index = index_manifest(data)
    production = data.get("production") if isinstance(data.get("production"), dict) else {}
    selection = {
        item.get("prompt_id"): item
        for item in production.get("selection", [])
        if isinstance(item, dict)
    }
    outputs = output_map(data)
    esc = lambda value: html.escape(str(value or ""), quote=True)
    role_labels = {
        "scene_panorama": "全景定场图",
        "scene_coverage_grid": "九宫格机位图",
    }
    cards: list[str] = []
    stats = Counter()
    for prompt_id in index["prompt_order"]:
        info = index["prompts"][prompt_id]
        prompt = info["prompt"]
        if (prompt.get("output_spec") or {}).get("media_type") != "image":
            continue
        selected = selection.get(prompt_id, {})
        output = outputs.get(prompt_id, {})
        tier = selected.get("tier", "optional")
        status = output.get("status", "pending" if selected.get("selected") else "not_selected")
        role = prompt.get("production_role", "")
        uri = output.get("uri") if output.get("status") == "succeeded" else ""
        href, exists = relative_href(uri, manifest_path, output_path) if uri else (None, False)
        image = (
            f'<button class="image" data-full="{esc(href)}"><img loading="lazy" src="{esc(href)}" alt="{esc(prompt.get("label", prompt_id))}"></button>'
            if href and exists
            else '<div class="image missing">图片尚未生成</div>'
        )
        asset = info["asset"]
        search = " ".join(
            str(value or "")
            for value in (prompt_id, asset.get("id"), asset.get("name"), prompt.get("label"), selected.get("reason"), role)
        ).lower()
        stats["total"] += 1
        stats[tier] += 1
        stats[status] += 1
        cards.append(
            f'<article class="card" data-tier="{esc(tier)}" data-status="{esc(status)}" data-type="{esc(asset.get("type"))}" data-search="{esc(search)}">'
            f'{image}<div class="body"><div class="eyebrow">{esc(asset.get("type"))} · {esc(asset.get("id"))} · {esc(tier)}</div>'
            f'<h2>{esc(asset.get("name"))}</h2><h3>{esc(prompt.get("label", prompt_id))}</h3>'
            f'<p class="meta">{esc(role_labels.get(role, role or "普通资产图"))} · {esc(status)} · {esc(selected.get("reason", "未进入选择流程"))}</p>'
            f'<div class="prompt"><button class="copy">复制当前提示词</button><pre class="zh">{esc(prompt.get("text"))}</pre><pre class="en" hidden>{esc(prompt.get("text_en"))}</pre></div>'
            f'<details><summary>输出与依赖</summary><p>{esc(json.dumps(prompt.get("output_spec", {}), ensure_ascii=False))}</p><p>{esc(", ".join(sorted(index["dependencies"][prompt_id])) or "无依赖")}</p></details>'
            '</div></article>'
        )
    issues = validate_production(data, manifest_path) + scene_coverage_issues(data)
    issue_html = "".join(f"<li>{esc(issue)}</li>" for issue in issues) or "<li>结构与场景定场检查通过</li>"
    title = data.get("title") or manifest_path.stem
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · 固定资产报告</title><style>
:root{{--paper:#ebe8e1;--ink:#252725;--muted:#686963;--rust:#9e3d2d;--line:#c9c3b8;--card:#f6f3ed}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}header{{position:sticky;top:0;z-index:5;background:#ebe8e1ee;backdrop-filter:blur(10px);border-bottom:2px solid var(--ink);padding:18px 24px}}h1,h2,h3{{margin:.15em 0}}h1{{font:700 24px/1.2 Georgia,"Songti SC",serif}}button,input,select{{font:inherit}}nav,.tools{{display:flex;gap:9px;flex-wrap:wrap;margin-top:13px}}button,input,select{{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:8px 11px;border-radius:3px}}button{{cursor:pointer}}button:hover{{border-color:var(--rust);color:var(--rust)}}main{{max-width:1600px;margin:auto;padding:24px}}.kpis{{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:10px;margin-bottom:18px}}.kpi{{border-top:4px solid var(--rust);background:var(--card);padding:14px}}.kpi b{{font:700 28px Georgia,serif;display:block}}.kpi span,.meta,.eyebrow{{color:var(--muted)}}.issues{{border-left:5px solid var(--rust);background:#f5ded7;padding:10px 16px;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}.card{{background:var(--card);border:1px solid var(--line);break-inside:avoid}}.image{{display:block;width:100%;padding:0;border:0;background:#d8d3c9;min-height:220px}}.image img{{display:block;width:100%;aspect-ratio:16/9;object-fit:contain;background:#242522}}.image.missing{{display:grid;place-items:center;color:var(--muted)}}.body{{padding:16px}}.eyebrow{{font:12px ui-monospace,SFMono-Regular,monospace;letter-spacing:.06em;text-transform:uppercase}}.prompt{{position:relative;margin-top:12px}}.copy{{float:right;margin:0 0 7px 8px}}pre{{clear:both;white-space:pre-wrap;word-break:break-word;background:#252725;color:#f4f0e8;padding:13px;border-radius:2px;max-height:330px;overflow:auto}}details{{border-top:1px solid var(--line);margin-top:12px;padding-top:9px}}dialog{{border:0;padding:0;background:#111;max-width:95vw;max-height:95vh}}dialog img{{display:block;max-width:95vw;max-height:90vh}}@media(max-width:850px){{.grid{{grid-template-columns:1fr}}.kpis{{grid-template-columns:1fr 1fr}}main{{padding:14px}}}}@media print{{header button,.tools,.copy{{display:none}}header{{position:static}}pre{{max-height:none}}.card{{page-break-inside:avoid}}}}@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important}}}}
</style></head><body><header><h1>{esc(title)} · 固定资产报告</h1><div class="meta">{esc(production.get("readiness", "未进入生产"))} · 全景定场与反打机位检查</div><nav><button id="lang">中文 / English</button><button id="export">导出 JSON</button></nav></header>
<main><div class="kpis"><div class="kpi"><b>{stats["total"]}</b><span>视觉提示词</span></div><div class="kpi"><b>{stats["core"]}</b><span>核心资产</span></div><div class="kpi"><b>{stats["succeeded"]}</b><span>已生成</span></div><div class="kpi"><b>{len(issues)}</b><span>检查项</span></div></div>
<div class="tools"><input id="search" placeholder="搜索资产、提示词或用途"><select id="filter"><option value="all">全部</option><option value="core">核心</option><option value="optional">可选</option><option value="scene">场景</option><option value="succeeded">已生成</option><option value="missing">未生成</option></select></div>
<section class="issues"><strong>质量门</strong><ul>{issue_html}</ul></section><section class="grid">{"".join(cards) or "<p>没有图片提示词。</p>"}</section></main>
<dialog id="lightbox"><img alt="资产大图"></dialog><script type="application/json" id="report-data">{json_for_script(data)}</script><script>
const data=JSON.parse(document.getElementById('report-data').textContent),cards=[...document.querySelectorAll('.card')];let english=false;
function apply(){{const q=document.getElementById('search').value.trim().toLowerCase(),f=document.getElementById('filter').value;cards.forEach(c=>{{const ok=f==='all'||(f==='core'||f==='optional'?c.dataset.tier===f:f==='scene'?c.dataset.type==='S':f==='succeeded'?c.dataset.status==='succeeded':c.dataset.status!=='succeeded');c.hidden=!ok||(q&&!c.dataset.search.includes(q))}})}}
document.getElementById('search').oninput=apply;document.getElementById('filter').onchange=apply;
document.getElementById('lang').onclick=()=>{{english=!english;document.querySelectorAll('.zh').forEach(x=>x.hidden=english);document.querySelectorAll('.en').forEach(x=>x.hidden=!english)}};
document.querySelectorAll('.copy').forEach(b=>b.onclick=async()=>{{const p=b.closest('.prompt'),t=[...p.querySelectorAll('pre')].find(x=>!x.hidden)?.textContent||'';try{{await navigator.clipboard.writeText(t)}}catch{{const a=document.createElement('textarea');a.value=t;document.body.append(a);a.select();document.execCommand('copy');a.remove()}}b.textContent='已复制';setTimeout(()=>b.textContent='复制当前提示词',900)}});
document.getElementById('export').onclick=()=>{{const blob=new Blob([JSON.stringify(data,null,2)],{{type:'application/json'}}),a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download='asset-manifest.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}};
const box=document.getElementById('lightbox');document.querySelectorAll('[data-full]').forEach(b=>b.onclick=()=>{{box.querySelector('img').src=b.dataset.full;box.showModal()}});box.onclick=()=>box.close();
</script></body></html>'''


def parse_ids(value: str | None) -> set[str]:
    return {item.strip() for item in (value or "").split(",") if item.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "approve", "queue", "record", "validate", "render"):
        command = sub.add_parser(name)
        command.add_argument("manifest", type=Path)
        if name in {"plan", "approve", "record"}:
            command.add_argument("--output", type=Path, required=True)
    approve_cmd = sub.choices["approve"]
    approve_cmd.add_argument("--include", help="逗号分隔的额外 prompt_id")
    approve_cmd.add_argument("--exclude", help="逗号分隔的排除 prompt_id")
    record_cmd = sub.choices["record"]
    record_cmd.add_argument("--prompt-id", required=True)
    record_cmd.add_argument("--status", choices=sorted(OUTPUT_STATUSES), required=True)
    record_cmd.add_argument("--uri")
    record_cmd.add_argument("--error")
    sub.choices["validate"].add_argument("--require-ready", action="store_true")
    sub.choices["validate"].add_argument("--require-scene-coverage", action="store_true")
    sub.choices["render"].add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = load_json(args.manifest)
        if args.command == "plan":
            write_json(args.output, plan(data))
            print(args.output.resolve())
        elif args.command == "approve":
            write_json(args.output, approve(data, parse_ids(args.include), parse_ids(args.exclude)))
            print(args.output.resolve())
        elif args.command == "queue":
            print(json.dumps(queue(data), ensure_ascii=False, indent=2))
        elif args.command == "record":
            write_json(args.output, record(data, args.prompt_id, args.status, args.uri, args.error))
            print(args.output.resolve())
        elif args.command == "validate":
            issues = validate_production(
                data,
                args.manifest,
                args.require_ready,
                args.require_scene_coverage,
            )
            print(json.dumps({"valid": not issues, "issues": issues}, ensure_ascii=False, indent=2))
            return 1 if issues else 0
        elif args.command == "render":
            if args.output.exists():
                raise AssetError(f"输出文件已存在，拒绝覆盖：{args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                render_asset_report_html(data, args.manifest, args.output),
                encoding="utf-8",
            )
            print(args.output.resolve())
    except AssetError as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
