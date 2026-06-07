from map_types import MAP_TYPES, USE_CASES
from schemas import AnalysisResult, ColorAssessment, Issue, Step


def analyze_map(image_bytes: bytes, map_type: str, use_case: str) -> AnalysisResult:
    if map_type not in MAP_TYPES:
        raise ValueError(f"Unsupported map type: {map_type}")
    if use_case not in USE_CASES:
        raise ValueError(f"Unsupported use case: {use_case}")
    if not image_bytes:
        raise ValueError("Image bytes cannot be empty")

    template = _REPORTS[map_type]
    paper_ready = _paper_ready_text(use_case, template["paper_ready"])

    return AnalysisResult(
        overall_score=template["overall_score"],
        summary=template["summary"],
        serious_issues=[_issue(1, "serious", *template["serious"])],
        improvements=[_issue(1, "improvement", *template["improvement"])],
        optional_polish=[_issue(1, "optional", *template["optional"])],
        paper_ready=paper_ready,
        arcgis_steps=[
            Step(goal=template["step_goal"], steps=template["step_steps"]),
        ],
        color_assessment=ColorAssessment(
            is_reasonable=template["color_ok"],
            comment=template["color_comment"],
        ),
    )


def _issue(id_: int, severity: str, element: str, issue: str, reason: str, suggestion: str) -> Issue:
    return Issue(
        id=id_,
        element=element,
        issue=issue,
        reason=reason,
        suggestion=suggestion,
        severity=severity,
    )


def _paper_ready_text(use_case: str, base_text: str) -> str:
    prefix = {
        "paper": "按论文投稿标准看，",
        "homework": "按课程作业标准看，",
        "presentation": "按组会汇报标准看，",
        "thesis": "按毕设图件标准看，",
    }[use_case]
    return prefix + base_text


_REPORTS = {
    "watershed": {
        "overall_score": 76,
        "summary": "该流域范围图能表达研究区主体，但流域边界和主河道层级还不够突出。",
        "serious": (
            "流域边界",
            "流域边界线宽偏弱，和行政区边界区分不明显。",
            "流域图的核心是研究边界，边界不突出会影响读者快速识别研究对象。",
            "在 ArcMap 中右键流域边界图层 → Properties → Symbology，将线宽调整为 1.5-2 pt，并使用深色实线。",
        ),
        "improvement": (
            "主河道",
            "主河道与支流视觉层级接近。",
            "主河道应作为流域图的重要参照，否则水系结构不够清楚。",
            "在 Layer Properties → Symbology 中按河流等级设置线宽，主河道使用更深蓝色和更粗线宽。",
        ),
        "optional": (
            "位置小图",
            "建议增加全国或省域位置小图。",
            "位置小图能帮助读者理解研究区在更大区域中的位置。",
            "在 Layout View 中 Insert → Data Frame，添加省域底图并用矩形标示研究区范围。",
        ),
        "step_goal": "强化流域边界",
        "step_steps": "右键流域边界图层 → Properties → Symbology → Symbol → 设置线宽 1.5-2 pt → OK",
        "color_ok": True,
        "color_comment": "基础配色可用，但边界和水系需要通过线宽建立更清晰层级。",
        "paper_ready": "需要强化边界和水系层级后再用于正式图件。",
    },
    "water_system": {
        "overall_score": 74,
        "summary": "该水系图表达了河网分布，但河流等级和标注可读性仍需优化。",
        "serious": (
            "河流层级",
            "主支流线型差异不足。",
            "水系图需要清楚表达河流等级，否则专题信息会被削弱。",
            "在 Layer Properties → Symbology 中使用 Categories 或 Graduated Symbols 按等级设置线宽。",
        ),
        "improvement": (
            "河流标注",
            "部分河流名称贴近线条，阅读不够舒适。",
            "标注与线条过近会降低小字号图件的可读性。",
            "打开 Label Manager，为河流标注设置 Offset，并启用 Maplex Label Engine 优化避让。",
        ),
        "optional": (
            "底图弱化",
            "行政边界可适当降低饱和度。",
            "弱化底图能让水系成为视觉主体。",
            "在行政区图层 Symbol Selector 中使用浅灰色细线，透明度设置为 30%-50%。",
        ),
        "step_goal": "按河流等级设置线宽",
        "step_steps": "右键水系图层 → Properties → Symbology → Categories → 按等级字段分类 → 设置线宽",
        "color_ok": True,
        "color_comment": "蓝色水系表达合理，但主支流需要更明显的视觉区分。",
        "paper_ready": "调整河流层级后可作为报告或论文初稿图件。",
    },
    "dem": {
        "overall_score": 79,
        "summary": "该 DEM 图具备基本地形表达，但高程单位和色带说明需要更明确。",
        "serious": (
            "高程单位",
            "图例中未清楚标注高程单位。",
            "DEM 图缺少单位会导致数值含义不完整。",
            "在图例标题或分类标签中补充单位 m，例如 Elevation (m)。",
        ),
        "improvement": (
            "阴影效果",
            "地形起伏表达略平。",
            "适度 hillshade 能增强地貌识别，但不能压过主色带。",
            "使用 Spatial Analyst → Surface → Hillshade 生成阴影层，并将透明度设置为 35%-50%。",
        ),
        "optional": (
            "等高线",
            "可增加稀疏等高线辅助阅读。",
            "等高线能补充色带表达，适合论文读者判断地形梯度。",
            "使用 Spatial Analyst → Surface → Contour 生成等高线，并使用浅灰细线显示。",
        ),
        "step_goal": "补充 DEM 单位",
        "step_steps": "右键图例 → Properties → Items → 选择 DEM 图层 → Style/Label 中补充 Elevation (m)",
        "color_ok": True,
        "color_comment": "绿-黄-棕的高程色带符合常见地形表达习惯。",
        "paper_ready": "补充单位和阴影说明后可用于论文初稿。",
    },
    "flood": {
        "overall_score": 72,
        "summary": "该洪水/积水图能表达淹没范围，但水深分级和风险说明不够直接。",
        "serious": (
            "水深分级",
            "水深等级数量偏多或间隔不清楚。",
            "洪水图需要快速识别风险等级，复杂分级会影响决策阅读。",
            "在 Layer Properties → Symbology → Classified 中将水深等级控制在 4-5 级，并明确每级范围。",
        ),
        "improvement": (
            "风险标注",
            "缺少高风险区域的文字提示。",
            "风险图应帮助读者直接定位重点区域。",
            "使用 Drawing 工具添加简短标注，或在高风险斑块上添加 Label。",
        ),
        "optional": (
            "透明叠加",
            "积水范围可与底图进行半透明叠加。",
            "半透明叠加有助于同时阅读淹没范围和地物背景。",
            "右键积水图层 → Properties → Display → Transparent 设置为 30%-45%。",
        ),
        "step_goal": "简化水深分级",
        "step_steps": "右键水深图层 → Properties → Symbology → Classified → Classes 设为 5 → 调整 Break Values",
        "color_ok": True,
        "color_comment": "浅蓝到深蓝适合表达水深，但等级数量应控制。",
        "paper_ready": "需要简化分级并补充风险说明后再正式使用。",
    },
    "landuse": {
        "overall_score": 77,
        "summary": "该土地利用图分类信息完整，但部分类型颜色接近，图例需要更易读。",
        "serious": (
            "分类颜色",
            "相邻土地类型颜色过于接近。",
            "土地利用图依赖分类色块识别，颜色接近会造成误读。",
            "在 Layer Properties → Symbology 中逐类调整色板，耕地、林地、水体、建设用地使用明显区分的颜色。",
        ),
        "improvement": (
            "图例顺序",
            "图例分类顺序与常见土地利用类别习惯不完全一致。",
            "稳定的图例顺序能提升读者查找效率。",
            "在 Legend Properties → Items 中调整图层类别顺序，将主要类别置于前列。",
        ),
        "optional": (
            "边界线",
            "分类斑块边界可适当弱化。",
            "过强边界会让图面显得拥挤。",
            "在 Symbol Selector 中将 Outline Color 设置为 No Color 或浅灰色。",
        ),
        "step_goal": "调整土地利用分类颜色",
        "step_steps": "右键土地利用图层 → Properties → Symbology → Categories → 双击各类别色块 → 选择差异明显颜色",
        "color_ok": False,
        "color_comment": "部分分类颜色相近，建议改用更具区分度的定性色板。",
        "paper_ready": "优化色板和图例顺序后可用于课程作业或论文初稿。",
    },
    "rainfall": {
        "overall_score": 75,
        "summary": "该降雨分布图能表达空间梯度，但时间范围和单位标注需要补齐。",
        "serious": (
            "时间范围",
            "标题或图例中未明确降雨统计时段。",
            "降雨图必须说明时间窗口，否则数值无法解释。",
            "在标题中补充统计时段，例如 2024年7月24日 08:00-20:00 降雨量分布。",
        ),
        "improvement": (
            "单位标注",
            "图例单位不够醒目。",
            "降雨量单位直接影响数据含义。",
            "在 Legend Properties 中将图例标题改为 Rainfall (mm)。",
        ),
        "optional": (
            "站点叠加",
            "可叠加雨量站点作为数据来源参照。",
            "站点位置能提升插值结果的可信度表达。",
            "添加雨量站点图层，使用小圆点符号，并在图例中说明。",
        ),
        "step_goal": "补充降雨单位",
        "step_steps": "右键图例 → Properties → Items → 选择降雨图层 → 将标题设置为 Rainfall (mm)",
        "color_ok": True,
        "color_comment": "浅到深的连续色带适合表达降雨增强趋势。",
        "paper_ready": "补充时间范围和单位后可用于汇报或论文初稿。",
    },
    "location": {
        "overall_score": 78,
        "summary": "该区位图能说明研究区位置，但研究区高亮和周边参照信息还可加强。",
        "serious": (
            "研究区高亮",
            "研究区边界或填充不够醒目。",
            "区位图的目标是快速定位研究区，弱高亮会降低信息效率。",
            "在研究区图层 Symbol Selector 中使用红色或深色边框，并设置半透明填充。",
        ),
        "improvement": (
            "周边参照",
            "周边城市或行政区标注偏少。",
            "适量参照信息能帮助读者理解空间位置。",
            "开启主要城市或行政区 Label，并控制字号为 7-9 pt。",
        ),
        "optional": (
            "比例尺",
            "比例尺样式可更简洁。",
            "区位图比例尺应提供参考但不抢占视觉主体。",
            "Insert → Scale Bar，选择简洁黑白样式并放置在右下角。",
        ),
        "step_goal": "突出研究区范围",
        "step_steps": "右键研究区图层 → Properties → Symbology → Symbol → 设置深色边框和 30% 透明填充",
        "color_ok": True,
        "color_comment": "底图颜色较克制，适合突出研究区高亮。",
        "paper_ready": "强化研究区高亮后可用于论文或汇报的位置说明图。",
    },
}
