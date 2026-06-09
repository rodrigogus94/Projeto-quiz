"""Preferência de aparência (sistema / claro / escuro) via CSS injetado."""
from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

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
        "text": "#000000",
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
        "text_muted": "#1c1e24",
        "text_subtle": "#2a2d33",
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
        "text": "#000000",
        # Hex de 8 dígitos (RRGGBBAA): matplotlib não aceita strings CSS rgba().
        "grid": "#31333F33",
        "correct": "#27ae60",
        "wrong": "#c75555",
        "bar": "#458588",
        "performance": "#d68910",
    },
    "dark": {
        "figure": "#1d2021",
        "text": "#e8edf2",
        "grid": "#E8EDF233",
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
        "form_title": "#000000",
        "form_sub": "#1c1e24",
        "form_muted": "#2a2d33",
        "or_line": "rgba(49, 51, 63, 0.3)",
        "label": "#1c1e24",
        "input_bg": "#FFFFFF",
        "input_border": "rgba(49, 51, 63, 0.35)",
        "input_text": "#000000",
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
[data-testid="stAppViewContainer"] :is(.main, .stMain) .block-container,
[data-testid="stAppViewContainer"] :is(.main, .stMain) p,
[data-testid="stAppViewContainer"] :is(.main, .stMain) h1,
[data-testid="stAppViewContainer"] :is(.main, .stMain) h2,
[data-testid="stAppViewContainer"] :is(.main, .stMain) h3,
[data-testid="stAppViewContainer"] :is(.main, .stMain) h4,
[data-testid="stAppViewContainer"] :is(.main, .stMain) h5,
[data-testid="stAppViewContainer"] :is(.main, .stMain) h6,
[data-testid="stAppViewContainer"] :is(.main, .stMain) label,
[data-testid="stAppViewContainer"] :is(.main, .stMain) .stMarkdown,
[data-testid="stAppViewContainer"] :is(.main, .stMain) [data-testid="stWidgetLabel"],
[data-testid="stAppViewContainer"] :is(.main, .stMain) [data-testid="stCaption"],
[data-testid="stAppViewContainer"] :is(.main, .stMain) [data-testid="stMarkdownContainer"],
[data-testid="stAppViewContainer"] :is(.main, .stMain) [data-testid="stMarkdownContainer"] p,
[data-testid="stAppViewContainer"] :is(.main, .stMain) [data-testid="stMarkdownContainer"] span,
[data-testid="stAppViewContainer"] :is(.main, .stMain) [data-testid="stMarkdownContainer"] li,
[data-testid="stAppViewContainer"] :is(.main, .stMain) [data-testid="stMarkdownContainer"] div {
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
/* Textos secundários do Streamlit (captions, métricas, uploader): usar o
   token do tema em vez do cinza claro interno do Streamlit. */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"] span,
[data-testid="stCaptionContainer"] div,
.stCaption,
.stCaption p,
[data-testid="stMarkdownContainer"] small,
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] label,
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploaderDropzoneInstructions"] div,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] [data-testid="stFileUploaderFileData"],
[data-testid="stFileUploader"] [data-testid="stFileUploaderFileName"] {
    color: var(--kahoot-text-muted) !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {
    color: var(--text-color) !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder,
[data-testid="stNumberInput"] input::placeholder {
    color: var(--kahoot-text-muted) !important;
    opacity: 0.75 !important;
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
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] input,
[data-testid="stSelectbox"] div[role="combobox"],
[data-testid="stSelectbox"] div[role="button"] {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stSelectbox"] [data-baseweb="select"] svg,
[data-testid="stSelectbox"] [data-baseweb="select"] path {
    color: var(--text-color) !important;
    fill: var(--text-color) !important;
}
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="popover"] ul,
[data-baseweb="popover"] li,
[data-testid="stSelectboxVirtualDropdown"],
[data-testid="stSelectboxVirtualDropdownEmpty"] {
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
}
[data-baseweb="popover"] li[aria-selected="true"],
[data-baseweb="popover"] li:hover {
    background-color: var(--secondary-background-color) !important;
}
[data-testid="stMultiSelect"] [data-baseweb="select"],
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
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
[data-testid="stFileUploader"],
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzone"] > div,
[data-testid="stFileUploaderDropzoneInstructions"] {
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
    border-color: var(--kahoot-border-strong) !important;
}
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
    border: 1px dashed var(--kahoot-border-strong) !important;
    border-radius: 0.5rem !important;
}
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
    background-color: var(--secondary-background-color) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--kahoot-border-strong) !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] p,
[data-testid="stFileUploaderDropzoneInstructions"] div {
    color: var(--kahoot-text-muted) !important;
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
[data-testid="stAppViewContainer"] :is(.main, .stMain) [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked),
[data-testid="stAppViewContainer"] :is(.main, .stMain) [data-testid="stRadio"] div[role="radiogroup"] > label[aria-checked="true"] {
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
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondaryBorderless"],
section[data-testid="stSidebar"] .stButton > button[kind="secondary"],
section[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):not([kind="primaryFormSubmit"]),
[data-testid="stAppViewContainer"] :is(.main, .stMain) .stButton > button[kind="secondary"],
[data-testid="stAppViewContainer"] :is(.main, .stMain) .stButton > button:not([kind="primary"]):not([kind="primaryFormSubmit"]) {
    color: var(--text-color) !important;
    border: 1px solid var(--kahoot-border-strong) !important;
    background-color: var(--secondary-background-color) !important;
}
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primaryFormSubmit"],
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button[kind="primaryFormSubmit"],
[data-testid="stAppViewContainer"] :is(.main, .stMain) .stButton > button[kind="primary"],
[data-testid="stAppViewContainer"] :is(.main, .stMain) .stButton > button[kind="primaryFormSubmit"] {
    background-color: var(--primary-color) !important;
    color: #ffffff !important;
    border: 1px solid color-mix(in srgb, var(--primary-color) 70%, transparent) !important;
}
[data-testid^="stBaseButton-"] p,
[data-testid^="stBaseButton-"] span,
[data-testid^="stBaseButton-"] div {
    color: inherit !important;
}
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stAppViewContainer"] :is(.main, .stMain) .stButton > button:not([kind="primary"]):not([kind="primaryFormSubmit"]):hover {
    background-color: color-mix(in srgb, var(--primary-color) 10%, var(--secondary-background-color)) !important;
    border-color: var(--primary-color) !important;
    color: var(--text-color) !important;
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


def _inject_javascript(script: str) -> None:
    """Executa JavaScript no cliente; compatível com várias versões do Streamlit."""
    snippet = f"<script>{script}</script>"
    try:
        st.html(snippet, unsafe_allow_javascript=True)
    except TypeError:
        components.html(snippet, height=0, width=0)


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
    _inject_javascript(
        f"""
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
            function isLoginSwitchButton(btn) {{
                const col = document.querySelector(
                    '[data-testid="stColumn"]:has(.kahoot-login-switch-marker)'
                );
                return Boolean(col && col.contains(btn));
            }}
            function paintThemedWidgets() {{
                const bg = readThemeVar("--background-color");
                const text = readThemeVar("--text-color");
                const secondary = readThemeVar("--secondary-background-color");
                const border = readThemeVar("--kahoot-border-strong");
                const muted = readThemeVar("--kahoot-text-muted");
                const primary = readThemeVar("--primary-color");
                if (!bg) return;
                document.querySelectorAll(
                    '[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryBorderless"]'
                ).forEach((btn) => {{
                    if (isLoginSwitchButton(btn)) {{
                        return;
                    }}
                    btn.style.setProperty("background-color", secondary, "important");
                    btn.style.setProperty("color", text, "important");
                    btn.style.setProperty("border-color", border, "important");
                    btn.querySelectorAll("p, span, div").forEach((node) => {{
                        node.style.setProperty("color", text, "important");
                    }});
                }});
                document.querySelectorAll('[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"]').forEach((btn) => {{
                    if (isLoginSwitchButton(btn)) {{
                        return;
                    }}
                    btn.style.setProperty("background-color", primary, "important");
                    btn.style.setProperty("color", "#ffffff", "important");
                    btn.querySelectorAll("p, span, div").forEach((node) => {{
                        node.style.setProperty("color", "#ffffff", "important");
                    }});
                }});
                document.querySelectorAll(
                    '[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploader"] section'
                ).forEach((zone) => {{
                    zone.style.setProperty("background-color", bg, "important");
                    zone.style.setProperty("color", text, "important");
                    zone.style.setProperty("border-color", border, "important");
                }});
                document.querySelectorAll('[data-testid="stFileUploaderDropzoneInstructions"]').forEach((el) => {{
                    el.style.setProperty("color", muted, "important");
                }});
                document.querySelectorAll('[data-testid="stSelectbox"] [data-baseweb="select"]').forEach((sel) => {{
                    sel.style.setProperty("background-color", bg, "important");
                    sel.style.setProperty("color", text, "important");
                    sel.style.setProperty("border-color", border, "important");
                    sel.querySelectorAll("span, div, input").forEach((node) => {{
                        node.style.setProperty("color", text, "important");
                        node.style.setProperty("background-color", bg, "important");
                    }});
                }});
                const switchCol = document.querySelector(
                    '[data-testid="stColumn"]:has(.kahoot-login-switch-marker)'
                );
                if (switchCol) {{
                        switchCol.querySelectorAll(
                            'button, [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"], [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryBorderless"]'
                        ).forEach((btn) => {{
                            btn.style.setProperty("background", "{LOGIN_SWITCH_BTN_BG}", "important");
                            btn.style.setProperty("background-color", "{LOGIN_SWITCH_BTN_BG}", "important");
                            btn.style.setProperty("color", "#ffffff", "important");
                            btn.style.setProperty("border", "none", "important");
                            btn.style.setProperty("border-radius", "25px", "important");
                            btn.style.setProperty("padding", "0.75rem 1.5rem", "important");
                            btn.style.setProperty("min-height", "2.75rem", "important");
                            btn.style.setProperty("height", "auto", "important");
                            btn.style.setProperty("width", "100%", "important");
                            btn.style.setProperty("display", "block", "important");
                            btn.style.setProperty("letter-spacing", "0.08em", "important");
                            btn.style.setProperty("font-weight", "600", "important");
                            btn.style.setProperty("box-sizing", "border-box", "important");
                            btn.querySelectorAll("p, span, div").forEach((node) => {{
                                node.style.setProperty("color", "#ffffff", "important");
                            }});
                        }});
                        switchCol.querySelectorAll(
                            '.element-container:has([data-testid="stButton"]), .element-container:has(.kahoot-login-switch-marker) + .element-container, [data-testid="stButton"], .stButton'
                        ).forEach((wrap) => {{
                            wrap.style.setProperty("width", "100%", "important");
                            wrap.style.setProperty("max-width", "360px", "important");
                            wrap.style.setProperty("margin", "0 auto", "important");
                        }});
                }}
            }}
            function repaintAll() {{
                paintSidebarChromeButtons();
                paintDataFrameContainers();
                paintThemedWidgets();
            }}
            repaintAll();
            setTimeout(repaintAll, 50);
            setTimeout(repaintAll, 300);
            setTimeout(repaintAll, 800);
        }})();
        """
    )


def apply_ui_theme() -> None:
    """Compatibilidade — tema aplicado via CSS em finalize_ui_theme()."""
    return


def finalize_ui_theme() -> None:
    inject_theme_css()


BRAND_TEAL = "#458588"
LOGIN_SWITCH_BTN_BG = "#1d2021"
LOGIN_SWITCH_BTN_BG_HOVER = "#2a2f30"

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

def _login_row_selector() -> str:
    return (
        '.stApp:has(.kahoot-login-marker) '
        '[data-testid="stHorizontalBlock"]:has(.kahoot-login-marker)'
    )


def login_page_css() -> str:
    row = _login_row_selector()
    return f"""
.stApp:has(.kahoot-login-marker) section[data-testid="stSidebar"],
.stApp:has(.kahoot-login-marker) footer {{
    display: none !important;
}}
.stApp:has(.kahoot-login-marker) header[data-testid="stHeader"],
.kahoot-on-login header[data-testid="stHeader"] {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    visibility: hidden !important;
    overflow: hidden !important;
    pointer-events: none !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stToolbar"],
.stApp:has(.kahoot-login-marker) [data-testid="stHeaderActionElements"],
.stApp:has(.kahoot-login-marker) [data-testid="stStatusWidget"],
.stApp:has(.kahoot-login-marker) [data-testid="stMainMenu"],
.kahoot-on-login [data-testid="stToolbar"],
.kahoot-on-login [data-testid="stHeaderActionElements"],
.kahoot-on-login [data-testid="stStatusWidget"],
.kahoot-on-login [data-testid="stMainMenu"] {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    max-height: 0 !important;
    overflow: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stDecoration"],
.kahoot-on-login [data-testid="stDecoration"] {{
    display: none !important;
}}
.stApp:has(.kahoot-login-marker) :is(.main, .stMain) {{
    padding-top: 0 !important;
}}
.stApp:has(.kahoot-login-marker) :is(.main, .stMain) .block-container {{
    padding: 0 !important;
    max-width: 100% !important;
    margin: 0 !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stSegmentedControl"],
.stApp:has(.kahoot-login-marker) [data-testid="stSegmentedControl"] *,
.stApp:has(.kahoot-login-marker) .kahoot-theme-icons,
.stApp:has(.kahoot-login-marker) .kahoot-menu-section-title,
.stApp:has(.kahoot-login-marker) .element-container:has([data-testid="stSegmentedControl"]):not(:has(.kahoot-left-panel)),
.stApp:has(.kahoot-login-marker) .element-container:has(.kahoot-theme-icons):not(:has(.kahoot-left-panel)),
.stApp:has(.kahoot-login-marker) section[data-testid="stSidebar"] [data-testid="stSegmentedControl"],
.stApp:has(.kahoot-login-marker) [data-testid="stPopoverBody"] [data-testid="stSegmentedControl"],
.kahoot-on-login [data-testid="stSegmentedControl"],
.kahoot-on-login [data-testid="stSegmentedControl"] *,
.kahoot-on-login .kahoot-theme-icons,
.kahoot-on-login .kahoot-menu-section-title,
.kahoot-on-login .element-container:has([data-testid="stSegmentedControl"]):not(:has(.kahoot-left-panel)),
.kahoot-on-login .element-container:has(.kahoot-theme-icons):not(:has(.kahoot-left-panel)),
.kahoot-on-login section[data-testid="stSidebar"] [data-testid="stSegmentedControl"],
.kahoot-on-login [data-testid="stPopoverBody"] [data-testid="stSegmentedControl"] {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    max-height: 0 !important;
    overflow: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
    margin: 0 !important;
    padding: 0 !important;
    position: absolute !important;
    left: -9999px !important;
    top: -9999px !important;
}}
.kahoot-login-marker,
.kahoot-login-form-marker {{
    display: none !important;
}}
.stApp:has(.kahoot-login-marker) .kahoot-login-toast {{
    position: fixed;
    top: 1rem;
    left: 50%;
    transform: translateX(-50%);
    z-index: 80;
    max-width: min(24rem, calc(100vw - 2rem));
    padding: 0.55rem 1rem;
    text-align: center;
    font-size: 0.85rem;
    border-radius: 8px;
    border: 1px solid var(--kahoot-alert-success-border);
    background: var(--kahoot-alert-success-bg);
    color: var(--kahoot-alert-success-text);
}}
{row},
.kahoot-login-row {{
    position: fixed !important;
    inset: 0 !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: stretch !important;
    width: 100% !important;
    height: 100% !important;
    min-height: 100vh !important;
    min-height: 100dvh !important;
    gap: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    z-index: 50 !important;
}}
{row} > [data-testid="stColumn"],
.kahoot-login-row > [data-testid="stColumn"] {{
    padding: 3.5rem 3rem !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    min-height: 100% !important;
    overflow-y: auto !important;
    box-sizing: border-box !important;
}}
{row} > [data-testid="stColumn"]:first-child,
.kahoot-login-row > [data-testid="stColumn"]:first-child {{
    background: {BRAND_TEAL} !important;
    flex: 0 0 50% !important;
    width: 50% !important;
    max-width: 50% !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}}
{row} > [data-testid="stColumn"]:last-child,
.kahoot-login-row > [data-testid="stColumn"]:last-child {{
    background: var(--kahoot-login-panel-right) !important;
    flex: 0 0 50% !important;
    width: 50% !important;
    max-width: 50% !important;
}}
{row} > [data-testid="stColumn"] > [data-testid="stVerticalBlock"],
.kahoot-login-row > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
    min-height: 100% !important;
    flex: 1 1 auto !important;
}}
{row} > [data-testid="stColumn"]:first-child > [data-testid="stVerticalBlock"],
{row} > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"],
.kahoot-login-row > [data-testid="stColumn"]:first-child > [data-testid="stVerticalBlock"],
.kahoot-login-row > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"] {{
    max-width: 360px;
}}
.kahoot-left-panel {{
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    width: 100% !important;
    max-width: 360px !important;
    margin: 0 auto !important;
    pointer-events: auto !important;
}}
.kahoot-left-inner {{ text-align: center; max-width: 360px; width: 100%; margin: 0 auto; }}
.kahoot-left-inner h2,
{row} > [data-testid="stColumn"]:first-child .kahoot-left-inner h2,
.kahoot-login-row > [data-testid="stColumn"]:first-child .kahoot-left-inner h2,
{row} > [data-testid="stColumn"]:first-child [data-testid="stMarkdownContainer"] h2,
.kahoot-login-row > [data-testid="stColumn"]:first-child [data-testid="stMarkdownContainer"] h2 {{
    color: #ffffff !important;
    font-size: 2.4rem; font-weight: 700;
    margin: 0 0 1rem; line-height: 1.2;
    font-family: "Segoe UI", system-ui, sans-serif;
    display: block !important;
    visibility: visible !important;
}}
.kahoot-left-inner p,
{row} > [data-testid="stColumn"]:first-child .kahoot-left-inner p,
.kahoot-login-row > [data-testid="stColumn"]:first-child .kahoot-left-inner p,
{row} > [data-testid="stColumn"]:first-child [data-testid="stMarkdownContainer"] p,
.kahoot-login-row > [data-testid="stColumn"]:first-child [data-testid="stMarkdownContainer"] p {{
    color: rgba(255,255,255,0.95) !important;
    font-size: 0.95rem; line-height: 1.7;
    margin: 0 0 2rem; font-family: "Segoe UI", system-ui, sans-serif;
    display: block !important;
    visibility: visible !important;
}}
{row} > [data-testid="stColumn"]:first-child .element-container:has([data-testid="stButton"]),
{row} > [data-testid="stColumn"]:first-child .element-container:has(.kahoot-login-switch-marker) + .element-container,
.kahoot-login-row > [data-testid="stColumn"]:first-child .element-container:has([data-testid="stButton"]),
.kahoot-login-row > [data-testid="stColumn"]:first-child .element-container:has(.kahoot-login-switch-marker) + .element-container,
{row} > [data-testid="stColumn"]:first-child [data-testid="stButton"],
.kahoot-login-row > [data-testid="stColumn"]:first-child [data-testid="stButton"] {{
    width: 100% !important;
    max-width: 360px !important;
    margin: 0 auto !important;
}}
{row} > [data-testid="stColumn"]:first-child [data-testid="stButton"] > button,
.kahoot-login-row > [data-testid="stColumn"]:first-child [data-testid="stButton"] > button {{
    background: {LOGIN_SWITCH_BTN_BG} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 25px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    padding: 0.75rem 1.5rem !important;
    width: 100% !important;
    min-height: 2.75rem !important;
    box-sizing: border-box !important;
}}
{row} > [data-testid="stColumn"]:first-child [data-testid="stButton"] > button:hover,
.kahoot-login-row > [data-testid="stColumn"]:first-child [data-testid="stButton"] > button:hover {{
    background: {LOGIN_SWITCH_BTN_BG_HOVER} !important;
}}
{row} > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual),
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) {{
    max-width: 42px !important; width: auto !important;
    margin: 0 auto 0.5rem !important;
}}
{row} > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"],
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"] {{
    flex: 0 0 auto !important; width: auto !important; max-width: none !important;
    min-height: unset !important; padding: 0 !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
}}
{row} > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2),
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2) {{
    position: relative !important;
    width: 42px !important; height: 42px !important;
    min-height: 42px !important; flex: 0 0 42px !important;
}}
{row} > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2) > [data-testid="stVerticalBlock"],
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
{row} > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2) .element-container:has(
    iframe[title="streamlit_oauth.authorize_button"]
),
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2) .element-container:has(
    iframe[title="streamlit_oauth.authorize_button"]
) {{
    position: absolute !important; top: 0 !important; left: 0 !important;
    width: 42px !important; height: 42px !important;
    opacity: 0 !important; z-index: 2 !important;
    margin: 0 !important; padding: 0 !important; overflow: visible !important;
    border: none !important; background: transparent !important;
}}
{row} > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) iframe[title="streamlit_oauth.authorize_button"],
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
{row} > [data-testid="stColumn"]:last-child label,
.kahoot-login-row > [data-testid="stColumn"]:last-child label {{
    color: var(--kahoot-login-label) !important; font-weight: 600 !important;
}}
{row} > [data-testid="stColumn"]:last-child input,
.kahoot-login-row > [data-testid="stColumn"]:last-child input {{
    background: var(--kahoot-login-input-bg) !important;
    border: 1px solid var(--kahoot-login-input-border) !important;
    color: var(--kahoot-login-input-text) !important;
    border-radius: 8px !important;
}}
{row} > [data-testid="stColumn"]:last-child .stTextInput > div > div,
.kahoot-login-row > [data-testid="stColumn"]:last-child .stTextInput > div > div {{
    background: var(--kahoot-login-input-bg) !important;
    border: 1px solid var(--kahoot-login-input-border) !important;
    border-radius: 8px !important;
}}
{row} > [data-testid="stColumn"]:last-child [data-testid="stFormSubmitButton"] > button,
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stFormSubmitButton"] > button {{
    background: {BRAND_TEAL} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 25px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    padding: 0.75rem 1.5rem !important;
    width: 100% !important;
    min-height: 2.75rem !important;
    box-sizing: border-box !important;
}}
{row} > [data-testid="stColumn"]:last-child [data-testid="stFormSubmitButton"] > button:hover,
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stFormSubmitButton"] > button:hover {{
    background: #3d7a72 !important;
}}
{row} > [data-testid="stColumn"]:last-child .stButton > button[kind="secondary"],
.kahoot-login-row > [data-testid="stColumn"]:last-child .stButton > button[kind="secondary"] {{
    background: var(--kahoot-login-secondary-btn-bg) !important;
    color: var(--kahoot-login-secondary-btn-text) !important;
    border: 1px solid var(--kahoot-login-input-border) !important;
    border-radius: 25px !important;
}}
{row} > [data-testid="stColumn"]:last-child [data-testid="stMarkdownContainer"] p,
{row} > [data-testid="stColumn"]:last-child [data-testid="stCaption"],
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stMarkdownContainer"] p,
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stCaption"] {{
    color: var(--kahoot-login-form-muted) !important;
}}
@media (max-width: 768px) {{
    {row},
    .kahoot-login-row {{
        position: relative !important;
        inset: auto !important;
        flex-direction: column !important;
        width: 100% !important;
        height: auto !important;
        min-height: 100dvh !important;
        z-index: auto !important;
    }}
    {row} > [data-testid="stColumn"],
    {row} > [data-testid="stColumn"]:first-child,
    {row} > [data-testid="stColumn"]:last-child,
    .kahoot-login-row > [data-testid="stColumn"],
    .kahoot-login-row > [data-testid="stColumn"]:first-child,
    .kahoot-login-row > [data-testid="stColumn"]:last-child {{
        flex: 0 0 auto !important;
        width: 100% !important;
        max-width: 100% !important;
        min-height: auto !important;
        padding: 2rem 1.25rem !important;
    }}
    {row} > [data-testid="stColumn"]:first-child,
    .kahoot-login-row > [data-testid="stColumn"]:first-child {{
        padding-top: 2.5rem !important;
    }}
    {row} > [data-testid="stColumn"]:first-child > [data-testid="stVerticalBlock"],
    {row} > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"],
    .kahoot-login-row > [data-testid="stColumn"]:first-child > [data-testid="stVerticalBlock"],
    .kahoot-login-row > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"] {{
        max-width: 100% !important;
    }}
    .kahoot-left-inner h2 {{
        font-size: 1.6rem !important;
    }}
    .kahoot-left-inner p {{
        font-size: 0.9rem !important;
        margin-bottom: 1.25rem !important;
    }}
    .kahoot-form-title {{
        font-size: 1.5rem !important;
    }}
    .stApp:has(.kahoot-login-marker) .kahoot-login-toast,
    .kahoot-on-login .kahoot-login-toast {{
        position: relative;
        top: auto;
        left: auto;
        transform: none;
        margin: 0.75rem auto;
    }}
    .stApp:has(.kahoot-login-marker) [data-testid="stSegmentedControl"],
    .stApp:has(.kahoot-login-marker) .kahoot-theme-icons,
    .kahoot-on-login [data-testid="stSegmentedControl"],
    .kahoot-on-login .kahoot-theme-icons,
    .kahoot-on-login [data-testid="stToolbar"],
    .kahoot-on-login [data-testid="stHeaderActionElements"] {{
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }}
}}
"""


def login_switch_button_css() -> str:
    """CSS do botão ENTRAR/CADASTRAR-SE — injetado após o widget para garantir prioridade."""
    switch_col = (
        ".stApp:has(.kahoot-login-switch-marker) "
        "[data-testid='stColumn']:has(.kahoot-login-switch-marker)"
    )
    switch_btn = (
        f"{switch_col} button, "
        f"{switch_col} [data-testid='stBaseButton-primary'], "
        f"{switch_col} [data-testid='stBaseButton-primaryFormSubmit'], "
        f"{switch_col} [data-testid='stBaseButton-secondary'], "
        f"{switch_col} [data-testid='stBaseButton-secondaryBorderless']"
    )
    switch_wrap = (
        f"{switch_col} .element-container:has([data-testid='stButton']), "
        f"{switch_col} .element-container:has(.kahoot-login-switch-marker) + .element-container, "
        f"{switch_col} .stButton, "
        f"{switch_col} [data-testid='stButton']"
    )
    return f"""
.kahoot-login-switch-marker {{
    display: none !important;
}}
{switch_wrap} {{
    width: 100% !important;
    max-width: 360px !important;
    margin: 0 auto !important;
}}
{switch_btn} {{
    background: {LOGIN_SWITCH_BTN_BG} !important;
    background-color: {LOGIN_SWITCH_BTN_BG} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 25px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    padding: 0.75rem 1.5rem !important;
    width: 100% !important;
    min-height: 2.75rem !important;
    height: auto !important;
    box-sizing: border-box !important;
    box-shadow: none !important;
    display: block !important;
}}
.stApp:has(.kahoot-login-switch-marker) [data-testid="stColumn"]:has(.kahoot-login-switch-marker) [data-testid^="stBaseButton"] p,
.stApp:has(.kahoot-login-switch-marker) [data-testid="stColumn"]:has(.kahoot-login-switch-marker) [data-testid^="stBaseButton"] span,
.stApp:has(.kahoot-login-switch-marker) [data-testid="stColumn"]:has(.kahoot-login-switch-marker) button p {{
    color: #ffffff !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.2 !important;
}}
.stApp:has(.kahoot-login-switch-marker) [data-testid="stColumn"]:has(.kahoot-login-switch-marker) button:hover,
.stApp:has(.kahoot-login-switch-marker) [data-testid="stColumn"]:has(.kahoot-login-switch-marker) [data-testid^="stBaseButton"]:hover {{
    background: {LOGIN_SWITCH_BTN_BG_HOVER} !important;
    background-color: {LOGIN_SWITCH_BTN_BG_HOVER} !important;
    color: #ffffff !important;
    border: none !important;
}}
@media (max-width: 768px) {{
    {switch_btn} {{
        padding: 0.75rem 1.5rem !important;
        min-height: 2.75rem !important;
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
    st.markdown(
        f"<style id='kahoot-login-style'>{login_page_css()}</style>",
        unsafe_allow_html=True,
    )


def inject_login_switch_button_css() -> None:
    st.markdown(
        f"<style id='kahoot-login-switch-btn-css'>{login_switch_button_css()}</style>",
        unsafe_allow_html=True,
    )


def inject_login_layout_script() -> None:
    _inject_javascript(
        """
        (function () {
            const THEME_SELECTORS = [
                '[data-testid="stSegmentedControl"]',
                '.kahoot-theme-icons',
                '.kahoot-menu-section-title',
                '[data-testid="stToolbar"]',
                '[data-testid="stHeaderActionElements"]',
                '[data-testid="stStatusWidget"]',
                '[data-testid="stMainMenu"]',
            ];

            function isLoginPage() {
                return Boolean(document.querySelector(".kahoot-login-marker"));
            }

            function markLoginPage() {
                if (!isLoginPage()) return;
                document.body.classList.add("kahoot-on-login");
                document.documentElement.classList.add("kahoot-on-login");
            }

            function isProtectedLoginContent(node) {
                return Boolean(
                    node && node.closest(
                        ".kahoot-left-panel, .kahoot-left-inner, .kahoot-login-marker"
                    )
                );
            }

            function paintLoginSwitchButton() {
                const col = document.querySelector(
                    '[data-testid="stColumn"]:has(.kahoot-login-switch-marker)'
                );
                if (!col) return;
                col.querySelectorAll(
                    'button, [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"], [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryBorderless"]'
                ).forEach((btn) => {
                    btn.style.setProperty("background", "{LOGIN_SWITCH_BTN_BG}", "important");
                    btn.style.setProperty("background-color", "{LOGIN_SWITCH_BTN_BG}", "important");
                    btn.style.setProperty("color", "#ffffff", "important");
                    btn.style.setProperty("border", "none", "important");
                    btn.style.setProperty("border-radius", "25px", "important");
                    btn.style.setProperty("padding", "0.75rem 1.5rem", "important");
                    btn.style.setProperty("min-height", "2.75rem", "important");
                    btn.style.setProperty("height", "auto", "important");
                    btn.style.setProperty("width", "100%", "important");
                    btn.style.setProperty("display", "block", "important");
                    btn.style.setProperty("letter-spacing", "0.08em", "important");
                    btn.style.setProperty("font-weight", "600", "important");
                    btn.style.setProperty("box-sizing", "border-box", "important");
                    btn.querySelectorAll("p, span, div").forEach((node) => {
                        node.style.setProperty("color", "#ffffff", "important");
                        node.style.setProperty("margin", "0", "important");
                        node.style.setProperty("padding", "0", "important");
                    });
                });
                col.querySelectorAll(
                    '.element-container:has([data-testid="stButton"]), .element-container:has(.kahoot-login-switch-marker) + .element-container, [data-testid="stButton"], .stButton'
                ).forEach((wrap) => {
                    wrap.style.setProperty("width", "100%", "important");
                    wrap.style.setProperty("max-width", "360px", "important");
                    wrap.style.setProperty("margin", "0 auto", "important");
                });
            }

            function hideThemeControlsOnLogin() {
                if (!isLoginPage()) return;
                THEME_SELECTORS.forEach((selector) => {
                    document.querySelectorAll(selector).forEach((el) => {
                        if (isProtectedLoginContent(el)) return;
                        const block = el.closest(".element-container") || el;
                        if (isProtectedLoginContent(block)) return;
                        block.style.setProperty("display", "none", "important");
                        block.style.setProperty("visibility", "hidden", "important");
                        block.style.setProperty("height", "0", "important");
                        block.style.setProperty("max-height", "0", "important");
                        block.style.setProperty("overflow", "hidden", "important");
                        block.style.setProperty("opacity", "0", "important");
                        block.style.setProperty("pointer-events", "none", "important");
                    });
                });
            }

            function applyLoginLayout() {
                markLoginPage();
                document.querySelectorAll(".kahoot-login-marker").forEach((marker) => {
                    const row = marker.closest('[data-testid="stHorizontalBlock"]');
                    if (row) row.classList.add("kahoot-login-row");
                });
                hideThemeControlsOnLogin();
                paintLoginSwitchButton();
            }

            applyLoginLayout();
            setTimeout(applyLoginLayout, 50);
            setTimeout(applyLoginLayout, 300);
            setTimeout(applyLoginLayout, 800);
            setTimeout(hideThemeControlsOnLogin, 800);
            window.addEventListener("resize", hideThemeControlsOnLogin);

            const observer = new MutationObserver(() => {
                if (!isLoginPage()) {
                    observer.disconnect();
                    return;
                }
                hideThemeControlsOnLogin();
                paintLoginSwitchButton();
            });
            observer.observe(document.body, { childList: true, subtree: true });
        })();
        """.replace("{LOGIN_SWITCH_BTN_BG}", LOGIN_SWITCH_BTN_BG)
    )


def clear_login_page_styles() -> None:
    _inject_javascript(
        """
        (function () {
            const style = document.getElementById("kahoot-login-style");
            if (style) style.remove();
            document.body.classList.remove("kahoot-on-login");
            document.documentElement.classList.remove("kahoot-on-login");
            document.querySelectorAll(".kahoot-login-row").forEach((row) => {
                row.classList.remove("kahoot-login-row");
            });
            // Remove os estilos inline aplicados por hideThemeControlsOnLogin()
            // na tela de login; sem isso o stToolbar (que contém o botão de
            // expandir a sidebar no Streamlit >= 1.58) fica oculto após o login.
            const HIDDEN_SELECTORS = [
                '[data-testid="stSegmentedControl"]',
                '.kahoot-theme-icons',
                '.kahoot-menu-section-title',
                '[data-testid="stToolbar"]',
                '[data-testid="stHeaderActionElements"]',
                '[data-testid="stStatusWidget"]',
                '[data-testid="stMainMenu"]',
            ];
            const HIDDEN_PROPS = [
                "display", "visibility", "height", "max-height",
                "overflow", "opacity", "pointer-events",
            ];
            HIDDEN_SELECTORS.forEach((selector) => {
                document.querySelectorAll(selector).forEach((el) => {
                    [el, el.closest(".element-container")].forEach((node) => {
                        if (!node) return;
                        HIDDEN_PROPS.forEach((prop) => node.style.removeProperty(prop));
                    });
                });
            });
        })();
        """
    )


def inject_sidebar_session_css() -> None:
    st.markdown(f"<style>{sidebar_session_css()}</style>", unsafe_allow_html=True)


def render_theme_selector(
    *,
    key: str = "ui_theme",
    compact: bool = False,
    icon_only: bool = False,
) -> None:
    if st.session_state.get("role") is None:
        return
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
