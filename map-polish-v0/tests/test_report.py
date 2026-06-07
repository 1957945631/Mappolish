import unittest

from mock_analyzer import analyze_map
from report import format_markdown_report


class ReportTest(unittest.TestCase):
    def test_format_markdown_report_contains_score_issues_and_arcgis_steps(self):
        result = analyze_map(b"fake image content", "landuse", "homework")

        markdown = format_markdown_report(result)

        self.assertIn("# MapPolish 审图报告", markdown)
        self.assertIn("## 综合评分", markdown)
        self.assertIn("## 严重问题", markdown)
        self.assertIn("## 建议优化", markdown)
        self.assertIn("## 可选美化", markdown)
        self.assertIn("## ArcGIS 操作步骤", markdown)
        self.assertTrue("Data Frame" in markdown or "Layer Properties" in markdown)


if __name__ == "__main__":
    unittest.main()
