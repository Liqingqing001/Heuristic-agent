# 智育助教 Agent

面向《数据结构与算法》课程的智能助教：**只启发、不泄题**。基于 RAG 检索课程知识点，用苏格拉底式提问引导学生自己定位和修复问题，并给教师提供班级学情看板。

> 2026-10 更新：新增教师端/学生端、班级与任务、结构化诊断、知识点库（kp）、自带密钥（BYOK）。
> 技术改动清单见 [`docs/本次改动.md`](docs/本次改动.md)。

---

## 1. 现在能做什么

### 学生端
- 注册时选择「学生」身份，用 6 位邀请码加入班级
- 「作业中心」：按班级看任务，按「待完成 / 已提交」筛选，点开能看到自己提交过的代码、AI 诊断全文、错因标签和提交时间
- 「学习助手」：对话问答与代码诊断合并在一页，两种模式共用知识点与「不泄题」约束
- 「我的」：个人资料（姓名、昵称、学校、院系、专业、性别、入学年份、简介）和修改密码

### 教师端
- 注册时选择「教师」身份，创建班级并生成邀请码
- 发布任务：标题、说明、类型、关联知识点、截止时间
- 学情看板：提交率、未交名单、错因分布、每个学生的进度
- 查看某个任务的所有提交、单个学生的代码与 AI 诊断全文
- 重建知识库（学生无此权限）

### 密钥（BYOK）
- 使用者点右上角「模型设置」填自己的 DeepSeek API Key
- Key 只存在浏览器本地（默认仅本次会话，勾选后记住本机）
- 请求时由后端透传给 DeepSeek，**不写数据库、不写日志**

---

## 2. 技术栈

| 层 | 技术 |
|---|---|
| 大模型 | DeepSeek `deepseek-chat`（OpenAI 兼容，BYOK 透传） |
| 向量化 | 本地 BGE `BAAI/bge-small-zh-v1.5`（sentence-transformers） |
| 向量库 | ChromaDB（本地持久化，四个 collection：讲义/题解/Bug库/知识点） |
| 后端 | FastAPI + Uvicorn + SQLite（单库 `app.db`） |
| 前端 | Vue3 + Vite（`marked` + `highlight.js`） |

---

## 3. 快速开始

### 环境要求
Python 3.12、Node 18+、一个 DeepSeek API Key（每个使用者自备）。

### 后端

```powershell
cd backend
py -m pip install -r requirements.txt
copy .env.example .env        # 可选：填 SECRET_KEY 与服务端公共 key
py -m uvicorn app.main:app --reload --port 8000
```

首次启动会自动建表，并把旧版 `data/chat.db` 里的会话迁移到 `data/app.db`（原文件保留）。

### 前端

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173 。

### 生产模式

```powershell
cd frontend
npm run build
cd ../backend
py -m uvicorn app.main:app --port 8000
```

打开 http://localhost:8000 （前后端同端口，FastAPI 托管 `dist`）。

---

## 4. 首次使用

1. **注册**：选择「我是学生」或「我是教师」。
2. **填密钥**：登录后点右上角「模型设置」，粘贴自己的 DeepSeek Key。不填且服务端也没配置公共 key 时，顶部横幅会提示，对话不可用。
3. **建知识库**（教师）：进入「知识库」页点「重新建库」。首次会下载 BGE 模型（约 100MB）。
4. **教师**：教师工作台 → 新建班级 → 复制邀请码 → 发布任务。
5. **学生**：我的班级 → 输入邀请码 → 点任务「去完成」→ 在代码剖析页提交 → 自动回到任务状态「已提交」。

### 演示账号（已内置一条示例数据）

| 角色 | 账号 | 密码 |
|---|---|---|
| 教师 | `demo_teacher` | `demo123456` |
| 学生 | `demo_student` | `demo123456` |

演示班级邀请码：`TYK975`（「数据结构 2026 春 · 演示班」，含一个代码任务和一个问答任务，学生已有一次提交）。

---

## 5. 目录结构

```
backend/
  app/
    main.py               # 入口：路由注册、数据库初始化
    config.py             # .env 与路径常量
    api/
      auth.py             # 注册/登录（含 role）
      profile.py          # 个人资料、修改密码
      chat.py             # 苏格拉底对话（SSE）
      code.py             # 代码剖析（SSE + 结构化诊断 + 作业提交）
      conversation.py     # 会话管理
      knowledge.py        # 知识库建库/浏览/搜索
      classes.py          # 班级、任务、提交、看板
      llm.py              # 模型状态（给前端横幅用）
    core/
      db.py               # 统一 SQLite：建表 + 旧库迁移
      store.py            # 数据访问层
      auth.py             # JWT（SECRET_KEY 从环境变量或 .secret_key 读取）
      llm.py              # 模型客户端（支持按请求传 key）
      rag.py              # 检索：向量优先，不可用时关键词降级
      embedding.py        # BGE 懒加载
    agents/
      prompts.py          # 人设 + 硬约束 + 三阶提示 + 结构化诊断协议
      socratic.py         # 编排：检索 → 拼装 → 流式 → 诊断
      stream_filter.py    # 把 <<<DIAG ... DIAG>>> 从流里剥离
      diagnosis.py        # 诊断 JSON 解析、校验与兜底
    utils/
      code_parser.py      # C/C++ 静态线索
      kp_meta.py          # 知识点 front matter 解析
  data/
    app.db                # 唯一数据库（忽略提交）
    knowledge/
      lecture/ solutions/ buglib/   # 旧版知识库
      kp/                           # 结构化知识点（带 kp_id）
  scripts/
    check_kp.py           # 知识点校验 + 覆盖矩阵
frontend/
  src/
    session.js            # 登录用户、个人密钥、当前任务
    api.js                # 接口封装（Token + X-LLM-Key + SSE）
    App.vue               # 布局、角色页签、状态横幅
    components/
      AssistantPanel.vue # 学习助手：对话 / 代码诊断两种模式
      ChatPanel.vue       # 对话
      CodeAnalyze.vue     # 代码剖析（含任务模式、诊断标签）
      HomeworkPanel.vue   # 作业中心（任务列表 + 我的提交）
      ProfilePanel.vue    # 我的（个人资料 / 安全设置）
      KnowledgeStatus.vue # 知识库浏览/建库
      TeacherPanel.vue    # 班级 / 任务 / 学情看板
      StatusBanner.vue    # 顶部状态横幅
      SettingsModal.vue   # 模型密钥设置
```

---

## 6. 数据与密钥

| 内容 | 位置 | 是否提交 Git |
|---|---|---|
| 业务数据 | `backend/data/app.db` | 否 |
| 向量库 | `backend/data/vector_db/` | 否（clone 后重建） |
| JWT 密钥 | 环境变量 `SECRET_KEY` 或 `backend/data/.secret_key` | 否 |
| 模型密钥 | 用户浏览器本地 | 否 |
| 知识点内容 | `backend/data/knowledge/kp/*.md` | 是 |

---

## 7. 常见问题

| 现象 | 原因 / 解决 |
|---|---|
| 顶部红色横幅"还没有可用的模型密钥" | 没填个人 key 且服务端没配公共 key，点「模型设置」填写 |
| 建库报 `torch_python.dll` 加载失败 | Windows 应用控制策略（Smart App Control）拦截了 torch；检索会自动降级为关键词匹配，功能仍可用。彻底解决见 `docs/本次改动.md` |
| 建库报 `np.float_ was removed` | numpy 2.x 与 chromadb 0.4.x 不兼容，`app/core/rag.py` 已加兼容垫片 |
| 打开 8000 端口白屏 | 未 `npm run build` 或 `dist` 过期 |
| 登录后提示"用户不存在" | 切换过 SECRET_KEY，旧 token 失效，重新登录 |
| 建库后知识点仍是 0 | kp 内容还没写完：`py scripts\check_kp.py` 可以看到进度 |

---

## 8. 课程核心设计

1. **不泄题三层防线**：Prompt 硬约束 → 三阶提示法 → 知识库内容自净（题解只写思路）。
2. **结构化诊断**：模型在回复末尾输出 `<<<DIAG {...} DIAG>>>`，后端剥离后解析成 `error_types / kp_ids / severity / hint_level_reached`，看板才能统计"错在哪、涉及哪个知识点、提示给到第几阶"。
3. **知识点库**：`ds-章节-序号`，front matter 记录前置知识与难度，检索结果带 `kp_id`，是掌握度统计的基础。
4. **教学闭环**：教师发任务 → 学生提交 → AI 诊断 → 教师看板，与「不泄题」的引导目标一致。

---

## 9. 已知限制与后续

- 知识点目前只写了 2 个（`ds-01-01`、`ds-01-02`），计划 20 个，用 `scripts/check_kp.py` 跟踪进度。
- 向量检索在本机被系统策略拦截，当前走关键词降级；换 ONNX（fastembed）可彻底摆脱 torch。
- 没有在线判题（编译运行/用例评测），学生提交的是"代码 + AI 诊断"，不是自动判分。
- 掌握度（`kp_mastery`）尚未落地，看板目前按任务与错因统计。
- 单机 SQLite，适合一个班几十人；并发更大时换 Postgres。
