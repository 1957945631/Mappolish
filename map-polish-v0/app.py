import os

import streamlit as st

from action_schema import actions_to_dicts, build_default_actions
from ai_analyzer import (
    OpenAIConfigError,
    analyze_map_with_mxd_context,
    analyze_map_with_openai,
    load_model_settings,
)
from arcmap_automation import (
    inspect_mxd,
    run_arcmap_polish,
    save_uploaded_mxd,
    validate_mxd_upload,
)
from layer_matching import LAYER_ROLES, suggest_layer_mapping
from map_types import MAP_TYPES, USE_CASES
from mock_analyzer import analyze_map
from report import format_markdown_report
from schemas import AnalysisResultWithActions
from utils import validate_image_upload


def main() -> None:
    st.set_page_config(page_title="MapPolish", page_icon="Map", layout="wide")
    inject_styles()
    render_header()

    nav_col, workspace_col, inspector_col = st.columns([0.85, 2.2, 1.25], gap="large")
    with nav_col:
        render_step_rail()
    with workspace_col:
        render_workspace()
    with inspector_col:
        render_inspector()

    render_execution_panel()


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f6f7f9;
            color: #181d26;
        }
        .main .block-container {
            max-width: 1480px;
            padding-top: 1rem;
            padding-bottom: 1.5rem;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        .mp-header, .mp-panel, .mp-execution {
            background: #ffffff;
            border: 1px solid #d9dde5;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(24, 29, 38, 0.04);
        }
        .mp-header {
            display: grid;
            grid-template-columns: minmax(0, 1.4fr) auto;
            align-items: stretch;
            gap: 14px;
            padding: 14px;
            margin-bottom: 16px;
        }
        .mp-workbench-brand {
            background: #181d26;
            border-radius: 8px;
            color: #ffffff;
            padding: 18px 20px;
        }
        .mp-kicker {
            color: #a8b0c2;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .mp-workbench-brand h1 {
            font-size: 28px;
            line-height: 1.15;
            margin: 0;
        }
        .mp-subtitle {
            color: #d6dbe7;
            font-size: 14px;
            line-height: 1.55;
            margin-top: 8px;
            max-width: 660px;
        }
        .mp-status {
            display: grid;
            grid-template-columns: repeat(3, minmax(118px, 1fr));
            gap: 8px;
            min-width: 430px;
        }
        .mp-chip {
            border: 1px solid #d9dde5;
            border-radius: 8px;
            padding: 11px 12px;
            font-size: 12px;
            color: #555c68;
            background: #f8fafc;
            min-height: 54px;
        }
        .mp-chip-label {
            display: block;
            color: #858b96;
            font-size: 11px;
            margin-bottom: 4px;
        }
        .mp-chip-value {
            display: block;
            color: #181d26;
            font-weight: 700;
            line-height: 1.35;
        }
        .mp-chip-strong {
            background: #eef0ff;
            border-color: #c7cbf7;
        }
        .mp-chip-strong .mp-chip-value {
            color: #4f58c9;
        }
        .mp-step-rail {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .mp-rail-title {
            color: #555c68;
            font-size: 12px;
            font-weight: 700;
            margin: 2px 2px 4px;
        }
        .mp-step-card {
            background: #ffffff;
            border: 1px solid #d9dde5;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(24, 29, 38, 0.04);
            padding: 13px;
        }
        .mp-step-card-active {
            background: #181d26;
            border-color: #181d26;
            color: #ffffff;
        }
        .mp-step-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 10px;
        }
        .mp-step-index {
            align-items: center;
            background: #f1f3f6;
            border: 1px solid #d9dde5;
            border-radius: 8px;
            color: #181d26;
            display: inline-flex;
            font-size: 12px;
            font-weight: 800;
            height: 28px;
            justify-content: center;
            width: 28px;
        }
        .mp-step-card-active .mp-step-index {
            background: #5e6ad2;
            border-color: #5e6ad2;
            color: #ffffff;
        }
        .mp-step-status {
            border: 1px solid #d9dde5;
            border-radius: 999px;
            color: #6b7280;
            font-size: 11px;
            padding: 3px 8px;
            white-space: nowrap;
        }
        .mp-step-card-active .mp-step-status {
            border-color: rgba(255, 255, 255, 0.2);
            color: #d6dbe7;
        }
        .mp-step-title {
            color: #181d26;
            font-weight: 650;
            font-size: 14px;
            line-height: 1.35;
        }
        .mp-step-card-active .mp-step-title {
            color: #ffffff;
        }
        .mp-step-copy {
            color: #6b7280;
            font-size: 12px;
            line-height: 1.5;
            margin-top: 5px;
        }
        .mp-step-card-active .mp-step-copy {
            color: #c8cedd;
        }
        .mp-panel {
            padding: 18px;
            margin-bottom: 14px;
        }
        .mp-panel-title {
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .mp-panel-copy {
            color: #5d6472;
            font-size: 13px;
            margin-bottom: 12px;
        }
        .mp-empty {
            border: 1px dashed #cfd5de;
            border-radius: 8px;
            padding: 28px;
            color: #6b7280;
            text-align: center;
            background: #fbfcfe;
        }
        .mp-action {
            border: 1px solid #dde1e7;
            border-radius: 6px;
            padding: 10px 12px;
            margin-bottom: 8px;
            background: #ffffff;
        }
        .mp-action-auto {
            border-left: 3px solid #15803d;
        }
        .mp-action-manual {
            border-left: 3px solid #b45309;
        }
        .mp-action-label {
            font-size: 11px;
            font-weight: 700;
            color: #5e6ad2;
            text-transform: uppercase;
        }
        .mp-action-text {
            font-size: 13px;
            color: #181d26;
            margin-top: 3px;
        }
        .mp-execution {
            padding: 16px 18px;
            margin-top: 14px;
        }
        div.stButton > button[kind="primary"] {
            background: #181d26;
            border-color: #181d26;
        }
        @media (max-width: 1100px) {
            .mp-header {
                grid-template-columns: 1fr;
            }
            .mp-status {
                min-width: 0;
            }
        }
        @media (max-width: 760px) {
            .mp-status {
                grid-template-columns: 1fr;
            }
            .mp-workbench-brand h1 {
                font-size: 23px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    mode = st.session_state.get("analyzer_mode", default_analyzer_mode())
    api_ready = bool(load_model_settings().api_key)
    api_status = "已配置" if api_ready else "未配置"
    step = current_step_label()
    st.markdown(
        f"""
        <div class="mp-header">
          <div class="mp-workbench-brand">
            <div class="mp-kicker">MAP QA WORKBENCH</div>
            <h1>MapPolish 审图工作台</h1>
            <div class="mp-subtitle">截图审图、动作确认、MXD 副本生成集中在一个离线优先流程里。</div>
          </div>
          <div class="mp-status">
            <div class="mp-chip mp-chip-strong">
              <span class="mp-chip-label">当前阶段</span>
              <span class="mp-chip-value">{step}</span>
            </div>
            <div class="mp-chip">
              <span class="mp-chip-label">审图模式</span>
              <span class="mp-chip-value">{mode}</span>
            </div>
            <div class="mp-chip">
              <span class="mp-chip-label">API 状态</span>
              <span class="mp-chip-value">{api_status}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def current_step_label() -> str:
    if st.session_state.get("polish_result"):
        return "4 输出结果"
    if st.session_state.get("mxd_layers"):
        return "3 MXD 修改"
    if st.session_state.get("review_result"):
        return "2 审图确认"
    return "1 上传截图"


def default_analyzer_mode() -> str:
    return "OpenAI 实审" if load_model_settings().api_key else "离线模拟"


def render_step_rail() -> None:
    active = current_step_label()
    render_html(build_step_rail_html(active))


def build_step_rail_html(active: str) -> str:
    steps = [
        ("1", "上传截图", "上传地图截图，选择地图类型和审图模式。"),
        ("2", "审图确认", "查看评分、问题分级、自动动作和人工建议。"),
        ("3", "MXD 修改", "上传工程，确认图层映射并调用 ArcMap。"),
    ]
    active_number = active.split(" ")[0]
    html = ['<div class="mp-step-rail">', '<div class="mp-rail-title">工作流程</div>']
    for number, title, copy in steps:
        if int(number) < int(active_number):
            status = "已完成"
        elif number == active_number:
            status = "当前"
        else:
            status = "待处理"
        active_class = " mp-step-card-active" if number == active_number else ""
        html.append(
            f"""
            <div class="mp-step-card{active_class}">
              <div class="mp-step-top">
                <span class="mp-step-index">{number}</span>
                <span class="mp-step-status">{status}</span>
              </div>
              <div class="mp-step-title">{number} {title}</div>
              <div class="mp-step-copy">{copy}</div>
            </div>
            """
        )
    html.append("</div>")
    return "\n".join(html)


def render_html(html: str) -> None:
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def render_workspace() -> None:
    render_upload_and_review_panel()
    if st.session_state.get("review_result"):
        render_mxd_panel()


def render_upload_and_review_panel() -> None:
    st.markdown(
        """
        <div class="mp-panel">
          <div class="mp-panel-title">截图审图</div>
          <div class="mp-panel-copy">先上传地图截图，生成审图报告和可执行修改动作。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "上传地图截图",
        type=["png", "jpg", "jpeg", "webp"],
        help="支持 PNG/JPG/WEBP，文件大小不超过 10MB。",
        key="image_upload",
    )

    controls_left, controls_mid, controls_right = st.columns(3)
    with controls_left:
        map_type = st.selectbox(
            "地图类型",
            options=list(MAP_TYPES.keys()),
            format_func=lambda key: MAP_TYPES[key]["label"],
            key="image_map_type",
        )
    with controls_mid:
        use_case = st.selectbox(
            "使用场景",
            options=list(USE_CASES.keys()),
            format_func=lambda key: USE_CASES[key],
            key="image_use_case",
        )
    with controls_right:
        analyzer_options = ["离线模拟", "OpenAI 实审"]
        analyzer_mode = st.radio(
            "审图模式",
            analyzer_options,
            index=analyzer_options.index(default_analyzer_mode()),
            horizontal=True,
            key="analyzer_mode",
        )

    if analyzer_mode == "OpenAI 实审":
        st.caption("模型接口从 .env.local 或环境变量读取：OPENAI_API_KEY、OPENAI_BASE_URL、OPENAI_MODEL。")

    st.caption(f"专项检查重点：{MAP_TYPES[map_type]['checks']}")

    if uploaded_file is None:
        st.markdown('<div class="mp-empty">上传截图后，这里会显示地图预览和审图结果。</div>', unsafe_allow_html=True)
        return

    image_bytes = uploaded_file.getvalue()
    try:
        validate_image_upload(uploaded_file.name, image_bytes)
    except ValueError as exc:
        st.error(str(exc))
        return

    st.image(image_bytes, caption="地图截图预览", use_container_width=True)

    if st.button("生成审图意见", type="primary", key="start_image_review"):
        try:
            review = create_review_result(image_bytes, map_type, use_case, analyzer_mode)
            st.session_state["review_result"] = review
            st.session_state["review_image"] = image_bytes
            st.session_state["review_filename"] = uploaded_file.name
            st.session_state.pop("mxd_layers", None)
            st.session_state.pop("polish_result", None)
        except OpenAIConfigError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"审图失败：{exc}")


def create_review_result(
    image_bytes: bytes,
    map_type: str,
    use_case: str,
    analyzer_mode: str,
) -> AnalysisResultWithActions:
    if analyzer_mode == "OpenAI 实审":
        settings = load_model_settings()
        return analyze_map_with_openai(image_bytes, map_type, use_case, settings)

    analysis = analyze_map(image_bytes, map_type, use_case)
    auto_actions, manual_actions = build_default_actions(analysis)
    return AnalysisResultWithActions(analysis=analysis, auto_actions=auto_actions, manual_actions=manual_actions)


def render_mxd_panel() -> None:
    st.markdown(
        """
        <div class="mp-panel">
          <div class="mp-panel-title">MXD 自动修改</div>
          <div class="mp-panel-copy">上传 ArcMap 10.8 工程，确认图层映射后生成优化副本。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded_mxd = st.file_uploader(
        "上传 ArcMap MXD 工程",
        type=["mxd"],
        help="仅支持 ArcMap 10.8 的 .mxd 文件。系统只生成副本，不覆盖原文件。",
        key="mxd_upload",
    )
    if uploaded_mxd is None:
        st.info("审图结果已生成。上传 MXD 后即可继续自动修改。")
        return

    mxd_bytes = uploaded_mxd.getvalue()
    try:
        validate_mxd_upload(uploaded_mxd.name, mxd_bytes)
    except ValueError as exc:
        st.error(str(exc))
        return

    if st.button("读取 MXD 图层", type="primary", key="inspect_mxd"):
        with st.spinner("正在调用 ArcPy 读取 MXD..."):
            mxd_path = save_uploaded_mxd(uploaded_mxd.name, mxd_bytes)
            inspection = inspect_mxd(mxd_path)
        st.session_state["mxd_path"] = mxd_path
        st.session_state["mxd_layers"] = inspection.layers
        st.session_state["mxd_layout_elements"] = inspection.layout_elements
        st.session_state["mxd_warnings"] = inspection.warnings
        st.session_state["suggested_mapping"] = suggest_layer_mapping(inspection.layers)
        st.session_state.pop("mxd_context_refined", None)
        st.session_state.pop("polish_result", None)

    layers = st.session_state.get("mxd_layers")
    if not layers:
        st.info("读取图层后会显示角色映射。")
        return

    st.markdown("### 图层映射")
    for warning in st.session_state.get("mxd_warnings", []):
        st.warning(warning)

    suggested = st.session_state.get("suggested_mapping", {})
    layer_mapping = {}
    options = [""] + layers
    for role, config in LAYER_ROLES.items():
        suggested_layer = suggested.get(role, "")
        default_index = options.index(suggested_layer) if suggested_layer in options else 0
        layer_mapping[role] = st.selectbox(
            config["label"],
            options=options,
            index=default_index,
            format_func=lambda value: "不设置" if value == "" else value,
            key=f"layer_role_{role}",
        )

    render_mxd_context_refinement(layer_mapping)

    st.markdown("### 执行设置")
    layout_col_1, layout_col_2 = st.columns(2)
    with layout_col_1:
        title = st.text_input("标题", value="MapPolish 自动优化地图")
        data_source = st.text_input("数据来源", value="数据来源：请补充")
    with layout_col_2:
        map_time = st.text_input("制图时间", value="制图时间：请补充")

    rule_col_1, rule_col_2 = st.columns(2)
    with rule_col_1:
        enable_layout = st.checkbox("启用布局元素补充", value=True)
    with rule_col_2:
        enable_symbol = st.checkbox("启用图层基础符号调整", value=True)

    if st.button("调用 ArcMap 10.8 生成优化副本", type="primary", key="run_arcmap_polish"):
        review = st.session_state["review_result"]
        layout_options = {
            "title": title,
            "data_source": data_source,
            "map_time": map_time,
        }
        rules = {
            "layout": enable_layout,
            "symbol": enable_symbol,
        }
        with st.spinner("正在调用 ArcPy 生成 MXD 副本和 PNG..."):
            result = run_arcmap_polish(
                st.session_state["mxd_path"],
                layer_mapping,
                layout_options,
                rules,
                actions_to_dicts(review.auto_actions),
            )
        st.session_state["polish_result"] = result


def render_mxd_context_refinement(layer_mapping: dict[str, str]) -> None:
    if st.session_state.get("analyzer_mode") != "OpenAI 实审":
        return

    review = st.session_state.get("review_result")
    image_bytes = st.session_state.get("review_image")
    if not review or not image_bytes:
        return

    if st.session_state.get("mxd_context_refined"):
        st.success("已结合 MXD 上下文精修审图动作。")
        return

    st.info("可选：读取图层后，让模型结合 MXD 图层、布局元素和当前映射再次生成更精准的可执行动作。")
    if st.button("结合 MXD 上下文精修动作", key="refine_actions_with_mxd"):
        mxd_context = {
            "layers": st.session_state.get("mxd_layers", []),
            "layout_elements": st.session_state.get("mxd_layout_elements", []),
            "warnings": st.session_state.get("mxd_warnings", []),
            "layer_mapping": layer_mapping,
        }
        previous_summary = format_markdown_report(review.analysis)
        try:
            with st.spinner("正在结合 MXD 上下文进行二次模型审图..."):
                refined = analyze_map_with_mxd_context(
                    image_bytes,
                    st.session_state["image_map_type"],
                    st.session_state["image_use_case"],
                    load_model_settings(),
                    mxd_context,
                    previous_summary,
                )
            st.session_state["review_result"] = refined
            st.session_state["mxd_context_refined"] = True
            st.session_state.pop("polish_result", None)
            st.success("MXD 上下文精修完成，右侧审图报告和自动动作已更新。")
        except OpenAIConfigError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"MXD 上下文精修失败：{exc}")


def render_inspector() -> None:
    st.markdown(
        """
        <div class="mp-panel">
          <div class="mp-panel-title">审图确认</div>
          <div class="mp-panel-copy">评分、问题和自动动作会在这里汇总。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    review = st.session_state.get("review_result")
    if review is None:
        st.markdown('<div class="mp-empty">等待截图审图结果。</div>', unsafe_allow_html=True)
        return

    st.metric("综合评分", f"{review.analysis.overall_score}/100")
    st.markdown(format_markdown_report(review.analysis))
    st.download_button(
        "导出 Markdown",
        data=format_markdown_report(review.analysis).encode("utf-8"),
        file_name="mappolish-report.md",
        mime="text/markdown",
    )

    st.markdown("### 自动执行动作")
    if review.auto_actions:
        for action in review.auto_actions:
            st.markdown(
                f"""
                <div class="mp-action mp-action-auto">
                  <div class="mp-action-label">{action.type} / {action.target_role}</div>
                  <div class="mp-action-text">{action.reason}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("没有可自动执行动作。")

    st.markdown("### 人工处理建议")
    if review.manual_actions:
        for action in review.manual_actions:
            st.markdown(
                f"""
                <div class="mp-action mp-action-manual">
                  <div class="mp-action-label">{action.target_role}</div>
                  <div class="mp-action-text">{action.reason}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("没有额外人工处理项。")


def render_execution_panel() -> None:
    st.markdown(
        """
        <div class="mp-execution">
          <div class="mp-panel-title">ArcPy 执行</div>
          <div class="mp-panel-copy">执行日志、警告和下载结果会显示在这里。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    result = st.session_state.get("polish_result")
    if not result:
        st.info("尚未执行 ArcMap 自动修改。")
        return

    for change in result.changes:
        st.success(change)
    for warning in result.warnings:
        st.warning(warning)
    for error in result.errors:
        st.error(error)

    download_col_1, download_col_2 = st.columns(2)
    with download_col_1:
        render_file_download("下载优化后的 MXD", result.output_mxd, "application/octet-stream")
    with download_col_2:
        render_file_download("下载导出的 PNG", result.output_png, "image/png")

    if result.output_png and os.path.exists(result.output_png):
        st.image(result.output_png, caption="导出 PNG 预览", use_container_width=True)


def render_file_download(label: str, path: str, mime: str) -> None:
    if not path or not os.path.exists(path):
        st.info(f"{label}：文件未生成。")
        return

    with open(path, "rb") as file_obj:
        st.download_button(
            label,
            data=file_obj.read(),
            file_name=os.path.basename(path),
            mime=mime,
        )


if __name__ == "__main__":
    main()
