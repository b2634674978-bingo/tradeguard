"""查询验证页：输入号码 / 公司 / 联系人，返回风险档案。"""

from __future__ import annotations

import html

import streamlit as st

from .. import components, theme
from ..nav import goto
from ... import i18n
from ...auth import is_admin

EXAMPLES = ["+1 555 010 4477", "NovaPeak Supplements", "+44 7700 900123"]


def _set_query(query: str) -> None:
    st.session_state["last_query"] = query
    st.session_state["search_query"] = query


def render(db) -> None:
    counts = db.quick_counts()
    last_query = (st.session_state.get("last_query") or "").strip()
    if "search_query" not in st.session_state:
        st.session_state["search_query"] = last_query
    if getattr(db, "is_postgres", False):
        intro_zh = (
            "输入 WhatsApp 号码、公司名或联系人，查一查情报库里的历史举报。"
            "数据存放在本服务自建的 PostgreSQL 中，查询本身不会通知对方。"
        )
        intro_en = (
            "Search a WhatsApp number, company, or contact against reports in this database. "
            "Records are stored in this service's own PostgreSQL, and the subject is not notified."
        )
    else:
        intro_zh = (
            "输入 WhatsApp 号码、公司名或联系人，查一查本地情报库里的历史举报。"
            "数据只存在你的电脑上，查询本身不会通知对方。"
        )
        intro_en = (
            "Search a WhatsApp number, company, or contact against reports in this local database. "
            "Queries stay on this machine and the subject is not notified."
        )
    theme.hero(
        i18n.tr("交易前先查一查", "CHECK BEFORE YOU TRADE"),
        i18n.tr("这个名字，靠谱吗？", "Is this buyer or supplier trustworthy?"),
        i18n.tr(intro_zh, intro_en),
        tag=i18n.tr(
            f"已收录 {counts['reports']} 条举报 · 覆盖 {counts['phones']} 个号码",
            f"{counts['reports']} reports · {counts['phones']} numbers",
        ),
    )

    with st.form("search_form"):
        columns = st.columns([5.4, 1.2])
        query = columns[0].text_input(
            i18n.tr("查询对象", "Search"),
            placeholder=i18n.tr(
                "例如：+1 555 010 4477、NovaPeak Supplements、Mike R.",
                "e.g. +1 555 010 4477, NovaPeak Supplements, Mike R.",
            ),
            label_visibility="collapsed",
            key="search_query",
        )
        submitted = columns[1].form_submit_button(
            i18n.tr("立即查询", "Search"),
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if query.strip():
            st.session_state["last_query"] = query.strip()
        else:
            st.warning(i18n.tr("先输入号码、公司名或联系人。", "Enter a number, company, or contact."))

    example_cols = st.columns([1.1, 2.1, 2.7, 2.2, 1.2])
    example_cols[0].caption(i18n.tr("试试：", "Try:"))
    for index, example in enumerate(EXAMPLES):
        example_cols[index + 1].button(
            example,
            key=f"example_{index}",
            on_click=_set_query,
            args=(example,),
            use_container_width=True,
        )

    last_query = (st.session_state.get("last_query") or "").strip()
    if last_query:
        _render_result(db, last_query)
    else:
        _render_intro(db)


def _render_intro(db) -> None:
    theme.section_title(i18n.tr("查询之前，先记住三条", "Three rules before you search"))
    columns = st.columns(3)
    cards = [
        (
            "🔎",
            i18n.tr("先查再谈", "Check first"),
            i18n.tr(
                "谈样品、谈价格之前，先用号码和公司名查一遍。30 秒，可能省下几周的样品和时间。",
                "Search the number and company before discussing samples or pricing. Thirty seconds can save weeks of samples and time.",
            ),
        ),
        (
            "⚖️",
            i18n.tr("风险提示 ≠ 判决", "A risk flag is not a verdict"),
            i18n.tr(
                "单条举报最高只到中风险。请结合多条记录、证据、时间和自己的判断，不要只凭一个分数拉黑客户。",
                "A single unverified report is capped at medium risk. Review multiple reports, evidence, timing, and your own judgment.",
            ),
        ),
        (
            "🕳️",
            i18n.tr("无记录 ≠ 可信", "No record does not mean safe"),
            i18n.tr(
                "骗子会换号、换公司名。没有记录只说明没人报过，验厂、担保、分阶段付款仍然是底线。",
                "Scammers change numbers and company names. No record only means nobody has reported them yet. Keep verifying factories and using escrow or staged payments.",
            ),
        ),
    ]
    for column, (icon, title, body) in zip(columns, cards):
        with column:
            st.markdown(
                f"""
                <div class="tg-card" style="height:100%">
                  <div style="font-size:1.5rem">{icon}</div>
                  <div class="tg-name" style="margin-top:.35rem">{html.escape(title)}</div>
                  <div class="tg-sub" style="margin-top:.4rem; line-height:1.75">{html.escape(body)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    theme.section_title(i18n.tr("这个库怎么来的", "How this database is built"))
    st.markdown(
        '<div class="tg-note">'
        + i18n.tr(
            "每一条记录都来自真实受骗者的主动上报，包含号码、问题类型、经过和聊天截图。"
            "系统会聚合同一个号码的多条记录，给出<strong>可解释</strong>的风险分，而不是一个黑箱结论。"
            "管理员审核通过后，记录才会公开显示。",
            "Every record comes from a voluntary report with the number, issue type, narrative, and screenshots. "
            "Reports are grouped by number with an <strong>explainable</strong> risk score, not a black-box verdict. "
            "Records become public only after admin review.",
        )
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_result(db, query: str) -> None:
    result = db.search(query)
    profiles = result["profiles"]
    text_reports = result["text_reports"]

    st.markdown(
        '<div class="tg-section-title">'
        + i18n.tr("查询结果", "Search results")
        + '</div><div class="tg-name" style="margin-bottom:.2rem">'
        + html.escape(query)
        + "</div>",
        unsafe_allow_html=True,
    )

    if not profiles and not text_reports:
        _render_no_result(db, query, result)
        return

    exact = [profile for profile in profiles if profile["match_kind"] == "phone_exact"]
    suffix = [profile for profile in profiles if profile["match_kind"] == "phone_suffix"]
    by_name = [profile for profile in profiles if profile["match_kind"] == "text"]

    if exact:
        theme.note(
            i18n.tr(
                f"⚠️ 本地库中找到了 <strong>{len(exact)}</strong> 个号码记录。以下风险分来自历史举报聚合，"
                "不是法律结论；请看完证据再决定。",
                f"⚠️ Found <strong>{len(exact)}</strong> matching number record(s). Scores aggregate prior reports "
                "and are not legal conclusions. Review the evidence before deciding.",
            ),
            "warn",
        )
        for profile in exact:
            components.profile_card(
                profile, db, masked=False, key_prefix=f"exact_{profile['phone']}"
            )

    if suffix:
        theme.note(
            i18n.tr(
                "没有完全一致的号码，但以下号码与查询号码<strong>尾号相同</strong>，可能是同一人换号，请人工核对。",
                "No exact number match, but the numbers below share the <strong>same last digits</strong>. "
                "They may be the same person using a new number; verify manually.",
            ),
            "warn",
        )
        for profile in suffix:
            components.profile_card(
                profile, db, masked=True, key_prefix=f"suffix_{profile['phone']}"
            )

    if by_name:
        theme.note(
            i18n.tr(
                "号码没有命中，但<strong>公司 / 联系人名称</strong>命中了以下记录。请结合公司地址、域名、联系人核实是否为同一主体。",
                "The number did not match, but the <strong>company or contact name</strong> did. "
                "Verify the address, domain, and contact before treating them as the same entity.",
            ),
            "warn",
        )
        for profile in by_name:
            components.profile_card(
                profile, db, masked=True, key_prefix=f"name_{profile['phone'] or profile['display_name']}"
            )

    if text_reports:
        st.markdown(
            '<div class="tg-section-title">'
            + i18n.tr("相关记录", "Related reports")
            + "</div>",
            unsafe_allow_html=True,
        )
        for report in text_reports:
            components.report_card(report, db, public_view=not is_admin())

    for note in result["notes"]:
        st.caption(note)

    st.caption(i18n.tr(
        "风险分仅用于提示交易风险，不构成对任何个人或公司的法律认定。",
        "Risk scores are for transaction risk awareness only and are not legal findings about any person or company.",
    ))
    _interpretation_expander()


def _render_no_result(db, query: str, result: dict) -> None:
    phone_input = result.get("phone_input")
    components.empty_state(
        "🕳️",
        i18n.tr(
            f"本地库暂无「{query}」的记录",
            f"No local record for “{query}”",
        ),
        [
            i18n.tr(
                "没有记录，不代表对方可信。骗子经常换号、换公司名、换接头人。",
                "No record does not mean the subject is trustworthy. Scammers change numbers, companies, and contacts.",
            ),
            i18n.tr(
                "建议先视频验厂/验货、核实公司注册信息，再走可追溯的付款方式。",
                "Verify the factory or goods on video, check company registration, and use traceable payments.",
            ),
            i18n.tr(
                "如果你和这个人打过交道并踩了坑，花 2 分钟上报，下一个人就能查到。",
                "If you have dealt with this subject and lost money, spend two minutes reporting it so others can find it.",
            ),
        ],
    )
    columns = st.columns([1.2, 1.2, 2.6])
    if columns[0].button(
        i18n.tr("我遇到过这个人，去上报", "I dealt with them — report"),
        type="primary",
        use_container_width=True,
    ):
        st.session_state["prefill_phone"] = phone_input or ""
        goto("上报记录")
    if columns[1].button(i18n.tr("换个号码再查", "Search another"), use_container_width=True):
        st.session_state["last_query"] = ""
        st.session_state["search_query"] = ""
        st.rerun()

    _interpretation_expander()


def _interpretation_expander() -> None:
    with st.expander(i18n.tr("风险分是怎么算的？", "How is the risk score calculated?")):
        st.markdown(
            i18n.tr(
                """
                **加分项**：被举报次数、问题类型严重度、最近 90 天是否活跃、是否附带聊天记录、涉及金额、举报可信度。

                **保守设计**：
                - 单条未经交叉验证的举报：有聊天记录且可信度 ≥70 时最高 **55 分（中风险）**；仅文字描述最高 **39 分（低风险）**；
                - 多条记录 + 严重类型 + 近期活跃，才可能进入 **高风险**；
                - 每条评分都会显示依据，方便你自己判断；
                - 所有记录都可以申诉，申诉会进入本地复核列表。

                这是一个**风险提示工具**，不是征信报告，也不是法院判决。
                """,
                """
                **Signals:** number of reports, issue severity, activity in the last 90 days, attached chat evidence, amount involved, and reporter credibility.

                **Conservative design:**
                - A single uncorroborated report is capped at **55 (medium)** when chat evidence exists and credibility is >=70; text-only reports are capped at **39 (low)**.
                - High risk requires multiple reports, a serious issue type, and recent activity.
                - Every score shows its reasons so you can judge for yourself.
                - Every record can be appealed.

                This is a **risk-awareness tool**, not a credit report or a court judgment.
                """,
            )
        )
