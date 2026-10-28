"""可复用的卡片、风险徽章、举报记录块与申诉入口。"""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

from .. import i18n
from ..auth import public_viewer
from ..config import APP_TAGLINE, APP_TITLE
from ..normalize import format_phone, mask_phone
from ..risk import assess


def esc(value: object) -> str:
    return html.escape(str(value or ""))


def risk_badge(risk: dict) -> str:
    tone = risk.get("tone", "unknown")
    label = i18n.risk_label(risk.get("level", "unknown"))
    score = int(risk.get("score") or 0)
    if tone == "unknown":
        return '<span class="tg-risk unknown">' + i18n.tr("暂无记录", "No record") + "</span>"
    return f'<span class="tg-risk {tone}">{esc(label)} · {score}</span>'


def category_pills(categories: list[dict]) -> str:
    if not categories:
        return ""
    return "".join(
        f'<span class="tg-pill">{esc(i18n.category_label(item["key"]))} <b>×{item["count"]}</b></span>'
        for item in categories
    )


def _last_seen_label(value: str) -> str:
    if not value:
        return "未知"
    try:
        seen = date.fromisoformat(value[:10])
    except ValueError:
        return value
    days = (date.today() - seen).days
    if days <= 0:
        return i18n.tr("今天", "today")
    if days == 1:
        return i18n.tr("昨天", "yesterday")
    if days < 30:
        return i18n.tr(f"{days} 天前", f"{days} days ago")
    if days < 365:
        return i18n.tr(f"{days // 30} 个月前", f"{days // 30} months ago")
    return i18n.tr(f"{days // 365} 年前", f"{days // 365} years ago")


def profile_card(profile: dict, db, *, masked: bool = False, show_appeal: bool = True, key_prefix: str = "p") -> None:
    phone = profile.get("masked_phone") if masked else profile.get("display_phone")
    phone_html = f'<div class="tg-phone">{esc(phone)}</div>' if phone else ""
    company = esc(profile.get("company"))
    country = esc(profile.get("country"))
    meta = " · ".join(part for part in (company, country) if part) or i18n.tr("未填写公司 / 国家", "No company / country")
    demo = '<span class="tg-tag">演示数据</span>' if profile.get("has_demo") else ""
    reasons = " · ".join(esc(reason) for reason in profile["risk"].get("reasons", [])[:4])
    match = (
        f'<div class="tg-match">{esc(profile.get("match_reason"))}</div>'
        if profile.get("match_reason")
        else ""
    )
    st.markdown(
        f"""
        <div class="tg-card">
          <div class="tg-row-between">
            <div>
              <div class="tg-name">{esc(profile.get("display_name"))}{demo}</div>
              <div class="tg-sub">{meta}</div>
              {phone_html}
              {match}
            </div>
            <div class="tg-right">
              {risk_badge(profile["risk"])}
              <div class="tg-sub" style="margin-top:.35rem">
                {profile["report_count"]} {i18n.tr("条记录", "reports")} · {i18n.tr("最近", "last")} {_last_seen_label(profile.get("last_seen", ""))}
              </div>
            </div>
          </div>
          <div class="tg-pills">{category_pills(profile.get("categories", []))}</div>
          <div class="tg-reasons"><span>{i18n.tr("评分依据", "Why this score")}</span> · {reasons}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    reports = profile.get("reports", [])
    with st.expander(
        i18n.tr(f"查看 {len(reports)} 条举报记录与证据", f"View {len(reports)} report(s) and evidence")
    ):
        for report in reports:
            report_card(report, db, public_view=public_viewer())
        if show_appeal and reports:
            appeal_block(db, reports[0], key_prefix=key_prefix)


def report_card(report: dict, db=None, *, public_view: bool = True) -> None:
    amount = ""
    if report.get("amount"):
        amount = f' · {esc(report.get("currency", ""))} {float(report["amount"]):,.0f}'
    labels = " · ".join(
        esc(i18n.category_label(key)) for key in report.get("categories", [])
    )
    source = esc(i18n.source_label(report.get("source", "")))
    demo = " · " + i18n.tr("演示", "demo") if report.get("source") == "demo" else ""
    evidence = ""
    evidence_text = str(report.get("evidence") or "")
    if evidence_text and not evidence_text.startswith("data:image"):
        evidence = f'<div class="tg-quote">{esc(evidence_text)}</div>'
    chat_meta = ""
    if report.get("chat_sha256"):
        chat_meta = (
            f'<div class="tg-sub" style="margin-top:.45rem">📎 聊天记录已核验指纹 '
            f'<span class="tg-mono">{esc((report.get("chat_sha256") or "")[:12])}…</span>'
            f' · {report.get("chat_message_count") or "—"} 条消息</div>'
        )
    st.markdown(
        f"""
        <div style="padding:.85rem 0; border-top:1px solid #eef2f7">
          <div class="tg-sub" style="display:flex; justify-content:space-between; gap:.6rem; flex-wrap:wrap">
            <span>{esc(report.get("date", ""))} · {labels}{amount}</span>
            <span>{source}{demo} · {i18n.tr("可信度", "credibility")} {report.get("credibility", 60)}</span>
          </div>
          <div style="font-size:.9rem; color:#334155; line-height:1.7; margin-top:.35rem; white-space:pre-wrap">{esc(report.get("narrative"))}</div>
          {evidence}
          {chat_meta}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if db is not None and report.get("id"):
        images = db.get_report_images(report["id"], public_only=public_view)
        if images:
            st.caption(
                i18n.tr("举报人同意公开的截图", "Screenshots shared by the reporter")
                if public_view
                else i18n.tr("截图证据（管理员可见）", "Screenshots (admin only)")
            )
            for index, image in enumerate(images):
                st.image(
                    image["data"],
                    caption=i18n.tr(f"截图 {index + 1}", f"Screenshot {index + 1}"),
                    use_container_width=True,
                )


def appeal_block(db, report: dict, *, key_prefix: str = "a") -> None:
    """申诉入口对所有人开放：这是被举报方的唯一救济渠道。"""
    with st.expander(
        i18n.tr("我是当事人 / 信息有误？提交申诉或补充说明", "Are you the subject? File an appeal")
    ):
        st.caption(i18n.tr(
            "申诉会记录到后台，由管理员逐条复核。原型阶段不会自动删除任何记录。",
            "Appeals go to the admin queue for manual review. Nothing is deleted automatically at this stage.",
        ))
        with st.form(f"appeal_form_{key_prefix}_{report.get('id')}"):
            message = st.text_area(
                i18n.tr("申诉说明", "Appeal details"),
                key=f"appeal_text_{key_prefix}_{report.get('id')}",
                placeholder=i18n.tr(
                    "请说明：哪一条信息与事实不符、你与对方的关系、可提供的证明……",
                    "Explain what is inaccurate, your relationship to the subject, and any proof you can provide.",
                ),
                height=100,
            )
            submitted = st.form_submit_button(i18n.tr("提交申诉", "Submit appeal"))
        if submitted:
            try:
                db.add_appeal(message, report_id=report.get("id"))
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(i18n.tr(
                    "申诉已记录，管理员复核后会联系你。",
                    "Appeal recorded. An admin will review it.",
                ))


def empty_state(icon: str, title: str, lines: list[str]) -> None:
    body = "".join(f"<p>{esc(line)}</p>" for line in lines)
    st.markdown(
        f'<div class="tg-empty"><div class="tg-empty-icon">{icon}</div>'
        f"<h3>{esc(title)}</h3>{body}</div>",
        unsafe_allow_html=True,
    )


def stat_strip(items: list[tuple[str, str]]) -> None:
    cells = "".join(
        f'<div class="tg-side-stat" style="margin:0"><div><b>{esc(value)}</b><span>{esc(label)}</span></div></div>'
        for label, value in items
    )
    st.markdown(f'<div style="display:flex; gap:.6rem">{cells}</div>', unsafe_allow_html=True)


def brand_block() -> None:
    st.markdown(
        f"""
        <div class="tg-brand">
          <div class="tg-logo">🛡️</div>
          <div>
            <div class="tg-brand-name">TradeGuard</div>
            <div class="tg-brand-sub">{i18n.tr("外贸防骗情报库", "Trade scam intel")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
