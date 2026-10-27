"""解析 WhatsApp 导出的聊天记录（Android / iOS TXT），提取号码与风险信号。

隐私原则：只在内存中解析；入库时只保存号码、时间范围、消息数与少量证据摘要，
默认不保存完整聊天记录。
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .config import MAX_CHAT_CHARS
from .normalize import format_phone, normalize_phone

# ---------------------------------------------------------------- 正则与常量

_IOS_RE = re.compile(
    r"^\[(\d{1,4}[./-]\d{1,2}[./-]\d{1,4}),?\s+"
    r"(\d{1,2}:\d{2}(?::\d{2})?)\s*([AaPp]\.?\s?[Mm]\.?)?\]\s*"
    r"([^:\n]{1,80}?):\s?(.*)$"
)
_ANDROID_RE = re.compile(
    r"^(\d{1,4}[./-]\d{1,2}[./-]\d{1,4}),?\s+"
    r"(\d{1,2}:\d{2}(?::\d{2})?)\s*([AaPp]\.?\s?[Mm]\.?)?\s+[-\u2013\u2014~]\s+"
    r"([^:\n]{1,80}?):\s?(.*)$"
)
_DATE_RE = re.compile(r"^(\d{1,4})[./-](\d{1,2})[./-](\d{1,4})$")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")

_SYSTEM_RE = re.compile(
    "|".join(
        [
            r"end-to-end encrypted",
            r"messages to this chat and calls are now secured",
            r"changed the group (?:icon|description|subject)",
            r"created group",
            r"joined using this group'?s invite link",
            r"added you",
            r"you were added",
            r"security code changed",
            r"changed their phone number",
            r"this message was deleted",
            r"已删除此消息",
            r"你加入了",
            r"加入了群组",
            r"创建了群组",
            r"更改了(?:群组|群聊)",
            r"安全码已更改",
            r"更改了手机号码",
            r"退出了群组",
            r"被移出",
            r"消息和通话已进行端到端加密",
        ]
    ),
    re.IGNORECASE,
)

_PHONE_RE = re.compile(r"(?<![\d])(?:\+|00)?\d(?:[\d\s().-]{6,18}\d)(?![\d])")
_DATE_TEXT_RE = re.compile(r"^\d{1,4}[./-]\d{1,2}[./-]\d{1,4}$")
_AMOUNT_RE = re.compile(r"^\d{1,3}(?:[,\s]\d{3})+(?:\.\d{1,2})?$|^\d{1,3}(?:,\d{3})*(?:\.\d{2})$")
_MEDIA_RE = re.compile(
    r"(<Media omitted>|\b(?:image|video|audio|sticker|GIF|document|Contact card) omitted\b|"
    r"\(文件已删除\)|已删除消息|媒体文件缺失)",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[\w.+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
_MONEY_RE = re.compile(
    r"(?:(?:USD|US\$|CNY|RMB|EUR|GBP|AUD|HKD|\$|¥|€|£)\s?\d[\d,]*(?:\.\d{1,2})?)|"
    r"(?:\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|US\$|CNY|RMB|EUR|GBP|AUD|HKD|dollars?|yuan))",
    re.IGNORECASE,
)

_FREE_MAIL = {
    "gmail.com", "googlemail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "live.com", "aol.com", "icloud.com", "qq.com", "163.com", "126.com",
    "protonmail.com", "proton.me", "mail.ru", "yandex.com",
}

_SIGNAL_DEFS: list[tuple[str, str, list[str]]] = [
    (
        "free_sample",
        "免费样品",
        ["免费样品", "免费拿样", "样品免费", "样品费免", "不付样品费", "白嫖",
         "free sample", "sample for free", "no sample fee", "free of charge"],
    ),
    (
        "payment_proof",
        "付款 / 水单",
        ["水单", "付款凭证", "转账截图", "汇款凭证", "银行回单", "bank slip",
         "swift copy", "payment proof", "payment screenshot", "western union",
         "usdt", "加密货币"],
    ),
    (
        "no_delivery",
        "不发货 / 失联",
        ["不发货", "没发货", "未发货", "失联", "拉黑", "跑路", "人间蒸发",
         "ghosted", "never shipped", "no delivery", "stopped replying", "blocked me"],
    ),
    (
        "unpaid",
        "拖欠 / 不付款",
        ["尾款", "拖欠", "不付款", "没付款", "未付款", "拒付",
         "unpaid", "balance due", "not paid", "refuse to pay"],
    ),
    (
        "quality",
        "质量问题",
        ["质量问题", "劣质", "假货", "不合格", "以次充好", "货不对板",
         "defective", "poor quality", "fake product", "counterfeit", "not as described"],
    ),
    (
        "phishing",
        "链接 / 钓鱼",
        ["钓鱼", "验证码", "verify your account", "click here", "login to confirm",
         "account suspended"],
    ),
    (
        "urgency",
        "催促施压",
        ["urgent", "asap", "今天必须", "马上", "立刻", "最后期限", "last chance"],
    ),
]


# ---------------------------------------------------------------- 数据模型


@dataclass
class ChatMessage:
    line_no: int
    timestamp: datetime | None
    sender: str
    text: str
    is_system: bool = False


@dataclass
class SignalHit:
    key: str
    label: str
    hits: int
    samples: list[str] = field(default_factory=list)


@dataclass
class DetectedPhone:
    norm: str
    mentions: int
    sample: str
    confidence: str  # high / medium / low

    @property
    def display(self) -> str:
        return format_phone(self.norm)


@dataclass
class ChatParseResult:
    filename: str
    size_bytes: int
    sha256: str
    encoding: str
    messages: list[ChatMessage]
    senders: list[tuple[str, int]]
    phones: list[DetectedPhone]
    signals: list[SignalHit]
    media_count: int
    url_count: int
    first_ts: datetime | None
    last_ts: datetime | None
    warnings: list[str] = field(default_factory=list)
    money_mentions: list[str] = field(default_factory=list)
    company_hints: list[str] = field(default_factory=list)

    @property
    def message_count(self) -> int:
        return sum(1 for m in self.messages if not m.is_system)

    @property
    def participant_count(self) -> int:
        return len(self.senders)

    @property
    def top_sender(self) -> str:
        return self.senders[0][0] if self.senders else ""

    @property
    def date_range(self) -> str:
        if not self.first_ts or not self.last_ts:
            return "未识别"
        if self.first_ts.date() == self.last_ts.date():
            return self.first_ts.strftime("%Y-%m-%d")
        return f"{self.first_ts:%Y-%m-%d} → {self.last_ts:%Y-%m-%d}"

    def primary_categories(self) -> list[str]:
        """把聊天里的信号映射为可预填的举报类型。"""
        signal_keys = {s.key for s in self.signals}
        mapping = {
            "free_sample": "free_samples",
            "no_delivery": "no_delivery",
            "unpaid": "unpaid_balance",
            "quality": "quality",
            "payment_proof": "fake_proof",
            "phishing": "fake_proof",
        }
        categories = [mapping[key] for key in signal_keys if key in mapping]
        if not categories:
            categories = ["fake_inquiry"]
        return categories

    def evidence_hint(self, limit: int = 3) -> str:
        lines: list[str] = []
        for signal in self.signals[:limit]:
            if signal.samples:
                lines.append(f"[{signal.label}] {signal.samples[0]}")
        return "\n".join(lines)


# ---------------------------------------------------------------- 解析


def _decode(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16"), "utf-16"
        except UnicodeDecodeError:
            pass
    for encoding in ("utf-8", "gb18030", "big5", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8(replace)"


def _parse_timestamp(date_part: str, time_part: str, ampm: str | None) -> datetime | None:
    date_match = _DATE_RE.match(date_part.strip())
    time_match = _TIME_RE.match(time_part.strip())
    if not date_match or not time_match:
        return None
    a, b, c = (int(x) for x in date_match.groups())
    if a > 31:
        year, month, day = a, b, c
    else:
        day, month, year = a, b, c
        if year < 100:
            year += 2000
    hour, minute, second = int(time_match.group(1)), int(time_match.group(2)), int(time_match.group(3) or 0)
    if ampm:
        marker = ampm.lower().replace(".", "").replace(" ", "")
        if marker.startswith("p") and hour < 12:
            hour += 12
        elif marker.startswith("a") and hour == 12:
            hour = 0
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def _is_system(sender: str, text: str) -> bool:
    if sender.strip().lower() in {"system", "系统", "system message"}:
        return True
    if not text:
        return False
    return bool(_SYSTEM_RE.search(text[:300]))


def _looks_like_amount(raw: str) -> bool:
    text = raw.strip()
    if re.fullmatch(r"\d{1,3}(?:[,\s]\d{3})+(?:\.\d{1,2})?", text):
        return True
    return bool(_AMOUNT_RE.match(text))


def _phone_confidence(raw: str, digits: str) -> str:
    stripped = raw.strip()
    if stripped.startswith("+") or stripped.startswith("00"):
        return "high"
    if len(digits) == 13 and digits.startswith("86") and digits[2] == "1" and digits[3] in "3456789":
        return "high"
    if len(digits) == 11 and digits[0] == "1" and digits[1] in "3456789":
        return "high"
    if len(digits) == 11 and digits[0] == "1" and digits[1] in "23456789":
        return "high"
    if len(digits) == 10 and digits[0] in "23456789":
        return "medium"
    if re.search(r"[\s().-]", stripped):
        return "medium"
    return "low"


def _iter_phone_candidates(text: str):
    for match in _PHONE_RE.finditer(text):
        raw = match.group(0).strip()
        if not raw:
            continue
        if _DATE_TEXT_RE.match(raw) or _looks_like_amount(raw):
            continue
        digits = re.sub(r"\D", "", raw)
        if not (8 <= len(digits) <= 15):
            continue
        if len(set(digits)) == 1:
            continue
        if re.fullmatch(r"(?:19|20)\d{6}", digits):
            continue
        has_prefix = raw.startswith("+") or raw.startswith("00")
        has_separator = bool(re.search(r"[\s().-]", raw))
        # 没有 +/00、没有分隔符、又不到 10 位的裸数字，多半是订单号或日期
        if not has_prefix and not has_separator and len(digits) < 10:
            continue
        norm = normalize_phone(raw)
        if not norm:
            continue
        yield raw, norm, _phone_confidence(raw, digits)


def _signal_hits(texts: list[str]) -> list[SignalHit]:
    hits: list[SignalHit] = []
    lowered = [t.lower() for t in texts]
    for key, label, needles in _SIGNAL_DEFS:
        count = 0
        samples: list[str] = []
        for original, low in zip(texts, lowered):
            matched = False
            for needle in needles:
                if needle.lower() in low:
                    matched = True
                    break
            if matched:
                count += 1
                if len(samples) < 2:
                    sample = " ".join(original.split())
                    samples.append(sample[:120])
        if count:
            hits.append(SignalHit(key=key, label=label, hits=count, samples=samples))
    hits.sort(key=lambda item: -item.hits)
    return hits


def _company_hints(text: str) -> list[str]:
    domains: Counter[str] = Counter()
    for match in _EMAIL_RE.finditer(text):
        domain = match.group(1).lower()
        if domain in _FREE_MAIL:
            continue
        domains[domain] += 1
    hints = []
    for domain, _ in domains.most_common(3):
        root = domain.split(".")[0]
        if 2 <= len(root) <= 24:
            hints.append(root.replace("-", " ").title())
    return hints


def parse_export(data: bytes | str, filename: str = "") -> ChatParseResult:
    """解析 WhatsApp 导出的聊天文件或纯文本。"""
    warnings: list[str] = []
    if isinstance(data, bytes):
        size_bytes = len(data)
        sha256 = hashlib.sha256(data).hexdigest()
        text, encoding = _decode(data)
    else:
        text = str(data)
        raw = text.encode("utf-8", errors="replace")
        size_bytes = len(raw)
        sha256 = hashlib.sha256(raw).hexdigest()
        encoding = "text"

    if len(text) > MAX_CHAT_CHARS:
        text = text[:MAX_CHAT_CHARS]
        warnings.append("文件过大，只解析了前 200 万字符。")

    # WhatsApp 导出里可能夹带窄不换行空格（U+202F）与 LRM（U+200E）等不可见字符
    text = (
        text.replace("\u202f", " ")
        .replace("\u200e", "")
        .replace("\u200f", "")
        .replace("\xa0", " ")
    )

    messages: list[ChatMessage] = []
    unparsed = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        match = _IOS_RE.match(line) or _ANDROID_RE.match(line)
        if match:
            date_part, time_part, ampm, sender, body = match.groups()
            timestamp = _parse_timestamp(date_part, time_part, ampm)
            sender = sender.strip().strip('"')[:80]
            messages.append(
                ChatMessage(
                    line_no=line_no,
                    timestamp=timestamp,
                    sender=sender,
                    text=body,
                    is_system=_is_system(sender, body),
                )
            )
        elif messages and not messages[-1].is_system:
            if _SYSTEM_RE.search(line):
                # 系统提示（加密提示、入群、删除消息等）不并入上一条正文
                unparsed += 1
            else:
                # 多行消息：追加到上一条
                messages[-1].text = f"{messages[-1].text}\n{line}".strip()
        else:
            unparsed += 1

    if not messages:
        warnings.append(
            "没有识别到 WhatsApp 聊天格式。请确认上传的是「导出聊天记录」生成的 .txt，"
            "或直接把包含号码和关键对话的文本粘贴进来。"
        )

    senders_counter: Counter[str] = Counter()
    phone_counter: Counter[str] = Counter()
    phone_samples: dict[str, str] = {}
    phone_confidence: dict[str, str] = {}
    signal_texts: list[str] = []

    for message in messages:
        if message.is_system:
            continue
        senders_counter[message.sender] += 1
        signal_texts.append(message.text)
        for source_text in (message.sender, message.text):
            for raw, norm, confidence in _iter_phone_candidates(source_text):
                phone_counter[norm] += 1
                phone_samples.setdefault(norm, raw)
                rank = {"low": 0, "medium": 1, "high": 2}
                if rank[confidence] > rank.get(phone_confidence.get(norm, "low"), 0):
                    phone_confidence[norm] = confidence

    all_text = "\n".join(signal_texts)
    signals = _signal_hits(signal_texts)
    media_count = len(_MEDIA_RE.findall(all_text))
    url_count = len(_URL_RE.findall(all_text))
    money_mentions = list(dict.fromkeys(match.group(0).strip() for match in _MONEY_RE.finditer(all_text)))[:12]
    company_hints = _company_hints(all_text)

    timestamps = [m.timestamp for m in messages if m.timestamp]
    phones = [
        DetectedPhone(norm=norm, mentions=count, sample=phone_samples.get(norm, ""), confidence=phone_confidence.get(norm, "low"))
        for norm, count in phone_counter.items()
    ]
    confidence_rank = {"high": 2, "medium": 1, "low": 0}
    phones.sort(key=lambda p: (-confidence_rank.get(p.confidence, 0), -p.mentions, p.norm))

    if unparsed and messages and unparsed > len(messages):
        warnings.append(f"有 {unparsed} 行未识别为聊天消息，可能影响解析结果。")

    return ChatParseResult(
        filename=filename or "粘贴的聊天内容",
        size_bytes=size_bytes,
        sha256=sha256,
        encoding=encoding,
        messages=messages,
        senders=senders_counter.most_common(10),
        phones=phones[:10],
        signals=signals,
        media_count=media_count,
        url_count=url_count,
        first_ts=min(timestamps) if timestamps else None,
        last_ts=max(timestamps) if timestamps else None,
        warnings=warnings,
        money_mentions=money_mentions,
        company_hints=company_hints,
    )
