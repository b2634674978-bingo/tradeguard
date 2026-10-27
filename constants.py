"""业务常量：问题类型、风险等级、状态、币种。"""

from __future__ import annotations

# 问题类型。severity 只用于风险评分的初始权重，最终评分仍由多条记录、时效、
# 证据共同决定；任何单一类型都不足以给一个人/公司“定罪”。
CATEGORIES: dict[str, dict] = {
    "free_samples": {
        "label": "样品费未付",
        "short": "样品费",
        "severity": 26,
        "desc": "以采购为名索要免费样品、样品费未付、收到样品后不再回复",
    },
    "no_delivery": {
        "label": "收款未发货",
        "short": "未发货",
        "severity": 30,
        "desc": "收到货款/定金后未发货、失联、拉黑",
    },
    "unpaid_balance": {
        "label": "尾款未付",
        "short": "尾款",
        "severity": 20,
        "desc": "收货后尾款未付、拒付、以质量问题为由压款",
    },
    "quality": {
        "label": "质量争议",
        "short": "质量",
        "severity": 16,
        "desc": "以次充好、批次不合格、货不对板",
    },
    "fake_inquiry": {
        "label": "无效询盘",
        "short": "询盘",
        "severity": 10,
        "desc": "反复索要报价/资料/规格，无真实采购意向",
    },
    "fake_proof": {
        "label": "付款凭证存疑",
        "short": "凭证",
        "severity": 28,
        "desc": "伪造付款水单、钓鱼链接、冒充采购方或货代",
    },
    "other": {
        "label": "其他争议",
        "short": "其他",
        "severity": 6,
        "desc": "其他交易争议，请在经过中说明",
    },
}

CATEGORY_KEYS = list(CATEGORIES)
CATEGORY_LABELS = {k: v["label"] for k, v in CATEGORIES.items()}
CATEGORY_BY_LABEL = {v["label"]: k for k, v in CATEGORIES.items()}
CATEGORY_SHORT = {k: v["short"] for k, v in CATEGORIES.items()}

# 风险等级（展示用；不是法律结论）
RISK_LEVELS = {
    "high": {"label": "高风险", "tone": "high", "desc": "多条记录或严重类型 + 近期活跃，建议先核实再交易"},
    "medium": {"label": "中风险", "tone": "medium", "desc": "存在明确投诉，建议分阶段付款并要求第三方担保"},
    "low": {"label": "低风险", "tone": "low", "desc": "有零散记录，先小额试单、保留证据"},
    "watch": {"label": "关注", "tone": "watch", "desc": "记录较少或较旧，仅作线索"},
    "unknown": {"label": "无记录", "tone": "unknown", "desc": "库里没有记录，不等于对方可信"},
}

REPORT_STATUS = {
    "approved": "已收录",
    "pending": "待复核",
    "rejected": "已驳回",
}

SOURCES = {
    "demo": "演示",
    "manual": "手动上报",
    "chat_import": "聊天导入",
    "csv_import": "批量导入",
}

CURRENCIES = ["USD", "CNY", "EUR", "GBP", "AUD", "HKD", "JPY", "其他"]

# 常见国家/地区：用于下拉提示，也允许自由填写
COUNTRIES = [
    "美国", "加拿大", "墨西哥", "巴西", "英国", "德国", "法国", "意大利",
    "西班牙", "荷兰", "波兰", "俄罗斯", "土耳其", "阿联酋", "沙特阿拉伯",
    "印度", "巴基斯坦", "孟加拉国", "越南", "泰国", "马来西亚", "新加坡",
    "印度尼西亚", "菲律宾", "日本", "韩国", "澳大利亚", "新西兰",
    "南非", "尼日利亚", "埃及", "中国香港", "中国台湾", "其他",
]

DEMO_MARK = "【演示数据】"
