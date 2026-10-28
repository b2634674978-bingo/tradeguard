# Postgres 持久化部署指南（Supabase / Neon → Render）

本文说明如何把 TradeGuard 从「SQLite 临时存储」切换到 **PostgreSQL 持久化**，实现 Render 重启、休眠、重新部署后数据不丢。

当前代码已支持双引擎：**不配 `DATABASE_URL` 就用 SQLite，配上就自动走 Postgres**，业务代码和页面无需任何改动。

---

## 0. 一句话原理

```
app.py → Database → dbdriver（方言层） ┬→ SQLite   （本地 / 未配置时）
                                      └→ PostgreSQL（配置 DATABASE_URL 后）
```

- `?` 占位符、`INSERT OR IGNORE/REPLACE`、`AUTOINCREMENT`、`BLOB` 等 SQLite 写法在方言层自动翻译；
- 写入后需要自增主键时，Postgres 走 `RETURNING id`；
- 截图仍以二进制存库（SQLite 用 `BLOB`，Postgres 用 `BYTEA`），单张已压缩到 1600px / JPEG 85。

---

## 1. 建库（二选一）

> **本项目已建好 Neon 实例**，日常无需重复本节，仅作切换/重建时的参考。
> 现有配置：项目 `tradeguard` · 区域 AWS us-west-2 (Oregon) · 库 `neondb` · pooled 端点
> `ep-broad-mud-arh7r4hs-pooler.c-4.us-west-2.aws.neon.tech`，连接串存在 Render 的 `DATABASE_URL`。

### 免费额度对照（2026-10 官方定价核实）

| | Neon Free | Supabase Free |
|---|---|---|
| 存储 | 1 GB / 项目 | 500 MB / 项目 |
| 闲置 | 5 分钟挂起，连接即唤醒 | **闲置 1 周暂停，需手动恢复** |
| 项目数 | 100 | 2 |
| 信用卡 | 不需要 | 不需要 |

结论：截图以 `BYTEA` 入库，500 MB 会先撞墙；且 Supabase 的「闲置一周暂停」对低频访问的防骗库是实质风险。**本项目选 Neon。**

### 方案 A：Neon（当前采用）

1. https://console.neon.tech → New project，区域选 **AWS US West 2 (Oregon)**（与 Render 默认区域同区，避免每次查询跨区往返）；
2. 项目页右上 **Connect** → 勾选 **Connection pooling** → **Show password**；
3. 复制连接串，形如：

```
postgresql://<user>:<password>@ep-xxx-pooler.c-4.us-west-2.aws.neon.tech/neondb?sslmode=require
```

4. Neon 的 pooled 端点基于 PgBouncer，但**支持预处理语句**，无需关闭；直连（去掉 `-pooler`）也可用，适合跑迁移脚本。

### 方案 B：Supabase（免费 500 MB）

1. 打开 https://supabase.com → New project，选区域（建议 Singapore / 靠近用户）；
2. 设置数据库密码（**记下来**，只显示一次）；
3. 进入 Project Settings → Database → Connection string → 选 **URI**；
4. 复制连接串，形如：

```
postgresql://postgres.abcdefgh:你的密码@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
```

**关键选择：端口**

| 端口 | 模式 | 适用 |
|---|---|---|
| 6543 | Transaction pooler | 无状态容器**首选**，连接数省，但**不支持预处理语句** |
| 5432 | Direct / Session | 单机脚本、迁移脚本用 |

代码已自动识别：URL 里带 `pgbouncer=true` 或端口为 `6543` 时会关闭预处理语句，不会报 `prepared statement already exists`。

> 密码含 `@ # / ? &` 等字符时，必须做 URL 编码（如 `@` → `%40`），否则连接串会被解析错。

---

## 2. 配置 Render

Render Dashboard → 你的 Web Service → Environment → Add Environment Variable：

| Key | Value | 必填 |
|---|---|---|
| `DATABASE_URL` | 上一步复制的连接串 | 是 |
| `ADMIN_PASSWORD` | 16 位以上强密码 | 是 |
| `TRADEGUARD_PUBLIC_DEMO` | `1` | 建议 |

保存后 Render 会自动重新部署。也可以用 `render.yaml`（仓库已带 `DATABASE_URL` 的 `sync: false` 占位）。

> **不要**同时在 `TRADEGUARD_DATA_DIR` 里配磁盘路径——配了 `DATABASE_URL` 后 SQLite 不再被使用。

---

## 3. 上线前自检（30 秒）

本地执行，验证建表、写入、自增主键、截图、查询、聚合、导出全链路：

```bash
pip install -r requirements.txt
set DATABASE_URL=postgresql://...        # Windows
export DATABASE_URL=postgresql://...     # macOS / Linux
python scripts/pg_selfcheck.py
```

期望最后一行：

```
PASS: 9 项全部通过，Postgres 持久化链路可用。
```

脚本使用固定测试号码 `+19990000000`，结束时自动删除自检记录，不污染正式数据。

---

## 4. 迁移现有 SQLite 数据

如果你已经在本地或之前的实例里积累了记录：

```bash
# 1) 先看会搬多少（默认 dry-run，不写库）
set TRADEGUARD_SRC_DB=C:\path\to\tradeguard.db
python scripts/migrate_sqlite_to_pg.py

# 2) 确认后真正写入
python scripts/migrate_sqlite_to_pg.py --apply
```

注意：
- 记录 id 会重新分配，脚本会打印 `旧 id -> 新 id`；
- 截图二进制原样搬运，不做二次压缩；
- **只跑一次**，重复执行会产生重复数据；
- 迁移前先备份源库。

---

## 5. 部署后验收清单

1. 首页侧边栏显示「存储：PostgreSQL · 重启不丢」；
2. 查询 `+1 555 010 4477` 能看到演示档案（首次部署会自动种入 9 条虚构数据）；
3. 提交一条带截图的举报 → 管理员「设置与合规」看到待审核与完整截图 → 通过；
4. **重启验证**：Render → Manual Deploy → Restart，刷新页面，刚才的记录仍在（这是本次改造的核心验收点）；
5. 「设置与合规」不再显示「下载 SQLite 备份」，改为 PostgreSQL 备份说明，CSV 导出仍可用。

---

## 6. 备份策略

Postgres 模式下备份方式变了：

| 方式 | 做法 | 频率 |
|---|---|---|
| 平台自动备份 | Supabase：Database → Backups（免费版 7 天）；Neon：History / PITR | 平台默认 |
| 逻辑备份 | `pg_dump "$DATABASE_URL" -Fc -f tradeguard.dump` | 每周 |
| 人工存档 | 设置页「导出全部记录 CSV」 | 按需 |

恢复：`pg_restore -d "$DATABASE_URL" tradeguard.dump`（会覆盖同名对象，操作前先导出一次）。

---

## 7. 容量与成本估算

- 单张截图压缩后约 **40–200 KB**；
- 1000 条举报 × 3 张截图 ≈ **150–500 MB**，接近 Supabase 免费额度上限；
- 超过时按顺序处理：① 清空驳回记录；② 降低 `storage.compress_image` 的 `quality`；③ 把截图迁到对象存储（Supabase Storage / R2），库里只留路径。

连接数：代码默认池上限 4（`TRADEGUARD_PG_POOL` 可调）。Render 免费实例 1 个进程，4 个连接足够；Supabase 免费版连接数有限，不要盲目调大。

---

## 8. 常见问题

**启动报 `ModuleNotFoundError: psycopg`**
`requirements.txt` 已含 `psycopg[binary]`，说明构建没重装依赖 → Render 手动 Clear build cache 后重新部署。

**报 `prepared statement "__async_1" already exists`**
连接串是 Supabase 6543 端口但代码没识别到。检查 URL 是否被改写过、端口是否真的是 6543；也可手动在 URL 加 `?pgbouncer=true`。

**报 `password authentication failed`**
密码里的特殊字符没做 URL 编码，或复制时带了首尾空格。

**报 `relation "reports" does not exist`**
`Database.init()` 没执行成功（通常连不上库）。先跑 `scripts/pg_selfcheck.py` 定位。

**中文乱码 / 排序异常**
数据库编码必须是 UTF8（Supabase / Neon 默认即是）。

**本地开发不想连云库**
什么都不配即可，自动回落 SQLite（`data/tradeguard.db`），单元测试也只跑 SQLite。
