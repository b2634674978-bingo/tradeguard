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
        "REPORT · 上传被骗经历",
        "把一次受骗，变成所有人的防线",
        "上传 WhatsApp 导出的聊天记录，系统自动提取对方号码、时间线和风险信号；"
        "补充经过后入库。只保存必要证据，不保存完整聊天原文。",
    )

    if public_mode() and not is_admin():
        theme.note(
            "当前是 <strong>公开只读演示版</strong>，暂不开放游客上报，避免未经审核的指控进入公开库。"
            "管理员可在左侧登录后上报；普通访客可以先查询演示数据。",
            "warn",
        )
        st.caption("公开演示版只应使用虚构数据；真实举报请使用本地完整版或私有部署。")
        return

    if public_mode():
        st.caption("云端临时存储：应用重启/重新部署后，本页新增的数据可能丢失。请及时在设置中备份。")

    _render_success_block()

    with st.container(border=True):
        st.markdown("#### 1 · 上传或粘贴聊天记录")
        st.caption("WhatsApp：打开聊天 → 更多 → 导出聊天 → 不含媒体，得到 .txt 文件。文件只在本机解析。")
        uploaded = st.file_uploader("聊天记录文件（.txt）", type=["txt", "log"], key="chat_upload")
        pasted = st.text_area(
            "没有文件？把关键聊天内容粘贴到这里",
            height=150,
            placeholder="[2026/10/01, 10:23:45] Mike: Sample is for testing, you pay shipping first...",
            key="chat_paste",
        )
        cols = st.columns([1.3, 1.3, 3.4])
        parse_clicked = cols[0].button("解析聊天记录", type="primary", use_container_width=True)
        clear_clicked = cols[1].button("清空解析结果", use_container_width=True)

        if clear_clicked:
            st.session_state.pop("parsed_chat", None)
            st.rerun()

        if parse_clicked:
            if uploaded is not None and uploaded.size > MAX_UPLOAD_BYTES:
                st.error("文件超过 8 MB，请截取关键部分后再上传。")
            elif uploaded is not None:
                data = uploaded.getvalue()
                with st.spinner("正在解析聊天记录…"):
                    st.session_state["parsed_chat"] = parse_export(data, uploaded.name)
            elif pasted.strip():
                if len(pasted) > 2_000_000:
                    st.error("粘贴内容过长，请只保留关键部分。")
                else:
                    with st.spinner("正在解析粘贴内容…"):
                        st.session_state["parsed_chat"] = parse_export(pasted, "粘贴内容.txt")
            else:
                st.warning("请先上传 .txt 文件，或粘贴一段聊天内容。")

    parsed = st.session_state.get("parsed_chat")
    if parsed:
        _render_parsed(parsed)

    _render_form(db, parsed)


def _render_success_block() -> None:
    success = st.session_state.get("report_success")
    if not success:
        return
    st.success(f"已收录：{success['label']} · {success['query']}。你可以在「查询验证」里立即查到它。")
    cols = st.columns([1.5, 1.5, 3.5])
    if cols[0].button("查看风险档案", type="primary", use_container_width=True):
        st.session_state["last_query"] = success["query"]
        st.session_state["search_query"] = success["query"]
        goto("查询验证")
    if cols[1].button("继续上报下一条", use_container_width=True):
        st.session_state.pop("report_success", None)
        st.session_state.pop("parsed_chat", None)
        st.rerun()
    st.caption("提示：原型默认提交即收录；你可以在「设置与合规」中复核、导出或删除记录。")


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
    st.markdown('<div class="tg-section-title">2 · 确认真实信息</div>', unsafe_allow_html=True)

    detected = parsed.phones if parsed else []
    labels = [f"{phone.display}（出现 {phone.mentions} 次）" for phone in detected]
    default_categories = parsed.primary_categories() if parsed else ["fake_inquiry"]
    default_name = parsed.top_sender if parsed else ""
    default_evidence = parsed.evidence_hint() if parsed else ""
    default_date = (
        min(parsed.last_ts.date(), date.today()) if parsed and parsed.last_ts else date.today()
    )
    default_company = parsed.company_hints[0] if parsed and parsed.company_hints else ""

    with st.form("report_form"):
        if detected:
            selected_label = st.selectbox("对方主要号码（从聊天中识别）", labels, index=0)
            selected_phone = detected[labels.index(selected_label)].norm
            extra_labels = st.multiselect(
                "同一人的其他号码（可选）",
                [label for label in labels if label != selected_label],
                help="骗子经常用多个号加人；把能确认是同一个人的号码都选上。",
            )
        else:
            selected_phone = ""
            extra_labels = []

        manual_phone = st.text_input(
            "手动输入 / 修正号码（优先于上面的选择）",
            value=st.session_state.get("prefill_phone", ""),
            placeholder="+86 138 0013 8000",
            help="支持 +、00、空格、括号等写法；至少 8 位数字。",
        )

        columns = st.columns(2)
        contact_name = columns[0].text_input(
            "对方称呼 / 昵称",
            value=default_name,
            placeholder="例如：Mike R.",
            help="聊天记录里出现的发送者名字；如果识别错了请手动改。",
        )
        company = columns[1].text_input(
            "公司名（如知道）",
            value=default_company,
            placeholder="例如：NovaPeak Supplements LLC",
        )
        country = columns[0].text_input("国家 / 地区", placeholder="例如：美国、United Kingdom")
        categories = columns[1].multiselect(
            "问题类型（可多选）",
            options=CATEGORY_KEYS,
            format_func=lambda key: CATEGORY_LABELS[key],
            default=[key for key in default_categories if key in CATEGORIES],
        )

        amount_columns = st.columns([1.2, 1, 1.4])
        amount = amount_columns[0].number_input(
            "涉及金额（可选）", min_value=0.0, step=100.0, value=0.0
        )
        currency = amount_columns[1].selectbox("币种", CURRENCIES, index=0)
        incident_date = amount_columns[2].date_input(
            "发生时间", value=default_date, max_value=date.today()
        )

        narrative = st.text_area(
            "事情经过（必填，至少 10 个字）",
            height=140,
            placeholder="什么时候、怎么认识的、对方承诺了什么、你损失了什么、对方后来怎么处理……",
        )
        evidence = st.text_area(
            "证据摘要（可选）",
            value=default_evidence,
            height=100,
            placeholder="粘贴 1–3 句最关键的聊天原话；不要粘贴完整聊天记录。",
        )

        consent = st.checkbox(
            "我确认以上信息基于真实经历，并愿意在必要时提供聊天记录原件。"
            "我理解恶意举报可能承担法律责任。"
        )
        submitted = st.form_submit_button("提交并入库", type="primary", use_container_width=True)

    if not submitted:
        return

    errors: list[str] = []
    manual_norm = normalize_phone(manual_phone) if manual_phone.strip() else None
    if manual_phone.strip() and not manual_norm:
        errors.append("手动输入的号码不合法，请输入 8–15 位有效号码。")

    phones: list[str] = []
    if manual_norm:
        phones.append(manual_norm)
    elif selected_phone:
        phones.append(selected_phone)
    for label in extra_labels:
        phones.append(detected[labels.index(label)].norm)
    phones = list(dict.fromkeys(phones))

    if not phones and not contact_name.strip() and not company.strip():
        errors.append("至少填写一个号码、公司名或联系人，否则这条记录无法被查到。")
    if not categories:
        errors.append("请至少选择一种问题类型。")
    if len(narrative.strip()) < 10:
        errors.append("事情经过太短，请至少写 10 个字。")
    if not consent:
        errors.append("请勾选真实性确认后再提交。")

    if errors:
        for error in errors:
            st.error(error)
        return

    report_id = db.add_report(
        phones=phones,
        contact_name=contact_name,
        company=company,
        country=country,
        categories=categories,
        amount=amount or None,
        currency=currency,
        incident_date=incident_date,
        narrative=narrative,
        evidence=evidence,
        source="chat_import" if parsed else "manual",
        chat_filename=parsed.filename if parsed else None,
        chat_sha256=parsed.sha256 if parsed else None,
        chat_message_count=parsed.message_count if parsed else None,
        credibility=70 if parsed else 55,
    )

    query = format_phone(phones[0]) if phones else (company.strip() or contact_name.strip())
    st.session_state["report_success"] = {
        "id": report_id,
        "query": query,
        "label": "、".join(CATEGORY_LABELS[key] for key in categories),
    }
    st.session_state["last_query"] = query
    st.session_state.pop("parsed_chat", None)
    st.session_state["prefill_phone"] = ""
    st.rerun()
