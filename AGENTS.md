# AGENTS.md

本文件用于帮助后续 Codex/代理快速接手 `ArcGIS制图助手` 项目。回答用户时默认使用中文；代码、文件名、变量名保持英文。

## 项目概览

当前项目只有一个可运行原型目录：

```text
D:\CodexStudy\ArcGIS制图助手\map-polish-v0
```

这是一个 Python + Streamlit 原型，不是 Node/Next.js 项目，因此本地运行不使用 `npm start`。

项目目标是构建 MapPolish 审图与 ArcMap 自动改图流程：

```text
上传地图截图
→ 模型初审，生成审图报告和初始 auto_actions
→ 上传 ArcMap 10.8 .mxd
→ ArcPy 读取图层、布局元素、数据源警告
→ 用户确认图层映射
→ 模型结合 MXD 上下文二次精修动作
→ ArcPy 按安全 action 生成 *_polished.mxd 和 PNG
```

## 本地运行

在 PowerShell 中运行：

```powershell
cd D:\CodexStudy\ArcGIS制图助手\map-polish-v0
.\deps-venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

访问：

```text
http://localhost:8502
```

如果 8502 被占用，可换端口：

```powershell
.\deps-venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```

## 配置文件

模型配置从 `.env.local` 或系统环境变量读取，不在 UI 中填写。

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

也支持 OpenAI 兼容的完整 Chat Completions endpoint，例如：

```env
OPENAI_BASE_URL=https://example.com/v1/chat/completions
```

注意：

- `.env.local` 存真实密钥，已被 `.gitignore` 忽略。
- `.env.local.example` 只应作为模板，不应保留真实 Key。
- 若模型返回非 JSON，`ai_analyzer.py` 会给出更清晰的错误提示。

## 依赖与环境

Python 3 原型依赖：

```text
streamlit
Pillow
pytest
requests
```

虚拟环境位置：

```text
map-polish-v0\deps-venv
```

ArcMap 自动化依赖本机 ArcMap 10.8：

```text
C:\Python27\ArcGIS10.8\python.exe
```

ArcPy worker 使用 Python 2.7 语法，修改 `scripts/arcmap_worker.py` 时必须保持 Python 2.7 兼容。

## 目录结构

```text
map-polish-v0/
  app.py                    Streamlit UI 和页面流程入口
  ai_analyzer.py            OpenAI/兼容模型调用、截图初审、MXD 上下文二次审图
  action_schema.py          安全 action 白名单、action 清洗、离线默认 action
  arcmap_automation.py      Python 3 侧 ArcPy 子进程调用、MXD 保存、配置写入
  layer_matching.py         图层角色关键词匹配
  map_types.py              地图类型、使用场景、专项检查说明
  mock_analyzer.py          离线 mock 审图结果
  report.py                 Markdown 报告格式化
  schemas.py                审图结果、问题、步骤、action 数据结构
  utils.py                  图片校验
  scripts/
    arcmap_worker.py        Python 2.7 ArcPy worker，真正读取/修改/导出 MXD
  tests/
    test_ai_analyzer.py
    test_app_ui.py
    test_arcmap_automation.py
    test_mock_analyzer.py
    test_report.py
    test_utils.py
```

## 主流程控制点

### 1. Streamlit 页面

入口文件：

```text
app.py
```

关键职责：

- 上传地图截图。
- 选择地图类型、使用场景、审图模式。
- 调用 `create_review_result()` 生成初审结果。
- 上传 `.mxd`。
- 调用 `inspect_mxd()` 读取图层。
- 展示图层映射下拉框。
- 在 OpenAI 实审模式下提供“结合 MXD 上下文精修动作”按钮。
- 调用 `run_arcmap_polish()` 执行 ArcMap 自动改图。

### 2. 模型审图

控制文件：

```text
ai_analyzer.py
```

关键函数：

- `analyze_map_with_openai()`：截图初审。
- `analyze_map_with_mxd_context()`：截图 + MXD 上下文二次审图。
- `build_request_payload()`：初审请求体。
- `build_mxd_context_request_payload()`：二次审图请求体。
- `parse_openai_response()`：解析模型 JSON 输出。

精度主要由 `_build_prompt()` 和 `_build_mxd_context_prompt()` 控制。

### 3. Action 安全边界

控制文件：

```text
action_schema.py
```

当前允许自动执行的 action：

```text
add_layout_text
emphasize_layer
set_layer_visibility
set_layer_transparency
export_preview
set_layer_order
set_text_element
set_layer_label_visibility
```

不允许模型生成任意 Python/ArcPy 脚本。未知 action 会降级为 `manual_only`。

### 4. MXD 图层识别

控制文件：

```text
layer_matching.py
```

当前采用“关键词预选 + 用户手动修正”：

- 水系/河流
- 流域边界
- 研究区
- 行政边界
- DEM/栅格
- 降雨/水深

若自动改图不准，优先检查图层映射是否正确。

### 5. ArcMap 自动修改

Python 3 调用侧：

```text
arcmap_automation.py
```

ArcPy 执行侧：

```text
scripts\arcmap_worker.py
```

worker 目前会：

- 复制原始 MXD，永远不覆盖原文件。
- 补充或克隆布局文本元素。
- 根据图层角色执行保守符号规则。
- 消费 `auto_actions`，执行文本、可见性、透明度、标签开关、图层顺序等安全动作。
- 导出 PNG 预览。

复杂色带、分类渲染、高级标注仍应谨慎处理，暂不允许模型直接生成任意 ArcPy 代码。

## 测试

运行全部测试：

```powershell
cd D:\CodexStudy\ArcGIS制图助手\map-polish-v0
.\deps-venv\Scripts\python.exe -m unittest discover -s tests -v
```

验证 ArcPy worker Python 2.7 语法：

```powershell
cd D:\CodexStudy\ArcGIS制图助手\map-polish-v0
& 'C:\Python27\ArcGIS10.8\python.exe' -B -c "compile(open('scripts\\arcmap_worker.py','rb').read(), 'scripts\\arcmap_worker.py', 'exec'); print('syntax ok')"
```

验证 Streamlit 页面渲染：

```powershell
cd D:\CodexStudy\ArcGIS制图助手\map-polish-v0
.\deps-venv\Scripts\python.exe -B -c "from streamlit.testing.v1 import AppTest; at=AppTest.from_file('app.py'); at.run(); print('exceptions', len(at.exception))"
```

## 实施注意事项

- 默认用中文回答用户。
- 不要把 API Key、真实 `.env.local` 内容、完整密钥打印到聊天中。
- UI 配置不应暴露 API Key/Base URL/模型名，只从配置文件或环境变量读取。
- 不要让模型输出任意 ArcPy/Python 代码并执行。
- 任何自动改图都必须保存为副本，不能覆盖用户原始 `.mxd`。
- 修改 `arcmap_worker.py` 时必须考虑 Python 2.7 兼容性。
- Streamlit UI 当前是原型工作台，不要引入 Node/npm 启动方式，除非项目明确迁移到前端框架。
- 若模型审图不准，优先检查：
  - 当前模型是否支持图像输入。
  - 模型是否稳定返回 JSON。
  - `_build_prompt()` 和 `_build_mxd_context_prompt()` 是否足够具体。
  - MXD 图层映射是否正确。
  - `arcmap_worker.py` 是否真正消费对应 action。

## 当前主要改进方向

- 继续细化二次审图 prompt，让模型结合图层、布局元素和初审问题输出更具体 action。
- 扩展安全 action，但仍保持白名单执行。
- 提升 ArcPy worker 对线宽、线色、图例、标注、图层顺序的可控修改能力。
- 增加真实 MXD 样例的集成测试。
