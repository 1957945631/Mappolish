LAYER_ROLES = {
    "water": {
        "label": "水系/河流",
        "keywords": ["river", "stream", "water", "hydro", "河流", "水系", "河道", "水域"],
    },
    "watershed_boundary": {
        "label": "流域边界",
        "keywords": ["watershed", "basin", "boundary", "流域", "边界", "范围线"],
    },
    "study_area": {
        "label": "研究区",
        "keywords": ["study", "area", "region", "研究区", "研究范围", "项目区"],
    },
    "admin_boundary": {
        "label": "行政边界",
        "keywords": ["admin", "district", "county", "province", "行政", "区划", "县界", "省界"],
    },
    "dem": {
        "label": "DEM/栅格",
        "keywords": ["dem", "elevation", "hillshade", "raster", "高程", "地形", "栅格"],
    },
    "rainfall_or_flood": {
        "label": "降雨/水深",
        "keywords": ["rain", "rainfall", "precip", "flood", "depth", "降雨", "雨量", "洪水", "积水", "水深"],
    },
}


def suggest_layer_mapping(layer_names: list[str]) -> dict[str, str]:
    mapping = {}
    used_layers = set()

    for role, config in LAYER_ROLES.items():
        match = ""
        for layer_name in layer_names:
            if layer_name in used_layers:
                continue
            normalized = layer_name.lower()
            if any(keyword.lower() in normalized for keyword in config["keywords"]):
                match = layer_name
                used_layers.add(layer_name)
                break
        mapping[role] = match

    return mapping
