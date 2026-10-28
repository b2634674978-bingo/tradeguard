"""轻量中英文切换（不引入 gettext / 额外依赖）。"""

from __future__ import annotations

import streamlit as st

from .constants import CATEGORY_LABELS, REPORT_STATUS, RISK_LEVELS, SOURCES

LANG_CHOICES = {"中文": "zh", "English": "en"}

PAGE_LABELS = {
    "查询验证": ("查询验证", "Check"),
    "上报记录": ("上报记录", "Report"),
    "情报库": ("情报库", "Intel"),
    "数据看板": ("数据看板", "Dashboard"),
    "帮助与合规": ("帮助与合规", "Help & rules"),
    "管理后台": ("管理后台", "Admin"),
}

CATEGORY_LABELS_EN = {
    "free_samples": "Unpaid samples",
    "no_delivery": "Paid, not shipped",
    "unpaid_balance": "Unpaid balance",
    "quality": "Quality dispute",
    "fake_inquiry": "Fake inquiry",
    "fake_proof": "Suspicious payment proof",
    "other": "Other dispute",
}

RISK_LABELS_EN = {
    "high": "High risk",
    "medium": "Medium risk",
    "low": "Low risk",
    "watch": "Watch",
    "unknown": "No record",
}

STATUS_LABELS_EN = {
    "approved": "Published",
    "pending": "Pending review",
    "rejected": "Rejected",
}

SOURCE_LABELS_EN = {
    "demo": "Demo",
    "manual": "User report",
    "chat_import": "Chat import",
    "csv_import": "CSV import",
}


def lang() -> str:
    return st.session_state.get("lang", "zh")


def tr(zh: str, en: str) -> str:
    return en if lang() == "en" else zh


def page_label(page: str) -> str:
    zh, en = PAGE_LABELS.get(page, (page, page))
    return en if lang() == "en" else zh


def category_label(key: str) -> str:
    if lang() == "en":
        return CATEGORY_LABELS_EN.get(key, CATEGORY_LABELS.get(key, key))
    return CATEGORY_LABELS.get(key, key)


def risk_label(level: str) -> str:
    if lang() == "en":
        return RISK_LABELS_EN.get(level, RISK_LEVELS.get(level, {}).get("label", level))
    return RISK_LEVELS.get(level, {}).get("label", level)


def status_label(status: str) -> str:
    if lang() == "en":
        return STATUS_LABELS_EN.get(status, REPORT_STATUS.get(status, status))
    return REPORT_STATUS.get(status, status)


def source_label(source: str) -> str:
    if lang() == "en":
        return SOURCE_LABELS_EN.get(source, SOURCES.get(source, source))
    return SOURCES.get(source, source)


def language_selector() -> None:
    current = 0 if lang() == "zh" else 1
    choice = st.selectbox(
        tr("语言 / Language", "Language / 语言"),
        list(LANG_CHOICES.keys()),
        index=current,
        key="lang_select",
    )
    st.session_state["lang"] = LANG_CHOICES.get(choice, "zh")
