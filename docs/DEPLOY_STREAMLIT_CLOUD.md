# 部署到 Streamlit Community Cloud

> 目标：把 TradeGuard 部署成一个可公开访问的网页，形如 **https://你的应用名.streamlit.app**。
>
> 说明：GitHub 与 Streamlit Cloud 都要求你本人登录授权，我无法代替你完成 OAuth，也无法直接生成最终链接。下面每一步都可以照着点；部署完成后把链接发我，我可以继续帮你验收。

## 0. 先看法律边界（重要）

TradeGuard 是「对特定个人/公司作出负面风险提示」的产品。把真实手机号、聊天记录和指控放到公开网页，会同时触及：

- 《个人信息保护法》的合法性基础、最小必要、告知与删除权；
- 《民法典》名誉权 / 商誉，以及《反不正当竞争法》商业诋毁；
- 海外号码还涉及 GDPR 删除权、当地诽谤法。

广州互联网法院「反恶」案已经确认：**打星、会员可见、内容由用户上传，都不能自动免责**。因此：

- **公开演示版请只放虚构数据**（项目自带 9 条，号码来自各国影视保留号段）；
- 真实举报请用**本地完整版**或 **Streamlit Cloud 私有应用 + 邀请成员**，并配套审核、申诉、脱敏；
- 不要把一个未经审核的真实“骗子名单”直接公开到互联网。

本次部署默认就是「公开只读演示版」：访客能查询演示数据，但不能上报、不能清空、不能备份；你登录管理员后才可管理。

## 1. 代码检查结果

| 检查项 | 状态 | 说明 |
|---|---|---|
| 入口文件在仓库根目录 | 需按本文上传 | 仓库根目录应有 app.py、requirements.txt，而不是再多一层 tradeguard 文件夹 |
| 依赖 | 已适配 | requirements.txt 使用 Streamlit 1.57+、pandas 2.2–3.x |
| Python 版本 | 建议 3.12 | 在 Streamlit Cloud 高级设置里选 3.12 |
| SQLite 可写 | 已适配 | 云端自动把数据放到 /tmp/tradeguard，避免仓库只读 |
| 首次启动演示数据 | 已适配 | 空库自动写入 9 条虚构演示记录 |
| 公开只读 | 已适配 | 未配置管理员密码时，上报/设置管理功能全部锁定 |
| 管理员密码 | 需配置 | 在 Streamlit Secrets 添加 ADMIN_PASSWORD |
| 数据持久化 | 有限制 | Streamlit Cloud 免费版文件系统是临时的，重启/重新部署会重置 |
| 自定义域名 | 平台分配 | 免费版使用 你的应用名.streamlit.app |

## 2. 你需要准备什么

1. **GitHub 账号**（免费）：https://github.com
2. **Streamlit Community Cloud 账号**：https://share.streamlit.io ，用 GitHub 登录即可
3. 一个仓库：public 或 private 都行；**private 仓库不会让代码公开**，但应用仍可设为公开
4. 一个管理员密码（建议 16 位以上，字母数字符号混合）
5. 约 10 分钟

## 3. 把代码上传到 GitHub

### 方式 A：网页上传（最简单）

1. 登录 GitHub，点右上角 **+** → **New repository**；
2. Repository name 填 **tradeguard**，选择 Public 或 Private，点 **Create repository**；
3. 打开本地文件夹 **tradeguard/**（就是包含 app.py 的那一层）；
4. 在 GitHub 仓库页点 **Add file** → **Upload files**；
5. 把 **app.py、requirements.txt、.streamlit、tradeguard、demo、docs、tests、README.md、start.bat、start.sh、.gitignore** 一起拖进去；
6. 确认页面上能看到 **app.py 在根目录**，不是 tradeguard/app.py；
7. 填提交信息，点 **Commit changes**。

不要上传：

- .pylibs / .venv / __pycache__ / .piptmp 等本地环境；
- data 目录里的 .db 数据库；
- .streamlit/secrets.toml（里面有密码）。

### 方式 B：命令行（已装 Git）

在 **tradeguard/** 目录打开终端：

    git init
    git add .
    git commit -m "TradeGuard initial"
    git branch -M main
    git remote add origin https://github.com/你的用户名/tradeguard.git
    git push -u origin main

推送时按提示登录 GitHub。仓库里不要出现 .pylibs 和 data/*.db；.gitignore 已经帮你排除。

## 4. 在 Streamlit Cloud 创建应用

1. 打开 https://share.streamlit.io ，点 **Sign in with GitHub** 并授权；
2. 点 **Create app**（或 **New app**）；
3. 选择 **Deploy a public app from GitHub**；
4. 填写：
   - Repository：你的用户名/tradeguard
   - Branch：main
   - Main file path：**app.py**
   - App URL：选一个名字，例如 **tradeguard-demo**，最终地址就是 https://tradeguard-demo.streamlit.app
5. 点 **Advanced settings**：
   - Python version：选 **3.12**（没有就选 3.11）；
   - Secrets：粘贴下面内容，把密码换成你自己的：

         ADMIN_PASSWORD = "请换成至少16位的强密码"

6. 点 **Deploy**，等待 2–5 分钟构建完成。

构建日志里如果出现 **ModuleNotFoundError: tradeguard**，说明仓库根目录少了 tradeguard 包，或者 Main file path 填错了。

## 5. 部署后验收

打开你的 https://xxx.streamlit.app ，按顺序检查：

1. 首页能打开，能看到「这个名字，靠谱吗？」；
2. 点示例 **+1 555 010 4477**，出现 NovaPeak 的高风险档案；
3. 点「上报记录」：未登录时应看到「公开只读演示版」，没有上报表单；
4. 左侧点「管理员」→ 输入你在 Secrets 里设置的密码；
5. 登录后再点「上报记录」，应出现上传/粘贴、解析、提交表单；
6. 提交一条演示记录，回到查询页应能查到；
7. 「设置与合规」里能导出 CSV、下载 SQLite 备份、清理演示数据。

如果第 4 步没有「管理员登录」，检查 Secrets 的键名是否严格为 **ADMIN_PASSWORD**，保存后点 **Reboot app**。

## 6. 日常管理：怎么新增举报、怎么维护

### 新增一条举报

1. 左侧登录管理员；
2. 进入「上报记录」；
3. 上传 WhatsApp 导出的 .txt，或粘贴关键聊天；
4. 点「解析聊天记录」，核对号码、类型、金额、经过；
5. 勾选真实性确认，提交；
6. 回「查询验证」输入号码即可看到新档案。

### 管理数据

在「设置与合规」里可以：

- 下载 SQLite 备份 / 导出全部 CSV；
- 批量导入 CSV（模板可下载）；
- 删除演示数据、清空记录；
- 查看申诉队列；
- 调整隐私模式（列表页是否隐藏完整号码）。

### 修改管理员密码

Streamlit Cloud 应用页 → 右下角 **Manage app** → **Settings** → **Secrets** → 修改 ADMIN_PASSWORD → 保存 → **Reboot app**。

### 删除应用

Manage app → Settings → 底部 **Delete app**。删除后链接失效。

## 7. 关键限制：云端数据不持久

Streamlit Community Cloud 免费版的容器文件系统是**临时的**：

- 应用休眠、重启、重新部署后，/tmp/tradeguard 里的 SQLite 可能被清空；
- 你新增的举报可能丢失，只剩仓库自带的 9 条演示数据；
- 多位访客同时写入时，SQLite 也可能遇到锁竞争。

所以：

- **公开演示版**：只放虚构数据，重启丢失没关系；
- **真实数据**：请用本地完整版，或把数据层换成 Supabase / Neon / PostgreSQL 等外部数据库；
- 每次维护前先在「设置」下载备份。

如果要把数据持久化到 Supabase/Postgres，我可以下一步帮你改数据层；这需要额外的数据库账号和连接串。

## 8. 公开还是私有？

| 模式 | 适合 | 风险 |
|---|---|---|
| 公开应用 + 虚构数据 | 产品演示、收集反馈 | 低 |
| 公开应用 + 真实举报 | 不推荐 | 高：个人信息 + 名誉权 + 无法审核 |
| 私有应用 + 邀请成员 | 小团队试点、货代/验厂合作 | 中：仍需授权、审核、申诉 |

Streamlit Cloud 私有应用：Manage app → Settings → Sharing，填写允许访问的邮箱。这样链接只有被邀请的人能打开，更适合真实数据试点。

## 9. 常见问题

**应用打开是白屏 / 一直转圈**
先看 Manage app 的 logs；免费版冷启动需要几十秒。

**提示仓库只读 / 无法创建数据库**
确认 Main file path 是 app.py，且没有把 TRADEGUARD_DATA_DIR 指到只读路径；代码默认在云端使用 /tmp。

**改了 Secrets 没生效**
保存 Secrets 后必须 Reboot app；密码不要带多余空格。

**想换应用名 / 链接**
Streamlit Cloud 的 App URL 可在应用设置里调整；改完后旧链接可能失效。

**想用自定义域名**
免费版不提供；需要自己的域名和反向代理/其他托管方式。

## 10. 下一步

部署完成后，把公开链接发我，我可以帮你：

1. 检查线上首页、查询、管理员登录是否正常；
2. 根据你的真实使用场景，判断要不要改成私有应用；
3. 把 SQLite 换成 Supabase/Postgres，解决数据持久化；
4. 加审核队列、举报人可信度、限流与申诉处理。
