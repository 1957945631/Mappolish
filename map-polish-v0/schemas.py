from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    id: int
    element: str
    issue: str
    reason: str
    suggestion: str
    severity: str


@dataclass(frozen=True)
class Step:
    goal: str
    steps: str


@dataclass(frozen=True)
class ColorAssessment:
    is_reasonable: bool
    comment: str


@dataclass(frozen=True)
class AnalysisResult:
    overall_score: int
    summary: str
    serious_issues: list[Issue]
    improvements: list[Issue]
    optional_polish: list[Issue]
    paper_ready: str
    arcgis_steps: list[Step]
    color_assessment: ColorAssessment


@dataclass(frozen=True)
class Action:
    type: str
    target_role: str
    params: dict
    reason: str


@dataclass(frozen=True)
class AnalysisResultWithActions:
    analysis: AnalysisResult
    auto_actions: list[Action]
    manual_actions: list[Action]
