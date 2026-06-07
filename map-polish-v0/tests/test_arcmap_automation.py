import json
import os
import tempfile
import unittest

from arcmap_automation import (
    ARCMAP_PYTHON,
    build_arcmap_command,
    parse_polish_result,
    validate_mxd_upload,
    write_polish_config,
)
from layer_matching import LAYER_ROLES, suggest_layer_mapping


class LayerMatchingTest(unittest.TestCase):
    def test_suggest_layer_mapping_matches_chinese_and_english_layer_names(self):
        layer_names = [
            "Main River",
            "流域边界",
            "研究区范围",
            "行政区划",
            "DEM elevation",
            "Rainfall_mm",
        ]

        mapping = suggest_layer_mapping(layer_names)

        self.assertEqual(mapping["water"], "Main River")
        self.assertEqual(mapping["watershed_boundary"], "流域边界")
        self.assertEqual(mapping["study_area"], "研究区范围")
        self.assertEqual(mapping["admin_boundary"], "行政区划")
        self.assertEqual(mapping["dem"], "DEM elevation")
        self.assertEqual(mapping["rainfall_or_flood"], "Rainfall_mm")

    def test_suggest_layer_mapping_uses_empty_string_when_no_match_exists(self):
        mapping = suggest_layer_mapping(["roads", "buildings"])

        for role in LAYER_ROLES:
            self.assertEqual(mapping[role], "")


class ArcMapAutomationTest(unittest.TestCase):
    def test_validate_mxd_upload_accepts_mxd_under_size_limit(self):
        result = validate_mxd_upload("project.MXD", b"content")

        self.assertEqual(result.extension, "mxd")
        self.assertEqual(result.size_bytes, len(b"content"))

    def test_validate_mxd_upload_rejects_non_mxd(self):
        with self.assertRaisesRegex(ValueError, "Only MXD"):
            validate_mxd_upload("project.aprx", b"content")

    def test_build_arcmap_command_uses_arcgis_python_and_script(self):
        command = build_arcmap_command("inspect", "D:/input.mxd", "D:/out", "D:/config.json")

        self.assertEqual(command[0], ARCMAP_PYTHON)
        self.assertIn("arcmap_worker.py", command[1])
        self.assertEqual(command[2:], ["inspect", "D:/input.mxd", "D:/out", "D:/config.json"])

    def test_write_polish_config_writes_expected_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")

            write_polish_config(
                config_path,
                layer_mapping={"water": "Main River"},
                layout_options={"title": "研究区水系图"},
                rules={"layout": True, "symbol": True},
                auto_actions=[
                    {
                        "type": "set_layer_order",
                        "target_role": "water",
                        "params": {"position": "TOP"},
                        "reason": "水系置顶",
                    }
                ],
            )

            with open(config_path, "r", encoding="utf-8") as file_obj:
                payload = json.load(file_obj)

        self.assertEqual(payload["layer_mapping"]["water"], "Main River")
        self.assertEqual(payload["layout_options"]["title"], "研究区水系图")
        self.assertTrue(payload["rules"]["layout"])
        self.assertEqual(payload["auto_actions"][0]["type"], "set_layer_order")

    def test_parse_polish_result_reports_subprocess_failure(self):
        with self.assertRaisesRegex(RuntimeError, "ArcPy execution failed"):
            parse_polish_result(return_code=1, result_path="missing.json", stdout="", stderr="boom")


if __name__ == "__main__":
    unittest.main()
