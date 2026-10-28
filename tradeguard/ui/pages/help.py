"""帮助与合规：面向普通用户的说明页。

这里只回答四个问题：怎么用、数据从哪来、发现错误怎么办、边界在哪。
不出现备份、导入、清空、存储引擎这类运维内容——那是管理后台的事。
"""

from __future__ import annotations

import streamlit as st

from .. import theme
from ... import i18n
from ...config import APP_TITLE, APP_TAGLINE, VERSION

COMPLIANCE_TEXT = """
**产品原则**

- 结果只是**风险提示**，不是事实认定、征信报告或法律判决；
- 单条未经证实的举报，最高只到「中风险」；
- 每条记录都提供申诉入口，任何人都可以对号入座提出更正；
- 数据最小化：只保存号码、问题类型、经过、金额与证据摘要，不保存完整聊天记录。

**使用边界（重要）**

- 不要把这个库里的内容公开发布、群发或做成“骗子名单”网站，除非已完成核实并咨询律师；
- 中国场景注意《个人信息保护法》的最小必要、告知同意、删除权，以及《民法典》名誉权 / 商誉；
- 海外场景注意 GDPR、当地诽谤法与数据跨境规则；
- 本工具不构成法律意见。
"""

COMPLIANCE_TEXT_EN = """
**Principles**

- Results are **risk signals**, not facts, credit reports, or legal judgments.
- A single uncorroborated report is capped at medium risk.
- Every record can be appealed, and anyone can request a correction.
- Data minimization: only numbers, issue types, narratives, amounts, and evidence summaries are stored.

**Boundaries**

- Do not publish these records as a public "scammer list" without verification and legal advice.
- China: PIPL, Civil Code reputation/privacy rules, and personal-information principles.
- Overseas: GDPR, local defamation law, and cross-border data rules.
- This tool is not legal advice.
"""


def render(db) -> None:
    counts = db.quick_counts()
    theme.page_header(
        i18n.tr("帮助与合规", "Help & rules"),
        i18n.tr("先查一查，再谈生意", "Check before you trade"),
        i18n.tr(
            f"这个库靠大家上报撑着，目前收录 {counts['reports']} 条举报、覆盖 {counts['phones']} 个号码。",
            f"{counts['reports']} reports across {counts['phones']} numbers, built entirely from user submissions.",
        ),
    )

    st.markdown(i18n.tr("#### 三步就能查完", "#### How to use it"))
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown(i18n.tr("**① 输入号码或公司名**", "**1. Enter a number or company**"))
            st.caption(i18n.tr(
                "WhatsApp 号码、公司名、联系人姓名都行。带上国家码更准。",
                "A WhatsApp number, company name, or contact name. Include the country code for best results.",
            ))
    with col2:
        with st.container(border=True):
            st.markdown(i18n.tr("**② 看风险等级和依据**", "**2. Read the risk level**"))
            st.caption(i18n.tr(
                "评分会列出每一项依据：举报次数、问题类型、时效、证据、金额。",
                "The score lists every basis: report count, issue type, recency, evidence, amount.",
            ))
    with col3:
        with st.container(border=True):
            st.markdown(i18n.tr("**③ 没记录也要留心**", "**3. No record is not safety**"))
            st.caption(i18n.tr(
                "库里没有记录，只说明没人报过，不代表对方可信。小额试单仍然必要。",
                "No record only means nobody has reported yet. Start with a small trial order anyway.",
            ))

    st.divider()

    left, right = st.columns([1, 1])
    with left:
        with st.container(border=True):
            st.markdown(i18n.tr("#### 数据从哪来", "#### Where the data comes from"))
            st.markdown(i18n.tr(
                "举报由用户主动提交，**经人工审核后**才会公开。"
                "未经核实的单条举报不会直接给对方定性，评分上限为中风险。",
                "Reports are submitted by users and published **only after review**. "
                "A single unverified report is capped at medium risk.",
            ))
            st.caption(i18n.tr(
                "截图属于证据材料，仅在举报人勾选「允许公开截图」且审核通过后展示；"
                "涉及个人隐私的部分会做模糊处理。",
                "Screenshots are evidence. They appear only if the reporter opted in and the report passed review.",
            ))

        with st.container(border=True):
            st.markdown(i18n.tr("#### 号码怎么显示", "#### How numbers are shown"))
            st.caption(i18n.tr(
                "列表页默认脱敏（如 +1 555***4477），需要完整号码请展开单条记录。"
                "查询行为不会通知被查询方。",
                "Lists are masked by default (e.g. +1 555***4477); expand a record for the full number. "
                "The subject is never notified.",
            ))

    with right:
        with st.container(border=True):
            st.markdown(i18n.tr("#### 我是当事人，信息有误", "#### I am the subject"))
            st.markdown(i18n.tr(
                "在查询结果里展开对应记录，点「我是当事人 / 信息有误」即可提交申诉，"
                "说明哪条信息不实、你与对方的关系、可提供的证明。",
                "Open the record in your search result and use “I am the subject” to file an appeal: "
                "say what is inaccurate, your relationship, and any proof.",
            ))
            st.caption(i18n.tr(
                "申诉由管理员逐条复核。原型阶段不会自动删除任何记录。",
                "Appeals are reviewed one by one by an admin. Nothing is deleted automatically at this stage.",
            ))

        with st.container(border=True):
            st.markdown(i18n.tr("#### 我要上报", "#### Reporting"))
            st.caption(i18n.tr(
                "去「上报记录」上传聊天截图、填写经过。请只提交真实发生的事，"
                "恶意诬告同样可能承担法律责任。",
                "Use “Report” to upload screenshots and describe what happened. Submit only real incidents — "
                "false accusations can carry legal liability too.",
            ))

    st.markdown(i18n.tr("#### 合规边界", "#### Compliance boundaries"))
    st.markdown(COMPLIANCE_TEXT_EN if i18n.lang() == "en" else COMPLIANCE_TEXT)

    theme.divider()
    st.caption(
        f"{APP_TITLE} · v{VERSION} · {i18n.tr(APP_TAGLINE, 'check before you trade')}"
    )
    st.markdown(
        "<div style='margin-top:.6rem;font-size:.75rem'>"
        f"<a href='?admin=1' target='_self' style='color:#94a3b8;text-decoration:none'>"
        + i18n.tr("管理员入口", "Admin entry")
        + "</a></div>",
        unsafe_allow_html=True,
    )
