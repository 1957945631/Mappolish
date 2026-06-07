MAP_TYPES = {
    "watershed": {
        "label": "流域范围图",
        "checks": "流域边界是否清晰、行政区叠加是否合理、主河道是否突出、是否需要位置小图。",
    },
    "water_system": {
        "label": "水系图",
        "checks": "河流层级是否可区分、水系颜色是否合理、标注是否可读。",
    },
    "dem": {
        "label": "DEM/高程图",
        "checks": "色带是否符合高程直觉、单位是否清楚、阴影效果是否增强地形表达。",
    },
    "flood": {
        "label": "洪水/积水图",
        "checks": "水深分级是否合理、色带是否直观、风险等级标注是否清楚。",
    },
    "landuse": {
        "label": "土地利用图",
        "checks": "分类颜色是否容易区分、图例是否完整、相邻色块对比度是否足够。",
    },
    "rainfall": {
        "label": "降雨分布图",
        "checks": "降雨色带是否直观、单位是否为 mm、时间范围是否标注清楚。",
    },
    "location": {
        "label": "普通区位图",
        "checks": "研究区是否高亮、周边参照信息是否充分、比例尺和指北针是否规范。",
    },
}


USE_CASES = {
    "paper": "论文投稿",
    "homework": "课程作业",
    "presentation": "组会汇报",
    "thesis": "毕设",
}
