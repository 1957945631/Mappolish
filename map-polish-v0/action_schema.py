from schemas import Action, AnalysisResult


ALLOWED_ACTION_TYPES = {
    "add_layout_text",
    "emphasize_layer",
    "set_layer_visibility",
    "set_layer_transparency",
    "export_preview",
    "set_layer_order",
    "set_text_element",
    "set_layer_label_visibility",
}

MANUAL_ACTION_TYPE = "manual_only"


def sanitize_actions(raw_actions: list[dict]) -> tuple[list[Action], list[Action]]:
    auto_actions = []
    manual_actions = []

    for raw_action in raw_actions:
        if not isinstance(raw_action, dict):
            manual_actions.append(
                Action(
                    MANUAL_ACTION_TYPE,
                    "report",
                    {},
                    f"Unsupported action item: {raw_action}",
                )
            )
            continue

        action_type = str(raw_action.get("type", "")).strip()
        target_role = str(raw_action.get("target_role", "")).strip() or "unknown"
        params = raw_action.get("params") if isinstance(raw_action.get("params"), dict) else {}
        reason = str(raw_action.get("reason", "")).strip()

        if action_type in ALLOWED_ACTION_TYPES:
            auto_actions.append(Action(action_type, target_role, params, reason))
        else:
            manual_actions.append(
                Action(
                    MANUAL_ACTION_TYPE,
                    target_role,
                    {},
                    f"Unsupported action '{action_type}': {reason}".strip(),
                )
            )

    return auto_actions, manual_actions


def build_default_actions(result: AnalysisResult) -> tuple[list[Action], list[Action]]:
    auto_actions = [
        Action(
            "add_layout_text",
            "layout",
            {"field": "title", "text": "MapPolish 自动优化地图"},
            "补充或规范布局标题。",
        ),
        Action(
            "add_layout_text",
            "layout",
            {"field": "data_source", "text": "数据来源：请补充"},
            "补充数据来源说明。",
        ),
        Action(
            "export_preview",
            "layout",
            {},
            "导出 PNG 预览图。",
        ),
    ]

    for issue in result.serious_issues + result.improvements:
        element = issue.element
        if "行政" in element:
            auto_actions.append(
                Action(
                    "set_layer_transparency",
                    "admin_boundary",
                    {"transparency": 55},
                    issue.issue,
                )
            )
        elif "水系" in element or "河" in element:
            auto_actions.append(
                Action(
                    "emphasize_layer",
                    "water",
                    {},
                    issue.issue,
                )
            )
        elif "边界" in element or "研究区" in element:
            auto_actions.append(
                Action(
                    "emphasize_layer",
                    "watershed_boundary",
                    {},
                    issue.issue,
                )
            )

    manual_actions = [
        Action("manual_only", "report", {"suggestion": issue.suggestion}, issue.issue)
        for issue in result.optional_polish
    ]
    if not manual_actions:
        manual_actions.append(
            Action("manual_only", "report", {"summary": result.summary}, "保留人工复核建议。")
        )

    return auto_actions, manual_actions


def actions_to_dicts(actions: list[Action]) -> list[dict]:
    return [
        {
            "type": action.type,
            "target_role": action.target_role,
            "params": action.params,
            "reason": action.reason,
        }
        for action in actions
    ]
