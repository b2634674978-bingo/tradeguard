"""号码、公司名与展示用的标准化工具。"""

from __future__ import annotations

import re

_DIGITS = re.compile(r"\D+")
_COMPANY_NOISE = re.compile(
    r"(co\.?,?\s*ltd\.?|company\s+limited|limited|ltd\.?|llc|inc\.?|corp\.?|"
    r"gmbh|s\.?a\.?|b\.?v\.?|pty\.?\s*ltd\.?|"
    r"有限责任公司|股份有限公司|有限公司|贸易有限公司|商贸有限公司|公司|集团)",
    re.IGNORECASE,
)
_NON_WORD = re.compile(r"[^0-9a-z\u4e00-\u9fff]+", re.IGNORECASE)


def digits_only(value: str | None) -> str:
    """只保留数字，用于号码比对。"""
    if not value:
        return ""
    return _DIGITS.sub("", str(value))


def normalize_phone(raw: str | None, default_cc: str | None = None) -> str | None:
    """把各种写法的号码归一为「国家码 + 号码」的纯数字串。

    - 支持 +86 138 0013 8000 / 0086... / (555) 010-4477 等写法；
    - 只有 8–15 位才视为有效号码，避免把订单号、日期当号码；
    - 不做真实运营商校验（本地工具，无法联网核验）。
    """
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None

    digits = digits_only(text)
    if not digits:
        return None

    # 00 开头的国际拨号前缀
    if text.startswith("00") and len(digits) > 8:
        digits = digits[2:]

    if default_cc and digits.startswith("0"):
        digits = default_cc + digits.lstrip("0")

    if default_cc == "86" and len(digits) == 11 and digits.startswith("1") and not digits.startswith("86"):
        digits = "86" + digits
    elif default_cc == "1" and len(digits) == 10:
        digits = "1" + digits

    if not (8 <= len(digits) <= 15):
        return None
    if len(set(digits)) == 1:
        return None
    # 排除 2024-05-01 这类被误当号码的日期；但保留 +852 2012 3456 这样的真实号码
    if re.fullmatch(r"(?:19|20)\d{6}", digits) and re.search(r"[./-]", text) and not text.startswith("+"):
        return None
    return digits


def phone_variants(raw: str | None) -> list[str]:
    """查询时可能的国家码变体，用于兼容“只输本地号码”的情况。"""
    digits = digits_only(raw)
    if not digits:
        return []
    text = str(raw).strip()
    if text.startswith("00") and len(digits) > 8:
        digits = digits[2:]

    # 用户已经写了 + 或 00 时，尊重其国家码，不再猜其他国家码。
    if text.startswith("+") or text.startswith("00"):
        return [digits] if 8 <= len(digits) <= 15 and len(set(digits)) > 1 else []

    out: list[str] = []

    def add(value: str) -> None:
        if value and 8 <= len(value) <= 15 and value not in out and len(set(value)) > 1:
            out.append(value)

    add(digits)
    if len(digits) == 11 and digits.startswith("1"):
        add("86" + digits)          # 中国手机号
    if len(digits) == 10:
        add("1" + digits)           # 北美 10 位
    if digits.startswith("0") and len(digits) >= 10:
        add(digits[1:])
    if digits.startswith("0") and len(digits) >= 11:
        add("86" + digits[1:])
    return out


def format_phone(norm: str | None) -> str:
    if not norm:
        return "—"
    return f"+{norm}"


def mask_phone(norm: str | None) -> str:
    """列表页脱敏显示；详情页在用户明确查询时再显示完整号码。"""
    if not norm:
        return "—"
    if len(norm) <= 8:
        return f"+{norm[:2]}***{norm[-2:]}"
    country = "1" if norm.startswith("1") and len(norm) == 11 else norm[:2]
    rest = norm[len(country):]
    if len(rest) >= 7:
        return f"+{country} {rest[:3]}***{rest[-4:]}"
    return f"+{norm[:3]}***{norm[-3:]}"


def is_probably_phone(value: str | None) -> bool:
    return normalize_phone(value) is not None


def company_key(name: str | None) -> str:
    """公司名归一：去掉法律后缀、标点与空白，便于同名匹配。"""
    if not name:
        return ""
    text = str(name).strip().lower()
    text = _COMPANY_NOISE.sub(" ", text)
    text = _NON_WORD.sub("", text)
    return text


def pick_display_name(contact_name: str | None, company: str | None, phone: str | None) -> str:
    name = (contact_name or "").strip()
    if name:
        return name
    company_name = (company or "").strip()
    if company_name:
        return company_name
    return mask_phone(phone) if phone else "未知联系人"


def short(text: str | None, limit: int = 90) -> str:
    if not text:
        return ""
    clean = " ".join(str(text).split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1] + "…"
