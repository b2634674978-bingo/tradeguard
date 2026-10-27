"""演示数据。

⚠️ 所有号码均取自各国「虚构/影视专用」保留号段，公司与人名均为虚构。
演示数据在界面中有明显标记，可在「设置与合规」一键清除。
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def demo_reports() -> list[dict]:
    today = date.today()

    def days_ago(n: int) -> str:
        return (today - timedelta(days=n)).isoformat()

    def created_ago(n: int) -> str:
        moment = datetime.now() - timedelta(days=n)
        return moment.replace(microsecond=0).isoformat(timespec="seconds")

    return [
        {
            "phones": ["+1 555 010 4477"],
            "contact_name": "Mike R.",
            "company": "NovaPeak Supplements LLC",
            "country": "美国",
            "categories": ["free_samples", "fake_inquiry"],
            "amount": 0,
            "currency": "USD",
            "incident_date": days_ago(46),
            "created_at": created_ago(45),
            "narrative": (
                "【演示数据】谈了 3 周，说先寄 2 公斤样品给美国客户测试。样品费和运费都不付，"
                "承诺下单后一起结算。样品签收后不再回复，换号继续加人。"
            ),
            "evidence": "“Sample is for testing, you pay shipping first, we order 2 containers later.”（演示）",
            "credibility": 72,
            "chat_filename": "demo-novapeak-1.txt",
            "chat_sha256": _hash("demo-novapeak-1"),
            "chat_message_count": 128,
        },
        {
            "phones": ["+1 555 010 4477"],
            "contact_name": "Mike R.",
            "company": "NovaPeak Supplements LLC",
            "country": "美国",
            "categories": ["free_samples"],
            "amount": 0,
            "currency": "USD",
            "incident_date": days_ago(20),
            "created_at": created_ago(19),
            "narrative": (
                "【演示数据】收到第一批免费样品后说“质量不达标”，要求再免费寄一批，"
                "仍然拒绝支付样品费，也不肯下正式订单。"
            ),
            "evidence": "“Quality not good, send another batch free, then we decide.”（演示）",
            "credibility": 68,
            "chat_filename": "demo-novapeak-2.txt",
            "chat_sha256": _hash("demo-novapeak-2"),
            "chat_message_count": 64,
        },
        {
            "phones": ["+1 555 010 4477"],
            "contact_name": "Mike R.",
            "company": "NovaPeak Supplements LLC",
            "country": "美国",
            "categories": ["free_samples", "fake_inquiry"],
            "amount": 0,
            "currency": "USD",
            "incident_date": days_ago(4),
            "created_at": created_ago(3),
            "narrative": (
                "【演示数据】同一个 Mike 用另一个号来加，话术和第一次一模一样：先免费寄样、"
                "再谈大货。同行提醒后才发现是同一伙人。"
            ),
            "evidence": "“We are a big distributor, need free samples for our 20 clinics.”（演示）",
            "credibility": 74,
            "chat_filename": "demo-novapeak-3.txt",
            "chat_sha256": _hash("demo-novapeak-3"),
            "chat_message_count": 43,
        },
        {
            "phones": ["+1 555 010 9922"],
            "contact_name": "Daniel K.",
            "company": "Summit Bio Labs Inc",
            "country": "美国",
            "categories": ["no_delivery"],
            "amount": 2800,
            "currency": "USD",
            "incident_date": days_ago(12),
            "created_at": created_ago(11),
            "narrative": (
                "【演示数据】支付 30% 定金 2,800 美元后，对方以“原料涨价”为由要求补款，"
                "补款后不发货，WhatsApp 拉黑，网站也打不开。"
            ),
            "evidence": "“Our bank flagged the payment, please pay the balance first.”（演示）",
            "credibility": 80,
            "chat_filename": "demo-summit.txt",
            "chat_sha256": _hash("demo-summit"),
            "chat_message_count": 96,
        },
        {
            "phones": ["+44 7700 900123"],
            "contact_name": "Sarah W.",
            "company": "BrightLife Wholesale Ltd",
            "country": "英国",
            "categories": ["quality"],
            "amount": 1200,
            "currency": "GBP",
            "incident_date": days_ago(83),
            "created_at": created_ago(82),
            "narrative": (
                "【演示数据】500 支货，收到后近一半包装破损、批次不对，客户拒收。"
                "对方只愿意补 10%，拒绝退款，也不提供质检报告。"
            ),
            "evidence": "“We can only offer 10% credit, no refund.”（演示）",
            "credibility": 62,
            "chat_filename": None,
            "chat_sha256": None,
            "chat_message_count": None,
        },
        {
            "phones": ["+61 491 570 006"],
            "contact_name": "Liam T.",
            "company": "AussieFit Distribution Pty Ltd",
            "country": "澳大利亚",
            "categories": ["unpaid_balance"],
            "amount": 3400,
            "currency": "AUD",
            "incident_date": days_ago(150),
            "created_at": created_ago(149),
            "narrative": (
                "【演示数据】首批货已签收，尾款 3,400 澳元拖了 60 多天。"
                "每次都说“下周付”，后来只读不回。"
            ),
            "evidence": "“Next week for sure, our accountant is away.”（演示）",
            "credibility": 66,
            "chat_filename": None,
            "chat_sha256": None,
            "chat_message_count": None,
        },
        {
            "phones": ["+44 7700 900456"],
            "contact_name": "James P.",
            "company": "PureForm Trading Co",
            "country": "英国",
            "categories": ["fake_proof"],
            "amount": 4600,
            "currency": "GBP",
            "incident_date": days_ago(31),
            "created_at": created_ago(30),
            "narrative": (
                "【演示数据】发来一张银行水单截图要求先放货，核对后发现付款人、金额、"
                "SWIFT 号都对不上，是 P 的图。被追问后立刻删消息。"
            ),
            "evidence": "“Payment done, see attached slip, release goods today.”（演示）",
            "credibility": 78,
            "chat_filename": "demo-pureform.txt",
            "chat_sha256": _hash("demo-pureform"),
            "chat_message_count": 37,
        },
        {
            "phones": ["+1 555 010 1188"],
            "contact_name": "Chris M.",
            "company": "OceanBridge Sourcing",
            "country": "美国",
            "categories": ["fake_inquiry"],
            "amount": 0,
            "currency": "USD",
            "incident_date": days_ago(205),
            "created_at": created_ago(204),
            "narrative": (
                "【演示数据】连续三周索要完整报价表、COA、MSDS 和包装设计稿，"
                "说要给连锁客户提案。资料给完后消失，换号再来问同样的问题。"
            ),
            "evidence": "“Send full spec and price list first, we will confirm this week.”（演示）",
            "credibility": 58,
            "chat_filename": None,
            "chat_sha256": None,
            "chat_message_count": None,
        },
        {
            "phones": ["+1 555 010 6655"],
            "contact_name": "Alex D.",
            "company": "GreenLeaf Nutra",
            "country": "美国",
            "categories": ["no_delivery", "fake_proof"],
            "amount": 5000,
            "currency": "USD",
            "incident_date": days_ago(6),
            "created_at": created_ago(5),
            "narrative": (
                "【演示数据】付了 5,000 美元货款，对方先发假水单拖延，随后以“海关扣货”为由"
                "要求再付清关费。拒绝后彻底失联。"
            ),
            "evidence": "“Customs need extra 1,200 USD, pay now or goods returned.”（演示）",
            "credibility": 82,
            "chat_filename": "demo-greenleaf.txt",
            "chat_sha256": _hash("demo-greenleaf"),
            "chat_message_count": 152,
        },
    ]
