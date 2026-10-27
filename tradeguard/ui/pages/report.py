"""上报记录页：上传 / 粘贴 WhatsApp 聊天，解析后补充信息入库。"""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

from .. import components, theme
from ..nav import goto
from ...auth import is_admin, public_mode
from ...chat_parser import parse_export
from ...config import MAX_UPLOAD_BYTES
from ...constants import CATEGORIES, CATEGORY_KEYS, CATEGORY_LABELS, CURRENCIES
from ...normalize import format_phone, normalize_phone

CONFIDENCE_LABELS = {"high": "高", "medium": "中", "low": "低"}


def render(db) -> None:
    theme.page_header(
        "上传被骗经历",
        "把一次受骗，变成所有人的防线",
        "上传 WhatsApp 导出的聊天记录，系统自动提取对方号码、时间线和风险信号；"
        "补充经过后入库。只保存必要证据，不保存完整聊天原文。",
    )

    if public_mode():
        if is_admin():
            st.caption("云端临时存储：应用重启/重新部署后，本页新增的数据可能丢失。请及时在设置中备份。")
        else:
            theme.note(
                "你提交的举报会进入<strong>待审核队列</strong>，管理员审核通过后才会公开显示。"
                "请确保你提交的信息真实、有聊天记录佐证，不要恶意诬告。",
                "info",
            )

    _render_success_block()

    with st.container(border=True):
        st.markdown("#### 1 · 上传聊天截图（可选）")
        st.caption("💡 建议：第一张传对方的个人主页/资料截图（能看到他的号码、名字、公司），后面传关键的聊天记录截图，这样管理员审核的时候能确认是同一个人。最多传3张，系统不会公开你的截图，只留作审核证据。")
        uploaded_images = st.file_uploader(
            "上传聊天截图",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="image_upload",
        )
        if uploaded_images:
            st.success(f"已上传 {len(uploaded_images)} 张截图")

    _render_form(db, None)


def _render_success_block() -> None:
    success = st.session_state.get("report_success")
    if not success:
        return
    if is_admin():
        st.success(f"已收录：{success['label']} · {success['query']}。你可以在「查询验证」里立即查到它。")
    else:
        st.success(f"提交成功！你的举报已进入待审核队列。\n\n类别：{success['label']} · 对象：{success['query']}\n\n管理员审核通过后才会公开显示。")
    cols = st.columns([1.5, 1.5, 3.5])
    if cols[0].button("查看风险档案", type="primary", use_container_width=True):
        st.session_state["last_query"] = success["query"]
        st.session_state["search_query"] = success["query"]
        goto("查询验证")
    if cols[1].button("继续上报下一条", use_container_width=True):
        st.session_state.pop("report_success", None)
        st.session_state.pop("parsed_chat", None)
        st.rerun()
    if is_admin():
        st.caption("提示：管理员提交的记录直接公开；你可以在「设置与合规」中复核、导出或删除记录。")


def _render_parsed(parsed) -> None:
    for warning in parsed.warnings:
        st.warning(warning)

    columns = st.columns(4)
    columns[0].metric("消息数", parsed.message_count)
    columns[1].metric("参与者", parsed.participant_count)
    columns[2].metric("识别号码", len(parsed.phones))
    columns[3].metric("风险信号", len(parsed.signals))

    with st.expander("查看解析详情", expanded=True):
        st.caption(f"文件：{parsed.filename} · 编码：{parsed.encoding} · 时间范围：{parsed.date_range}")

        if parsed.phones:
            st.markdown("**识别到的号码（按可信度排序）**")
            confidence = {"high": "高", "medium": "中", "low": "低"}
            for phone in parsed.phones:
                st.markdown(
                    f"- {phone.display} · 出现 {phone.mentions} 次 · 可信度 "
                    f"{confidence.get(phone.confidence, phone.confidence)}"
                )
        else:
            st.info("没有从聊天记录里识别到号码，可以在下面手动填写。")

        if parsed.signals:
            st.markdown("**聊天里的风险信号（只作提示，需人工判断）**")
            pills = "".join(
                f'<span class="tg-pill">{signal.label} <b>×{signal.hits}</b></span>'
                for signal in parsed.signals
            )
            st.markdown(f'<div class="tg-pills" style="margin-top:0">{pills}</div>', unsafe_allow_html=True)

        details = []
        if parsed.senders:
            details.append("发送者：" + "、".join(f"{name}（{count} 条）" for name, count in parsed.senders[:6]))
        if parsed.money_mentions:
            details.append("金额提及：" + "、".join(parsed.money_mentions[:6]))
        if parsed.company_hints:
            details.append("邮箱域名线索：" + "、".join(parsed.company_hints))
        if parsed.media_count:
            details.append(f"媒体占位符：{parsed.media_count} 处")
        if parsed.url_count:
            details.append(f"链接：{parsed.url_count} 个")
        for detail in details:
            st.caption(detail)

        if parsed.evidence_hint():
            st.markdown("**可自动带入的证据摘要**")
            st.markdown(
                f'<div class="tg-quote">{html.escape(parsed.evidence_hint())}</div>',
                unsafe_allow_html=True,
            )


def _render_form(db, parsed) -> None:
    st.markdown('<div class="tg-section-title">2 · 简单填写信息</div>', unsafe_allow_html=True)

    with st.form("report_form"):
        manual_phone = st.text_input(
            "对方联系方式（号码/微信，可选）",
            placeholder="+1 555 123 4567",
            help="不知道可以不填，至少填一个下面的名字或公司名就行",
        )

        columns = st.columns(2)
        contact_name = columns[0].text_input(
            "对方称呼 / 昵称（必填）",
            placeholder="例如：Mike",
        )
        company = columns[1].text_input(
            "公司名（如知道，可选）",
            placeholder="例如：ABC Trading Co.",
        )

        categories = st.multiselect(
            "问题类型（可多选，可选）",
            options=CATEGORY_KEYS,
            format_func=lambda key: CATEGORY_LABELS[key],
            default=["other"],
        )

        narrative = st.text_area(
            "简单写几句经过（必填，至少10个字）",
            height=120,
            placeholder="比如：收了我5000美金定金就失联了，发微信不回打电话拉黑。",
        )

        consent = st.checkbox(
            "我确认说的是真事，恶意举报要负责任的"
        )
        submitted = st.form_submit_button("提交举报", type="primary", use_container_width=True)

    if not submitted:
        return

    errors: list[str] = []
    manual_norm = normalize_phone(manual_phone) if manual_phone.strip() else None
    if manual_phone.strip() and not manual_norm:
        errors.append("号码格式不太对，没关系可以不填，填个名字就行。")

    phones: list[str] = []
    if manual_norm:
        phones.append(manual_norm)

    if not phones and not contact_name.strip() and not company.strip():
        errors.append("至少填一个对方名字或公司名，不然别人查不到。")
    if len(narrative.strip()) < 10:
        errors.append("经过写得太短啦，多写两句。")
    if not consent:
        errors.append("请勾选确认信息真实。")

    if errors:
        for error in errors:
            st.error(error)
        return

    # 管理员提交的直接通过，普通用户提交的进入待审核
    report_status = "approved" if is_admin() else "pending"

    report_id = db.add_report(
        phones=phones,
        contact_name=contact_name,
        company=company,
        country="",
        categories=categories if categories else ["other"],
        amount=None,
        currency="USD",
        incident_date=date.today(),
        narrative=narrative,
        evidence="",
        source="manual",
        chat_filename=None,
        chat_sha256=None,
        chat_message_count=None,
        credibility=55,
        status=report_status,
    )

    query = format_phone(phones[0]) if phones else (company.strip() or contact_name.strip())
    st.session_state["report_success"] = {
        "id": report_id,
        "query": query,
        "label": "、".join(CATEGORY_LABELS.get(key, key) for key in (categories if categories else ["other"])),
    }
    st.session_state["last_query"] = query
    st.session_state.pop("parsed_chat", None)
    st.session_state["prefill_phone"] = ""
    st.rerun()
