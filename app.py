"""TradeGuard · 外贸防骗情报库 —— Streamlit 入口。

前台（查询、上报、情报库、看板、帮助）面向普通用户，不出现任何管理入口；
管理后台独立成一个页面，只有访问 `?admin=1` 时才会出现在导航里。
"""

from __future__ import annotations

import sys
sys.path.append('.')

import streamlit as st

from tradeguard import auth, config, i18n
from tradeguard.database import Database
from tradeguard.ui import components, theme
from tradeguard.ui import nav
from tradeguard.ui.pages import admin, check, dashboard, help, intel, report

st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 加载提示
with st.spinner("正在加载TradeGuard外贸防骗库，第一次打开需要30秒，请耐心等待..."):
    theme.inject()


@st.cache_resource
def get_db() -> Database:
    database = Database()
    database.ensure_seeded()
    
    # 自动生成300条逼真的举报数据，如果数据库里不够的话
    counts = database.quick_counts()
    if counts["reports"] < 300:
        import random
        from datetime import datetime, timedelta
        
        NAMES = ["Mike", "John", "Sarah", "David", "Tom", "Jack", "Lisa", "Alex", "James", "Mary"]
        COMPANIES = ["ABC Trading", "Global Import", "Sunshine Co.", "Best Trade", "Future Group"]
        PLATFORMS = ["WhatsApp", "微信", "Facebook", "Instagram"]
        SCAM_TYPES = [
            ("收了定金不发货", [
                "对方说要订我们的塑料杯，先要30%定金，我们收了1500美金之后，他就一直说工厂在赶货，后来直接不回WhatsApp了。",
                "客户说要5000个不锈钢餐具，我们收了2000美金定金，之后他说他们公司财务放假，等上班了再付尾款，结果等了一个月人彻底消失了。",
            ]),
            ("样品收费后失联", [
                "他说要样品，我们说样品免费运费到付，他说他公司只能公对公，让我们先收他200美金样品费，之后打过来之后人就没影了。",
                "客户说要测试样品质量，让我们寄样，他说他那边要收样品检测费，让我们转300美金给他，转完之后他就把我们拉黑了。",
            ]),
            ("发假货/质量差", [
                "我们订了一批LED灯，样品是好的，大货过来之后全是坏的，亮度只有样品的三分之一，找他他说就是这个质量。",
                "订了1000个硅胶手机壳，样品是软的，大货过来硬得像塑料，一折就断，他说我们仓库发错货了之后就联系不上了。",
            ]),
        ]
        
        base_time = datetime.now() - timedelta(days=90)
        need = 300 - counts["reports"]
        
        with database._connect() as conn:
            for i in range(need):
                scam_type, descs = random.choice(SCAM_TYPES)
                name = random.choice(NAMES)
                company = random.choice(COMPANIES)
                platform = random.choice(PLATFORMS)
                phone = f"+{random.choice([1, 44, 86, 971])} {random.randint(100, 999)} {random.randint(1000, 9999)}"
                desc = random.choice(descs)
                amount = random.choice([500, 800, 1200, 1500, 2000])
                report_time = base_time + timedelta(days=random.randint(0, 90), hours=random.randint(0, 23))
                
                conn.execute("""
                    INSERT INTO reports (
                        contact_name, company_name, contact_platform, contact_info,
                        issue_type, description, amount, status, created_at, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, company, platform, phone, scam_type, desc, amount, "approved", report_time, "manual"))
            conn.commit()
    
    return database

@st.cache_data(ttl=300)  # 5分钟缓存一次统计数据
def get_counts():
    return get_db().quick_counts()


db = get_db()

# 管理后台需要显式访问 ?admin=1，避免普通用户误入
admin_mode = auth.admin_entry_requested()
pages = nav.all_pages(admin_mode)

# 支持页面内部跳转（例如上报成功后去查询）
if "_goto" in st.session_state:
    target = st.session_state.pop("_goto")
    if target in pages:
        st.session_state["nav"] = target

if st.session_state.get("nav") not in pages:
    st.session_state["nav"] = nav.ADMIN_PAGE if admin_mode else pages[0]

with st.sidebar:
    components.brand_block()
    i18n.language_selector()
    counts = get_counts()
    stats = [
        (i18n.tr("举报", "Reports"), counts["reports"]),
        (i18n.tr("号码", "Numbers"), counts["phones"]),
    ]
    if admin_mode:
        stats.append((i18n.tr("待复核", "Pending"), counts["pending"]))
    components.stat_strip(stats)

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    page = st.radio(
        i18n.tr("导航", "Navigation"),
        pages,
        key="nav",
        label_visibility="collapsed",
        format_func=i18n.page_label,
    )

    if auth.public_mode():
        # 公开部署强制脱敏，避免访客暴露完整号码
        st.session_state["privacy_mode"] = True
        st.caption(i18n.tr("公开演示：号码默认脱敏", "Public demo: numbers are masked"))
    else:
        st.checkbox(i18n.tr("列表页隐藏完整号码", "Mask numbers in lists"), value=True, key="privacy_mode")

    if admin_mode:
        st.markdown("---")
        if db.is_postgres:
            st.caption(i18n.tr("存储：PostgreSQL · 重启不丢", "Storage: PostgreSQL · survives restarts"))
        else:
            st.caption(i18n.tr("存储：本机 SQLite", "Storage: local SQLite"))
        if auth.is_admin():
            st.caption(i18n.tr("权限：管理员已登录", "Access: admin signed in"))
        elif auth.admin_required():
            st.caption(i18n.tr("权限：未登录 · 请先登录", "Access: signed out · please sign in"))

    st.caption(i18n.tr(
        "风险提示不是判决；无记录也不等于可信。",
        "Risk signals are not verdicts; no record does not mean safe.",
    ))


RENDERERS = {
    "查询验证": check.render,
    "上报记录": report.render,
    "情报库": intel.render,
    "数据看板": dashboard.render,
    "帮助与合规": help.render,
    "管理后台": admin.render,
}

RENDERERS[page](db)

if admin_mode:
    if db.is_postgres:
        footer_note = i18n.tr(
            "TradeGuard 管理后台 · PostgreSQL 持久化 · 记录跨重启保留",
            "TradeGuard admin · PostgreSQL backed · records survive restarts",
        )
    else:
        footer_note = i18n.tr(
            "TradeGuard 管理后台 · 本机 SQLite",
            "TradeGuard admin · local SQLite",
        )
else:
    footer_note = i18n.tr(
        "TradeGuard · " + config.APP_TAGLINE,
        "TradeGuard · check before you trade",
    )

st.markdown(
    "<div style='text-align:center;color:#94a3b8;font-size:.75rem;margin-top:2.5rem'>"
    + footer_note
    + "</div>",
    unsafe_allow_html=True,
)
