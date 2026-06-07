# MapPolish

MapPolish 是一个面向 ArcMap 10.8 的 GIS 制图审查与自动改图原型。当前版本基于 Streamlit 构建，支持上传地图截图进行模型审图，并在上传 `.mxd` 后结合 MXD 图层上下文生成更精准的可执行修改动作，最后通过 ArcPy 生成优化副本和 PNG 预览。

## 功能概览

- 上传 PNG/JPG/WEBP 地图截图。
- 选择地图类型和使用场景。
- 支持离线模拟审图和 OpenAI/兼容模型实审。
- 生成结构化审图报告和 Markdown 导出。
- 上传 ArcMap 10.8 `.mxd` 工程。
- 读取 MXD 图层、布局元素和数据源警告。
- 用户确认图层角色映射。
- 模型结合截图和 MXD 上下文二次生成可执行动作。
- ArcPy worker 生成 `*_polished.mxd` 副本和 PNG 预览。
- 永远不覆盖用户原始 `.mxd`。

## 工作流程

```text
上传地图截图
→ 模型初审，生成审图报告和初始 auto_actions
→ 上传 ArcMap 10.8 .mxd
→ ArcPy 读取图层、布局元素、数据源警告
→ 用户确认图层映射
→ 模型结合 MXD 上下文二次精修动作
→ ArcPy 按安全 action 生成 *_polished.mxd 和 PNG
```

## 项目结构

```text
map-polish-v0/
  app.py                    Streamlit 页面入口
  ai_analyzer.py            模型调用、截图初审、MXD 上下文二次审图
  action_schema.py          安全 action 白名单和 action 清洗
  arcmap_automation.py      Python 3 侧 ArcPy 子进程调用
  layer_matching.py         图层角色关键词匹配
  map_types.py              地图类型、使用场景、专项检查说明
  mock_analyzer.py          离线 mock 审图结果
  report.py                 Markdown 报告格式化
  schemas.py                数据结构
  utils.py                  图片校验
  scripts/
    arcmap_worker.py        Python 2.7 ArcPy worker
  tests/                    单元测试
```

## 环境要求

- Windows
- Python 3.12 或兼容版本
- Streamlit
- ArcMap 10.8
- ArcGIS Python 2.7，默认路径：

```text
C:\Python27\ArcGIS10.8\python.exe
```

## 安装依赖

项目当前使用本地虚拟环境：

```text
map-polish-v0\deps-venv
```

如需重新安装依赖：

```powershell
cd D:\CodexStudy\ArcGIS制图助手\map-polish-v0
python -m venv deps-venv
.\deps-venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 本地运行

```powershell
cd D:\CodexStudy\ArcGIS制图助手\map-polish-v0
.\deps-venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

访问：

```text
http://localhost:8502
```

如果端口被占用，可改用其他端口：

```powershell
.\deps-venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```

## 模型配置

模型配置只从 `.env.local` 或环境变量读取，不在 UI 中填写。

在 `map-polish-v0/.env.local` 中配置：

```env
OPENAI_API_KEY=你的 API Key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

也支持 OpenAI 兼容的完整 Chat Completions endpoint：

```env
OPENAI_BASE_URL=https://example.com/v1/chat/completions
```

注意：

- `.env.local` 不应提交到 GitHub。
- `.env.local.example` 只保留变量模板。
- 实审模式需要使用支持图像输入和 JSON 输出的多模态模型。

## 安全 action

模型不能生成任意 Python/ArcPy 脚本。当前只允许以下白名单 action：

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

未知 action 会降级为人工建议，不会自动执行。

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

## 当前限制

- 第一版仍是 Streamlit 原型，不是 Next.js 产品化应用。
- 自动改图只执行安全白名单动作，不允许模型直接执行任意 ArcPy 代码。
- 复杂色带、分类渲染、高级标注仍需继续扩展。
- 图层识别当前采用关键词预选和用户手动确认。
- 实审精度依赖模型是否支持图像输入、JSON 输出和稳定的多模态能力。

## 后续方向

- 继续细化 MXD 上下文二次审图 prompt。
- 扩展安全 action schema。
- 增强 ArcPy worker 对线宽、线色、图例、标注、图层顺序的可控修改能力。
- 增加真实 MXD 样例集成测试。
- 在保持安全边界的前提下提升自动改图精度。
