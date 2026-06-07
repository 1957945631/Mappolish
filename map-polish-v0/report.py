from schemas import AnalysisResult, Issue


def format_markdown_report(result: AnalysisResult) -> str:
    sections = [
        "# MapPolish 审图报告",
        "",
        "## 综合评分",
        f"{result.overall_score}/100",
        "",
        "## 摘要",
        result.summary,
        "",
        "## 严重问题",
        _format_issues(result.serious_issues),
        "",
        "## 建议优化",
        _format_issues(result.improvements),
        "",
        "## 可选美化",
        _format_issues(result.optional_polish),
        "",
        "## ArcGIS 操作步骤",
        *[f"{index}. **{step.goal}**：{step.steps}" for index, step in enumerate(result.arcgis_steps, start=1)],
        "",
        "## 色带评估",
        result.color_assessment.comment,
        "",
        "## 就绪度判断",
        result.paper_ready,
        "",
    ]
    return "\n".join(sections)


def _format_issues(issues: list[Issue]) -> str:
    lines = []
    for issue in issues:
        lines.extend(
            [
                f"### {issue.id}. {issue.element}",
                f"- 问题：{issue.issue}",
                f"- 原因：{issue.reason}",
                f"- 建议：{issue.suggestion}",
                "",
            ]
        )
    return "\n".join(lines).strip()
