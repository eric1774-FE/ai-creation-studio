#!/usr/bin/env python3
"""Validate or render a story-asset Manifest V2 as one offline HTML report."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "story-asset-manifest/v2"
ASSET_TYPES = {"G", "C", "W", "S", "P", "V", "E", "L", "F", "A"}
ENTITY_TYPES = {"character", "scene"}
IMPORTANCE_LEVELS = {"A", "B", "C"}
W_SUBTYPES = {"costume", "hair", "makeup"}
FACT_SOURCES = {"user", "source_text", "style_bible", "inference", "creative"}
FACT_STATUSES = {"confirmed", "estimated", "pending", "conflict"}
PROMPT_MODES = {"generate", "edit"}
INPUT_SOURCE_KINDS = {"reference_input", "prompt_output"}
MEDIA_TYPES = {"image", "audio"}
REFERENCE_ROLES = {"identity", "style", "costume", "scene"}
RENDER_MODES = {"live_action", "2d_comic", "3d_animation", "hybrid"}
COVERAGE_STATUSES = {"present", "none"}
QUALITY_STATUSES = {"pass", "warning", "pending"}


class ManifestError(ValueError):
    pass


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{path} 必须是对象")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ManifestError(f"{path} 必须是数组")
    return value


def _string(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ManifestError(f"{path} 必须是{'' if allow_empty else '非空'}字符串")
    return value


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ManifestError(f"{path} 必须是大于等于 {minimum} 的整数")
    return value


def _number(value: Any, path: str, *, minimum: float = 0) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < minimum:
        raise ManifestError(f"{path} 必须是大于等于 {minimum} 的数字")
    return value


def _optional_string(obj: dict[str, Any], key: str, path: str) -> None:
    if key in obj:
        _string(obj[key], f"{path}.{key}", allow_empty=True)


def _string_list(value: Any, path: str) -> None:
    for index, item in enumerate(_list(value, path)):
        _string(item, f"{path}[{index}]")


def _validate_fact_list(value: Any, path: str) -> None:
    keys: set[str] = set()
    for index, item in enumerate(_list(value, path)):
        fact_path = f"{path}[{index}]"
        fact = _object(item, fact_path)
        key = _string(fact.get("key"), f"{fact_path}.key")
        if key in keys:
            raise ManifestError(f"{path} 重复事实键：{key}")
        keys.add(key)
        fact_value = fact.get("value")
        if isinstance(fact_value, (dict, list)) or fact_value is None:
            raise ManifestError(f"{fact_path}.value 必须是字符串、数字或布尔值")
        if not isinstance(fact_value, (str, int, float, bool)):
            raise ManifestError(f"{fact_path}.value 必须是字符串、数字或布尔值")
        _optional_string(fact, "unit", fact_path)
        source = _string(fact.get("source"), f"{fact_path}.source")
        if source not in FACT_SOURCES:
            raise ManifestError(f"{fact_path}.source 必须是 {sorted(FACT_SOURCES)} 之一")
        status = _string(fact.get("status"), f"{fact_path}.status")
        if status not in FACT_STATUSES:
            raise ManifestError(f"{fact_path}.status 必须是 {sorted(FACT_STATUSES)} 之一")
        _string(fact.get("evidence"), f"{fact_path}.evidence")
        if source == "source_text":
            _string(fact.get("source_locator"), f"{fact_path}.source_locator")
        else:
            _optional_string(fact, "source_locator", fact_path)


def _validate_ref(
    value: Any,
    path: str,
    version_keys: set[tuple[str, str]],
) -> tuple[str, str]:
    ref = _object(value, path)
    asset_id = _string(ref.get("asset_id"), f"{path}.asset_id")
    version = _string(ref.get("version"), f"{path}.version")
    _string(ref.get("relation_label"), f"{path}.relation_label")
    key = (asset_id, version)
    if key not in version_keys:
        raise ManifestError(f"{path} 引用了不存在的资产版本 {asset_id}-{version}")
    return key


def _validate_ref_list(
    value: Any,
    path: str,
    version_keys: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(_list(value, path)):
        key = _validate_ref(item, f"{path}[{index}]", version_keys)
        if key in seen:
            raise ManifestError(f"{path} 重复引用了 {key[0]}-{key[1]}")
        seen.add(key)
    return seen


def _validate_prompt_graph(dependencies: dict[str, set[str]]) -> None:
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(prompt_id: str) -> None:
        if prompt_id in visited:
            return
        if prompt_id in visiting:
            raise ManifestError(f"提示词依赖存在循环：{prompt_id}")
        visiting.add(prompt_id)
        for dependency in dependencies[prompt_id]:
            visit(dependency)
        visiting.remove(prompt_id)
        visited.add(prompt_id)

    for prompt_id in dependencies:
        visit(prompt_id)


def validate_manifest(value: Any) -> dict[str, Any]:
    data = _object(value, "manifest")
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ManifestError(f"schema_version 必须是 {SCHEMA_VERSION}")
    _string(data.get("title"), "manifest.title")
    _string(data.get("input_summary"), "manifest.input_summary", allow_empty=True)

    for key in ("constraints", "pending_questions"):
        _string_list(data.get(key, []), f"manifest.{key}")

    for index, item in enumerate(_list(data.get("aliases", []), "manifest.aliases")):
        path = f"manifest.aliases[{index}]"
        alias = _object(item, path)
        _string(alias.get("alias"), f"{path}.alias")
        _string(alias.get("canonical"), f"{path}.canonical")
        _optional_string(alias, "note", path)

    reference_ids: set[str] = set()
    for index, item in enumerate(
        _list(data.get("reference_inputs"), "manifest.reference_inputs")
    ):
        path = f"manifest.reference_inputs[{index}]"
        reference = _object(item, path)
        reference_id = _string(reference.get("id"), f"{path}.id")
        if reference_id in reference_ids:
            raise ManifestError(f"{path}.id 重复：{reference_id}")
        reference_ids.add(reference_id)
        if _string(reference.get("media_type"), f"{path}.media_type") != "image":
            raise ManifestError(f"{path}.media_type 目前只支持 image")
        _string(reference.get("source_ref"), f"{path}.source_ref")
        role = _string(reference.get("role"), f"{path}.role")
        if role not in REFERENCE_ROLES:
            raise ManifestError(f"{path}.role 必须是 {sorted(REFERENCE_ROLES)} 之一")
        _string(reference.get("description"), f"{path}.description")
        _string_list(reference.get("allowed_influence"), f"{path}.allowed_influence")
        _string_list(reference.get("prohibited_influence"), f"{path}.prohibited_influence")
        if not reference["allowed_influence"] or not reference["prohibited_influence"]:
            raise ManifestError(f"{path} 必须分别声明允许影响和禁止影响")

    assets = _list(data.get("assets"), "manifest.assets")
    asset_ids: set[str] = set()
    asset_types: dict[str, str] = {}
    version_keys: set[tuple[str, str]] = set()
    type_counts = {asset_type: 0 for asset_type in ASSET_TYPES}
    prompt_ids: set[str] = set()
    prompt_inputs: dict[str, list[dict[str, Any]]] = {}
    prompt_text_owners: dict[str, dict[str, str]] = {"text": {}, "text_en": {}}

    for asset_index, item in enumerate(assets):
        path = f"manifest.assets[{asset_index}]"
        asset = _object(item, path)
        asset_id = _string(asset.get("id"), f"{path}.id")
        if asset_id in asset_ids:
            raise ManifestError(f"{path}.id 重复：{asset_id}")
        asset_ids.add(asset_id)
        asset_type = _string(asset.get("type"), f"{path}.type")
        if asset_type not in ASSET_TYPES:
            raise ManifestError(f"{path}.type 必须是 {sorted(ASSET_TYPES)} 之一")
        asset_types[asset_id] = asset_type
        type_counts[asset_type] += 1
        _string(asset.get("name"), f"{path}.name")
        _optional_string(asset, "first_appearance", path)
        _string(asset.get("definition"), f"{path}.definition")
        _string_list(asset.get("anchors"), f"{path}.anchors")
        _validate_fact_list(asset.get("facts"), f"{path}.facts")
        if asset_type in {"C", "S"}:
            importance = _string(asset.get("importance_level"), f"{path}.importance_level")
            if importance not in IMPORTANCE_LEVELS:
                raise ManifestError(
                    f"{path}.importance_level 必须是 {sorted(IMPORTANCE_LEVELS)} 之一"
                )
        elif "importance_level" in asset:
            raise ManifestError(f"{path}.importance_level 只适用于 C 或 S")
        if asset_type == "W":
            subtype = _string(asset.get("subtype"), f"{path}.subtype")
            if subtype not in W_SUBTYPES:
                raise ManifestError(f"{path}.subtype 必须是 {sorted(W_SUBTYPES)} 之一")
        elif "subtype" in asset:
            raise ManifestError(f"{path}.subtype 只适用于 W")

        versions = _list(asset.get("versions"), f"{path}.versions")
        if not versions:
            raise ManifestError(f"{path}.versions 至少包含一个版本")
        local_versions: set[str] = set()
        for version_index, version_item in enumerate(versions):
            version_path = f"{path}.versions[{version_index}]"
            version_item = _object(version_item, version_path)
            version_id = _string(version_item.get("id"), f"{version_path}.id")
            if version_id in local_versions:
                raise ManifestError(f"{version_path}.id 重复：{version_id}")
            local_versions.add(version_id)
            version_keys.add((asset_id, version_id))
            _string(version_item.get("label"), f"{version_path}.label")
            _optional_string(version_item, "story_stage", version_path)
            _optional_string(version_item, "changes", version_path)
            _validate_fact_list(version_item.get("facts"), f"{version_path}.facts")
            prompts = _list(version_item.get("prompts"), f"{version_path}.prompts")
            if not prompts:
                raise ManifestError(f"{version_path}.prompts 至少包含一条提示词")
            for prompt_index, prompt_item in enumerate(prompts):
                prompt_path = f"{version_path}.prompts[{prompt_index}]"
                prompt = _object(prompt_item, prompt_path)
                prompt_id = _string(prompt.get("id"), f"{prompt_path}.id")
                if prompt_id in prompt_ids:
                    raise ManifestError(f"{prompt_path}.id 重复：{prompt_id}")
                prompt_ids.add(prompt_id)
                _string(prompt.get("label"), f"{prompt_path}.label")
                mode = _string(prompt.get("mode"), f"{prompt_path}.mode")
                if mode not in PROMPT_MODES:
                    raise ManifestError(f"{prompt_path}.mode 必须是 generate 或 edit")
                inputs = _list(prompt.get("input_refs"), f"{prompt_path}.input_refs")
                if mode == "edit" and not inputs:
                    raise ManifestError(f"{prompt_path}.input_refs 编辑提示词至少需要一个输入")
                seen_inputs: set[tuple[str, str]] = set()
                normalized_inputs: list[dict[str, Any]] = []
                for input_index, input_item in enumerate(inputs):
                    input_path = f"{prompt_path}.input_refs[{input_index}]"
                    input_ref = _object(input_item, input_path)
                    source_kind = _string(input_ref.get("source_kind"), f"{input_path}.source_kind")
                    if source_kind not in INPUT_SOURCE_KINDS:
                        raise ManifestError(
                            f"{input_path}.source_kind 必须是 reference_input 或 prompt_output"
                        )
                    ref_id = _string(input_ref.get("ref_id"), f"{input_path}.ref_id")
                    _string(input_ref.get("role"), f"{input_path}.role")
                    input_key = (source_kind, ref_id)
                    if input_key in seen_inputs:
                        raise ManifestError(f"{prompt_path}.input_refs 重复输入 {ref_id}")
                    seen_inputs.add(input_key)
                    normalized_inputs.append(input_ref)
                prompt_inputs[prompt_id] = normalized_inputs
                output = _object(prompt.get("output_spec"), f"{prompt_path}.output_spec")
                media_type = _string(output.get("media_type"), f"{prompt_path}.output_spec.media_type")
                if media_type not in MEDIA_TYPES:
                    raise ManifestError(
                        f"{prompt_path}.output_spec.media_type 必须是 image 或 audio"
                    )
                _integer(output.get("count"), f"{prompt_path}.output_spec.count", minimum=1)
                if media_type == "image":
                    _string(output.get("layout"), f"{prompt_path}.output_spec.layout")
                    _string(output.get("aspect_ratio"), f"{prompt_path}.output_spec.aspect_ratio")
                else:
                    if "duration_seconds" in output:
                        _number(
                            output["duration_seconds"],
                            f"{prompt_path}.output_spec.duration_seconds",
                            minimum=0.001,
                        )
                    if "loopable" in output and not isinstance(output["loopable"], bool):
                        raise ManifestError(f"{prompt_path}.output_spec.loopable 必须是布尔值")
                for field, markers in (
                    ("text", ("风格：", "负面约束：")),
                    ("text_en", ("Style:", "Negative constraints:")),
                ):
                    prompt_text = _string(prompt.get(field), f"{prompt_path}.{field}")
                    missing_markers = [marker for marker in markers if marker not in prompt_text]
                    if missing_markers:
                        raise ManifestError(
                            f"{prompt_path}.{field} 缺少明确段落：{', '.join(missing_markers)}"
                        )
                    normalized_text = " ".join(prompt_text.split()).casefold()
                    previous_prompt_id = prompt_text_owners[field].get(normalized_text)
                    if previous_prompt_id:
                        raise ManifestError(
                            f"提示词 {prompt_id} 的 {field} 正文与 {previous_prompt_id} 完全相同；请合并或明确区分"
                        )
                    prompt_text_owners[field][normalized_text] = prompt_id
            _string_list(version_item.get("prohibitions"), f"{version_path}.prohibitions")

    if asset_types.get("G01") != "G":
        raise ManifestError("manifest.assets 必须包含 type 为 G 的 G01")
    global_asset = next(asset for asset in assets if asset["id"] == "G01")
    render_mode = next((fact for fact in global_asset["facts"] if fact["key"] == "render_mode"), None)
    if render_mode is None:
        raise ManifestError("G01.facts 必须包含 render_mode")
    if render_mode["value"] not in RENDER_MODES:
        raise ManifestError(f"G01 render_mode 必须是 {sorted(RENDER_MODES)} 之一")
    if render_mode["status"] != "confirmed":
        raise ManifestError("G01 render_mode 必须为 confirmed")

    dependencies = {prompt_id: set() for prompt_id in prompt_ids}
    for prompt_id, inputs in prompt_inputs.items():
        for input_ref in inputs:
            source_kind = input_ref["source_kind"]
            ref_id = input_ref["ref_id"]
            if source_kind == "reference_input":
                if ref_id not in reference_ids:
                    raise ManifestError(f"提示词 {prompt_id} 引用了不存在的参考输入 {ref_id}")
            else:
                if ref_id not in prompt_ids:
                    raise ManifestError(f"提示词 {prompt_id} 引用了不存在的提示词产物 {ref_id}")
                if ref_id == prompt_id:
                    raise ManifestError(f"提示词 {prompt_id} 不得依赖自身")
                dependencies[prompt_id].add(ref_id)
    _validate_prompt_graph(dependencies)

    coverage_items = _list(
        data.get("asset_type_coverage"), "manifest.asset_type_coverage"
    )
    coverage_types: set[str] = set()
    for index, item in enumerate(coverage_items):
        path = f"manifest.asset_type_coverage[{index}]"
        coverage = _object(item, path)
        asset_type = _string(coverage.get("type"), f"{path}.type")
        if asset_type not in ASSET_TYPES:
            raise ManifestError(f"{path}.type 必须是 {sorted(ASSET_TYPES)} 之一")
        if asset_type in coverage_types:
            raise ManifestError(f"{path}.type 重复：{asset_type}")
        coverage_types.add(asset_type)
        status = _string(coverage.get("status"), f"{path}.status")
        if status not in COVERAGE_STATUSES:
            raise ManifestError(f"{path}.status 必须是 present 或 none")
        count = _integer(coverage.get("count"), f"{path}.count")
        if count != type_counts[asset_type]:
            raise ManifestError(
                f"{path}.count 应为 {type_counts[asset_type]}，实际为 {count}"
            )
        expected_status = "present" if count else "none"
        if status != expected_status:
            raise ManifestError(f"{path}.status 应为 {expected_status}")
        _optional_string(coverage, "note", path)
    if coverage_types != ASSET_TYPES:
        missing = ", ".join(sorted(ASSET_TYPES - coverage_types))
        extra = ", ".join(sorted(coverage_types - ASSET_TYPES))
        detail = missing or extra
        raise ManifestError(f"manifest.asset_type_coverage 必须完整覆盖十类资产：{detail}")

    referenced: set[tuple[str, str]] = set()
    entity_ids: set[str] = set()
    entities = _list(data.get("entities"), "manifest.entities")
    for entity_index, item in enumerate(entities):
        path = f"manifest.entities[{entity_index}]"
        entity = _object(item, path)
        entity_id = _string(entity.get("id"), f"{path}.id")
        if entity_id in entity_ids:
            raise ManifestError(f"{path}.id 重复：{entity_id}")
        entity_ids.add(entity_id)
        entity_type = _string(entity.get("type"), f"{path}.type")
        if entity_type not in ENTITY_TYPES:
            raise ManifestError(f"{path}.type 必须是 character 或 scene")
        _string(entity.get("name"), f"{path}.name")
        _optional_string(entity, "description", path)
        common = _validate_ref_list(
            entity.get("common_asset_refs"),
            f"{path}.common_asset_refs",
            version_keys,
        )
        referenced.update(common)
        entity_refs = set(common)
        states = _list(entity.get("states"), f"{path}.states")
        if not states:
            raise ManifestError(f"{path}.states 至少包含一个状态")
        state_ids: set[str] = set()
        for state_index, state_item in enumerate(states):
            state_path = f"{path}.states[{state_index}]"
            state = _object(state_item, state_path)
            state_id = _string(state.get("id"), f"{state_path}.id")
            if state_id in state_ids:
                raise ManifestError(f"{state_path}.id 重复：{state_id}")
            state_ids.add(state_id)
            _string(state.get("label"), f"{state_path}.label")
            _optional_string(state, "story_stage", state_path)
            state_refs = _validate_ref_list(
                state.get("asset_refs"),
                f"{state_path}.asset_refs",
                version_keys,
            )
            overlap = common & state_refs
            if overlap:
                key = sorted(overlap)[0]
                raise ManifestError(
                    f"{state_path}.asset_refs 与共用资产重复引用 {key[0]}-{key[1]}"
                )
            referenced.update(state_refs)
            entity_refs.update(state_refs)
        required_type = "C" if entity_type == "character" else "S"
        if not any(asset_types[asset_id] == required_type for asset_id, _ in entity_refs):
            raise ManifestError(f"{path} 必须引用至少一个 {required_type} 资产版本")

    referenced.update(
        _validate_ref_list(
            data.get("standalone_asset_refs"),
            "manifest.standalone_asset_refs",
            version_keys,
        )
    )
    unreferenced = version_keys - referenced
    if unreferenced:
        missing = ", ".join(
            f"{asset_id}-{version_id}" for asset_id, version_id in sorted(unreferenced)
        )
        raise ManifestError(f"以下资产版本未被实体、状态或独立资产区引用：{missing}")

    stage_ids: set[str] = set()
    stages = _list(data.get("continuity"), "manifest.continuity")
    if not stages:
        raise ManifestError("manifest.continuity 至少包含一个阶段")
    for index, item in enumerate(stages):
        path = f"manifest.continuity[{index}]"
        stage = _object(item, path)
        stage_id = _string(stage.get("stage_id"), f"{path}.stage_id")
        if stage_id in stage_ids:
            raise ManifestError(f"{path}.stage_id 重复：{stage_id}")
        stage_ids.add(stage_id)
        _string(stage.get("label"), f"{path}.label")
        _string(stage.get("source_locator"), f"{path}.source_locator")
        stage_refs = _validate_ref_list(stage.get("asset_refs"), f"{path}.asset_refs", version_keys)
        if not stage_refs:
            raise ManifestError(f"{path}.asset_refs 至少包含一个资产版本")

    checks = _list(data.get("quality_checks"), "manifest.quality_checks")
    for index, item in enumerate(checks):
        path = f"manifest.quality_checks[{index}]"
        check = _object(item, path)
        _string(check.get("label"), f"{path}.label")
        status = _string(check.get("status"), f"{path}.status")
        if status not in QUALITY_STATUSES:
            raise ManifestError(f"{path}.status 必须是 pass、warning 或 pending")
        _optional_string(check, "note", path)

    return data


def load_and_validate(input_path: Path) -> dict[str, Any]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    return validate_manifest(data)


def _json_for_html(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def build_html(data: dict[str, Any], skill_dir: Path | None = None) -> str:
    validate_manifest(data)
    root = skill_dir or Path(__file__).resolve().parents[1]
    asset_dir = root / "assets" / "prompt-report"
    template = (asset_dir / "template.html").read_text(encoding="utf-8")
    styles = (asset_dir / "styles.css").read_text(encoding="utf-8")
    script = (asset_dir / "app.js").read_text(encoding="utf-8")
    replacements = {
        "__REPORT_TITLE__": html.escape(data["title"], quote=True),
        "__REPORT_STYLES__": styles,
        "__REPORT_DATA__": _json_for_html(data),
        "__REPORT_SCRIPT__": script,
    }
    for placeholder, replacement in replacements.items():
        if template.count(placeholder) != 1:
            raise RuntimeError(f"模板占位符 {placeholder} 必须且只能出现一次")
        template = template.replace(placeholder, replacement)
    return template


def render_file(input_path: Path, output_path: Path) -> None:
    if output_path.exists():
        raise FileExistsError(f"输出文件已存在：{output_path}")
    data = load_and_validate(input_path)
    rendered = build_html(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(rendered)
            temporary = Path(handle.name)
        os.replace(temporary, output_path)
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 JSON Manifest V2")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path, help="目标 HTML；不得已存在")
    action.add_argument("--validate-only", action="store_true", help="只校验，不生成 HTML")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.validate_only:
            load_and_validate(args.input)
            print(f"验证通过：{args.input.resolve()}")
        else:
            render_file(args.input, args.output)
            print(args.output.resolve())
    except (ManifestError, json.JSONDecodeError, OSError, RuntimeError) as error:
        print(f"处理失败：{error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
