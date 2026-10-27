"""全站视觉：深色侧栏 + 浅色内容区，风险色只用于风险提示。"""

from __future__ import annotations

import html

import streamlit as st

from ..config import APP_TAGLINE, APP_TITLE

CSS = """
<style>
:root {
  --tg-ink: #0f172a;
  --tg-muted: #64748b;
  --tg-line: #e2e8f0;
  --tg-bg: #f6f8fb;
  --tg-teal: #0f766e;
  --tg-teal-soft: #ccfbf1;
  --tg-red: #dc2626;
  --tg-amber: #d97706;
}

html, body, [class*="css"] {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

.stApp {
  background:
    radial-gradient(900px 380px at 85% -5%, rgba(15, 118, 110, 0.09), transparent 60%),
    var(--tg-bg);
}

.block-container { padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1180px; }

header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }

/* ---------------------------------------------------------------- 侧栏 */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0b1f2a 0%, #0d2b33 60%, #0b3b3b 100%);
  border-right: 1px solid rgba(148, 163, 184, 0.16);
}
section[data-testid="stSidebar"] * { color: #dbe7e6; }
section[data-testid="stSidebar"] .tg-brand-name { color: #ffffff !important; }
section[data-testid="stSidebar"] .tg-brand-sub { color: #7dd3c7 !important; }
section[data-testid="stSidebar"] .stRadio > div { gap: 0.15rem; }
section[data-testid="stSidebar"] .stRadio label {
  padding: 0.35rem 0.45rem;
  border-radius: 10px;
}
section[data-testid="stSidebar"] .stRadio label:hover { background: rgba(148, 163, 184, 0.12); }
section[data-testid="stSidebar"] .stCheckbox label p { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(148, 163, 184, 0.2); }
section[data-testid="stSidebar"] a { color: #5eead4 !important; }

.tg-brand { display: flex; gap: 0.75rem; align-items: center; padding: 0.2rem 0 1.1rem; }
.tg-logo {
  width: 44px; height: 44px; border-radius: 14px; display: flex; align-items: center;
  justify-content: center; font-size: 22px;
  background: linear-gradient(135deg, #14b8a6, #0f766e);
  box-shadow: 0 8px 24px rgba(20, 184, 166, 0.32);
}
.tg-brand-name { font-size: 1.15rem; font-weight: 800; letter-spacing: 0.01em; }
.tg-brand-sub { font-size: 0.72rem; letter-spacing: 0.14em; }

.tg-side-stat { display: flex; gap: 0.5rem; margin: 0.2rem 0 0.8rem; }
.tg-side-stat div {
  flex: 1; background: rgba(148, 163, 184, 0.1); border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px; padding: 0.55rem 0.6rem; text-align: center;
}
.tg-side-stat b { display: block; font-size: 1.1rem; color: #ffffff; }
.tg-side-stat span { font-size: 0.68rem; color: #9ab8b4; }

/* ---------------------------------------------------------------- 通用 */
.tg-hero {
  position: relative;
  background:
    radial-gradient(900px 320px at 8% -30%, rgba(45, 212, 191, 0.45), transparent 55%),
    radial-gradient(700px 260px at 100% 120%, rgba(20, 184, 166, 0.22), transparent 60%),
    linear-gradient(135deg, #0b1f2a 0%, #0f3a41 58%, #0f766e 100%);
  border-radius: 22px;
  padding: 2.1rem 2.2rem 1.9rem;
  color: #f8fafc;
  box-shadow: 0 20px 45px -28px rgba(8, 47, 73, 0.65);
  margin-bottom: 1.4rem;
}
.tg-hero.compact { padding: 1.45rem 1.7rem; border-radius: 18px; }
.tg-kicker {
  font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase;
  color: #5eead4; font-weight: 700; margin-bottom: 0.55rem;
}
.tg-hero h1 { margin: 0 0 0.5rem; font-size: 2.05rem; line-height: 1.18; letter-spacing: -0.02em; }
.tg-hero.compact h1 { font-size: 1.45rem; }
.tg-hero p { margin: 0; color: #b8ddd7; font-size: 0.98rem; line-height: 1.65; max-width: 760px; }
.tg-hero .tg-hero-tag {
  display: inline-block; margin-top: 1rem; font-size: 0.75rem; color: #99f6e4;
  border: 1px solid rgba(94, 234, 212, 0.35); border-radius: 999px; padding: 0.28rem 0.7rem;
}

.tg-card {
  background: #ffffff;
  border: 1px solid var(--tg-line);
  border-radius: 18px;
  padding: 1.2rem 1.35rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  margin-bottom: 0.9rem;
}
.tg-row-between { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
.tg-name { font-size: 1.12rem; font-weight: 750; color: var(--tg-ink); line-height: 1.4; }
.tg-sub { color: var(--tg-muted); font-size: 0.83rem; line-height: 1.6; }
.tg-phone { color: #0f766e; font-weight: 650; font-size: 0.95rem; letter-spacing: 0.01em; margin-top: 0.25rem; }
.tg-right { text-align: right; flex-shrink: 0; }
.tg-match { color: #0f766e; font-size: 0.76rem; margin-top: 0.4rem; }

.tg-risk {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0.3rem 0.68rem; border-radius: 999px; font-size: 0.8rem; font-weight: 750;
  white-space: nowrap;
}
.tg-risk.high { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.tg-risk.medium { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.tg-risk.low { background: #fefce8; color: #a16207; border: 1px solid #fef08a; }
.tg-risk.watch { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }
.tg-risk.unknown { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }

.tg-pills { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.85rem; }
.tg-pill {
  font-size: 0.75rem; color: #334155; background: #f1f5f9;
  border: 1px solid #e2e8f0; border-radius: 999px; padding: 0.22rem 0.62rem;
}
.tg-pill b { color: #0f766e; }

.tg-reasons { margin-top: 0.75rem; color: #475569; font-size: 0.8rem; line-height: 1.7; }
.tg-reasons span { color: #0f766e; }

.tg-quote {
  margin: 0.55rem 0 0.2rem;
  padding: 0.65rem 0.8rem;
  border-left: 3px solid #14b8a6;
  background: #f0fdfa;
  border-radius: 0 10px 10px 0;
  color: #134e4a;
  font-size: 0.85rem;
  line-height: 1.65;
  white-space: pre-wrap;
}

.tg-tag {
  display: inline-block; margin-left: 0.45rem; padding: 0.05rem 0.4rem;
  border-radius: 6px; background: #fef3c7; color: #92400e;
  font-size: 0.66rem; font-weight: 700; vertical-align: middle;
}
.tg-mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

.tg-empty {
  background: #ffffff; border: 1px dashed #cbd5e1; border-radius: 18px;
  padding: 1.6rem 1.8rem; text-align: center; margin: 1rem 0;
}
.tg-empty .tg-empty-icon { font-size: 2rem; }
.tg-empty h3 { margin: 0.35rem 0 0.3rem; color: #0f172a; }
.tg-empty p { color: #64748b; font-size: 0.9rem; margin: 0.2rem 0; line-height: 1.7; }

.tg-note {
  background: #f0fdfa; border: 1px solid #99f6e4; color: #115e59;
  border-radius: 12px; padding: 0.75rem 0.95rem; font-size: 0.84rem; line-height: 1.65;
}
.tg-warn {
  background: #fffbeb; border: 1px solid #fde68a; color: #92400e;
  border-radius: 12px; padding: 0.75rem 0.95rem; font-size: 0.84rem; line-height: 1.65;
}
.tg-danger {
  background: #fef2f2; border: 1px solid #fecaca; color: #991b1b;
  border-radius: 12px; padding: 0.75rem 0.95rem; font-size: 0.84rem; line-height: 1.65;
}

.tg-section-title {
  font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase;
  color: #0f766e; font-weight: 750; margin: 1.4rem 0 0.55rem;
}
.tg-divider { height: 1px; background: var(--tg-line); margin: 1.1rem 0; }

div[data-testid="stMetric"] {
  background: #ffffff; border: 1px solid var(--tg-line); border-radius: 16px;
  padding: 0.85rem 1rem; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}
div[data-testid="stMetric"] label p { color: #64748b !important; font-size: 0.78rem; }
div[data-testid="stMetricValue"] { color: #0f172a; }

.stButton > button, .stFormSubmitButton > button {
  border-radius: 10px;
  font-weight: 650;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: linear-gradient(135deg, #0f766e, #0d9488);
  border: 1px solid #0f766e;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #115e59, #0f766e);
  border-color: #115e59;
}
.stTextInput input, .stTextArea textarea { border-radius: 10px; }
.stSelectbox div[data-baseweb="select"] > div { border-radius: 10px; }
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(kicker: str, title: str, subtitle: str, *, compact: bool = False, tag: str = "") -> None:
    css_class = "tg-hero compact" if compact else "tg-hero"
    tag_html = f'<div class="tg-hero-tag">{html.escape(tag)}</div>' if tag else ""
    st.markdown(
        f"""
        <div class="{css_class}">
          <div class="tg-kicker">{html.escape(kicker)}</div>
          <h1>{html.escape(title)}</h1>
          <p>{html.escape(subtitle)}</p>
          {tag_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(kicker: str, title: str, subtitle: str) -> None:
    hero(kicker, title, subtitle, compact=True)


def section_title(text: str) -> None:
    st.markdown(f'<div class="tg-section-title">{html.escape(text)}</div>', unsafe_allow_html=True)


def note(text: str, kind: str = "note") -> None:
    css = {"note": "tg-note", "warn": "tg-warn", "danger": "tg-danger"}.get(kind, "tg-note")
    st.markdown(f'<div class="{css}">{text}</div>', unsafe_allow_html=True)


def divider() -> None:
    st.markdown('<div class="tg-divider"></div>', unsafe_allow_html=True)
