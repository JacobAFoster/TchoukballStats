"""Configuration constants and default settings for Tchoukball Stats."""

DB_NAME = "my_database.db"
SETTINGS_FILE = "settings.json"
BACKUPS_DIR = "backups"
MAX_BACKUPS = 20

# Palette
BG        = "#12141a"
SURFACE   = "#1b1e26"
SURFACE_2 = "#252a36"
STRIPE    = "#20242f"
BORDER    = "#2f3546"
FG        = "#e8eaf0"
MUTED     = "#8b93a7"
ACCENT    = "#4c8dff"
ACCENT_HI = "#6aa1ff"
DANGER    = "#ff6b6b"
DANGER_BG = "#8f2d2d"

# Fonts
FONT    = "Segoe UI"
F_TITLE = (FONT, 18, "bold")
F_BODY  = (FONT, 10)
F_SMALL = (FONT, 9)
F_CAPS  = (FONT, 9, "bold")

# Chart Colors
CHART_COLORS = [
    "#4c8dff", "#6ee7b7", "#fbbf24", "#f472b6",
    "#a78bfa", "#f87171", "#22d3ee", "#fb923c",
    "#a3e635", "#e879f9", "#38bdf8", "#facc15",
]

PERIOD_COLORS = [
    "#4c8dff", "#6ee7b7", "#fbbf24", "#f472b6",
    "#a78bfa", "#f87171", "#22d3ee", "#fb923c",
]

DEFAULT_SETTINGS = {
    "win_points": 3,
    "draw_points": 1,
    "loss_points": 0,
    "layout_order": ["actions"],
    "action_card_order": ["BROWSE", "ADD", "EDIT", "REMOVE"],
    "main_bg": "#121212", # (or whatever your default BG is)
    "section_bg": {
        "actions": "#1e1e1e"
    },
    "section_title_color": {
        "actions": "#888888"
    }
}