# 更新说明 —— 用户系统与代码剖析持久化

> 本文档记录在原有项目基础上新增的功能与改动。
> 更新日期：2026-09-19

---

## 一、本次新增功能

### 1. 用户注册与登录

- 新增页面：`frontend/src/Login.vue`
- 新增接口：
  - `POST /api/auth/register` —— 注册
  - `POST /api/auth/login` —— 登录
  - `GET /api/auth/me` —— 获取当前用户信息
- 使用 JWT Token 鉴权，Token 存在浏览器 `localStorage` 里
- 密码用 Python 内置 `hashlib.pbkdf2_hmac` 加密（不依赖 passlib，避免与 bcrypt 的版本冲突）

### 2. 数据按用户隔离

- 每个会话绑定 `user_id`
- 每个代码剖析记录绑定 `user_id`
- 用户只能看到、删除自己的数据，无法访问别人的

### 3. 代码剖析历史存后端

- 新增数据库表 `code_analyses`
- 新增接口：
  - `GET /api/code/analyses` —— 列出当前用户的剖析记录
  - `GET /api/code/analyses/{id}` —— 获取剖析详情
  - `DELETE /api/code/analyses/{id}` —— 删除剖析记录
- 前端不再用 `localStorage`，改为读后端，换设备登录也能看到历史

### 4. 知识库页面改造

- 分类卡片式布局（讲义 / 题解 / Bug库）
- 支持关键词搜索
- 支持点击卡片展开全文
- 顶部有搜索框，可直接定位想看的资料

### 5. 代码剖析页快捷指令

- 新增 4 个快捷按钮：语法检查 / 代码诊断 / 代码优化 / 代码注释
- 点击按钮选中对应模式，再提交代码
- 隐藏指令拼接到用户问题中一并发给后端

---

## 二、改动的文件

### 新增文件

| 文件                             | 作用                      |
| ------------------------------ | ----------------------- |
| `backend/app/core/database.py` | 用户数据库连接与建表              |
| `backend/app/core/auth.py`     | 密码加密 + JWT 生成/验证 + 鉴权依赖 |
| `backend/app/api/auth.py`      | 注册/登录/获取当前用户接口          |
| `frontend/src/Login.vue`       | 登录/注册页面                 |
| `TELLME_更新说明.md`               | 本文档                     |

### 修改文件

| 文件                                            | 改动                              |
| --------------------------------------------- | ------------------------------- |
| `backend/app/main.py`                         | 初始化数据库 + 注册 auth 路由             |
| `backend/app/core/store.py`                   | 所有函数加 `user_id` 参数；新增代码剖析相关函数   |
| `backend/app/api/conversation.py`             | 加登录保护 + 按用户隔离                   |
| `backend/app/api/chat.py`                     | 加登录保护 + 按用户隔离                   |
| `backend/app/api/code.py`                     | 加登录保护 + 剖析结果落库 + 新增 3 个接口       |
| `backend/app/api/knowledge.py`                | 新增 `/list` 和 `/search` 接口       |
| `frontend/src/api.js`                         | Token 自动注入 + 401 处理 + 新增认证/历史接口 |
| `frontend/src/App.vue`                        | 未登录显示登录页 + 顶部显示用户名和退出按钮         |
| `frontend/src/components/CodeAnalyze.vue`     | 历史记录从 localStorage 改成读后端        |
| `frontend/src/components/KnowledgeStatus.vue` | 分类卡片 + 搜索 + 展开                  |

---

## 三、依赖变化

新增 Python 依赖：

```bash
py -m pip install "python-jose[cryptography]"
```

> 注意：如果之前装过 `passlib`，本次已不再使用，可以保留不动。

---

## 四、数据库说明

两个 SQLite 文件，都在 `backend/data/` 下：

| 文件        | 存什么表                                                       |
| --------- | ---------------------------------------------------------- |
| `app.db`  | `users`（用户）                                                |
| `chat.db` | `conversations`（会话）+ `messages`（消息）+ `code_analyses`（代码剖析） |

**注意事项**：

- 不要随便删除这两个文件，否则用户数据和历史记录会丢失
- 首次启动会自动建表，无需手动初始化
- 从旧版本升级时，如果 `conversations` 表缺 `user_id` 字段，会自动 `ALTER TABLE` 补上

---

## 五、如何运行

### 后端

```bash
cd backend
py -m pip install -r requirements.txt
py -m pip install "python-jose[cryptography]"
py -m uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`，**先注册一个账号再使用**（未登录会停留在登录页）。

---

## 六、核心接口一览

| 方法     | 路径                                     | 说明          | 是否需要登录 |
| ------ | -------------------------------------- | ----------- | ------ |
| POST   | `/api/auth/register`                   | 注册          | 否      |
| POST   | `/api/auth/login`                      | 登录          | 否      |
| GET    | `/api/auth/me`                         | 当前用户信息      | 是      |
| POST   | `/api/chat`                            | 苏格拉底对话（SSE） | 是      |
| POST   | `/api/code/analyze`                    | 代码剖析（SSE）   | 是      |
| GET    | `/api/code/analyses`                   | 剖析记录列表      | 是      |
| GET    | `/api/code/analyses/{id}`              | 剖析详情        | 是      |
| DELETE | `/api/code/analyses/{id}`              | 删除剖析记录      | 是      |
| POST   | `/api/conversations`                   | 新建会话        | 是      |
| GET    | `/api/conversations`                   | 会话列表        | 是      |
| GET    | `/api/conversations/{id}/messages`     | 会话消息        | 是      |
| DELETE | `/api/conversations/{id}`              | 删除会话        | 是      |
| POST   | `/api/knowledge/ingest`                | 重建知识库       | 否      |
| GET    | `/api/knowledge/stats`                 | 知识库统计       | 否      |
| GET    | `/api/knowledge/list?category=lecture` | 列出某分类知识     | 否      |
| GET    | `/api/knowledge/search?q=关键词`          | 搜索知识库       | 否      |

> "是否需要登录"为"是"的接口，请求头必须带 `Authorization: Bearer <token>`。

---

## 七、已知限制 / 待改进

| 项     | 现状              | 后续计划                   |
| ----- | --------------- | ---------------------- |
| 数据库   | 用户和会话分两个 .db 文件 | 可合并为单库                 |
| 会话重命名 | 不支持             | 可加双击重命名                |
| 移动端适配 | 未做              | 可加响应式布局                |
| 深色模式  | 未做              | 可加主题切换                 |
| 部署上线  | 未做              | 计划 build 后用 FastAPI 托管 |
| 密码找回  | 未做              | 可加邮箱验证                 |
| 速率限制  | 未做              | 可加防刷接口限制               |
