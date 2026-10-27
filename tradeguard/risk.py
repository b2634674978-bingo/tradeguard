"""风险评分：透明、保守、可解释。

设计原则（重要）：
1. 单条未经交叉验证的举报最高只能到「中风险」，避免一次指控毁掉一个客户；
2. 评分只做风险提示，不做事实认定；界面必须同时展示“无记录 ≠ 可信”；
3. 每条加分都有对应理由，方便用户自己判断，而不是只给一个黑箱数字。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from .constants import CATEGORIES, RISK_LEVELS


@dataclass
class RiskAssessment:
    score: int
    level: str
    label: str
    reasons: list[str] = field(default_factory=list)

    @property
    def tone(self) -> str:
        return RISK_LEVELS.get(self.level, RISK_LEVELS["unknown"])["tone"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "label": self.label,
            "tone": self.tone,
            "reasons": self.reasons,
        }


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _latest_activity(reports: list[dict]) -> date | None:
    dates = []
    for report in reports:
        value = _as_date(report.get("incident_date")) or _as_date(report.get("created_at"))
        if value:
            dates.append(value)
    return max(dates) if dates else None


def assess(reports: Iterable[dict], *, today: date | None = None) -> RiskAssessment:
    reports = list(reports)
    if not reports:
        return RiskAssessment(
            score=0,
            level="unknown",
            label=RISK_LEVELS["unknown"]["label"],
            reasons=["本地库中暂无该对象的举报记录"],
        )

    today = today or date.today()
    ids = {r.get("id") for r in reports if r.get("id") is not None}
    count = max(len(ids), len(reports)) if ids else len(reports)

    categories: set[str] = set()
    for report in reports:
        for key in report.get("categories") or []:
            if key in CATEGORIES:
                categories.add(key)
    severity = max((CATEGORIES[c]["severity"] for c in categories), default=CATEGORIES["other"]["severity"])

    base = min(40, 16 + 8 * count)
    score = base + severity

    latest = _latest_activity(reports)
    recency = 0
    if latest:
        age = (today - latest).days
        if age <= 90:
            recency = 12
        elif age <= 365:
            recency = 6
    score += recency

    has_chat = any(bool(r.get("chat_sha256")) for r in reports)
    score += 8 if has_chat else 0

    amounts = [float(r.get("amount") or 0) for r in reports]
    total_amount = sum(a for a in amounts if a > 0)
    if total_amount >= 5000:
        amount_points = 8
    elif total_amount >= 1000:
        amount_points = 5
    elif total_amount > 0:
        amount_points = 2
    else:
        amount_points = 0
    score += amount_points

    credibilities = [int(r.get("credibility") or 60) for r in reports]
    avg_cred = sum(credibilities) / len(credibilities)
    credibility_adj = max(-3, min(3, round((avg_cred - 60) / 10)))
    score += credibility_adj

    # 单条记录的封顶：未经交叉验证的举报不能直接变成“高风险”。
    # 有聊天记录且可信度较高 → 中风险；仅文字描述 → 低风险线索。
    if count <= 1:
        if has_chat and avg_cred >= 70:
            score = min(score, 55)
        else:
            score = min(score, 39)

    score = max(0, min(100, score))

    if score >= 70:
        level = "high"
    elif score >= 45:
        level = "medium"
    elif score >= 20:
        level = "low"
    else:
        level = "watch"

    reasons: list[str] = []
    if count >= 2:
        reasons.append(f"被 {count} 条独立记录举报")
    else:
        reasons.append("仅 1 条记录，尚未交叉验证")
    if categories:
        labels = "、".join(CATEGORIES[c]["label"] for c in sorted(categories, key=lambda x: -CATEGORIES[x]["severity"]))
        reasons.append(f"涉及类型：{labels}")
    if recency >= 12:
        reasons.append("最近 90 天内仍有新记录")
    elif recency:
        reasons.append("近一年内有记录")
    if has_chat:
        reasons.append("附带聊天记录佐证")
    if total_amount > 0:
        reasons.append(f"记录涉及金额合计约 {total_amount:,.0f}（未折算币种）")
    if count >= 3 and avg_cred >= 70:
        reasons.append("多条记录的可信度较高")

    return RiskAssessment(score=score, level=level, label=RISK_LEVELS[level]["label"], reasons=reasons)
