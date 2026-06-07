import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path

import requests

from action_schema import sanitize_actions
from map_types import MAP_TYPES, USE_CASES
from schemas import (
    AnalysisResult,
    AnalysisResultWithActions,
    ColorAssessment,
    Issue,
    Step,
)


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o"
ENV_FILE = Path(__file__).with_name(".env.local")


class OpenAIConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelSettings:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL


def load_env_file(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_model_settings(
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> ModelSettings:
    load_env_file()
    return ModelSettings(
        api_key=(api_key or os.getenv("OPENAI_API_KEY", "")).strip(),
        base_url=(base_url or os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)).strip() or DEFAULT_BASE_URL,
        model=(model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)).strip() or DEFAULT_MODEL,
    )


def build_responses_url(settings: ModelSettings) -> str:
    if not settings.api_key:
        raise OpenAIConfigError("OPENAI_API_KEY is required for OpenAI analysis.")
    if is_chat_completions_endpoint(settings.base_url):
        return settings.base_url.rstrip("/")
    return settings.base_url.rstrip("/") + "/responses"


def is_chat_completions_endpoint(base_url: str) -> bool:
    return base_url.rstrip("/").endswith("/chat/completions")


def analyze_map_with_openai(
    image_bytes: bytes,
    map_type: str,
    use_case: str,
    settings: ModelSettings,
) -> AnalysisResultWithActions:
    if map_type not in MAP_TYPES:
        raise ValueError(f"Unsupported map type: {map_type}")
    if use_case not in USE_CASES:
        raise ValueError(f"Unsupported use case: {use_case}")
    if not image_bytes:
        raise ValueError("Image bytes cannot be empty")

    response = requests.post(
        build_responses_url(settings),
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        json=build_request_payload(image_bytes, map_type, use_case, settings),
        timeout=90,
    )
    if not response.ok:
        raise OpenAIConfigError(format_api_error(response))
    return parse_openai_response(response.json())


def analyze_map_with_mxd_context(
    image_bytes: bytes,
    map_type: str,
    use_case: str,
    settings: ModelSettings,
    mxd_context: dict,
    previous_summary: str = "",
) -> AnalysisResultWithActions:
    if map_type not in MAP_TYPES:
        raise ValueError(f"Unsupported map type: {map_type}")
    if use_case not in USE_CASES:
        raise ValueError(f"Unsupported use case: {use_case}")
    if not image_bytes:
        raise ValueError("Image bytes cannot be empty")

    response = requests.post(
        build_responses_url(settings),
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        json=build_mxd_context_request_payload(image_bytes, map_type, use_case, settings, mxd_context, previous_summary),
        timeout=90,
    )
    if not response.ok:
        raise OpenAIConfigError(format_api_error(response))
    return parse_openai_response(response.json())


def format_api_error(response) -> str:
    message = response.text
    try:
        payload = response.json()
        error = payload.get("error", payload)
        if isinstance(error, dict):
            parts = []
            if error.get("message"):
                parts.append(str(error["message"]))
            if error.get("code"):
                parts.append(f"code={error['code']}")
            if error.get("type"):
                parts.append(f"type={error['type']}")
            message = "；".join(parts) or message
    except ValueError:
        pass
    return f"模型接口请求失败：HTTP {response.status_code}；{message}"


def parse_openai_response(payload: dict) -> AnalysisResultWithActions:
    text = payload.get("output_text") or _extract_output_text(payload)
    if not text:
        raise ValueError("OpenAI response did not include output text.")
    data = _load_json_object(text)
    if not isinstance(data, dict):
        raise ValueError("OpenAI response JSON must be an object.")

    color_assessment = data.get("color_assessment", {})
    if not isinstance(color_assessment, dict):
        color_assessment = {"comment": str(color_assessment)}

    analysis = AnalysisResult(
        overall_score=_parse_score(data.get("overall_score", 0)),
        summary=str(data.get("summary", "")),
        serious_issues=[_parse_issue(item, "serious") for item in _as_list(data.get("serious_issues", []))],
        improvements=[_parse_issue(item, "improvement") for item in _as_list(data.get("improvements", []))],
        optional_polish=[_parse_issue(item, "optional") for item in _as_list(data.get("optional_polish", []))],
        paper_ready=str(data.get("paper_ready", "")),
        arcgis_steps=[_parse_step(item) for item in _as_list(data.get("arcgis_steps", []))],
        color_assessment=ColorAssessment(
            is_reasonable=bool(color_assessment.get("is_reasonable", False)),
            comment=str(color_assessment.get("comment", "")),
        ),
    )
    auto_actions, downgraded_manual = sanitize_actions(_as_list(data.get("auto_actions", [])))
    explicit_manual = [
        _parse_manual_action(item)
        for item in _as_list(data.get("manual_actions", []))
    ]
    return AnalysisResultWithActions(
        analysis=analysis,
        auto_actions=auto_actions,
        manual_actions=downgraded_manual + explicit_manual,
    )


def build_request_payload(image_bytes: bytes, map_type: str, use_case: str, settings: ModelSettings) -> dict:
    if is_chat_completions_endpoint(settings.base_url):
        return _build_chat_completions_payload(image_bytes, map_type, use_case, settings.model)
    return _build_responses_payload(image_bytes, map_type, use_case, settings.model)


def build_mxd_context_request_payload(
    image_bytes: bytes,
    map_type: str,
    use_case: str,
    settings: ModelSettings,
    mxd_context: dict,
    previous_summary: str = "",
) -> dict:
    prompt = _build_mxd_context_prompt(map_type, use_case, mxd_context, previous_summary)
    if is_chat_completions_endpoint(settings.base_url):
        return _build_chat_payload_from_prompt(image_bytes, prompt, settings.model)
    return _build_responses_payload_from_prompt(image_bytes, prompt, settings.model)


def _build_chat_completions_payload(image_bytes: bytes, map_type: str, use_case: str, model: str) -> dict:
    prompt = _build_prompt(map_type, use_case)
    return _build_chat_payload_from_prompt(image_bytes, prompt, model)


def _build_chat_payload_from_prompt(image_bytes: bytes, prompt: str, model: str) -> dict:
    image_data = base64.b64encode(image_bytes).decode("ascii")
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt + "\n" + json.dumps(_json_schema_hint(), ensure_ascii=False)},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                ],
            }
        ],
        "response_format": {"type": "json_object"},
    }


def _build_responses_payload(image_bytes: bytes, map_type: str, use_case: str, model: str) -> dict:
    prompt = _build_prompt(map_type, use_case)
    return _build_responses_payload_from_prompt(image_bytes, prompt, model)


def _build_responses_payload_from_prompt(image_bytes: bytes, prompt: str, model: str) -> dict:
    image_data = base64.b64encode(image_bytes).decode("ascii")
    return {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt + "\n" + json.dumps(_json_schema_hint(), ensure_ascii=False)},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{image_data}"},
                ],
            }
        ],
    }


def _build_prompt(map_type: str, use_case: str) -> str:
    return (
        "你是资深 GIS 科研制图审查专家。请审查用户上传的地图截图，输出严格 JSON。"
        f"地图类型：{MAP_TYPES[map_type]['label']}。使用场景：{USE_CASES[use_case]}。"
        "同时生成可自动执行的安全 action 和需要人工处理的 manual action。"
        "只允许 auto_actions 使用这些 type：add_layout_text, emphasize_layer, "
        "set_layer_visibility, set_layer_transparency, export_preview。"
        "serious_issues、improvements、optional_polish、arcgis_steps、auto_actions、manual_actions "
        "必须是数组；数组每一项必须是对象，不能返回字符串数组。"
    )


def _build_mxd_context_prompt(map_type: str, use_case: str, mxd_context: dict, previous_summary: str) -> str:
    return (
        _build_prompt(map_type, use_case)
        + "这次不是初审，而是 MXD 上下文精修。请结合地图截图和下面的 MXD 图层上下文，"
        + "把视觉问题落到具体 target_role、图层角色和可执行 action。"
        + "只生成 ArcPy worker 能安全执行的动作；无法确定的内容放入 manual_actions。"
        + "允许的新增动作 type：set_layer_order、set_text_element、set_layer_label_visibility。"
        + "MXD 图层上下文："
        + json.dumps(mxd_context, ensure_ascii=False)
        + "。初审摘要："
        + previous_summary
        + "。"
    )


def _json_schema_hint() -> dict:
    return {
        "overall_score": 78,
        "summary": "地图总体评价",
        "serious_issues": [],
        "improvements": [],
        "optional_polish": [],
        "paper_ready": "就绪度判断",
        "arcgis_steps": [],
        "color_assessment": {"is_reasonable": True, "comment": "色带评价"},
        "auto_actions": [
            {
                "type": "add_layout_text",
                "target_role": "layout",
                "params": {"field": "data_source", "text": "数据来源：请补充"},
                "reason": "缺少数据来源",
            },
            {
                "type": "set_layer_order",
                "target_role": "water",
                "params": {"position": "TOP"},
                "reason": "水系需要置顶以增强可读性",
            }
        ],
        "manual_actions": [
            {
                "type": "manual_only",
                "target_role": "legend",
                "params": {},
                "reason": "复杂图例顺序需要人工确认",
            }
        ],
    }


def _extract_output_text(payload: dict) -> str:
    choices = payload.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks = []
            for item in content:
                if isinstance(item, dict) and item.get("text"):
                    chunks.append(str(item["text"]))
            return "\n".join(chunks)

    chunks = []
    for output in payload.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    return "\n".join(chunks)


def _load_json_object(text: str) -> dict:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()

    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start:end + 1]

    if not candidate:
        raise ValueError("模型返回了空内容，无法解析审图 JSON。请确认当前模型支持图像输入和 JSON 输出。")

    try:
        data = json.loads(candidate)
    except ValueError:
        preview = candidate[:240].replace("\n", " ")
        raise ValueError(f"模型未按 JSON 格式返回审图结果。返回片段：{preview}")
    if not isinstance(data, dict):
        raise ValueError("模型返回的 JSON 不是对象，无法解析审图结果。")
    return data


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _parse_score(value) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def _parse_issue(item, default_severity: str) -> Issue:
    if not isinstance(item, dict):
        return Issue(
            id=1,
            element="未分类",
            issue=str(item),
            reason="模型返回了非结构化问题条目。",
            suggestion="请人工复核该建议，或切换更稳定的多模态模型。",
            severity=default_severity,
        )
    return Issue(
        id=int(item.get("id", 1)),
        element=str(item.get("element", "")),
        issue=str(item.get("issue", "")),
        reason=str(item.get("reason", "")),
        suggestion=str(item.get("suggestion", "")),
        severity=str(item.get("severity", default_severity)),
    )


def _parse_step(item) -> Step:
    if not isinstance(item, dict):
        return Step(goal="人工复核", steps=str(item))
    return Step(goal=str(item.get("goal", "")), steps=str(item.get("steps", "")))


def _parse_manual_action(item):
    from schemas import Action

    if not isinstance(item, dict):
        return Action("manual_only", "report", {}, str(item))
    return Action(
        type="manual_only",
        target_role=str(item.get("target_role", "report")),
        params=item.get("params") if isinstance(item.get("params"), dict) else {},
        reason=str(item.get("reason", "")),
    )
