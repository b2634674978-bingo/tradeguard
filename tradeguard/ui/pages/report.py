"""上报记录页：上传截图 + 简单填写，普通用户进入待审核。"""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

from .. import components, theme
from ..nav import goto
from ... import i18n, storage
from ...auth import is_admin, public_mode
from ...config import MAX_IMAGES, MAX_IMAGE_BYTES
from ...constants import CATEGORIES, CATEGORY_KEYS, CATEGORY_LABELS
from ...normalize import format_phone, normalize_phone


def render(db) -> None:
    theme.page_header(
        i18n.tr("上传被骗经历", "Report a scam"),
        i18n.tr("把一次受骗，变成所有人的防线", "Turn one bad experience into protection for everyone"),
        i18n.tr(
            "上传 3 张聊天截图，简单填写信息。管理员审核通过后才会公开显示，避免未经核实的指控。",
            "Upload three chat screenshots and fill in a few fields. Reports become public only after admin review.",
        ),
    )

    if public_mode():
        if is_admin():
            st.caption(i18n.tr(
                "管理员提交的记录会直接公开；云端重启后数据可能重置，请及时备份。",
                "Admin reports are published immediately. Cloud data may reset on restart; back up regularly.",
            ))
        else:
            theme.note(
                i18n.tr(
                    "你提交的举报会进入<strong>待审核队列</strong>，管理员审核通过后才会公开显示。"
                    "请确保信息真实、有截图佐证，不要恶意诬告。",
                    "Your report enters a <strong>pending review queue</strong> and becomes public only after approval. "
                    "Make sure it is truthful and supported by screenshots. False reports may have legal consequences.",
                ),
                "info",
            )

    _render_success_block()

    with st.container(border=True):
        st.markdown(i18n.tr("#### 1 · 上传聊天截图（至少 3 张）", "#### 1 · Upload screenshots (at least 3)"))
        st.caption(i18n.tr(
            "💡 第一张上传对方的个人主页/资料截图（能看到号码、名字、公司），"
            "后两张上传关键聊天记录。截图只用于审核；只有你勾选「同意公开」并通过审核后，其他访客才能看到。",
            "💡 Upload the subject's profile screenshot first (showing number/name/company), then two key chat screenshots. "
            "Screenshots are used for review; other visitors see them only if you opt in and the report is approved.",
        ))
        uploaded_images = st.file_uploader(
            i18n.tr("上传聊天截图", "Upload screenshots"),
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="image_upload",
        )
        if uploaded_images:
            if len(uploaded_images) > MAX_IMAGES:
                st.error(i18n.tr(f"最多上传 {MAX_IMAGES} 张截图，请删掉一些。", f"Up to {MAX_IMAGES} screenshots; please remove some."))
            elif len(uploaded_images) >= 3:
                st.success(i18n.tr(f"已上传 {len(uploaded_images)} 张截图，符合要求。", f"{len(uploaded_images)} screenshots uploaded."))
            else:
                st.warning(i18n.tr(
                    f"已上传 {len(uploaded_images)} 张，还需要至少 {3 - len(uploaded_images)} 张才能提交。",
                    f"{len(uploaded_images)} uploaded; at least {3 - len(uploaded_images)} more required.",
                ))
            preview_cols = st.columns(min(3, len(uploaded_images)))
            for index, image in enumerate(uploaded_images[:6]):
                with preview_cols[index % len(preview_cols)]:
                    st.image(
                        image.getvalue(),
                        caption=i18n.tr(f"截图 {index + 1}", f"Screenshot {index + 1}"),
                        use_container_width=True,
                    )

    _render_form(db, uploaded_images)


def _render_success_block() -> None:
    success = st.session_state.get("report_success")
    if not success:
        return
    if success.get("pending"):
        st.success(
            i18n.tr(
                f"提交成功！举报已进入待审核队列。\n\n类别：{success['label']} · 对象：{success['query']}\n\n"
                "管理员审核通过后才会公开显示。",
                f"Submitted. Your report is pending review.\n\nType: {success['label']} · Subject: {success['query']}\n\n"
                "It becomes public only after admin approval.",
            )
        )
        cols = st.columns([1.5, 1.5, 3.5])
        if cols[0].button(i18n.tr("返回查询", "Back to search"), type="primary", use_container_width=True, key="success_back"):
            st.session_state.pop("report_success", None)
            goto("查询验证")
        if cols[1].button(i18n.tr("继续上报", "Report another"), use_container_width=True, key="success_continue"):
            st.session_state.pop("report_success", None)
            st.rerun()
        return

    st.success(i18n.tr(
        f"已收录：{success['label']} · {success['query']}。你可以在「查询验证」里立即查到它。",
        f"Published: {success['label']} · {success['query']}. You can find it in Search now.",
    ))
    cols = st.columns([1.5, 1.5, 3.5])
    if cols[0].button(i18n.tr("查看风险档案", "View risk profile"), type="primary", use_container_width=True, key="success_view"):
        st.session_state["last_query"] = success["query"]
        st.session_state["search_query"] = success["query"]
        goto("查询验证")
    if cols[1].button(i18n.tr("继续上报下一条", "Report another"), use_container_width=True, key="success_next"):
        st.session_state.pop("report_success", None)
        st.rerun()
    st.caption(i18n.tr(
        "提示：管理员提交的记录直接公开；你可以在「设置与合规」中复核、导出或删除记录。",
        "Admin reports are published immediately. You can review, export, or delete records in Settings.",
    ))


def _render_form(db, uploaded_images) -> None:
    st.markdown(
        '<div class="tg-section-title">'
        + i18n.tr("2 · 简单填写信息", "2 · Basic details")
        + "</div>",
        unsafe_allow_html=True,
    )

    with st.form("report_form"):
        columns = st.columns(2)
        contact_name = columns[0].text_input(
            i18n.tr("对方称呼 / 昵称（必填）", "Name / nickname (required)"),
            placeholder=i18n.tr("例如：Mike", "e.g. Mike"),
        )
        company = columns[1].text_input(
            i18n.tr("公司名（如知道，可选）", "Company (optional)"),
            placeholder=i18n.tr("例如：ABC Trading Co.", "e.g. ABC Trading Co."),
        )

        platform_options = ["WhatsApp", "微信", "Facebook", "Instagram", "其他"]
        contact_platform = st.selectbox(
            i18n.tr("对方联系平台（必填）", "Contact platform (required)"),
            options=platform_options,
        )
        manual_phone = st.text_input(
            i18n.tr("对方联系方式（必填）", "Contact info (required)"),
            placeholder="+1 555 123 4567",
        )

        categories = st.multiselect(
            i18n.tr("问题类型（可多选，可选）", "Issue type (optional, multi-select)"),
            options=CATEGORY_KEYS,
            format_func=i18n.category_label,
            default=["other"],
        )

        narrative = st.text_area(
            i18n.tr("简单写几句经过（必填，至少 10 个字）", "What happened? (required, at least 10 characters)"),
            height=120,
            placeholder=i18n.tr(
                "比如：收了我 5000 美金定金就失联了，发微信不回打电话拉黑。",
                "e.g. They took a USD 5,000 deposit, then disappeared and blocked me.",
            ),
        )

        consent = st.checkbox(i18n.tr("我确实说的是真实事件，恶意举报要承担法律责任", "I confirm this is a true account; false reports may have legal consequences."))
        publish_screenshots = st.checkbox(
            i18n.tr(
                "同意公开聊天截图作为证据（不勾选的话只有管理员能看到）",
                "Allow screenshots to be shown publicly as evidence (otherwise only admins can see them).",
            ),
            value=False,
        )
        submitted = st.form_submit_button(
            i18n.tr("提交举报", "Submit report"),
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    errors: list[str] = []
    if not manual_phone.strip():
        errors.append(i18n.tr("请填写对方联系方式。", "Please enter the contact info."))
    if not contact_name.strip():
        errors.append(i18n.tr("请填写对方称呼 / 昵称。", "Please enter the subject's name or nickname."))
    if len(narrative.strip()) < 10:
        errors.append(i18n.tr("经过写得太短，请至少写 10 个字。", "Please describe what happened in at least 10 characters."))
    if not consent:
        errors.append(i18n.tr("请勾选确认信息真实。", "Please confirm the information is true."))
    if not uploaded_images or len(uploaded_images) < 3:
        errors.append(i18n.tr(
            "必须至少上传 3 张截图（1 张对方资料 + 2 张聊天记录）。",
            "Upload at least three screenshots (one profile, two chat screenshots).",
        ))
    if uploaded_images and len(uploaded_images) > MAX_IMAGES:
        errors.append(i18n.tr(f"最多上传 {MAX_IMAGES} 张截图。", f"Upload at most {MAX_IMAGES} screenshots."))
    for image in uploaded_images or []:
        if image.size > MAX_IMAGE_BYTES:
            errors.append(i18n.tr(
                f"截图 {image.name} 超过 10 MB，请压缩后再上传。",
                f"Screenshot {image.name} exceeds 10 MB; please compress it first.",
            ))

    if errors:
        for error in errors:
            st.error(error)
        return

    compressed: list[dict] = []
    try:
        with st.spinner(i18n.tr("正在压缩截图…", "Compressing screenshots…")):
            for image in uploaded_images:
                data, mime = storage.compress_image(image.getvalue())
                compressed.append(
                    {
                        "data": data,
                        "mime": mime,
                        "is_public": bool(publish_screenshots),
                    }
                )
    except storage.ImageError as exc:
        st.error(i18n.tr(f"截图处理失败：{exc}", f"Could not process screenshot: {exc}"))
        return

    report_status = "approved" if is_admin() else "pending"
    report_id = db.add_report(
        phones=[manual_norm] if manual_norm else [],
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
        publish_screenshots=publish_screenshots,
    )
    db.add_report_images(report_id, compressed)

    query = format_phone(manual_norm) if manual_norm else (company.strip() or contact_name.strip())
    st.session_state["report_success"] = {
        "id": report_id,
        "query": query,
        "label": "、".join(i18n.category_label(key) for key in (categories if categories else ["other"])),
        "pending": report_status == "pending",
    }
    st.session_state["last_query"] = query
    st.session_state.pop("parsed_chat", None)
    st.session_state["prefill_phone"] = ""
    st.rerun()
