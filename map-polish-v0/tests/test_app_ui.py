import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app import build_step_rail_html, default_analyzer_mode


class AppUiTest(unittest.TestCase):
    def test_app_renders_workbench_shell_without_errors(self):
        app = AppTest.from_file("app.py")
        app.run()

        markdown = "\n".join(item.value for item in app.markdown)

        self.assertEqual(len(app.exception), 0)
        self.assertIn("审图工作台", markdown)
        self.assertIn("1 上传截图", markdown)
        self.assertIn("API 状态", markdown)
        self.assertIn("ArcPy 执行", markdown)
        self.assertIn("mp-workbench-brand", markdown)

    def test_step_rail_html_contains_status_cards(self):
        html = build_step_rail_html("2 审图确认")

        self.assertIn("mp-step-card", html)
        self.assertIn("mp-step-status", html)
        self.assertIn("1 上传截图", html)
        self.assertIn("2 审图确认", html)
        self.assertIn("3 MXD 修改", html)
        self.assertIn("已完成", html)
        self.assertIn("当前", html)

    @patch("app.load_model_settings")
    def test_default_analyzer_mode_uses_openai_when_api_key_exists(self, mock_load_settings):
        mock_load_settings.return_value.api_key = "sk-test"

        self.assertEqual(default_analyzer_mode(), "OpenAI 实审")

    @patch("app.load_model_settings")
    def test_default_analyzer_mode_uses_mock_when_api_key_is_missing(self, mock_load_settings):
        mock_load_settings.return_value.api_key = ""

        self.assertEqual(default_analyzer_mode(), "离线模拟")


if __name__ == "__main__":
    unittest.main()
