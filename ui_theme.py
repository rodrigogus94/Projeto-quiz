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


def get_theme_colors() -> dict[str, str]:
    """Paleta unificada do tema resolvido (CSS + gráficos + badges)."""
    theme = get_resolved_theme()
    merged: dict[str, str] = {}
    merged.update(THEME_COLORS[theme])
    merged.update(THEME_TOKENS[theme])
    merged.update(CHART_PALETTES[theme])
    merged.update(CLASSIFICATION_BADGE_COLORS[theme])
    return merged


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
[data-testid="stRadio"] div[role="radiogroup"] > label {
    padding: 0.42rem 0.7rem !important;
    margin: 0.12rem 0 !important;
    border-radius: 0.5rem !important;
    border: 1px solid transparent !important;
    background-color: transparent !important;
    transition: background-color 0.15s ease, border-color 0.15s ease !important;
}
[data-testid="stAppViewContainer"] .main [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked),
[data-testid="stAppViewContainer"] .main [data-testid="stRadio"] div[role="radiogroup"] > label[aria-checked="true"] {
    background-color: color-mix(in srgb, var(--primary-color) 12%, var(--background-color)) !important;
    border-color: color-mix(in srgb, var(--primary-color) 38%, transparent) !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked),
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label[aria-checked="true"] {
    background-color: color-mix(in srgb, var(--primary-color) 15%, var(--secondary-background-color)) !important;
    border-color: color-mix(in srgb, var(--primary-color) 42%, transparent) !important;
}
[data-testid="stRadio"] label,
[data-testid="stRadio"] label span,
[data-testid="stRadio"] label p,
[data-testid="stRadio"] div[role="radiogroup"] {
    color: var(--text-color) !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) span,
section[data-testid="stSidebar"] [data-testid="stRadio"] label[aria-checked="true"] span,
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p,
section[data-testid="stSidebar"] [data-testid="stRadio"] label[aria-checked="true"] p {
    font-weight: 600 !important;
}
[data-testid="stRadio"] input[type="radio"] {
    accent-color: var(--primary-color) !important;
}
[data-testid="stForm"] {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.65rem !important;
    padding: 1rem 1.1rem !important;
    background-color: var(--background-color) !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
}
[data-testid="stForm"] label,
[data-testid="stForm"] p,
[data-testid="stForm"] span,
[data-testid="stForm"] [data-testid="stWidgetLabel"] {
    color: var(--text-color) !important;
}
[data-testid="stForm"] [data-testid="stTextInput"] > div > div,
[data-testid="stForm"] [data-testid="stTextArea"] > div > div,
[data-testid="stForm"] [data-testid="stNumberInput"] > div > div,
[data-testid="stForm"] [data-testid="stSelectbox"] [data-baseweb="select"] {
    background-color: var(--background-color) !important;
    border-color: var(--kahoot-border-strong) !important;
}
[data-testid="stFormSubmitButton"] > button {
    border-radius: 0.5rem !important;
}
[data-testid="stCheckbox"] label span,
[data-testid="stCheckbox"] label p,
[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] {
    color: var(--text-color) !important;
}
[data-testid="stCheckbox"] input[type="checkbox"] {
    accent-color: var(--primary-color) !important;
}
[data-testid="stProgress"] > div > div > div {
    background-color: var(--primary-color) !important;
}
[data-testid="stProgress"] > div > div {
    background-color: var(--secondary-background-color) !important;
}
[data-testid="stSpinner"] > div {
    border-top-color: var(--primary-color) !important;
}
[data-testid="stDataFrame"] {
    overflow: hidden !important;
}
[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {
    border-radius: 0.45rem !important;
}
[data-testid="stDataFrame"] ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb {
    background: var(--kahoot-border-strong);
    border-radius: 4px;
}
[data-testid="stDataFrame"] ::-webkit-scrollbar-track {
    background: var(--secondary-background-color);
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
            function readThemeVar(name) {{
                return getComputedStyle(document.documentElement)
                    .getPropertyValue(name)
                    .trim();
            }}
            function paintDataFrameContainers() {{
                const bg = readThemeVar("--background-color");
                const text = readThemeVar("--text-color");
                const secondary = readThemeVar("--secondary-background-color");
                if (!bg) return;
                document.querySelectorAll('[data-testid="stDataFrame"]').forEach((frame) => {{
                    frame.style.backgroundColor = bg;
                    frame.style.color = text;
                    frame.querySelectorAll('[data-testid="stDataFrameResizable"], [data-testid="glideDataEditor"]').forEach((el) => {{
                        el.style.backgroundColor = bg;
                        el.style.color = text;
                    }});
                    frame.querySelectorAll('div:not(:has(canvas))').forEach((div) => {{
                        if (div.closest('[data-testid="stDataFrame"]') === frame) {{
                            div.style.backgroundColor = secondary || bg;
                            div.style.color = text;
                        }}
                    }});
                }});
            }}
            paintSidebarChromeButtons();
            paintDataFrameContainers();
            setTimeout(paintSidebarChromeButtons, 50);
            setTimeout(paintDataFrameContainers, 50);
            setTimeout(paintSidebarChromeButtons, 300);
            setTimeout(paintDataFrameContainers, 300);
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


BRAND_TEAL = "#458588"

GOOGLE_ICON_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E"
    "%3Cpath fill='%23FFC107' d='M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8"
    "-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657"
    "C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20"
    "c0-1.341-.138-2.65-.389-3.916z'/%3E"
    "%3Cpath fill='%23FF3D00' d='m6.306 14.691 6.571 4.819C14.655 15.108 18.961 12 24 12"
    "c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4"
    " 16.318 4 9.656 8.337 6.306 14.691z'/%3E"
    "%3Cpath fill='%234CAF50' d='M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238"
    "C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025"
    "C9.505 39.556 16.227 44 24 44z'/%3E"
    "%3Cpath fill='%231976D2' d='M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571"
    "l6.19 5.238C42.022 35.026 44 30.038 44 24c0-1.341-.138-2.65-.389-3.917z'/%3E"
    "%3C/svg%3E"
)

def login_page_css() -> str:
    return f"""
.stApp:has(.kahoot-login-marker) section[data-testid="stSidebar"],
.stApp:has(.kahoot-login-marker) footer {{
    display: none !important;
}}
.stApp:has(.kahoot-login-marker) header[data-testid="stHeader"] {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    visibility: hidden !important;
}}
.stApp:has(.kahoot-login-marker) .main {{
    padding-top: 0 !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stDecoration"] {{
    display: none !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stHorizontalBlock"]:has(.kahoot-login-theme-marker) {{
    height: 0 !important;
    min-height: 0 !important;
    overflow: visible !important;
    margin: 0 !important;
    border: none !important;
}}
.stApp:has(.kahoot-login-marker) .main .block-container {{
    padding: 0 !important;
    max-width: 100% !important;
    margin: 0 !important;
}}
.kahoot-login-marker {{ display: none !important; }}
.stApp:has(.kahoot-login-marker) [data-testid="stHorizontalBlock"]:has(.kahoot-login-theme-marker) {{
    position: fixed !important;
    top: 1rem !important;
    right: 1.25rem !important;
    z-index: 60 !important;
    width: auto !important;
    max-width: 11rem !important;
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stHorizontalBlock"]:has(.kahoot-login-theme-marker) > [data-testid="stColumn"] {{
    width: auto !important;
    flex: 0 0 auto !important;
    padding: 0 !important;
    min-height: unset !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stHorizontalBlock"]:has(.kahoot-login-theme-marker) [data-testid="stSegmentedControl"] {{
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12) !important;
}}
.kahoot-login-theme-marker {{ display: none !important; }}
.kahoot-login-row {{
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    min-height: 100vh !important;
    gap: 0 !important;
    margin: 0 !important;
    z-index: 50 !important;
    align-items: stretch !important;
}}
.kahoot-login-row > [data-testid="stColumn"] {{
    padding: 3.5rem 3rem !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    min-height: 100vh !important;
    overflow-y: auto !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child {{
    background: {BRAND_TEAL} !important;
    flex: 0 0 50% !important;
    width: 50% !important;
    max-width: 50% !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child {{
    background: var(--kahoot-login-panel-right) !important;
    flex: 0 0 50% !important;
    width: 50% !important;
    max-width: 50% !important;
}}
.kahoot-login-row > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
    min-height: 100% !important;
    flex: 1 1 auto !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child > [data-testid="stVerticalBlock"],
.kahoot-login-row > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"] {{
    max-width: 360px;
}}
.kahoot-left-inner {{ text-align: center; max-width: 320px; }}
.kahoot-left-inner h2 {{
    color: #ffffff; font-size: 2.4rem; font-weight: 700;
    margin: 0 0 1rem; line-height: 1.2;
    font-family: "Segoe UI", system-ui, sans-serif;
}}
.kahoot-left-inner p {{
    color: rgba(255,255,255,0.95); font-size: 0.95rem; line-height: 1.7;
    margin: 0 0 2rem; font-family: "Segoe UI", system-ui, sans-serif;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child .stButton {{
    width: 100%; display: flex; justify-content: center;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child .stButton > button {{
    background: transparent !important;
    color: #ffffff !important;
    border: 2px solid #ffffff !important;
    border-radius: 25px !important;
    font-weight: 600 !important;
    padding: 0.7rem 2.8rem !important;
    letter-spacing: 0.08em !important;
    min-width: 200px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child .stButton > button:hover {{
    background: rgba(255,255,255,0.12) !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) {{
    max-width: 42px !important; width: auto !important;
    margin: 0 auto 0.5rem !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"] {{
    flex: 0 0 auto !important; width: auto !important; max-width: none !important;
    min-height: unset !important; padding: 0 !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2) {{
    position: relative !important;
    width: 42px !important; height: 42px !important;
    min-height: 42px !important; flex: 0 0 42px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2) > [data-testid="stVerticalBlock"] {{
    position: relative !important;
    width: 42px !important; height: 42px !important;
    min-height: 42px !important; justify-content: flex-start !important;
}}
.kahoot-google-visual {{
    width: 42px; height: 42px; border-radius: 50%;
    border: 1px solid var(--kahoot-login-google-border);
    background-color: var(--kahoot-login-google-bg);
    background-image: url("{GOOGLE_ICON_SVG}");
    background-size: 22px; background-repeat: no-repeat; background-position: center;
    margin: 0 auto; pointer-events: none;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2) .element-container:has(
    iframe[title="streamlit_oauth.authorize_button"]
) {{
    position: absolute !important; top: 0 !important; left: 0 !important;
    width: 42px !important; height: 42px !important;
    opacity: 0 !important; z-index: 2 !important;
    margin: 0 !important; padding: 0 !important; overflow: visible !important;
    border: none !important; background: transparent !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) iframe[title="streamlit_oauth.authorize_button"] {{
    width: 42px !important; height: 42px !important; border: none !important;
    margin: 0 !important; cursor: pointer !important;
}}
.kahoot-form-wrap {{ width: 100%; max-width: 360px; margin: 0 auto; }}
.kahoot-form-title {{
    color: var(--kahoot-login-form-title); font-size: 1.85rem; font-weight: 700;
    text-align: center; margin: 0 0 1.25rem;
    font-family: "Segoe UI", system-ui, sans-serif;
}}
.kahoot-form-sub {{
    color: var(--kahoot-login-form-sub); font-size: 0.85rem; text-align: center; margin: 0 0 1rem;
}}
.kahoot-or-line {{
    display: flex; align-items: center; gap: 0.75rem;
    margin: 1.25rem 0; color: var(--kahoot-login-form-muted); font-size: 0.82rem;
}}
.kahoot-or-line::before, .kahoot-or-line::after {{
    content: ""; flex: 1; height: 1px; background: var(--kahoot-login-or-line);
}}
.kahoot-footnote {{
    color: var(--kahoot-login-form-muted); font-size: 0.78rem; text-align: center;
    margin-top: 1.25rem; line-height: 1.5;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child label {{
    color: var(--kahoot-login-label) !important; font-weight: 600 !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child input {{
    background: var(--kahoot-login-input-bg) !important;
    border: 1px solid var(--kahoot-login-input-border) !important;
    color: var(--kahoot-login-input-text) !important;
    border-radius: 8px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child .stTextInput > div > div {{
    background: var(--kahoot-login-input-bg) !important;
    border: 1px solid var(--kahoot-login-input-border) !important;
    border-radius: 8px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stFormSubmitButton"] > button {{
    background: {BRAND_TEAL} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 25px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    padding: 0.75rem 1.5rem !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stFormSubmitButton"] > button:hover {{
    background: #3d7a72 !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child .stButton > button[kind="secondary"] {{
    background: var(--kahoot-login-secondary-btn-bg) !important;
    color: var(--kahoot-login-secondary-btn-text) !important;
    border: 1px solid var(--kahoot-login-input-border) !important;
    border-radius: 25px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stMarkdownContainer"] p,
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stCaption"] {{
    color: var(--kahoot-login-form-muted) !important;
}}
@media (max-width: 768px) {{
    .kahoot-login-row {{
        position: relative !important;
        flex-direction: column !important;
        height: auto !important;
        min-height: 100vh !important;
    }}
    .kahoot-login-row > [data-testid="stColumn"] {{
        min-height: auto !important;
        width: 100% !important;
        max-width: 100% !important;
        flex: 1 1 auto !important;
    }}
}}
"""


def _app_chrome_css() -> str:
    return """
footer { visibility: hidden; }
"""

def _app_hide_toolbar_css() -> str:
    return """
header[data-testid="stHeader"] [data-testid="stMainMenu"],
header[data-testid="stHeader"] [data-testid="stToolbarActions"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    background: var(--background-color) !important;
    border-bottom: 1px solid var(--kahoot-border) !important;
    box-shadow: none !important;
}
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] button,
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button {
    color: var(--kahoot-chrome-btn-icon) !important;
    background: var(--kahoot-chrome-btn-bg) !important;
    border: 1.5px solid var(--kahoot-chrome-btn-border) !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1) !important;
}
[data-testid="stExpandSidebarButton"] span,
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stExpandSidebarButton"] path,
[data-testid="stExpandSidebarButton"] *,
[data-testid="stSidebarCollapseButton"] span,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapseButton"] path,
[data-testid="stSidebarCollapseButton"] * {
    color: var(--kahoot-chrome-btn-icon) !important;
    fill: var(--kahoot-chrome-btn-icon) !important;
    stroke: var(--kahoot-chrome-btn-icon) !important;
    -webkit-text-fill-color: var(--kahoot-chrome-btn-icon) !important;
}
"""

def sidebar_session_css() -> str:
    return f"""
section[data-testid="stSidebar"]:has(.kahoot-sidebar-shell) {{
    padding-top: 0.25rem !important;
}}
section[data-testid="stSidebar"] .kahoot-sidebar-account-block {{
    margin-top: 0.65rem;
    padding: 0.75rem 0.35rem 0.5rem;
    border-top: 1px solid var(--kahoot-border);
}}
section[data-testid="stSidebar"]:has(.kahoot-sidebar-shell) .kahoot-account-menu-anchor ~ [data-testid="stVerticalBlock"] [data-testid="stPopover"],
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] {{
    width: 100% !important;
    opacity: 1 !important;
    visibility: visible !important;
    margin-bottom: 0.15rem !important;
}}
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] > button,
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] .stButton > button,
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button {{
    background: var(--background-color) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.86rem !important;
    line-height: 1.2 !important;
    padding: 0.5rem 0.8rem !important;
    min-height: 2.5rem !important;
    width: 100% !important;
    letter-spacing: 0 !important;
    opacity: 1 !important;
    visibility: visible !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.45rem !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
}}
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] .stButton {{
    width: 100% !important;
}}
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button [data-testid="stIconMaterial"],
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button span[data-testid="stIconMaterial"] {{
    color: {BRAND_TEAL} !important;
}}
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] > button:hover,
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] .stButton > button:hover,
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button:hover {{
    background: color-mix(in srgb, {BRAND_TEAL} 9%, var(--background-color)) !important;
    color: var(--text-color) !important;
    border-color: {BRAND_TEAL} !important;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.07) !important;
}}
section[data-testid="stSidebar"] .kahoot-account-menu-anchor {{
    display: none !important;
}}
/* Sidebar recolhida: só ícone do menu, centralizado */
section[data-testid="stSidebar"][aria-expanded="false"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button {{
    padding: 0.45rem !important;
    min-width: 2.5rem !important;
    width: 2.5rem !important;
    min-height: 2.5rem !important;
    border-radius: 0.65rem !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button p,
section[data-testid="stSidebar"][aria-expanded="false"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button span:not([data-testid="stIconMaterial"]) {{
    display: none !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"] .kahoot-sidebar-account-block {{
    display: none !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"]:has(.kahoot-sidebar-shell) hr {{
    display: none !important;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) [data-testid="stSegmentedControl"] {{
    width: 100% !important;
    margin-bottom: 0.35rem !important;
}}
.kahoot-session-bar {{
    display: flex;
    align-items: center;
    gap: 0.85rem;
    min-width: 0;
}}
.kahoot-session-avatar {{
    flex: 0 0 auto;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    color: #ffffff;
    background: linear-gradient(135deg, {BRAND_TEAL} 0%, #3d7a72 100%);
    border: 2px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
}}
.kahoot-session-info {{
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
    flex: 1 1 auto;
}}
.kahoot-session-line {{
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
}}
.kahoot-session-name {{
    color: var(--text-color, #31333F);
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1.2;
}}
.kahoot-session-email {{
    color: var(--kahoot-text-muted, #5c6370);
    font-size: 0.78rem;
    line-height: 1.25;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.kahoot-session-role {{
    display: inline-flex;
    align-items: center;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    background: color-mix(in srgb, var(--primary-color) 18%, transparent);
    color: var(--primary-color) !important;
    border: 1px solid color-mix(in srgb, var(--primary-color) 45%, transparent);
}}
.kahoot-session-role--student {{
    background: var(--kahoot-student-role-bg);
    color: var(--kahoot-student-role-text);
    border-color: var(--kahoot-student-role-border);
}}
section[data-testid="stSidebar"] .kahoot-logout-confirm {{
    margin-top: 0.65rem;
    padding-top: 0.65rem;
    border-top: 1px solid var(--kahoot-border);
}}
section[data-testid="stSidebar"] .kahoot-sidebar-nav-title {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--kahoot-text-subtle, #6b7280);
    margin: 0.35rem 0 0.5rem;
}}
.kahoot-menu-panel {{
    min-width: 12.5rem;
    padding: 0.1rem 0 0.15rem;
}}
.kahoot-menu-account-name {{
    color: var(--text-color, #31333F);
    font-size: 0.92rem;
    font-weight: 700;
    line-height: 1.25;
    margin-bottom: 0.2rem;
}}
.kahoot-menu-role {{
    color: var(--kahoot-text-muted, #5c6370);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.15rem;
}}
.kahoot-menu-email {{
    color: var(--kahoot-text-muted, #5c6370);
    font-size: 0.78rem;
    line-height: 1.3;
    word-break: break-word;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) {{
    min-width: 13rem !important;
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) .stButton > button {{
    background-color: var(--secondary-background-color) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--kahoot-border-strong) !important;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) .element-container:has(.kahoot-menu-logout-marker) + .element-container .stButton > button {{
    background: transparent !important;
    color: var(--kahoot-danger) !important;
    border: 1px solid color-mix(in srgb, var(--kahoot-danger) 55%, transparent) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 0.45rem 1rem !important;
    min-height: 2.75rem !important;
    height: 2.75rem !important;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) .element-container:has(.kahoot-menu-logout-marker) + .element-container .stButton > button:hover {{
    background: var(--kahoot-danger-bg-hover) !important;
    border-color: var(--kahoot-danger) !important;
    color: var(--kahoot-danger-hover) !important;
}}
.kahoot-menu-section-title {{
    color: var(--kahoot-text-subtle, #6b7280);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 0.15rem 0 0.35rem;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) [data-testid="stRadio"] label {{
    font-size: 0.84rem !important;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) .element-container:has(.kahoot-menu-action-marker) + .element-container .stButton > button {{
    min-height: 2.5rem !important;
    font-size: 0.82rem !important;
}}
"""


def inject_app_chrome(*, hide_toolbar: bool = False) -> None:
    css = _app_chrome_css() + (_app_hide_toolbar_css() if hide_toolbar else "")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def inject_login_page_css() -> None:
    st.markdown(f"<style>{login_page_css()}</style>", unsafe_allow_html=True)


def inject_login_layout_script() -> None:
    css_json = json.dumps(login_page_css())
    st.html(
        f"""
        <script>
        (function() {{
            function applyLoginLayout() {{
                let style = document.getElementById("kahoot-login-style");
                if (!style) {{
                    style = document.createElement("style");
                    style.id = "kahoot-login-style";
                    document.head.appendChild(style);
                }}
                style.textContent = {css_json};
                document.querySelectorAll(".kahoot-login-marker").forEach((marker) => {{
                    const row = marker.closest('[data-testid="stHorizontalBlock"]');
                    if (row) row.classList.add("kahoot-login-row");
                }});
            }}
            applyLoginLayout();
            setTimeout(applyLoginLayout, 50);
            setTimeout(applyLoginLayout, 300);
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def clear_login_page_styles() -> None:
    st.html(
        """
        <script>
        (function () {
            const style = document.getElementById("kahoot-login-style");
            if (style) style.remove();
            document.querySelectorAll(".kahoot-login-row").forEach((row) => {
                row.classList.remove("kahoot-login-row");
            });
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def inject_sidebar_session_css() -> None:
    st.markdown(f"<style>{sidebar_session_css()}</style>", unsafe_allow_html=True)


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
