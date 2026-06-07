import json
import os
import tempfile
import unittest
from pathlib import Path

from ai_analyzer import (
    ModelSettings,
    OpenAIConfigError,
    build_mxd_context_request_payload,
    build_request_payload,
    build_responses_url,
    format_api_error,
    load_env_file,
    load_model_settings,
    parse_openai_response,
)
from action_schema import (
    ALLOWED_ACTION_TYPES,
    build_default_actions,
    sanitize_actions,
)
from mock_analyzer import analyze_map


class ActionSchemaTest(unittest.TestCase):
    def test_sanitize_actions_keeps_allowed_actions_and_downgrades_unknown_actions(self):
        actions = [
            {
                "type": "set_layer_transparency",
                "target_role": "admin_boundary",
                "params": {"transparency": 55},
                "reason": "弱化行政边界",
            },
            {
                "type": "run_python",
                "target_role": "admin_boundary",
                "params": {"code": "danger"},
                "reason": "不安全动作",
            },
        ]

        auto_actions, manual_actions = sanitize_actions(actions)

        self.assertEqual(auto_actions[0].type, "set_layer_transparency")
        self.assertEqual(manual_actions[0].type, "manual_only")
        self.assertIn("run_python", manual_actions[0].reason)

    def test_build_default_actions_generates_safe_actions_from_mock_result(self):
        result = analyze_map(b"fake image", "watershed", "paper")

        auto_actions, manual_actions = build_default_actions(result)

        self.assertTrue(auto_actions)
        self.assertTrue(manual_actions)
        self.assertTrue(all(action.type in ALLOWED_ACTION_TYPES for action in auto_actions))

    def test_sanitize_actions_accepts_mxd_context_action_types(self):
        actions = [
            {"type": "set_layer_order", "target_role": "water", "params": {"position": "TOP"}, "reason": "水系置顶"},
            {"type": "set_text_element", "target_role": "layout", "params": {"field": "title", "text": "研究区水系图"}, "reason": "标题具体化"},
            {"type": "set_layer_label_visibility", "target_role": "water", "params": {"enabled": True}, "reason": "打开河流标注"},
        ]

        auto_actions, manual_actions = sanitize_actions(actions)

        self.assertEqual([action.type for action in auto_actions], ["set_layer_order", "set_text_element", "set_layer_label_visibility"])
        self.assertEqual(manual_actions, [])


class AiAnalyzerTest(unittest.TestCase):
    def test_format_api_error_includes_status_message_and_code(self):
        class FakeResponse:
            status_code = 429
            text = '{"error":{"message":"当前分组上游负载已饱和，请稍后再试","code":"model_not_found","type":"new_api_error"}}'

            def json(self):
                return json.loads(self.text)

        message = format_api_error(FakeResponse())

        self.assertIn("HTTP 429", message)
        self.assertIn("上游负载已饱和", message)
        self.assertIn("model_not_found", message)

    def test_load_model_settings_reads_env_local_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env.local"
            env_path.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=sk-local",
                        "OPENAI_BASE_URL=https://compatible.example/v1",
                        "OPENAI_MODEL=vision-model",
                    ]
                ),
                encoding="utf-8",
            )

            old_values = {
                key: os.environ.pop(key, None)
                for key in ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"]
            }
            try:
                load_env_file(env_path)
                settings = load_model_settings()
            finally:
                for key in ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"]:
                    os.environ.pop(key, None)
                    if old_values[key] is not None:
                        os.environ[key] = old_values[key]

        self.assertEqual(settings.api_key, "sk-local")
        self.assertEqual(settings.base_url, "https://compatible.example/v1")
        self.assertEqual(settings.model, "vision-model")

    def test_build_responses_url_accepts_openai_compatible_base_url(self):
        settings = ModelSettings(
            api_key="sk-test",
            base_url="https://example.com/openai/v1/",
            model="gpt-4o",
        )

        self.assertEqual(build_responses_url(settings), "https://example.com/openai/v1/responses")

    def test_build_responses_url_accepts_chat_completions_endpoint(self):
        settings = ModelSettings(
            api_key="sk-test",
            base_url="https://example.com/v1/chat/completions",
            model="vision-model",
        )

        self.assertEqual(build_responses_url(settings), "https://example.com/v1/chat/completions")

    def test_build_request_payload_uses_chat_completions_shape_for_chat_endpoint(self):
        settings = ModelSettings(
            api_key="sk-test",
            base_url="https://example.com/v1/chat/completions",
            model="vision-model",
        )

        payload = build_request_payload(b"image", "watershed", "paper", settings)

        self.assertIn("messages", payload)
        self.assertNotIn("input", payload)
        self.assertEqual(payload["response_format"]["type"], "json_object")
        self.assertEqual(payload["messages"][0]["content"][1]["type"], "image_url")

    def test_build_mxd_context_request_payload_includes_layers_and_mapping(self):
        settings = ModelSettings(
            api_key="sk-test",
            base_url="https://example.com/v1/chat/completions",
            model="vision-model",
        )
        mxd_context = {
            "layers": ["Main River", "流域边界"],
            "layout_elements": [{"name": "Title", "type": "TEXT_ELEMENT"}],
            "layer_mapping": {"water": "Main River"},
            "warnings": [],
        }

        payload = build_mxd_context_request_payload(
            b"image",
            "watershed",
            "paper",
            settings,
            mxd_context,
            previous_summary="初审认为水系不突出。",
        )
        text = payload["messages"][0]["content"][0]["text"]

        self.assertIn("MXD 图层上下文", text)
        self.assertIn("Main River", text)
        self.assertIn("初审认为水系不突出", text)
        self.assertEqual(payload["messages"][0]["content"][1]["type"], "image_url")

    def test_build_responses_url_requires_api_key(self):
        settings = ModelSettings(api_key="", base_url="https://api.openai.com/v1", model="gpt-4o")

        with self.assertRaises(OpenAIConfigError):
            build_responses_url(settings)

    def test_parse_openai_response_parses_structured_output_text(self):
        content = {
            "overall_score": 82,
            "summary": "地图整体可用，但需要补充数据来源。",
            "serious_issues": [],
            "improvements": [],
            "optional_polish": [],
            "paper_ready": "补充来源后可用于论文初稿。",
            "arcgis_steps": [],
            "color_assessment": {"is_reasonable": True, "comment": "色带基本合理。"},
            "auto_actions": [
                {
                    "type": "add_layout_text",
                    "target_role": "layout",
                    "params": {"field": "data_source", "text": "数据来源：请补充"},
                    "reason": "缺少数据来源",
                }
            ],
            "manual_actions": [
                {
                    "type": "manual_only",
                    "target_role": "legend",
                    "params": {},
                    "reason": "图例顺序需人工确认",
                }
            ],
        }
        payload = {"output_text": json.dumps(content, ensure_ascii=False)}

        result = parse_openai_response(payload)

        self.assertEqual(result.analysis.overall_score, 82)
        self.assertEqual(result.auto_actions[0].type, "add_layout_text")
        self.assertEqual(result.manual_actions[0].target_role, "legend")

    def test_parse_openai_response_parses_chat_completions_content(self):
        content = {
            "overall_score": 82,
            "summary": "地图整体可用。",
            "serious_issues": [],
            "improvements": [],
            "optional_polish": [],
            "paper_ready": "可用于初稿。",
            "arcgis_steps": [],
            "color_assessment": {"is_reasonable": True, "comment": "色带基本合理。"},
            "auto_actions": [],
            "manual_actions": [],
        }
        payload = {"choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}]}

        result = parse_openai_response(payload)

        self.assertEqual(result.analysis.summary, "地图整体可用。")

    def test_parse_openai_response_parses_json_code_fence(self):
        content = {
            "overall_score": 80,
            "summary": "地图需要优化。",
            "serious_issues": [],
            "improvements": [],
            "optional_polish": [],
            "paper_ready": "修改后可用。",
            "arcgis_steps": [],
            "color_assessment": {"is_reasonable": True, "comment": "基本可读。"},
            "auto_actions": [],
            "manual_actions": [],
        }
        payload = {"choices": [{"message": {"content": "```json\n" + json.dumps(content, ensure_ascii=False) + "\n```"}}]}

        result = parse_openai_response(payload)

        self.assertEqual(result.analysis.summary, "地图需要优化。")

    def test_parse_openai_response_reports_non_json_text_clearly(self):
        payload = {"choices": [{"message": {"content": "我无法处理这张图片。"}}]}

        with self.assertRaisesRegex(ValueError, "模型未按 JSON 格式返回"):
            parse_openai_response(payload)

    def test_parse_openai_response_tolerates_string_items_from_model(self):
        content = {
            "overall_score": "88",
            "summary": "地图可读。",
            "serious_issues": ["图例太小"],
            "improvements": "行政边界过重",
            "optional_polish": [],
            "paper_ready": "需要修改后使用。",
            "arcgis_steps": ["在 ArcMap 中调整图例字号"],
            "color_assessment": "色带可读性一般",
            "auto_actions": ["加粗水系"],
            "manual_actions": ["人工检查色带"],
        }
        payload = {"output_text": json.dumps(content, ensure_ascii=False)}

        result = parse_openai_response(payload)

        self.assertEqual(result.analysis.overall_score, 88)
        self.assertEqual(result.analysis.serious_issues[0].issue, "图例太小")
        self.assertEqual(result.analysis.improvements[0].issue, "行政边界过重")
        self.assertIn("调整图例字号", result.analysis.arcgis_steps[0].steps)
        self.assertTrue(result.manual_actions)


if __name__ == "__main__":
    unittest.main()
