# TradeGuard 项目交接说明

> 交接时间：2026-10-28
> 用途：把「外贸防骗情报库」项目从上一任助手移交给下一位接手者（AI 或人）。
> 读这一份就够，不用翻聊天记录。

---

## 0. 一句话说清这是什么

**TradeGuard** 是一个给外贸从业者用的防骗查询站：

- 业务员在报价、发货、收款前，输入对方的**手机号 / WhatsApp 号 / 公司名**，看有没有人踩过坑；
- 踩过坑的人可以**匿名上报**经过（文字 + 聊天截图）；
- 所有号码默认**脱敏显示**，避免误伤和人肉；
- 管理员在独立后台**审核、去重、处理申诉、备份**数据。

形态是 **Streamlit 单页应用**，部署在 Render.com，数据存 Neon PostgreSQL。

---

## 1. 当前进度快照（先看这个）

| 项目 | 状态 |
|---|---|
| 功能开发 | ✅ 完成（前台 + 后台已分离） |
| 本地运行 | ✅ 正常（`http://localhost:8501`） |
| 代码提交 | ✅ 本地 3 个提交完成 |
| **推送到 GitHub** | ❌ **卡在这里，这是唯一的阻塞点** |
| Render 部署 | ⬜ 未做（等推送完） |
| 线上验收 | ⬜ 未做 |

### 阻塞原因

本地 Git 仓库比远端**领先 3 个提交**，推不上去，原因有两个：

1. 生成的 `一键推送.bat` 被 **Windows 安全策略拦截**（已删除该文件）；
2. `git push` 需要 **GitHub 账号交互登录**，助手侧运行环境弹不出登录窗口，也拿不到凭据。

### 接手后第一件事

让项目所有者**在他自己的电脑上**执行一次推送（只需成功一次，凭据会存进 Windows 凭据管理器，之后助手就能直接推了）：

```bat
cd /d "C:\Users\26346\Documents\deepseek-harness\default-workspace\tradeguard-cloud"
git push origin main
```

成功标志：输出里出现 `main -> main`。

推送成功后，本交接文档的第 3 节「部署」可以直接往下走。

---

## 2. 项目基本信息

| 项 | 值 |
|---|---|
| 本地路径 | `C:\Users\26346\Documents\deepseek-harness\default-workspace\tradeguard-cloud` |
| GitHub 仓库 | https://github.com/b2634674978-bingo/tradeguard （**公开仓库**） |
| 分支 | `main` |
| 代码量 | `tradeguard/` 约 4770 行 Python |
| 技术栈 | Streamlit 1.57+ / pandas / Pillow / psycopg3 |
| 数据库 | SQLite（本地）↔ PostgreSQL（云端，双引擎兼容） |

### 未推送的 3 个提交

```
2dc46e5  refactor: 前后台分离，公开站只留普通用户需要的内容
63e58b9  fix: 管理员登录入口按「是否配密码」判定，而非按运行环境
bd36a67  feat: Postgres 持久化（双引擎兼容层）+ 真库验证
```

远端当前停在 `4b86bbe Add files via upload`（早期版本，未包含以上改动）。

---

## 3. 部署方案（推送之后的完整步骤）

### 3.1 平台

**Render.com 免费 Web Service**，已写好 `render.yaml`。免费版注意：

- 文件系统是**临时的**，重启/休眠/重部署会清空 SQLite 和截图；
- **所以必须配 `DATABASE_URL`**，否则数据留不住；
- 15 分钟无访问会休眠，首次打开要等 30～50 秒唤醒，属正常现象。

### 3.2 必须配置的环境变量

在 Render Dashboard → 服务 → Environment 里填：

| Key | Value | 说明 |
|---|---|---|
| `DATABASE_URL` | Neon 的连接串（pooled） | 云库地址，**从 `.streamlit/secrets.toml` 里取** |
| `ADMIN_PASSWORD` | 强随机密码 | 管理员登录密码，**由所有者保管，不要写进本文件** |
| `TRADEGUARD_PUBLIC_DEMO` | `1` | 公开站模式，访客只读 + 号码强制脱敏 |

> ⚠️ **安全约定**：本文件会随代码推到公开仓库，**严禁**在此写入任何真实密码、连接串、Token。
> 敏感信息只存在于两个地方：
> 1. 本地 `.streamlit/secrets.toml`（已在 `.gitignore`，不会上传）
> 2. Render 后台的环境变量（网页端，不落仓库）

### 3.3 Render 服务配置

- Build Command：`pip install -r requirements.txt`
- Start Command：`streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true`
- Instance Type：`Free`
- Root Directory：留空

### 3.4 验收清单

1. 访问 `https://<域名>.onrender.com` → 只看到 5 个公开页，**没有任何管理入口字样**；
2. 访问 `https://<域名>.onrender.com/?admin=1` → 出现管理员登录框；
3. 输入密码 → 出现 5 个 tab 的后台；
4. 提交一条测试举报 → 后台「待审核」里能看到 → 说明数据库通了；
5. 刷新页面 → 数据还在 → 说明不是临时 SQLite。

---

## 4. 代码结构

```
app.py                     入口：路由 + 侧边栏 + 页面分发
render.yaml                Render 部署描述
requirements.txt           运行依赖（含 psycopg[binary]）
.streamlit/secrets.toml    本地密钥（已 gitignore，勿提交）

tradeguard/
├── config.py              配置：DATABASE_URL / PUBLIC_DEMO / 路径 / 上限
├── auth.py                管理员门禁：登录、退出、公开访客判定
├── database.py            全部业务 SQL（方言模板，双引擎通用）
├── dbdriver.py            ★ SQLite↔PostgreSQL 方言兼容层（核心）
├── risk.py                风险打分（举报数 × 时间衰减 × 严重度）
├── normalize.py           号码/公司名归一化
├── chat_parser.py         聊天记录解析（多语言、多日期格式）
├── storage.py             截图压缩与存取（BLOB/BYTEA）
├── seed.py                演示数据
├── i18n.py                中英双语
└── ui/
    ├── nav.py             导航：公开 5 页 + 条件追加「管理后台」
    ├── theme.py           主题注入
    ├── components.py      复用组件（统计条、申诉块、卡片）
    └── pages/
        ├── check.py       查询验证（公开）
        ├── report.py      上报记录（公开）
        ├── intel.py       情报库（公开）
        ├── dashboard.py   数据看板（公开）
        ├── help.py        帮助与合规（公开，含隐藏的管理员入口链接）
        └── admin.py       管理后台（?admin=1 才可见）

scripts/
├── pg_selfcheck.py        连库自检 9 项
├── pg_fullcheck.py        24 个公开方法全跑一遍（自清理）
└── migrate_sqlite_to_pg.py SQLite→PG 迁移（默认 dry-run）

tests/                     49 项测试
docs/                      部署 / 合规 / 产品 / 变更记录
```

### 数据表（5 张）

`reports`（举报主表）、`report_phones`（号码关联，带归一化索引）、
`report_images`（截图 BLOB）、`appeals`（申诉）、`meta`（键值元信息）。

---

## 5. 前后台分离机制（本次改动的核心，别改坏）

这是上一轮最重要的需求：**「管理员和普通人应该分开，这个网页是给普通人用的」**。

实现方式：

1. **公开站只有 5 页**：查询验证 / 上报记录 / 情报库 / 数据看板 / 帮助与合规。
2. **后台不是导航里的一个 tab**，而是靠 URL 参数进入：
   访问 `?admin=1` 时，`auth.admin_entry_requested()` 返回 True，才会把「管理后台」追加进导航。
   普通用户永远看不到入口（帮助页底部有一个极小的「管理员入口」链接）。
3. **门禁只看有没有配密码**，不看运行环境：
   - 配了 `ADMIN_PASSWORD` → 任何环境都要求登录（本地也一样）；
   - 没配密码 + 公开部署 → 强制只读，谁都改不了数据；
   - 没配密码 + 本地 → 开放全部权限（省得本地调试每次输密码）。
4. **访客视角 `public_viewer()`** = 公开部署 且 未登录 → 号码强制脱敏 + 新举报进待审核队列。

⚠️ 三个容易改坏的点：

- **别在公开页里加任何管理按钮**。这是上一轮明确否掉的设计。
- **登录/退出必须用 `st.button(on_click=...)` 回调**，不能用脚本内 `st.rerun()`。
  否则会出现「管理区」和「只读提示」同屏的鬼畜渲染。
- **`public_viewer()` 不能改成「本地也脱敏」**，那会破坏本地工作流。

---

## 6. 双引擎兼容层（最脆弱的地方，改 SQL 前必读）

`dbdriver.py` 用**运行时 SQL 翻译**实现 SQLite ↔ PostgreSQL 双跑，没有引入 ORM（为了不改 1000 行业务 SQL）。

翻译规则：

| SQLite 写法 | PostgreSQL 写法 |
|---|---|
| `?` 占位符 | `%s` |
| `AUTOINCREMENT` | `GENERATED ... AS IDENTITY` + `RETURNING id` |
| `BLOB` | `BYTEA` |
| `INSERT OR IGNORE` | `ON CONFLICT DO NOTHING` |
| `INSERT OR REPLACE` | `ON CONFLICT DO UPDATE` |
| `PRAGMA table_info` | `information_schema.columns` |
| `cursor.lastrowid` | `RETURNING id` 取回（封装成 `insert_id()`） |

DSN 归一化也在这里：`postgres://` → `postgresql://`、剥离 pgbouncer 参数、6543 端口关闭预处理语句。

### 踩过的真坑（务必记住）

**PostgreSQL 不允许 `SELECT DISTINCT` 配 `ORDER BY` 表达式。**
`_reports_for_phone` 原来写 `SELECT DISTINCT r.* ... ORDER BY COALESCE(...)`，
在 SQLite 能跑，在 PG 直接报 `InvalidColumnReference`。
已改为子查询先排序再 DISTINCT。

> 教训：**任何新写的 SQL 都要在真 PG 上跑一遍**，SQLite 会掩盖这类语义差异。
> 用 `scripts/pg_fullcheck.py` 验证，它会自清理，不污染数据。

---

## 7. 本地怎么跑

```bat
cd /d "C:\Users\26346\Documents\deepseek-harness\default-workspace\tradeguard-cloud"
python -m streamlit run app.py
```

打开 http://localhost:8501

- 本地密码在 `.streamlit/secrets.toml` 的 `ADMIN_PASSWORD`；
- 本地后台地址：http://localhost:8501/?admin=1
- 本地默认走 SQLite（`data/tradeguard.db`），除非 secrets 里配了 `DATABASE_URL`。

### 跑测试

```bat
set PYTHONPATH=C:\Users\26346\Documents\deepseek-harness\default-workspace\tradeguard-cloud\.pylibs
python -m pytest -q
```

**当前环境限制**：本机 Python 没装 streamlit，且 pip 源不可达，所以
- 依赖界面层的测试（`test_app.py`、`test_admin_gate.py` 等）**暂时跑不了**；
- 纯逻辑部分已验证：`--noconftest` 模式 **26 项通过**（normalize / risk / chat_parser / dbdriver）；
- 曾在完整环境跑过 **49 项全通过**。

`tests/conftest.py` 有一个 autouse 夹具，强制把测试环境钉死为「本地 SQLite + 无管理员密码」，
**不要删**。删了之后测试会读真实 `secrets.toml`，连上线上 Neon 库写脏数据。

---

## 8. 已知问题 / 待办

### P0（阻塞上线）
- [ ] 推送到 GitHub（见第 1 节）
- [ ] Render 建服务 + 填 3 个环境变量
- [ ] 按 3.4 验收

### P1（上线后该做）
- [ ] 把 Render 上的 `ADMIN_PASSWORD` 换成所有者自己的强密码（当前是临时生成的）
- [ ] 观察 Neon 免费额度（1 GB 存储），截图存 BLOB 会占空间，考虑加清理策略
- [ ] Render 免费版休眠体验差，如需常驻考虑 Starter（$7/月）

### P2（产品层面）
- 当前号码脱敏是展示层做的，导出/备份里是明文，需要评估合规风险
- 批量导入只支持 CSV，没有做字段校验提示
- 没有速率限制，公开站可能被刷举报

---

## 9. 给接任者的三条提醒

1. **先确认推送成功再动别的**。代码没上去，后面全都白搭。
2. **别把敏感信息写进这个文件**。仓库是 public。
3. **改 SQL 一定要用真 PG 验证**（`scripts/pg_fullcheck.py`），SQLite 会骗你。

---

## 10. 相关文档

| 文件 | 内容 |
|---|---|
| `docs/DEPLOY_RENDER.md` | Render 部署细节、持久化方案对比 |
| `docs/DEPLOY_POSTGRES.md` | Neon 建库、连接串、迁移 |
| `docs/COMPLIANCE.md` | 合规边界：什么能记、什么不能记 |
| `docs/PRODUCT_PLAN.md` | 产品规划 |
| `docs/MARKET_RESEARCH.md` | 竞品与市场调研 |
| `docs/CHANGELOG-2026-10-28-postgres.md` | 本轮改动的详细技术说明（9 章） |
| `README.md` | 面向使用者的说明 |
