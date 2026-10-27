# TradeGuard · 外贸防骗情报库

> 先查一查，再谈生意。

TradeGuard 是一个**本地优先**的外贸防骗原型：把被骗者上传的 WhatsApp 聊天记录，自动整理成「号码 + 问题类型 + 经过 + 证据摘要」，聚合成可查询的风险档案。下次有人来谈样品、谈大货，先输入号码或公司名查一查。

数据默认只保存在你自己的电脑上（完整版用 SQLite，演示版用浏览器本地存储），不联网、不上传云端。

> **想先看一眼？** 直接双击 [demo/index.html](demo/index.html)，零安装、零依赖，浏览器打开就能查询、上报、看板。完整版（SQLite + CSV 导入导出 + 申诉队列）见下方启动方式。

## 它解决什么问题

外贸和跨境采购里，骗子和小白嫖党的成本太低了：

- 换个 WhatsApp 号就能继续骗下一家；
- 骗样品、骗报价、骗设计稿，几乎没有后果；
- 受害者只能在微信群、朋友圈、Excel 里互相提醒，信息散、查不到、留不住。

TradeGuard 想做的是**交易前的风险提示层**：不替代验厂、不做公开曝光，而是在你投入样品和时间之前，给你一个可以核实的线索。

## 能做什么

- **聊天记录解析**：支持 WhatsApp Android / iOS 导出的 .txt，自动识别号码、参与者、时间范围、媒体数量和风险信号；
- **号码归一与匹配**：兼容 +86 / 0086 / 空格 / 括号等写法；支持完整号码、尾号 8 位、公司名、联系人查询；
- **风险评分**：按举报次数、问题类型、时效、证据、金额、可信度计算，并展示每条依据；
- **上报入库**：可只填号码/公司，也可上传聊天记录自动预填；只保存必要证据，不保存完整聊天；
- **情报库**：按类型、风险等级、关键词筛选，默认脱敏显示，一键导出 CSV；
- **数据看板**：趋势、类型分布、国家分布、已记录损失；
- **申诉入口**：每条记录可提交「误伤申诉」，进入本地复核队列；
- **备份与迁移**：下载 SQLite 备份、导出/导入 CSV、清空数据。

## 零安装演示版（1 分钟）

双击 **demo/index.html** 即可。所有解析、查询、评分都在浏览器里完成，数据保存在 localStorage；适合快速体验、给同事演示，不适合长期存证。

完整版则把数据写进本机 SQLite，支持备份、CSV 导入导出、申诉队列和更多筛选，适合真正开始积累情报时使用。

## 部署到 Streamlit Community Cloud

项目已适配 Streamlit Cloud：云端自动使用 /tmp 临时 SQLite、默认公开只读、管理员密码保护写操作。完整步骤见 **[部署指南](docs/DEPLOY_STREAMLIT_CLOUD.md)**。

> 注意：免费版文件系统是临时的，重启/重新部署会重置数据；公开演示请只放虚构数据。真实举报建议用私有应用或本地完整版。

## 完整版启动（3 分钟）

### Windows

1. 安装 Python 3.11 或 3.12（安装时勾选 **Add Python to PATH**）；
2. 双击 **tradeguard/start.bat**；
3. 首次启动会自动创建虚拟环境并安装依赖，完成后浏览器打开 http://127.0.0.1:8501 。

### macOS / Linux

    cd tradeguard
    bash start.sh

手动方式：

    cd tradeguard
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt   # Windows
    # 或 .venv/bin/python -m pip install -r requirements.txt   # macOS/Linux
    .venv\Scripts\python -m streamlit run app.py

首次启动会写入 9 条**虚构的演示数据**（号码来自各国影视保留号段），方便直接体验。真实使用前可在「设置与合规」一键删除。

## 使用流程

1. **查询**：输入 WhatsApp 号码、公司名或联系人；
2. **看结果**：风险等级、举报次数、类型、最近活跃时间、证据摘要；
3. **上报**：上传聊天记录或手动填写 → 确认号码 → 选问题类型 → 写经过 → 提交；
4. **复核/申诉**：在「设置与合规」查看申诉队列，必要时删除或纠正记录。

## 隐私与边界

- 聊天记录**只在本机内存中解析**，上传动作不经过任何服务器；
- 入库只保存号码、时间、类型、金额、经过和最多 5000 字证据摘要，**不保存完整聊天原文**；
- 本地私密**不等于法律豁免**：处理他人号码/聊天仍涉及个人信息与名誉权，详见合规文档；
- 风险分是**提示**，不是事实认定、征信报告或法律判决；
- 单条未经交叉验证的举报最高只到「中风险」；
- 无记录 ≠ 可信：骗子会换号、换公司名；
- 对外转发或公开这些记录前，请先核实事实并咨询律师。详见 [合规边界](docs/COMPLIANCE.md)。

## 目录结构

    tradeguard/
      app.py                     Streamlit 入口
      tradeguard/
        config.py                路径与上限
        constants.py             问题类型、风险等级、状态
        normalize.py             号码/公司名归一、脱敏
        chat_parser.py           WhatsApp 导出解析
        risk.py                  可解释的风险评分
        database.py              SQLite 数据层与查询聚合
        seed.py                  虚构演示数据
        ui/                      主题、组件、五个页面
      demo/                      零安装单页演示版（HTML/CSS/JS）
      tests/                     pytest 测试
      docs/                      产品方案、合规、插件设计
      data/                      本地数据库（gitignore）
      requirements.txt

## 测试

    cd tradeguard
    python -m pip install -r requirements-dev.txt
    python -m pytest

## 路线图

- **Phase 1（当前）**：本地网页 + 手动导出聊天记录解析 + 查询/上报/看板；
- **Phase 2**：Chrome 侧边栏插件，在 web.whatsapp.com 当前聊天界面一键查询、半自动上报（明确点击确认，不自动发消息）；
- **Phase 3**：团队版，多人共享情报库、审核队列、权限与审计；
- **Phase 4**：与货代、验厂、担保支付合作，把「查询」嵌入交易流程。

## 文档

- [产品方案](docs/PRODUCT_PLAN.md)
- [合规边界](docs/COMPLIANCE.md)
- [WhatsApp 插件设计](docs/WHATSAPP_PLUGIN.md)
- [市场与竞品调研](docs/MARKET_RESEARCH.md)
- [Streamlit Cloud 部署指南](docs/DEPLOY_STREAMLIT_CLOUD.md)

## 边界声明

本项目是产品原型，不构成法律意见。涉及公开他人信息、名誉权、个人信息保护、平台条款时，请务必先咨询专业律师。
