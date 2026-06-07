"""Preferência de aparência (sistema / claro / escuro) via CSS injetado."""
from __future__ import annotations

import json

import streamlit as st

THEME_OPTIONS = ("system", "light", "dark")

THEME_LABELS = {
    "system": "Sistema",
    "light": "Claro",
    "dark": "Escuro",
}

THEME_ICONS = {
    "system": "🌓",
    "light": "☀️",
    "dark": "🌙",
}

THEME_COLORS = {
    "light": {
        "primary": "#458588",
        "background": "#FFFFFF",
        "secondary": "#F0F2F6",
        "text": "#31333F",
    },
    "dark": {
        "primary": "#458588",
        "background": "#1d2021",
        "secondary": "#2d3436",
        "text": "#e8edf2",
    },
}

THEME_TOKENS = {
    "light": {
        "text_muted": "#5c6370",
        "text_subtle": "#6b7280",
        "border": "rgba(49, 51, 63, 0.22)",
        "border_strong": "rgba(49, 51, 63, 0.38)",
        "student_role_text": "#3d5a72",
        "student_role_bg": "rgba(61, 90, 114, 0.12)",
        "student_role_border": "rgba(61, 90, 114, 0.35)",
        "danger": "#c75555",
        "danger_hover": "#b91c1c",
        "danger_bg_hover": "rgba(199, 85, 85, 0.12)",
        "segment_selected_text": "#ffffff",
        "segment_bg": "#e8eaed",
        "chrome_btn_bg": "#FFFFFF",
        "chrome_btn_icon": "#458588",
        "chrome_btn_border": "rgba(49, 51, 63, 0.48)",
    },
    "dark": {
        "text_muted": "#b8c5d0",
        "text_subtle": "#9aa8b4",
        "border": "rgba(232, 237, 242, 0.18)",
        "border_strong": "rgba(232, 237, 242, 0.28)",
        "student_role_text": "#a8c4e0",
        "student_role_bg": "rgba(152, 184, 220, 0.18)",
        "student_role_border": "rgba(152, 184, 220, 0.42)",
        "danger": "#f08080",
        "danger_hover": "#ffb3b3",
        "danger_bg_hover": "rgba(240, 128, 128, 0.16)",
        "segment_selected_text": "#ffffff",
        "segment_bg": "#3a3f44",
        "chrome_btn_bg": "#2d3436",
        "chrome_btn_icon": "#e8edf2",
        "chrome_btn_border": "rgba(232, 237, 242, 0.35)",
    },
}

ALERT_TOKENS = {
    "light": {
        "success_bg": "rgba(39, 174, 96, 0.12)",
        "success_text": "#1a5c38",
        "success_border": "rgba(39, 174, 96, 0.4)",
        "warning_bg": "rgba(243, 156, 18, 0.14)",
        "warning_text": "#8a5a00",
        "warning_border": "rgba(243, 156, 18, 0.45)",
        "error_bg": "rgba(231, 76, 60, 0.12)",
        "error_text": "#8b2e24",
        "error_border": "rgba(231, 76, 60, 0.42)",
        "info_bg": "rgba(52, 152, 219, 0.12)",
        "info_text": "#1a5276",
        "info_border": "rgba(52, 152, 219, 0.4)",
    },
    "dark": {
        "success_bg": "rgba(88, 214, 141, 0.16)",
        "success_text": "#b8f0d0",
        "success_border": "rgba(88, 214, 141, 0.38)",
        "warning_bg": "rgba(245, 176, 65, 0.18)",
        "warning_text": "#ffe0a8",
        "warning_border": "rgba(245, 176, 65, 0.42)",
        "error_bg": "rgba(240, 128, 128, 0.18)",
        "error_text": "#ffd0d0",
        "error_border": "rgba(240, 128, 128, 0.42)",
        "info_bg": "rgba(91, 168, 160, 0.2)",
        "info_text": "#c5e8e4",
        "info_border": "rgba(91, 168, 160, 0.42)",
    },
}

CHART_PALETTES = {
    "light": {
        "figure": "#FFFFFF",
        "text": "#31333F",
        "grid": "rgba(49, 51, 63, 0.2)",
        "correct": "#27ae60",
        "wrong": "#c75555",
        "bar": "#458588",
        "performance": "#d68910",
    },
    "dark": {
        "figure": "#1d2021",
        "text": "#e8edf2",
        "grid": "rgba(232, 237, 242, 0.2)",
        "correct": "#58d68d",
        "wrong": "#f08080",
        "bar": "#5ba8a0",
        "performance": "#f5b041",
    },
}

CLASSIFICATION_BADGE_COLORS = {
    "light": {"A": "#27ae60", "PA": "#d68910", "NA": "#c75555"},
    "dark": {"A": "#3dd68c", "PA": "#f5b041", "NA": "#f08080"},
}

LOGIN_THEME_TOKENS = {
    "light": {
        "panel_right": "#FFFFFF",
        "form_title": "#31333F",
        "form_sub": "#5c6370",
        "form_muted": "#6b7280",
        "or_line": "rgba(49, 51, 63, 0.3)",
        "label": "#5c6370",
        "input_bg": "#FFFFFF",
        "input_border": "rgba(49, 51, 63, 0.35)",
        "input_text": "#31333F",
        "google_border": "rgba(49, 51, 63, 0.3)",
        "google_bg": "#FFFFFF",
        "secondary_btn_bg": "#F0F2F6",
        "secondary_btn_text": "#31333F",
    },
    "dark": {
        "panel_right": "#1d2021",
        "form_title": "#c8d6e0",
        "form_sub": "#7f8c9a",
        "form_muted": "#6b7c93",
        "or_line": "#3d4f66",
        "label": "#aabbc8",
        "input_bg": "#2d3436",
        "input_border": "#3d4f66",
        "input_text": "#e8edf2",
        "google_border": "#3d4f66",
        "google_bg": "#ffffff",
        "secondary_btn_bg": "#2d3436",
        "secondary_btn_text": "#c5d0dc",
    },
}


def _current_theme() -> str:
    """Somente leitura — não alterar ui_theme após o widget ser criado."""
    choice = st.session_state.get("ui_theme", "system")
    if choice not in THEME_OPTIONS:
        return "system"
    return choice


def get_resolved_theme() -> str:
    """Tema efetivo para código Python (gráficos, badges). Sistema → claro."""
    choice = _current_theme()
    if choice in THEME_COLORS:
        return choice
    return "light"


def chart_palette() -> dict[str, str]:
    return CHART_PALETTES[get_resolved_theme()]


def classification_badge_colors() -> dict[str, str]:
    return CLASSIFICATION_BADGE_COLORS[get_resolved_theme()]


def style_matplotlib_figure(fig, ax, *, grid: bool = True) -> None:
    """Aplica cores do tema atual a uma figura Matplotlib."""
    pal = chart_palette()
    fig.patch.set_facecolor(pal["figure"])
    ax.set_facecolor(pal["figure"])
    ax.tick_params(colors=pal["text"])
    ax.xaxis.label.set_color(pal["text"])
    ax.yaxis.label.set_color(pal["text"])
    title = ax.get_title()
    if title:
        ax.set_title(title, color=pal["text"])
    for spine in ax.spines.values():
        spine.set_color(pal["grid"])
    if grid:
        ax.grid(True, alpha=0.25, color=pal["grid"])


def _css_variables(theme: str) -> str:
    colors = THEME_COLORS[theme]
    tokens = THEME_TOKENS[theme]
    login = LOGIN_THEME_TOKENS[theme]
    alerts = ALERT_TOKENS[theme]
    return f"""
    color-scheme: {theme};
    --primary-color: {colors["primary"]};
    --background-color: {colors["background"]};
    --secondary-background-color: {colors["secondary"]};
    --text-color: {colors["text"]};
    --kahoot-text-muted: {tokens["text_muted"]};
    --kahoot-text-subtle: {tokens["text_subtle"]};
    --kahoot-border: {tokens["border"]};
    --kahoot-border-strong: {tokens["border_strong"]};
    --kahoot-student-role-text: {tokens["student_role_text"]};
    --kahoot-student-role-bg: {tokens["student_role_bg"]};
    --kahoot-student-role-border: {tokens["student_role_border"]};
    --kahoot-danger: {tokens["danger"]};
    --kahoot-danger-hover: {tokens["danger_hover"]};
    --kahoot-danger-bg-hover: {tokens["danger_bg_hover"]};
    --kahoot-segment-bg: {tokens["segment_bg"]};
    --kahoot-segment-selected-text: {tokens["segment_selected_text"]};
    --kahoot-chrome-btn-bg: {tokens["chrome_btn_bg"]};
    --kahoot-chrome-btn-icon: {tokens["chrome_btn_icon"]};
    --kahoot-chrome-btn-border: {tokens["chrome_btn_border"]};
    --kahoot-login-panel-right: {login["panel_right"]};
    --kahoot-login-form-title: {login["form_title"]};
    --kahoot-login-form-sub: {login["form_sub"]};
    --kahoot-login-form-muted: {login["form_muted"]};
    --kahoot-login-or-line: {login["or_line"]};
    --kahoot-login-label: {login["label"]};
    --kahoot-login-input-bg: {login["input_bg"]};
    --kahoot-login-input-border: {login["input_border"]};
    --kahoot-login-input-text: {login["input_text"]};
    --kahoot-login-google-border: {login["google_border"]};
    --kahoot-login-google-bg: {login["google_bg"]};
    --kahoot-login-secondary-btn-bg: {login["secondary_btn_bg"]};
    --kahoot-login-secondary-btn-text: {login["secondary_btn_text"]};
    --kahoot-alert-success-bg: {alerts["success_bg"]};
    --kahoot-alert-success-text: {alerts["success_text"]};
    --kahoot-alert-success-border: {alerts["success_border"]};
    --kahoot-alert-warning-bg: {alerts["warning_bg"]};
    --kahoot-alert-warning-text: {alerts["warning_text"]};
    --kahoot-alert-warning-border: {alerts["warning_border"]};
    --kahoot-alert-error-bg: {alerts["error_bg"]};
    --kahoot-alert-error-text: {alerts["error_text"]};
    --kahoot-alert-error-border: {alerts["error_border"]};
    --kahoot-alert-info-bg: {alerts["info_bg"]};
    --kahoot-alert-info-text: {alerts["info_text"]};
    --kahoot-alert-info-border: {alerts["info_border"]};
    """


def _root_block(theme: str) -> str:
    return f":root {{{_css_variables(theme)}}}"


def _shared_component_css() -> str:
    return """
.stApp,
[data-testid="stAppViewContainer"] {
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
}
section[data-testid="stSidebar"] > div {
    background-color: var(--secondary-background-color) !important;
    color: var(--text-color) !important;
    border-right: 1px solid var(--kahoot-border-strong) !important;
}
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] button,
button[data-testid="collapsedControl"] {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 2.125rem !important;
    height: 2.125rem !important;
    min-width: 2.125rem !important;
    min-height: 2.125rem !important;
    padding: 0 !important;
    margin: 0.35rem 0.45rem !important;
    color: var(--kahoot-chrome-btn-icon) !important;
    background: var(--kahoot-chrome-btn-bg) !important;
    border: 1.5px solid var(--kahoot-chrome-btn-border) !important;
    border-radius: 0.5rem !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1) !important;
    opacity: 1 !important;
    visibility: visible !important;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
}
[data-testid="stSidebarCollapseButton"]:hover,
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stExpandSidebarButton"]:hover,
[data-testid="stExpandSidebarButton"] button:hover,
button[data-testid="collapsedControl"]:hover {
    background: color-mix(in srgb, var(--primary-color) 12%, var(--kahoot-chrome-btn-bg)) !important;
    border-color: var(--primary-color) !important;
    color: var(--primary-color) !important;
}
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapseButton"] span,
[data-testid="stSidebarCollapseButton"] path,
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] *,
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stExpandSidebarButton"] span,
[data-testid="stExpandSidebarButton"] path,
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
[data-testid="stExpandSidebarButton"] *,
button[data-testid="collapsedControl"] svg,
button[data-testid="collapsedControl"] span,
button[data-testid="collapsedControl"] path,
button[data-testid="collapsedControl"] * {
    color: var(--kahoot-chrome-btn-icon) !important;
    fill: var(--kahoot-chrome-btn-icon) !important;
    stroke: var(--kahoot-chrome-btn-icon) !important;
    -webkit-text-fill-color: var(--kahoot-chrome-btn-icon) !important;
}
[data-testid="stSidebarCollapseButton"]:hover *,
[data-testid="stExpandSidebarButton"]:hover *,
button[data-testid="collapsedControl"]:hover * {
    color: var(--primary-color) !important;
    fill: var(--primary-color) !important;
    stroke: var(--primary-color) !important;
    -webkit-text-fill-color: var(--primary-color) !important;
}
[data-testid="stAppViewContainer"] .main .block-container,
[data-testid="stAppViewContainer"] .main p,
[data-testid="stAppViewContainer"] .main h1,
[data-testid="stAppViewContainer"] .main h2,
[data-testid="stAppViewContainer"] .main h3,
[data-testid="stAppViewContainer"] .main h4,
[data-testid="stAppViewContainer"] .main h5,
[data-testid="stAppViewContainer"] .main h6,
[data-testid="stAppViewContainer"] .main label,
[data-testid="stAppViewContainer"] .main .stMarkdown,
[data-testid="stAppViewContainer"] .main [data-testid="stWidgetLabel"],
[data-testid="stAppViewContainer"] .main [data-testid="stCaption"],
[data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"],
[data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"] p,
[data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"] span,
[data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"] li,
[data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"] div {
    color: var(--text-color) !important;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] div {
    color: var(--text-color) !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label,
section[data-testid="stSidebar"] [data-testid="stRadio"] label span,
section[data-testid="stSidebar"] [data-testid="stRadio"] label p,
section[data-testid="stSidebar"] [data-testid="stRadio"] div {
    color: var(--text-color) !important;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
    color: var(--text-color) !important;
    -webkit-text-fill-color: var(--text-color) !important;
    background-color: var(--background-color) !important;
}
[data-testid="stTextInput"] > div > div,
[data-testid="stTextArea"] > div > div,
[data-testid="stNumberInput"] > div > div {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
    background-color: var(--background-color) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
    background-color: var(--background-color) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] span {
    color: var(--text-color) !important;
}
[data-testid="stMultiSelect"] [data-baseweb="select"] {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.75rem !important;
    background-color: var(--background-color) !important;
}
[data-testid="stExpander"] {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary p {
    color: var(--text-color) !important;
}
[data-testid="stFileUploader"] section {
    border: 1px dashed var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
    background-color: var(--background-color) !important;
}
[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"],
[data-testid="stDataFrame"] [data-testid="glideDataEditor"],
[data-testid="stDataFrame"] canvas,
[data-testid="stDataFrame"] div {
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
}
[data-testid="stMetric"] {
    background-color: var(--secondary-background-color) !important;
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
    padding: 0.65rem 0.85rem !important;
}
[data-testid="stMetricLabel"] {
    color: var(--kahoot-text-muted) !important;
}
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] div {
    color: var(--kahoot-text-muted) !important;
}
[data-testid="stMetricValue"] {
    color: var(--text-color) !important;
}
[data-testid="stMetricValue"] div {
    color: var(--text-color) !important;
}
[data-testid="stMetricDelta"] svg {
    stroke: currentColor !important;
}
[data-testid="stAlertContainer"] {
    background: transparent !important;
    padding: 0 !important;
    margin: 0.25rem 0 !important;
}
[data-testid="stAlertContentSuccess"] {
    background-color: var(--kahoot-alert-success-bg) !important;
    color: var(--kahoot-alert-success-text) !important;
    border: 1px solid var(--kahoot-alert-success-border) !important;
    border-radius: 0.5rem !important;
}
[data-testid="stAlertContentWarning"] {
    background-color: var(--kahoot-alert-warning-bg) !important;
    color: var(--kahoot-alert-warning-text) !important;
    border: 1px solid var(--kahoot-alert-warning-border) !important;
    border-radius: 0.5rem !important;
}
[data-testid="stAlertContentError"] {
    background-color: var(--kahoot-alert-error-bg) !important;
    color: var(--kahoot-alert-error-text) !important;
    border: 1px solid var(--kahoot-alert-error-border) !important;
    border-radius: 0.5rem !important;
}
[data-testid="stAlertContentInfo"] {
    background-color: var(--kahoot-alert-info-bg) !important;
    color: var(--kahoot-alert-info-text) !important;
    border: 1px solid var(--kahoot-alert-info-border) !important;
    border-radius: 0.5rem !important;
}
[data-testid^="stAlertContent"] p,
[data-testid^="stAlertContent"] span,
[data-testid^="stAlertContent"] div,
[data-testid^="stAlertContent"] label {
    color: inherit !important;
}
[data-testid="stAppViewContainer"] .main [data-testid="stRadio"] label,
[data-testid="stAppViewContainer"] .main [data-testid="stRadio"] label span,
[data-testid="stAppViewContainer"] .main [data-testid="stRadio"] label p,
[data-testid="stAppViewContainer"] .main [data-testid="stRadio"] div[role="radiogroup"] {
    color: var(--text-color) !important;
}
[data-testid="stForm"] {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
    padding: 0.75rem !important;
    background-color: var(--background-color) !important;
}
[data-testid="stForm"] label,
[data-testid="stForm"] p,
[data-testid="stForm"] span {
    color: var(--text-color) !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"],
section[data-testid="stSidebar"] .stButton > button:not([kind="primary"]),
[data-testid="stAppViewContainer"] .main .stButton > button[kind="secondary"],
[data-testid="stAppViewContainer"] .main .stButton > button:not([kind="primary"]) {
    color: var(--text-color) !important;
    border: 1px solid var(--kahoot-border-strong) !important;
    background-color: var(--secondary-background-color) !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stAppViewContainer"] .main .stButton > button[kind="primary"] {
    background-color: var(--primary-color) !important;
    color: #ffffff !important;
    border: 1px solid color-mix(in srgb, var(--primary-color) 70%, transparent) !important;
}
[data-testid="stSegmentedControl"] {
    background-color: var(--kahoot-segment-bg) !important;
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
}
[data-testid="stSegmentedControl"] button {
    color: var(--text-color) !important;
}
[data-testid="stSegmentedControl"] button[aria-checked="true"] {
    color: var(--kahoot-segment-selected-text) !important;
    background-color: var(--primary-color) !important;
}
[data-testid="stSegmentedControl"] button span,
[data-testid="stSegmentedControl"] button p {
    color: inherit !important;
}
.kahoot-theme-icons [data-testid="stSegmentedControl"] button {
    font-size: 1.05rem !important;
    line-height: 1 !important;
    min-width: 2.25rem !important;
    padding: 0.35rem 0.5rem !important;
}
.kahoot-session-name,
.kahoot-menu-account-name {
    color: var(--text-color) !important;
}
.kahoot-session-email,
.kahoot-menu-email,
.kahoot-menu-role {
    color: var(--kahoot-text-muted) !important;
}
.kahoot-menu-section-title,
section[data-testid="stSidebar"] .kahoot-sidebar-nav-title {
    color: var(--kahoot-text-subtle) !important;
}
.kahoot-session-role--student {
    color: var(--kahoot-student-role-text) !important;
    background: var(--kahoot-student-role-bg) !important;
    border-color: var(--kahoot-student-role-border) !important;
}
section[data-testid="stSidebar"] .kahoot-logout-confirm {
    border-top-color: var(--kahoot-border) !important;
}
[data-testid="stAlert"] p,
[data-testid="stAlert"] div {
    color: inherit !important;
}
[data-baseweb="toast"] [data-testid="stAlertContentSuccess"],
[data-baseweb="toast"] [data-testid="stAlertContentWarning"],
[data-baseweb="toast"] [data-testid="stAlertContentError"],
[data-baseweb="toast"] [data-testid="stAlertContentInfo"] {
    border-radius: 0.5rem !important;
}
header[data-testid="stHeader"] {
    background: var(--background-color) !important;
    border-bottom: 1px solid var(--kahoot-border-strong) !important;
}
[data-testid="stPopoverBody"],
[data-testid="stPopoverBody"] > div,
[data-testid="stPopoverBody"] [data-testid="stVerticalBlock"],
[data-testid="stPopover"] [data-baseweb="popover"],
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
div[data-testid="stPopover"] > div {
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
    border-color: var(--kahoot-border-strong) !important;
}
[data-testid="stPopoverBody"] {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.14) !important;
}
[data-testid="stPopoverBody"] p,
[data-testid="stPopoverBody"] span,
[data-testid="stPopoverBody"] label,
[data-testid="stPopoverBody"] [data-testid="stWidgetLabel"],
[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"],
[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"] p,
[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"] span,
[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"] div,
[data-testid="stPopoverBody"] div {
    color: var(--text-color) !important;
}
[data-testid="stPopoverBody"] .kahoot-menu-account-name {
    color: var(--text-color) !important;
}
[data-testid="stPopoverBody"] .kahoot-menu-role,
[data-testid="stPopoverBody"] .kahoot-menu-email {
    color: var(--kahoot-text-muted) !important;
}
[data-testid="stPopoverBody"] .stButton > button[kind="secondary"],
[data-testid="stPopoverBody"] .stButton > button:not([kind="primary"]) {
    background-color: var(--secondary-background-color) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--kahoot-border-strong) !important;
}
[data-testid="stPopoverBody"] .stButton > button[kind="primary"] {
    background-color: var(--primary-color) !important;
    color: #ffffff !important;
    border: 1px solid color-mix(in srgb, var(--primary-color) 70%, transparent) !important;
}
[data-testid="stPopoverBody"] hr,
[data-testid="stPopoverBody"] [data-testid="stDivider"],
[data-testid="stPopoverBody"] [data-testid="stDivider"] hr {
    border-color: var(--kahoot-border) !important;
    background-color: var(--kahoot-border) !important;
}
hr {
    border-color: var(--kahoot-border) !important;
}
"""


def _build_theme_css() -> str:
    choice = _current_theme()
    if choice == "system":
        root_css = f"""
@media (prefers-color-scheme: light) {{
    :root {{{_css_variables("light")}}}
}}
@media (prefers-color-scheme: dark) {{
    :root {{{_css_variables("dark")}}}
}}
"""
    else:
        root_css = _root_block(choice)
    return root_css + _shared_component_css()


def _chrome_icon_colors() -> tuple[str, str]:
    return (
        THEME_TOKENS["light"]["chrome_btn_icon"],
        THEME_TOKENS["dark"]["chrome_btn_icon"],
    )


def inject_theme_css() -> None:
    """Injeta ou substitui um único bloco de CSS de tema (evita tags duplicadas)."""
    css = _build_theme_css()
    css_json = json.dumps(css)
    light_icon, dark_icon = _chrome_icon_colors()
    theme_choice = json.dumps(_current_theme())
    light_icon_json = json.dumps(light_icon)
    dark_icon_json = json.dumps(dark_icon)
    st.markdown(
        f"<style id='kahoot-theme-override'>{css}</style>",
        unsafe_allow_html=True,
    )
    st.html(
        f"""
        <script>
        (function () {{
            const css = {css_json};
            const themeChoice = {theme_choice};
            const lightIcon = {light_icon_json};
            const darkIcon = {dark_icon_json};
            function resolveIconColor() {{
                if (themeChoice === "dark") return darkIcon;
                if (themeChoice === "light") return lightIcon;
                return window.matchMedia("(prefers-color-scheme: dark)").matches
                    ? darkIcon
                    : lightIcon;
            }}
            document.querySelectorAll("#kahoot-theme-override").forEach((el) => el.remove());
            const style = document.createElement("style");
            style.id = "kahoot-theme-override";
            style.textContent = css;
            document.head.appendChild(style);

            function paintSidebarChromeButtons() {{
                const iconColor = resolveIconColor();
                const selectors = [
                    '[data-testid="stExpandSidebarButton"]',
                    '[data-testid="stSidebarCollapseButton"]',
                ];
                selectors.forEach((sel) => {{
                    document.querySelectorAll(sel).forEach((root) => {{
                        root.style.color = iconColor;
                        root.querySelectorAll("button, span, svg, path").forEach((node) => {{
                            node.style.setProperty("color", iconColor, "important");
                            node.style.setProperty("fill", iconColor, "important");
                            node.style.setProperty("stroke", iconColor, "important");
                            node.style.setProperty("-webkit-text-fill-color", iconColor, "important");
                        }});
                    }});
                }});
            }}
            paintSidebarChromeButtons();
            setTimeout(paintSidebarChromeButtons, 50);
            setTimeout(paintSidebarChromeButtons, 300);
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def apply_ui_theme() -> None:
    """Compatibilidade — tema aplicado via CSS em finalize_ui_theme()."""
    return


def finalize_ui_theme() -> None:
    inject_theme_css()


def render_theme_selector(
    *,
    key: str = "ui_theme",
    compact: bool = False,
    icon_only: bool = False,
) -> None:
    if not icon_only:
        st.markdown(
            '<div class="kahoot-menu-section-title">Aparência</div>',
            unsafe_allow_html=True,
        )
    st.markdown('<span class="kahoot-theme-icons"></span>', unsafe_allow_html=True)
    st.segmented_control(
        "Tema",
        options=list(THEME_OPTIONS),
        format_func=lambda option: THEME_ICONS[option],
        key=key,
        help="Sistema segue o tema do dispositivo; ☀️ claro; 🌙 escuro.",
        label_visibility="collapsed",
        width="stretch" if not compact else "content",
    )
