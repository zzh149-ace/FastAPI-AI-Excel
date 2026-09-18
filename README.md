# AI 全栈开发学习计划生成器

一套完整、可直接部署、逻辑闭环的学习计划生成软件：用户填写表单 → 后端优先校验学历 → 拼接固定 8 门课程 → 调用 Claude 生成个性化可落地学习计划 → 自动导出本地 Excel 文件（文件名固定为 **学习计划.xlsx**）。

## 目录结构

```
learning-plan-generator/
├── app.py              # FastAPI 后端入口（路由 + 学历校验 + 导出）
├── config.py           # 固定课程体系、学历选项、文案、模型、文件名
├── generator.py        # 拼接 Prompt + 调用 Claude + JSON 解析 + 演示兜底
├── excel_writer.py     # openpyxl 生成「学习计划.xlsx」
├── static/
│   └── index.html      # 前端表单页面
├── exports/            # 生成的 Excel 存放目录（自动创建）
├── requirements.txt
└── README.md
```

## 业务规则（与需求一一对应）

1. **前端表单**：姓名（文本框）、性别（单选 男/女）、年龄（文本框）、学历（下拉，默认「本科」）、知识基础（文本框）、学习习惯（文本框）。
2. **后端校验优先**：学历选「其他」时，直接返回固定文案「同学，可以考虑其他非开发类的方向。」，不拼接课程、不调用 AI、不生成计划、不导出 Excel。
3. **固定课程体系**：后端内置 8 门课程，正常流程下自动与用户信息拼接为 Prompt。
4. **AI 生成**：个性化、可落地、全覆盖 8 门课程、分层规划（入门/进阶/实战/就业冲刺）、每日任务、阶段目标、就业备考方案、个性化建议。
5. **导出**：固定文件名 `学习计划.xlsx`，包含全部 8 项内容。

## 环境准备

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Claude API Key（真实调用）

- **Windows CMD**：`set ANTHROPIC_API_KEY=sk-ant-...`
- **PowerShell**：`$env:ANTHROPIC_API_KEY="sk-ant-..."`
- **Git Bash / Linux / macOS**：`export ANTHROPIC_API_KEY=sk-ant-...`

> 未配置 Key 或调用失败时，程序会自动降级为**演示模式**（用固定逻辑生成一份可用计划），保证整条「表单 → 校验 → 生成 → 导出」闭环始终可跑通。

### 3. 启动服务

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

浏览器访问：<http://127.0.0.1:8000>

## 使用流程

1. 填写表单（学历默认「本科」）。
2. 点击「生成学习计划」。
3. 后端优先校验学历：
   - 选择「其他」→ 页面直接显示劝退文案，流程终止。
   - 其他学历 → 自动拼接 8 门课程，调用 Claude 生成计划，浏览器自动下载 `学习计划.xlsx`。
