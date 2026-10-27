# WhatsApp 插件设计（Phase 2）

目标：在 **web.whatsapp.com** 的当前聊天界面，给用户一个 TradeGuard 侧边栏：一键查询对方号码、查看风险档案、把当前聊天半自动整理成上报草稿。

原则：**只读、可见、用户确认、不自动发消息、不后台抓取**。

## 1. 用户体验

1. 用户打开 web.whatsapp.com，点开与客户的聊天；
2. 右侧出现 TradeGuard 面板，自动读取当前聊天标题（号码/名称）；
3. 点「查一查」→ 调用本地 TradeGuard 服务；
4. 面板显示：风险等级、举报次数、类型、最近记录、证据摘要；
5. 点「上报」→ 弹出表单，预填号码/名称/最近消息中的风险信号；
6. 用户勾选「我确认这段聊天可作为证据」→ 提交；
7. 全程不自动发送任何 WhatsApp 消息。

## 2. 技术架构

    web.whatsapp.com
      └─ Content Script（读取聊天标题与可见消息，渲染侧边栏）
            │  chrome.runtime.sendMessage
      └─ Service Worker（权限、消息路由、去重）
            │  fetch http://127.0.0.1:8765
      └─ 本地 TradeGuard API（FastAPI，读写同一个 SQLite）
            └─ tradeguard.db

为什么需要本地 API：

- Streamlit 不适合作为插件后端（无稳定 JSON API、会话模型重）；
- 用 FastAPI 暴露 3 个接口即可：查询、上报、健康检查；
- 仍保持本地优先，不经过云端。

接口草案：

- GET /api/lookup?q=+15550104477
- POST /api/reports（JSON，含号码、类型、经过、证据摘要、聊天 SHA-256）
- GET /api/health

## 3. Manifest V3 权限（最小化）

    {
      "manifest_version": 3,
      "name": "TradeGuard for WhatsApp",
      "version": "0.1.0",
      "permissions": ["storage", "activeTab"],
      "host_permissions": ["https://web.whatsapp.com/*"],
      "content_scripts": [{
        "matches": ["https://web.whatsapp.com/*"],
        "js": ["content.js"],
        "css": ["panel.css"]
      }],
      "background": { "service_worker": "background.js" }
    }

注意：

- 不申请 **tabs**、**webRequest**、**cookies** 等宽权限；
- 不注入到其他站点；
- 不读取通讯录、群成员列表；
- 不上传数据到第三方服务器。

## 4. 如何读取当前聊天

WhatsApp Web 的 DOM 经常变化，因此：

- 优先从页面标题、聊天头部、URL 参数中提取号码；
- 只解析**当前可见**的消息气泡，不滚动加载历史；
- 用多个选择器兜底，失败时提示用户手动复制号码；
- 把 DOM 解析封装为独立模块，方便随 WhatsApp 更新维护。

已知格式差异（解析器必须兼容）：

- iOS：方括号包裹，如 [24/10/24, 9:18:35 AM] 张三: 内容，可能含窄不换行空格 U+202F 与 LRM U+200E；
- Android：如 4/11/25, 9:17:58 PM ~ 张三: 内容，时间与发送者之间可能是「~」而不是「-」；
- 旧版 / 其他语言：如 15.04.2016, 15:04 - 张三: 内容；
- 日期顺序随系统语言变化（DMY / MDY），媒体占位符与系统消息需过滤，多行消息要合并到上一条。

不要做的事：

- 不调用 WhatsApp 内部 WebSocket / 协议；
- 不注入脚本修改发送逻辑；
- 不自动滚动、不批量读取会话列表；
- 不后台常驻抓取。

## 5. 平台条款与账号风险

- WhatsApp 服务条款禁止未经授权的自动化、抓取、批量操作；浏览器插件读取自己已登录页面的 DOM，处于灰色地带；
- 为降低风险：只读、用户主动点击、单条查询、不自动发送、不批量；
- 插件商店审核需要明确隐私说明与权限理由；
- 保留「手动导出 .txt」作为兜底路径，插件不可用时产品仍能工作；
- 如果要做稳定、合规的规模化接入，优先走 **WhatsApp Business Cloud API**（仅企业号，官方支持）。

## 6. 开发拆分与工期（1 人）

| 模块 | 内容 | 工期 |
|---|---|---|
| 本地 API | FastAPI + 复用 database.py | 2 天 |
| 插件骨架 | MV3、侧边栏、权限 | 2 天 |
| 聊天读取 | 号码/标题/可见消息解析，多选择器兜底 | 3 天 |
| 查询 UI | 风险卡片、证据展开 | 2 天 |
| 上报联动 | 预填表单、确认、提交 | 2 天 |
| 联调与合规 | 权限说明、隐私页、测试 | 3 天 |
| 合计 | | 约 2 周 |

## 7. 验收标准

- 在 web.whatsapp.com 打开任意聊天，3 秒内显示号码；
- 查询命中时展示风险等级与至少 1 条证据摘要；
- 上报必须经过两次用户确认（勾选 + 提交）；
- 不产生任何自动发送；
- 断网/本地服务未启动时有清晰提示，不白屏；
- 卸载插件后不残留数据。
