# 在 Render.com 上部署 / 持久化 TradeGuard

当前公开站点使用 Render.com 免费 Web Service。本文说明如何更新、配置管理员密码，以及如何解决“重启后数据清空”。

## 1. 当前部署信息

- 仓库：https://github.com/b2634674978-bingo/tradeguard
- 分支：main
- 构建命令：pip install -r requirements.txt
- 启动命令：

      streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true

Render 会自动注入 $PORT；不要写死 8501。

## 2. 必须配置的环境变量

进入 Render Dashboard → 你的 Web Service → Environment：

| 变量 | 值 | 说明 |
|---|---|---|
| ADMIN_PASSWORD | 你自己的 16 位以上强密码 | 管理员登录；代码里不再硬编码密码 |
| TRADEGUARD_PUBLIC_DEMO | 1 | 公开访问模式；不设也会在 Render 自动识别 |
| TRADEGUARD_DATA_DIR | /var/data（仅挂载磁盘时） | SQLite 持久化目录 |

修改环境变量后点 **Save Changes**，Render 会自动重启服务。

> 重要：旧版本的硬编码密码已从代码中移除。部署新代码前先在 Render 配好 ADMIN_PASSWORD，否则管理员入口会提示“未配置”。

## 3. 免费版的数据问题

Render 免费 Web Service 的文件系统是**临时的**：

- 服务重启、重新部署、休眠唤醒后，/tmp 里的 SQLite 会丢失；
- 现在截图以压缩后的 BLOB 存在同一个 SQLite 文件里，所以截图也会一起丢；
- 免费版不能挂载 Persistent Disk。

临时缓解：

1. 管理员在「设置与合规」定期下载 SQLite 备份；
2. 需要恢复时，在设置页上传这个 .db 文件（新增的恢复功能）；
3. 不要把它当长期数据库。

## 4. 方案 A：Render Persistent Disk（推荐给付费用户）

升级到 **Starter** 实例，添加 Disk：

- Name: tradeguard-data
- Mount Path: /var/data
- Size: 1 GB 起

然后在 Environment 设置：

    TRADEGUARD_DATA_DIR = /var/data

保存并重启。之后 SQLite 和截图都在 /var/data/tradeguard.db，重启/重新部署不会丢。

这是改动最小、最稳的方案；成本约每月 $7 起（以 Render 官网为准）。

## 5. 方案 B：外部数据库（推荐给长期免费方案）

把 SQLite 换成 Supabase / Neon PostgreSQL：

- 优点：免费额度通常够用，数据独立于 Render 实例；
- 缺点：需要改数据层（当前代码是 sqlite3 原生 SQL），并把截图放到对象存储或 bytea；
- 建议：先选 Supabase（免费 500 MB 数据库 + 1 GB 存储），我可以下一步改成 Postgres + Storage。

在没改完之前，不要直接把 Render 免费版当正式数据库。

## 6. 用 render.yaml 重建服务（可选）

仓库根目录提供了 render.yaml，可用于 Blueprint 新建服务。它默认 free plan、不挂磁盘；需要持久化时按方案 A 手动加 Disk 和 TRADEGUARD_DATA_DIR。

## 7. 部署后检查

1. 打开站点首页，查询 +1 555 010 4477 应能看到演示档案；
2. 左侧管理员登录，密码为 ADMIN_PASSWORD；
3. 「上报记录」上传 3 张截图，普通用户提交后进入待审核；
4. 「设置与合规」能看到待审核队列和完整截图；
5. 通过后，勾选“同意公开”的截图普通访客可见；
6. 下载 SQLite 备份，确认包含截图（文件会比较大）。

## 8. 常见问题

**管理员登录一直不出现**
检查 Render Environment 是否有 ADMIN_PASSWORD，保存后是否重启；变量名必须完全一致。

**上传 3 张截图报错**
截图单张上限 10 MB，应用会自动压缩；如果原图太大，先截图压缩。Streamlit 的 maxUploadSize 已调到 25 MB。

**重启后举报没了**
免费版正常现象。用备份恢复，或按方案 A/B 做持久化。

**数据库越来越大**
截图已压缩为 JPEG BLOB；仍建议定期清理驳回记录和旧备份。1 GB 磁盘能存数千条带图举报。
