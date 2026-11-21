# Process-craft-rag

基于检索增强生成（RAG）的轻量级企业工艺知识问答与加工指令生成系统。

项目对工艺 PDF 进行解析、分块和混合检索，结合大模型生成带有文档名、物理页码及原文片段引用的回答与加工指令草案。所有输出仅供工艺人员审核，不直接用于生产控制。

## 当前状态

**I1 核心链路已实现并完成真实样例验收。** 使用 69 页 NIST AMS 400-1 建立了 250 个分块的不可变快照，SQLite、Qdrant 和 BM25 的 chunk ID 完全一致。系统已支持：

- PDF 导入、后台处理、状态查询和原文下载；失败记录可重试或删除；
- 服务端设置页：模型、密钥、嵌入/重排和检索参数，支持真实连接测试与恢复环境默认；
- 稠密检索、BM25、RRF 融合、百炼重排序和上下文预算控制；
- DeepSeek 非流式知识问答与结构化加工指令草案；
- 引用白名单、物理页码、原文快照和 PDF 对应页链接；
- Vue 3 最小工作台、固定 8 题评估脚本和 I1 验收报告。

本轮 8 题开发核查的有效回答基线为 **5/8（62.5%）**，18 条引用全部可定位，未出现无依据关键工艺参数。多要点检索遗漏和草案引用过宽已列为后续改进项，不把本轮结果视为最终质量达标。

详见 **[I1 验收报告](docs/评估记录/I1/验收报告.md)**。

## 快速启动

### Docker Compose

准备 Docker Desktop 或等价 Docker Compose 环境，然后启动：

```bash
docker compose up -d --build
docker compose ps
```

启动后打开“设置”页即可配置模型密钥和参数。也可以先执行 `cp .env.example .env`，在本地 `.env` 中填写 `LLM_API_KEY` 与 `DASHSCOPE_API_KEY`；页面保存的运行时配置优先于环境变量，真实密钥不得提交。

- 工作台：http://localhost:8080
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health

首次启动会自动执行 SQLite 迁移，并启动 API、单 Worker、前端和 Qdrant。进入工作台后导入文本型 PDF，等待状态变为“可检索”再提问。后续更新代码同样执行 `docker compose up -d --build`。

常用运维命令：

```bash
docker compose logs -f api worker  # 查看 API 与 Worker 日志
docker compose restart api worker  # 重启应用服务
docker compose stop                # 停止全部服务，保留数据卷
```

### 模型 API 获取与配置

本项目默认使用 DeepSeek 生成、阿里云百炼文本嵌入和重排序。嵌入与重排可以共用同一个、且与地域匹配的百炼 API Key。

| 用途 | 获取入口 | 本项目默认值 |
| --- | --- | --- |
| DeepSeek 生成模型 | [DeepSeek API Keys](https://platform.deepseek.com/api_keys) | `LLM_MODEL=deepseek-flash` |
| 百炼嵌入与重排 | [百炼控制台](https://bailian.console.aliyun.com/cn-beijing#/home) → API Key；[官方获取与配置指南](https://help.aliyun.com/zh/model-studio/get-api-key) | `EMBEDDING_MODEL=text-embedding-v4`，`RERANK_MODEL=qwen3-rerank` |
| 嵌入接口说明 | [百炼文本嵌入 API](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api) | 北京地域 Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 重排接口说明 | [百炼文本重排序 API](https://help.aliyun.com/zh/model-studio/text-rerank-api) | 由后端按地域生成独立重排地址 |

获取百炼密钥时，在控制台选择**华北2（北京）**并创建或复制 API Key；新版密钥可能只在创建时完整显示一次，应立即保存。API Key 按地域隔离，不能跨地域混用；如使用其他地域，必须同时在设置页修改服务地域。

推荐使用页面配置：打开 http://localhost:8080 → **设置** → **嵌入与重排序**，填写百炼 API Key，Workspace ID 按所属业务空间填写，保存后点击“测试嵌入”和“测试重排序”。

也可以通过 `.env` 提供初始值：

```dotenv
LLM_API_KEY=<你的 DeepSeek API Key>
DASHSCOPE_API_KEY=<你的百炼 API Key>
DASHSCOPE_WORKSPACE_ID=
DASHSCOPE_REGION=cn-beijing
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSIONS=1024
RERANK_MODEL=qwen3-rerank
```

`.env` 只用于首次提供环境默认值；在设置页保存后，以服务端运行时配置为准。不要把真实密钥写入 README、前端源码或 Git。

### 本机开发

需要 Python 3.11、uv、Node.js 24 和 Docker。

```bash
docker compose up -d qdrant

cd backend
uv sync --python 3.11
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

另开终端启动单 Worker：

```bash
cd backend
uv run python -m app.worker
```

前端开发服务：

```bash
cd frontend
npm ci
npm run dev
```

开发页面位于 http://localhost:5173。配置由后端 Pydantic Settings 集中读取；前端不持有模型密钥。

## 验证

在 Git Bash 中执行：

```bash
cd backend
uv run ruff check app tests scripts migrations
uv run pytest -q
RUN_QDRANT_TESTS=1 uv run pytest -q  # 需要本地 Qdrant

cd ../frontend
npm run build
npm audit
```

对正在运行的真实 API 执行 I1 冻结题集：

```bash
cd backend
uv run python scripts/run_i1_smoke.py
```

脚本会上传或复用 A4、等待 `ready`、运行 8 题并保存四阶段诊断。默认写入 `docs/评估记录/I1/原始输出.json`；为保留已评分基线，复现时应指定新文件，例如 `--output data/i1-rerun.json`。脚本不会自动生成人工评分。

## 文档入口

- **[开发文档与数据集](docs/README.md)**：需求、架构、调研、模型验证、UML 和样例数据的统一入口。
- [开发计划与风险](docs/开发文档/开发计划.md)：双周迭代、中期报告、需求追踪和完成定义。
- [协作与提交规范](docs/开发文档/协作与提交规范.md)：AI 开发提示词、分支、提交、PR、合并、标签和检查要求。
- [I1 验收报告](docs/评估记录/I1/验收报告.md)：版本、测试、真实输出、评分、已知问题和后续调整。
- [样例候选与下载](docs/样例文件/候选与下载.md)：开放资料、下载状态和入库约定。

## 使用边界

系统输出为 **AI 辅助生成的工艺建议，必须由工艺人员审核**，不可直接用于生产控制或替代正式工艺规程。缺少材料、图纸、公差或设备条件时，系统应标记待确认信息，不得编造参数或引用。

当前项目样例允许发送到所选外部模型服务；新增资料仍须单独确认外发权限。外部样例资料仅在各自许可范围内使用，正式演示包须保留来源、许可和必要署名。
