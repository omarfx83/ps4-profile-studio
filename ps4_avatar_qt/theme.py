"""Design tokens and the Qt style sheet for PS4 Profile Studio.

The palette matches the previous Tkinter look so the app keeps its dark
identity. Styling is done with Qt Style Sheets (QSS), which Qt renders with
anti-aliasing and full HiDPI support.
"""

# --- palette ---------------------------------------------------------------
BG = "#1b1c1f"
PANEL = "#25272b"
CANVAS_BG = "#141517"
INPUT_BG = "#202226"
FG = "#e8e9eb"
MUTED = "#9aa0a6"
FAINT = "#5c6169"
ACCENT = "#4da3ff"
ACCENT_HOVER = "#74b8ff"
ACCENT_TEXT = "#0e1116"
BTN = "#34373c"
BTN_HOVER = "#41454b"
BORDER = "#3a3d42"
CARD = "#2a2c31"
CARD_HOVER = "#31343a"
DANGER = "#e06c6c"
DANGER_BG = "#3a2a2c"
DANGER_BG_HOVER = "#4a3234"
WARN = "#d8a33a"
SUCCESS = "#5fbf7f"
TRACK = "#26282c"

FONT_FAMILIES = ["Inter", "Segoe UI Variable Text", "Segoe UI", "Tahoma",
                 "sans-serif"]

from .resources import assets_path

_ASSETS = assets_path()

# --- geometry --------------------------------------------------------------
PAD = 14
RADIUS = 10



def build_qss():
    """Return the application style sheet."""
    arrow_down = (_ASSETS / "arrow_down.png").as_posix()
    arrow_up = (_ASSETS / "arrow_up.png").as_posix()
    return f"""
    * {{
        font-family: "Inter", "Segoe UI Variable Text", "Segoe UI", Tahoma,
                     sans-serif;
        font-size: 10pt;
        outline: none;
    }}

    QWidget {{
        background: {BG};
        color: {FG};
    }}
    QWidget#root, QMainWindow {{ background: {BG}; }}

    QLabel {{ background: transparent; color: {FG}; }}
    QLabel[muted="true"] {{ color: {MUTED}; font-size: 9pt; font-weight: 500; }}
    QLabel[faint="true"] {{ color: {FAINT}; font-size: 9pt; font-weight: 500; }}
    QLabel[heading="true"] {{
        color: {MUTED};
        font-size: 9pt;
        font-weight: 600;
        letter-spacing: 1px;
    }}

    /* --- buttons ------------------------------------------------------- */
    QPushButton {{
        background: {BTN};
        color: {FG};
        border: none;
        border-radius: 7px;
        padding: 7px 16px;
        min-height: 20px;
        max-height: 20px;
    }}
    QPushButton:hover {{ background: {BTN_HOVER}; }}
    QPushButton:pressed {{ background: {BTN_HOVER}; }}
    QPushButton:disabled {{ background: #2a2c30; color: #6b6f76; }}

    QPushButton#accent {{ background: {ACCENT}; color: {ACCENT_TEXT}; font-weight: 600; }}
    QPushButton#accent:hover {{ background: {ACCENT_HOVER}; }}
    QPushButton#accent:disabled {{ background: #2f3a48; color: #7d8a99; }}

    QPushButton#ghost {{
        background: transparent;
        color: {FG};
        padding: 7px 12px;
    }}
    QPushButton#ghost:hover {{ background: {TRACK}; }}

    QPushButton#danger {{ background: {DANGER_BG}; color: {DANGER}; }}
    QPushButton#danger:hover {{ background: {DANGER_BG_HOVER}; }}
    QPushButton#danger:disabled {{ background: #2a2c30; color: #6b6f76; }}

    /* --- segmented view switch ---------------------------------------- */
    QFrame#segTrack {{ background: {TRACK}; border-radius: 20px; }}
    QPushButton#seg {{
        background: transparent;
        color: {MUTED};
        border-radius: 15px;
        padding: 6px 24px;
        font-weight: 600;
    }}
    QPushButton#seg:hover {{ color: {FG}; }}
    QPushButton#seg:checked {{ background: {ACCENT}; color: {ACCENT_TEXT}; }}

    /* --- picker tiles -------------------------------------------------- */
    QWidget#pickerPopup, QWidget#pickerBody {{ background: {PANEL}; }}
    QToolButton#symbolCell, QToolButton#emojiCell {{
        background: {CARD};
        border: none;
        border-radius: 8px;
    }}
    QToolButton#symbolCell:hover, QToolButton#emojiCell:hover {{
        background: {CARD_HOVER};
    }}
    QToolButton#emojiCell {{
        font-family: "Segoe UI Emoji", "Apple Color Emoji",
                     "Noto Color Emoji", "Segoe UI Symbol", sans-serif;
        font-size: 17pt;
    }}
    QToolButton#emojiCell:disabled {{ color: {FAINT}; }}

    /* --- skin tone swatches ------------------------------------------- */
    QLabel#pickerNotice {{
        color: {WARN};
        font-size: 9pt;
        font-weight: 600;
        padding: 2px 0;
    }}

    QLabel#nameCounter {{ color: {MUTED}; font-size: 9pt; font-weight: 600; }}
    QLabel#nameCounter[full="true"] {{ color: {WARN}; }}

    /* --- inputs -------------------------------------------------------- */
    QLineEdit {{
        background: {INPUT_BG};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 20px;
        max-height: 20px;
        selection-background-color: {ACCENT};
        selection-color: {ACCENT_TEXT};
    }}
    QLineEdit:focus {{ border: 1px solid {ACCENT}; }}

    QSpinBox {{
        background: {INPUT_BG};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 20px 6px 8px;
        min-height: 20px;
        max-height: 20px;
    }}
    QSpinBox:focus {{ border: 1px solid {ACCENT}; }}
    QSpinBox::up-button, QSpinBox::down-button {{
        width: 16px;
        border: none;
        background: transparent;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background: {BTN_HOVER};
        border-radius: 4px;
    }}
    QSpinBox::up-arrow {{ image: url("{arrow_up}"); width: 14px; height: 9px; }}
    QSpinBox::down-arrow {{ image: url("{arrow_down}"); width: 14px; height: 9px; }}

    /* --- combo box ----------------------------------------------------- */
    QComboBox {{
        background: {INPUT_BG};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 26px 6px 10px;
        min-height: 20px;
        max-height: 20px;
        min-width: 96px;
    }}
    QComboBox:hover {{ border: 1px solid {MUTED}; }}
    QComboBox:focus {{ border: 1px solid {ACCENT}; }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
        background: transparent;
    }}
    QComboBox::down-arrow {{
        image: url("{arrow_down}");
        width: 14px;
        height: 9px;
    }}
    /* Editable combos contain a QLineEdit: keep it borderless inside. */
    QComboBox QLineEdit {{
        background: transparent;
        border: none;
        padding: 0;
        min-height: 0;
    }}

    /* --- dropdown / menu cards ----------------------------------------- */
    QListView#popupList {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListView#popupList::item {{
        color: {FG};
        padding: 6px 9px;
        border-radius: 7px;
        min-height: 20px;
    }}
    QListView#popupList::item:hover {{
        background: {ACCENT};
        color: {ACCENT_TEXT};
    }}
    QPushButton#menuRow {{
        background: transparent;
        border: none;
        border-radius: 7px;
        color: {FG};
        text-align: left;
        padding: 7px 10px;
        min-width: 150px;
    }}
    QPushButton#menuRow:hover {{
        background: {ACCENT};
        color: {ACCENT_TEXT};
    }}
    QPushButton#menuRow:disabled {{
        color: {FAINT};
        background: transparent;
    }}
    QFrame#menuSeparator {{
        background: {BORDER};
        border: none;
    }}
    QToolButton#deviceMenu {{
        background: transparent;
        border: none;
        border-radius: 8px;
        color: {MUTED};
        font-size: 13pt;
        padding: 0 6px;
        min-width: 20px;
    }}
    QToolButton#deviceMenu:hover {{ background: {TRACK}; color: {FG}; }}
    QToolButton#deviceMenu:pressed {{ background: {BTN}; }}
    QToolButton#deviceMenu:disabled {{ color: #4a4d52; }}
    QToolButton#deviceMenu::menu-indicator {{ image: none; width: 0; }}

    /* --- progress ------------------------------------------------------ */
    QProgressBar {{
        background: #2a2c30;
        border: none;
        border-radius: 4px;
        height: 8px;
        text-align: center;
    }}
    QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}

    /* --- scroll areas / bars ------------------------------------------ */
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px 2px;
    }}
    QScrollBar::handle:vertical {{
        background: #454a52;
        border-radius: 3px;
        min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{ background: #5c6169; }}
    QScrollBar::handle:vertical:pressed {{ background: {ACCENT}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{ height: 0; }}

    /* --- frames -------------------------------------------------------- */
    QFrame#card {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 10px;
    }}
    QFrame#card[selected="true"] {{
        border: 1px solid {ACCENT};
        background: {CARD_HOVER};
    }}
    QFrame#panel {{ background: {PANEL}; border: none; border-radius: 10px; }}
    QFrame#separator {{ background: {BORDER}; max-height: 1px; min-height: 1px; }}
    QFrame#listBg {{ background: {CANVAS_BG}; border: none; border-radius: 10px; }}

    QToolTip {{
        background: {PANEL};
        color: {FG};
        border: 1px solid {BORDER};
        padding: 4px 6px;
    }}
    """
