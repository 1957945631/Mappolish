import unittest

from map_types import MAP_TYPES, USE_CASES
from mock_analyzer import analyze_map


class MockAnalyzerTest(unittest.TestCase):
    def test_analyze_map_returns_complete_result_for_each_map_type(self):
        image_bytes = b"fake image content"

        for map_type in MAP_TYPES:
            result = analyze_map(image_bytes, map_type, "paper")

            self.assertTrue(0 <= result.overall_score <= 100)
            self.assertTrue(result.summary)
            self.assertTrue(result.serious_issues)
            self.assertTrue(result.improvements)
            self.assertTrue(result.optional_polish)
            self.assertTrue(result.paper_ready)
            self.assertTrue(result.arcgis_steps)
            self.assertTrue(result.color_assessment.comment)


    def test_analyze_map_returns_type_specific_reports(self):
        image_bytes = b"fake image content"

        watershed = analyze_map(image_bytes, "watershed", "paper")
        dem = analyze_map(image_bytes, "dem", "paper")

        self.assertNotEqual(watershed.summary, dem.summary)
        self.assertNotEqual(watershed.serious_issues[0].element, dem.serious_issues[0].element)


    def test_each_issue_contains_required_fields_and_valid_severity(self):
        result = analyze_map(b"fake image content", "rainfall", "thesis")
        issues = result.serious_issues + result.improvements + result.optional_polish

        for issue in issues:
            self.assertTrue(issue.element)
            self.assertTrue(issue.issue)
            self.assertTrue(issue.suggestion)
            self.assertIn(issue.severity, {"serious", "improvement", "optional"})


    def test_unknown_map_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported map type"):
            analyze_map(b"fake image content", "unknown", "paper")


    def test_unknown_use_case_is_rejected(self):
        self.assertIn("paper", USE_CASES)

        with self.assertRaisesRegex(ValueError, "Unsupported use case"):
            analyze_map(b"fake image content", "watershed", "unknown")


if __name__ == "__main__":
    unittest.main()
