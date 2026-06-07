# -*- coding: utf-8 -*-
from __future__ import print_function

import codecs
import json
import os
import shutil
import sys
import traceback

import arcpy


def main():
    mode, mxd_path, output_dir, config_path = sys.argv[1:5]
    result_path = os.path.join(output_dir, "result.json")
    try:
        if mode == "inspect":
            result = inspect_mxd(mxd_path)
        elif mode == "polish":
            config = read_json(config_path)
            result = polish_mxd(mxd_path, output_dir, config)
        else:
            raise ValueError("Unsupported mode: {0}".format(mode))
        write_json(result_path, result)
    except Exception:
        write_json(result_path, {
            "layers": [],
            "layout_elements": [],
            "output_mxd": "",
            "output_png": "",
            "changes": [],
            "warnings": [],
            "errors": [traceback.format_exc()],
        })
        raise


def inspect_mxd(mxd_path):
    mxd = arcpy.mapping.MapDocument(mxd_path)
    warnings = []
    layers = []

    for layer in arcpy.mapping.ListLayers(mxd):
        layers.append(layer.name)
        try:
            if layer.isBroken:
                warnings.append(u"图层数据源失效：{0}".format(layer.name))
        except Exception:
            pass

    layout_elements = []
    for element in arcpy.mapping.ListLayoutElements(mxd):
        layout_elements.append({
            "name": element.name,
            "type": element.type,
        })

    del mxd
    return {
        "layers": layers,
        "layout_elements": layout_elements,
        "warnings": warnings,
        "changes": [],
        "errors": [],
    }


def polish_mxd(mxd_path, output_dir, config):
    base_name = os.path.splitext(os.path.basename(mxd_path))[0]
    output_mxd = os.path.join(output_dir, base_name + "_polished.mxd")
    output_png = os.path.join(output_dir, base_name + "_polished.png")
    shutil.copy2(mxd_path, output_mxd)

    mxd = arcpy.mapping.MapDocument(output_mxd)
    changes = []
    warnings = []
    errors = []

    if config.get("rules", {}).get("layout", True):
        apply_layout_rules(mxd, config.get("layout_options", {}), changes, warnings)
    if config.get("rules", {}).get("symbol", True):
        apply_symbol_rules(mxd, config.get("layer_mapping", {}), changes, warnings)
    apply_auto_actions(mxd, config.get("auto_actions", []), config.get("layer_mapping", {}), changes, warnings)

    mxd.save()
    try:
        arcpy.mapping.ExportToPNG(mxd, output_png, resolution=150)
        changes.append(u"已导出 PNG 预览图。")
    except Exception as exc:
        warnings.append(u"PNG 导出失败：{0}".format(exc))

    del mxd
    return {
        "layers": [],
        "layout_elements": [],
        "output_mxd": output_mxd,
        "output_png": output_png if os.path.exists(output_png) else "",
        "changes": changes,
        "warnings": warnings,
        "errors": errors,
    }


def apply_layout_rules(mxd, layout_options, changes, warnings):
    title = layout_options.get("title") or u"MapPolish 自动优化地图"
    data_source = layout_options.get("data_source") or u"数据来源：请补充"
    map_time = layout_options.get("map_time") or u"制图时间：请补充"

    text_elements = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")
    if not text_elements:
        warnings.append(u"当前 MXD 没有可克隆的文本元素；ArcMap arcpy.mapping 无法从零创建文本元素。")
        return

    ensure_text(text_elements, u"title", title, changes)
    ensure_text(text_elements, u"source", data_source, changes)
    ensure_text(text_elements, u"time", map_time, changes)


def ensure_text(text_elements, name_hint, text_value, changes):
    existing = None
    for element in text_elements:
        haystack = (element.name + u" " + element.text).lower()
        if name_hint in haystack:
            existing = element
            break

    if existing:
        if not existing.text.strip():
            existing.text = text_value
            changes.append(u"已补充文本元素：{0}".format(text_value))
        return

    try:
        clone = text_elements[0].clone("_mappolish_" + name_hint)
        clone.text = text_value
        clone.name = "mappolish_" + name_hint
        changes.append(u"已新增文本元素：{0}".format(text_value))
    except Exception as exc:
        changes.append(u"未新增文本元素 {0}，原因：{1}".format(text_value, exc))


def apply_symbol_rules(mxd, layer_mapping, changes, warnings):
    layer_by_name = {}
    for layer in arcpy.mapping.ListLayers(mxd):
        layer_by_name[layer.name] = layer

    role_transparency = {
        "admin_boundary": 55,
        "dem": 20,
        "rainfall_or_flood": 35,
    }

    for role, layer_name in layer_mapping.items():
        if not layer_name:
            continue
        layer = layer_by_name.get(layer_name)
        if not layer:
            warnings.append(u"未找到映射图层：{0}".format(layer_name))
            continue

        if role in role_transparency:
            try:
                layer.transparency = role_transparency[role]
                changes.append(u"已设置 {0} 透明度为 {1}%。".format(layer.name, role_transparency[role]))
            except Exception as exc:
                warnings.append(u"设置 {0} 透明度失败：{1}".format(layer.name, exc))
        elif role in ("water", "watershed_boundary", "study_area"):
            try:
                layer.visible = True
                changes.append(u"已确认 {0} 可见；线宽/颜色建议仍需在 ArcMap 中按图层类型精修。".format(layer.name))
            except Exception as exc:
                warnings.append(u"设置 {0} 可见性失败：{1}".format(layer.name, exc))

    warnings.append(u"复杂色带、分类渲染和高级标注规则本版只输出建议，不强制重写。")


def apply_auto_actions(mxd, auto_actions, layer_mapping, changes, warnings):
    if not auto_actions:
        return

    text_elements = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")
    layer_by_name = {}
    for layer in arcpy.mapping.ListLayers(mxd):
        layer_by_name[layer.name] = layer

    for action in auto_actions:
        if not isinstance(action, dict):
            warnings.append(u"跳过非结构化 action：{0}".format(action))
            continue

        action_type = action.get("type", "")
        params = action.get("params") if isinstance(action.get("params"), dict) else {}

        if action_type in ("add_layout_text", "set_text_element"):
            text_value = params.get("text") or action.get("reason") or u"请补充"
            field = params.get("field") or action.get("target_role") or u"note"
            if text_elements:
                ensure_text(text_elements, unicode(field), unicode(text_value), changes)
            else:
                warnings.append(u"无法执行文本 action，当前布局没有可克隆文本元素。")
        elif action_type == "set_layer_visibility":
            layer = resolve_action_layer(action, params, layer_mapping, layer_by_name)
            if layer:
                try:
                    layer.visible = bool(params.get("visible", True))
                    changes.append(u"已按模型动作设置 {0} 可见性。".format(layer.name))
                except Exception as exc:
                    warnings.append(u"设置图层可见性失败：{0}".format(exc))
            else:
                warnings.append(u"模型动作未匹配到图层：{0}".format(action))
        elif action_type == "set_layer_transparency":
            layer = resolve_action_layer(action, params, layer_mapping, layer_by_name)
            if layer:
                try:
                    transparency = int(params.get("transparency", 0))
                    layer.transparency = max(0, min(100, transparency))
                    changes.append(u"已按模型动作设置 {0} 透明度。".format(layer.name))
                except Exception as exc:
                    warnings.append(u"设置图层透明度失败：{0}".format(exc))
            else:
                warnings.append(u"模型动作未匹配到图层：{0}".format(action))
        elif action_type == "emphasize_layer":
            layer = resolve_action_layer(action, params, layer_mapping, layer_by_name)
            if layer:
                try:
                    layer.visible = True
                    if hasattr(layer, "transparency"):
                        layer.transparency = 0
                    changes.append(u"已按模型动作突出显示图层：{0}。".format(layer.name))
                except Exception as exc:
                    warnings.append(u"突出显示图层失败：{0}".format(exc))
            else:
                warnings.append(u"模型动作未匹配到图层：{0}".format(action))
        elif action_type == "set_layer_label_visibility":
            layer = resolve_action_layer(action, params, layer_mapping, layer_by_name)
            if layer:
                try:
                    layer.showLabels = bool(params.get("enabled", True))
                    changes.append(u"已按模型动作设置 {0} 标注开关。".format(layer.name))
                except Exception as exc:
                    warnings.append(u"设置标注开关失败：{0}".format(exc))
            else:
                warnings.append(u"模型动作未匹配到图层：{0}".format(action))
        elif action_type == "set_layer_order":
            layer = resolve_action_layer(action, params, layer_mapping, layer_by_name)
            if layer:
                move_layer_by_position(mxd, layer, params.get("position", "TOP"), changes, warnings)
            else:
                warnings.append(u"模型动作未匹配到图层：{0}".format(action))
        elif action_type == "export_preview":
            changes.append(u"模型动作要求导出预览图，已由主流程统一导出。")
        else:
            warnings.append(u"跳过不支持的模型 action：{0}".format(action_type))


def resolve_action_layer(action, params, layer_mapping, layer_by_name):
    layer_name = params.get("layer_name") or layer_mapping.get(action.get("target_role", ""))
    if not layer_name:
        return None
    return layer_by_name.get(layer_name)


def move_layer_by_position(mxd, layer, position, changes, warnings):
    position = unicode(position or "TOP").upper()
    for data_frame in arcpy.mapping.ListDataFrames(mxd):
        layers = arcpy.mapping.ListLayers(mxd, "", data_frame)
        if layer not in layers or len(layers) < 2:
            continue
        try:
            if position == "BOTTOM":
                reference = layers[-1]
                insert_position = "AFTER"
            else:
                reference = layers[0]
                insert_position = "BEFORE"
            if reference == layer:
                changes.append(u"图层 {0} 已在目标顺序位置。".format(layer.name))
                return
            arcpy.mapping.MoveLayer(data_frame, reference, layer, insert_position)
            changes.append(u"已按模型动作调整图层顺序：{0}。".format(layer.name))
            return
        except Exception as exc:
            warnings.append(u"调整图层顺序失败：{0}".format(exc))
            return
    warnings.append(u"未找到可调整顺序的数据框图层：{0}".format(layer.name))


def read_json(path):
    with codecs.open(path, "r", "utf-8") as file_obj:
        return json.load(file_obj)


def write_json(path, payload):
    with codecs.open(path, "w", "utf-8") as file_obj:
        file_obj.write(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
