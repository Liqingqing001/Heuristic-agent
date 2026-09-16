# 智育助教 Agent —— 基于 RAG 与苏格拉底教学法的数据结构智能助教

为学习《数据结构与算法》的学生打造的**"只启发、不泄题"**智能 AI 助教：复用 RAG 检索课程知识库，通过硬性 Prompt 约束保证助教绝不直接给出 C/C++ 完整代码，而是用提问、逻辑诊断、伪代码引导学生自主 Debug。

## 技术栈

| 层 | 技术 |
|---|---|
| 大模型 | DeepSeek（`deepseek-chat`，OpenAI 兼容） |
| 向量化 | 本地 BGE 模型 `BAAI/bge-small-zh-v1.5`（sentence-transformers） |
| 向量库 | ChromaDB（本地持久化） |
| 后端 | FastAPI + Uvicorn |
| 前端 | Vue3 + Vite（`marked` + `highlight.js` 渲染） |

## 目录结构

```
backend/
  app/
    main.py            # FastAPI 入口
    config.py          # 读取 .env、路径常量
    api/               # chat.py / code.py / knowledge.py 三个路由
    core/              # llm.py(DeepSeek) / embedding.py(BGE) / rag.py(建库检索)
    agents/            # prompts.py(硬约束Prompt) / socratic.py(对话编排)   ← 课题核心
    utils/             # code_parser.py(代码控制流粗解析)
  data/
    knowledge/         # 讲义 / 题解 / bug库 示例知识库（Markdown）
    vector_db/         # ChromaDB 持久化目录（首次建库后生成）
frontend/              # Vue3 + Vite
```

## 环境要求

- Python 3.12（本机已验证）
- Node 18+（本机已验证 v22）
- 一个可用的 DeepSeek API Key

## 安装

### 1. 后端

```powershell
cd backend
py -m pip install -r requirements.txt
```

> 首次会安装 torch（约 2GB），请耐心等待。

### 2. 配置密钥

```powershell
copy .env.example .env
```

编辑 `.env`，把 `DEEPSEEK_API_KEY` 替换成你的真实密钥。

### 3. 前端

```powershell
cd ../frontend
npm install
```

## 启动

### 方式一：开发模式（推荐，前后端分离）

终端 1 启动后端：

```powershell
cd backend
py -m uvicorn app.main:app --reload --port 8000
```

终端 2 启动前端：

```powershell
cd frontend
npm run dev
```

浏览器打开 http://localhost:5173 （前端已把 `/api` 代理到后端 8000）。

### 方式二：生产模式（FastAPI 托管前端构建产物）

```powershell
cd frontend
npm run build          # 产出 frontend/dist
cd ../backend
py -m uvicorn app.main:app --port 8000
```

浏览器打开 http://localhost:8000 即可。

## 首次使用

1. 打开「知识库状态」页，点击**「重新建库」**。首次会下载 BGE 模型（约 100MB），耗时较长。
2. 建库完成后，各知识库显示分块数量 > 0。
3. 切换到「苏格拉底对话」或「代码剖析」开始体验。

## 验证"不泄题"

- 在对话页问 **「怎么反转单链表？」** → 助教应反问引导，**不输出**完整的反转函数。
- 在代码剖析页提交一段**含断链/内存泄漏的 C++ 代码** → 助教应给出逻辑诊断 + 提问，且不含可直接运行的完整修复代码。

## 课题核心说明

**1. 苏格拉底 Prompt 工程（`backend/app/agents/prompts.py`）**

系统 Prompt 以"硬性约束"为最高优先级，明确：禁止输出完整可编译代码、禁止泄题、先诊断后引导；并定义了**三阶提示法**（一阶反问 → 二阶定位到行 → 三阶伪代码/类比），让助教由浅入深、逐级引导而非一次性抛答案。

**2. 代码控制流剖析（`backend/app/utils/code_parser.py`）**

对提交的 C/C++ 代码做启发式粗解析，提取内存操作、指针链操作、可能的树旋转、疑似递归等线索，作为额外上下文喂给 LLM，使诊断聚焦在断链、内存泄漏、旋转失衡等具体痛点。

**3. RAG 建库与检索（`backend/app/core/rag.py`）**

讲义/题解/bug 库按二级标题分块存入 ChromaDB；代码剖析场景下 bug 库优先加权检索，命中高频错误案例辅助诊断。

## 自定义知识库

替换 `backend/data/knowledge/` 下的 Markdown 文档即可。文档用 `## ` 二级标题分节（每个小节成为一个检索块），然后在「知识库状态」页点击「重新建库」。
