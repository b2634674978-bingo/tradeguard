# 2026-10-28 本次修改说明

## 1. 截图：完整显示 + 不再用 base64 存 evidence

- 新增 tradeguard/storage.py：用 Pillow 把上传截图压缩成 JPEG，长边限制 1600px，质量 85；
- 新增 report_images 表（BLOB）：截图从 reports.evidence 的 base64 大文本迁移到独立二进制表；
- 启动时自动迁移旧数据：evidence LIKE 'data:image%' 的记录会拆成多张图片、压缩后写入 report_images，并清空 evidence；
- 管理员审核页和举报详情页改用 st.image(..., use_container_width=True)，不再用 HTML 宽度限制，解决“只能看到一小段”；
- 旧的 base64 数据仍兼容：迁移失败时会跳过，不会阻塞启动。

## 2. 公开截图（同意公开）

- 上报表单新增「同意公开聊天截图作为证据」复选框；
- 写入 reports.publish_screenshots 与 report_images.is_public；
- 普通访客查询时只显示：status=approved 且 is_public=1 的截图；
- 管理员始终能看到全部截图（包括未公开的）；
- 未同意公开的举报，通过审核后访客只看到文字，不显示截图。

## 3. 待审核队列

- 普通用户提交 -> status=pending，不进入公开查询；
- 管理员「设置与合规」顶部显示待审核列表；
- 每条显示基本信息、经过、完整截图、是否同意公开；
- 「通过收录」-> approved；「驳回」-> rejected；
- 使用 db.list_pending_reports()，不再在页面里直接拼 SQL。

## 4. 中英文切换

- 新增 tradeguard/i18n.py，侧边栏「语言 / Language」切换；
- 导航、查询页、上报表单、情报库、看板、设置主要文案、管理员入口均支持中英文；
- 问题类型、风险等级、状态、来源也做了英文映射；
- 合规长文提供英文简版。

## 5. 安全：移除硬编码管理员密码（重要）

- 删除 auth.py 里的 TradeGuard2026!Admin123；
- 管理员密码只从 st.secrets 或环境变量读取：
  - 优先 st.secrets["ADMIN_PASSWORD"]
  - 其次 ADMIN_PASSWORD
  - 再其次 TRADEGUARD_ADMIN_PASSWORD
- **部署新代码前，必须在 Render 的 Environment 配置 ADMIN_PASSWORD**，否则管理员入口会显示“未配置”。
- 旧的 Render 环境变量如果没设置，请现在补上，并重启服务。

## 6. 数据持久化

- 新增「恢复 SQLite 备份」：管理员在设置页上传 .db，覆盖当前数据库（会校验 SQLite 文件头，大小上限 200 MB）；
- 新增 render.yaml 和 docs/DEPLOY_RENDER.md；
- Render 免费版没有持久磁盘：重启/重新部署仍会清空 /tmp；
- 付费方案：Starter + Disk 挂载 /var/data，设置 TRADEGUARD_DATA_DIR=/var/data；
- 免费长期方案：Supabase/Neon Postgres（需要下一步改数据层）；
- 现有备份恢复只能降低损失，不能替代持久化。

## 7. 其他修复

- 移除无效的 .streamlit/config.toml 配置 forceDarkMode（Streamlit 1.66 会警告）；
- 上传限制从 8 MB 提高到 25 MB，单张截图上限 10 MB；
- requirements.txt 增加 Pillow；
- 管理员登录入口默认展开；
- 修复审核按钮重复 key 的问题；
- 通过/驳回后自动刷新。

## 8. 部署步骤

1. 把本目录更新到 GitHub 仓库 b2634674978-bingo/tradeguard（main）；
2. Render 会自动重新部署；
3. 在 Render Environment 添加/确认 ADMIN_PASSWORD；
4. 打开站点，管理员登录，检查「设置与合规」是否有待审核队列；
5. 上传 3 张截图测试：普通用户提交 -> pending -> 管理员通过 -> 勾选公开的截图在查询页可见；
6. 下载 SQLite 备份，确认文件大小包含截图。

## 9. 已验证

- 本地 AppTest：查询、上报、管理员审核、通过、公开截图可见；
- 图片压缩：14 KB -> 13 KB，2200x1400 -> 1600x1018；
- 旧 base64 evidence 迁移：2 张成功迁移；
- 中英文切换：导航与首页英文渲染通过；
- 备份恢复：上传 .db 覆盖恢复通过；
- 编译通过。

## 10. 下一步建议

1. 先配好 ADMIN_PASSWORD 并重新部署，确认线上管理员可用；
2. 决定持久化方案：Render Disk（最快）或 Supabase Postgres（免费长期）；
3. 如果选 Supabase，提供 DATABASE_URL，我继续把 data 层改成 Postgres，并把截图放 Supabase Storage。
