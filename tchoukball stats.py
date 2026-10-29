"""Tchoukball Stats – dark-themed Tkinter dashboard with tournaments."""

from tkinter import *
from tkinter import ttk, messagebox, simpledialog, colorchooser
from tkinter.font import Font as TkFont
import tkinter as tk
import sqlite3
import datetime
import json
import os
import sys
DB = "my_database.db"

# ------------------------------------------------------------------ palette
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

FONT    = "Segoe UI"
F_TITLE = (FONT, 18, "bold")
F_BODY  = (FONT, 10)
F_SMALL = (FONT, 9)
F_CAPS  = (FONT, 9, "bold")


# ------------------------------------------------------------------ connection
def connect_db():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ------------------------------------------------------------------ settings
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "win_points": 2,
    "draw_points": 1,
    "loss_points": 0,
    "calendar_starts_monday": True,
    "recent_matches_count": 10,
    "auto_open_roster_after_match": True,
    "focus_tournament_id": None,
    # --- layout & appearance ---
    "layout_order": ["actions", "dashboard", "calendar"],
    "section_bg": {
        "actions":   "#1b1e26",
        "dashboard": "#1b1e26",
        "calendar":  "#1b1e26",
    },
    "section_title_color": {
        "actions":   "#8b93a7",
        "dashboard": "#8b93a7",
        "calendar":  "#8b93a7",
    },
}


def _is_hex_colour(value):
    if not isinstance(value, str):
        return False
    if len(value) not in (4, 7) or not value.startswith("#"):
        return False
    return all(c in "0123456789abcdefABCDEF" for c in value[1:])


def _validate_layout_and_colours(merged):
    """Post-validate the complex (nested) settings after load."""
    valid_sections = ["actions", "dashboard", "calendar"]

    layout = merged.get("layout_order")
    if not isinstance(layout, list):
        merged["layout_order"] = list(DEFAULT_SETTINGS["layout_order"])
    else:
        cleaned = [s for s in layout if s in valid_sections]
        for s in valid_sections:
            if s not in cleaned:
                cleaned.append(s)
        merged["layout_order"] = cleaned

    for key in ("section_bg", "section_title_color"):
        raw = merged.get(key)
        default = DEFAULT_SETTINGS[key]
        if not isinstance(raw, dict):
            merged[key] = dict(default)
            continue
        cleaned = {}
        for section, default_colour in default.items():
            colour = raw.get(section)
            cleaned[section] = (colour
                                if _is_hex_colour(colour)
                                else default_colour)
        merged[key] = cleaned


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(DEFAULT_SETTINGS)
        merged = dict(DEFAULT_SETTINGS)
        for key, value in data.items():
            if key in DEFAULT_SETTINGS:
                merged[key] = value
        _validate_layout_and_colours(merged)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(SETTINGS, f, indent=2)
    except OSError as exc:
        messagebox.showerror("Could not save settings", str(exc))


SETTINGS = load_settings()


# ------------------------------------------------------------------ backups
BACKUPS_DIR = "backups"
MAX_BACKUPS = 20


def _backup_db(reason="auto"):
    """Snapshot my_database.db into backups/ with a timestamp.
    Keeps the newest MAX_BACKUPS files; older ones are pruned silently.
    Returns the backup path, or None if the DB doesn't exist or copy fails."""
    if not os.path.exists(DB):
        return None
    try:
        import shutil
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_reason = "".join(c for c in reason
                              if c.isalnum() or c in "-_")[:20]
        name = (f"{stamp}_{safe_reason}.db" if safe_reason
                else f"{stamp}.db")
        dest = os.path.join(BACKUPS_DIR, name)
        shutil.copy2(DB, dest)
        entries = sorted(
            (os.path.join(BACKUPS_DIR, f) for f in os.listdir(BACKUPS_DIR)
             if f.endswith(".db")),
            key=lambda p: os.path.getmtime(p),
            reverse=True,
        )
        for old in entries[MAX_BACKUPS:]:
            try:
                os.remove(old)
            except OSError:
                pass
        return dest
    except OSError:
        return None


def _open_backups_folder():
    try:
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(BACKUPS_DIR)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", BACKUPS_DIR])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", BACKUPS_DIR])
    except Exception as exc:
        messagebox.showerror("Could not open folder", str(exc))


# ------------------------------------------------------------------ database
def init_db():
    with connect_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS Teams (
          TeamID   INTEGER PRIMARY KEY,
          TeamName TEXT NOT NULL UNIQUE,
          ClubID   INTEGER REFERENCES Clubs(ClubID)
        );
        CREATE TABLE IF NOT EXISTS Clubs (
          ClubID   INTEGER PRIMARY KEY,
          ClubName TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS Players (
          PlayerID        INTEGER PRIMARY KEY,
          PlayerName      TEXT NOT NULL,
          PlayerSurname   TEXT,
          TeamID          INTEGER REFERENCES Teams(TeamID),
          PlayerBirthdate TEXT
        );
        CREATE TABLE IF NOT EXISTS Tournaments (
          TournamentID       INTEGER PRIMARY KEY,
          TournamentName     TEXT NOT NULL UNIQUE,
          TournamentDate     TEXT,
          TournamentLocation TEXT
        );
        CREATE TABLE IF NOT EXISTS Matches (
          MatchID         INTEGER PRIMARY KEY,
          MatchHome       INTEGER NOT NULL,
          MatchAway       INTEGER NOT NULL,
          MatchLocation   TEXT,
          MatchHScore     INTEGER,
          MatchAScore     INTEGER,
          TournamentID    INTEGER,
          MatchDate       TEXT,
          PeriodCount     INTEGER,
          PeriodMinutes   INTEGER,
          FOREIGN KEY (MatchHome) REFERENCES Teams(TeamID),
          FOREIGN KEY (MatchAway) REFERENCES Teams(TeamID),
          FOREIGN KEY (TournamentID) REFERENCES Tournaments(TournamentID)
        );
        CREATE TABLE IF NOT EXISTS MatchPeriods (
          MatchID       INTEGER NOT NULL,
          PeriodNumber  INTEGER NOT NULL,
          HomeScore     INTEGER DEFAULT 0,
          AwayScore     INTEGER DEFAULT 0,
          PeriodMinutes INTEGER,
          PRIMARY KEY (MatchID, PeriodNumber),
          FOREIGN KEY (MatchID) REFERENCES Matches(MatchID)
        );
        CREATE TABLE IF NOT EXISTS MatchRoster (
          MatchID      INTEGER NOT NULL,
          TeamID       INTEGER NOT NULL,
          PlayerID     INTEGER NOT NULL,
          PlayerPoints INTEGER DEFAULT 0,
          PRIMARY KEY (MatchID, PlayerID),
          FOREIGN KEY (MatchID)  REFERENCES Matches(MatchID),
          FOREIGN KEY (TeamID)   REFERENCES Teams(TeamID),
          FOREIGN KEY (PlayerID) REFERENCES Players(PlayerID)
        );
        """)
        # Structural migrations — add one tuple here whenever a new
        # column is introduced. Old databases get upgraded in place.
        MIGRATIONS = [
            ("Matches",     "TournamentID",
             "ALTER TABLE Matches ADD COLUMN TournamentID INTEGER"),
            ("Matches",     "MatchDate",
             "ALTER TABLE Matches ADD COLUMN MatchDate TEXT"),
            ("Teams",       "ClubID",
             "ALTER TABLE Teams ADD COLUMN ClubID INTEGER"),
            ("Players",     "TeamID",
             "ALTER TABLE Players ADD COLUMN TeamID INTEGER"),
            ("Players",     "PlayerBirthdate",
             "ALTER TABLE Players ADD COLUMN PlayerBirthdate TEXT"),
            ("MatchRoster", "PlayerPoints",
             "ALTER TABLE MatchRoster ADD COLUMN PlayerPoints INTEGER DEFAULT 0"),
            ("Matches",     "PeriodCount",
             "ALTER TABLE Matches ADD COLUMN PeriodCount INTEGER"),
            ("Matches",     "PeriodMinutes",
             "ALTER TABLE Matches ADD COLUMN PeriodMinutes INTEGER"),
        ]
        for table, column, ddl in MIGRATIONS:
            existing = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
            if column not in existing:
                conn.execute(ddl)

        # Indexes for the queries the app makes most often.
        conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_matches_date       ON Matches(MatchDate);
        CREATE INDEX IF NOT EXISTS idx_matches_home       ON Matches(MatchHome);
        CREATE INDEX IF NOT EXISTS idx_matches_away       ON Matches(MatchAway);
        CREATE INDEX IF NOT EXISTS idx_matches_tournament ON Matches(TournamentID);
        CREATE INDEX IF NOT EXISTS idx_roster_player      ON MatchRoster(PlayerID);
        CREATE INDEX IF NOT EXISTS idx_roster_match       ON MatchRoster(MatchID);
        CREATE INDEX IF NOT EXISTS idx_roster_team        ON MatchRoster(TeamID);
        CREATE INDEX IF NOT EXISTS idx_players_team       ON Players(TeamID);
        CREATE INDEX IF NOT EXISTS idx_teams_club         ON Teams(ClubID);
        """)


# ------------------------------------------------------------------ helpers
def center_window(win, width, height):
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{width}x{height}+{(sw - width) // 2}+{(sh - height) // 3}")


def apply_theme(win):
    style = ttk.Style(win)
    style.theme_use("clam")
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE,
                    foreground=FG, rowheight=26, borderwidth=0, font=F_BODY)
    style.configure("Treeview.Heading", background=SURFACE_2, foreground=MUTED,
                    relief="flat", borderwidth=0,
                    font=(FONT, 9, "bold"), padding=(10, 7))
    style.map("Treeview.Heading", background=[("active", BORDER)])
    style.map("Treeview", background=[("selected", ACCENT)],
              foreground=[("selected", "#ffffff")])
    style.configure("Vertical.TScrollbar", background=SURFACE_2,
                    troughcolor=BG, bordercolor=BG, arrowcolor=MUTED,
                    relief="flat", borderwidth=0)
    style.map("Vertical.TScrollbar", background=[("active", BORDER)])
    style.configure("TCombobox", padding=6, arrowsize=14,
                    fieldbackground=SURFACE, background=SURFACE_2,
                    foreground=FG, arrowcolor=FG, borderwidth=0)
    style.map("TCombobox",
              fieldbackground=[("readonly", SURFACE)],
              foreground=[("readonly", FG)],
              selectbackground=[("readonly", SURFACE)],
              selectforeground=[("readonly", FG)],
              bordercolor=[("focus", ACCENT)],
              arrowcolor=[("active", ACCENT)])
    win.option_add("*TCombobox*Listbox.background", SURFACE_2)
    win.option_add("*TCombobox*Listbox.foreground", FG)
    win.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    win.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")


def make_button(parent, text, command, accent=False, danger=False, anchor="w"):
    if danger:
        base, hover, fg = DANGER_BG, DANGER, "#ffffff"
    elif accent:
        base, hover, fg = ACCENT, ACCENT_HI, "#ffffff"
    else:
        base, hover, fg = SURFACE_2, BORDER, FG
    btn = tk.Button(parent, text=text, command=command,
                    bg=base, fg=fg, activebackground=hover, activeforeground=fg,
                    relief="flat", bd=0, highlightthickness=0,
                    anchor=anchor, padx=14, pady=8, cursor="hand2", font=F_BODY)
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda e: btn.configure(bg=base))
    return btn


def make_small_button(parent, text, command, danger=False):
    if danger:
        base, hover, fg = DANGER_BG, DANGER, "#ffffff"
    else:
        base, hover, fg = SURFACE_2, BORDER, FG
    btn = tk.Button(parent, text=text, command=command,
                    bg=base, fg=fg, activebackground=hover, activeforeground=fg,
                    relief="flat", bd=0, highlightthickness=0,
                    anchor="w", padx=10, pady=5, cursor="hand2", font=F_SMALL)
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda e: btn.configure(bg=base))
    return btn


# ------------------------------------------------------------------ date picker
def open_date_picker(parent_win, entry_widget):
    """Popup mini-calendar that writes YYYY-MM-DD into entry_widget."""
    initial = entry_widget.get().strip()
    try:
        start = datetime.datetime.strptime(initial, "%Y-%m-%d").date()
    except ValueError:
        start = datetime.date.today()

    pop = Toplevel(parent_win)
    pop.overrideredirect(True)
    pop.configure(bg=SURFACE, highlightbackground=BORDER,
                  highlightthickness=1)
    pop.transient(parent_win)

    state = {"year": start.year, "month": start.month, "selected": start}

    head = tk.Frame(pop, bg=SURFACE)
    head.pack(fill="x", padx=6, pady=(6, 4))
    title_lbl = tk.Label(head, text="", bg=SURFACE, fg=FG,
                         font=(FONT, 10, "bold"))
    title_lbl.pack(side="left", fill="x", expand=True, padx=(2, 0))

    def shift(delta):
        y, m = state["year"], state["month"]
        m += delta
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        state["year"], state["month"] = y, m
        render()

    make_small_button(head, "‹", lambda: shift(-1)).pack(side="right", padx=1)
    make_small_button(head, "›", lambda: shift(1)).pack(side="right", padx=1)

    grid = tk.Frame(pop, bg=SURFACE)
    grid.pack(padx=6, pady=(0, 6))

    day_names = (["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
                 if SETTINGS["calendar_starts_monday"]
                 else ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"])
    for i, n in enumerate(day_names):
        tk.Label(grid, text=n, bg=SURFACE, fg=MUTED, font=(FONT, 8),
                 width=3).grid(row=0, column=i, padx=1, pady=(0, 2))

    cells = []
    for r in range(6):
        row = []
        for c in range(7):
            lbl = tk.Label(grid, text="", bg=SURFACE, fg=FG,
                           font=(FONT, 9), width=3, height=1)
            lbl.grid(row=r + 1, column=c, padx=1, pady=1)
            row.append(lbl)
        cells.append(row)

    today = datetime.date.today()

    def pick(d):
        entry_widget.delete(0, "end")
        entry_widget.insert(0, d.isoformat())
        try:
            pop.grab_release()
        except Exception:
            pass
        pop.destroy()

    def render():
        first = datetime.date(state["year"], state["month"], 1)
        next_m = (datetime.date(state["year"] + 1, 1, 1)
                  if state["month"] == 12
                  else datetime.date(state["year"], state["month"] + 1, 1))
        title_lbl.configure(text=first.strftime("%B %Y"))

        offset = first.weekday()
        if not SETTINGS["calendar_starts_monday"]:
            offset = (offset + 1) % 7
        days = (next_m - first).days

        for r in range(6):
            for c in range(7):
                idx = r * 7 + c
                day_num = idx - offset + 1
                lbl = cells[r][c]
                if day_num < 1 or day_num > days:
                    lbl.configure(text="", bg=SURFACE, cursor="")
                    lbl.unbind("<Button-1>")
                    continue
                d = datetime.date(state["year"], state["month"], day_num)
                lbl.configure(text=str(day_num), cursor="hand2")
                if d == state["selected"]:
                    lbl.configure(bg=ACCENT, fg="#ffffff",
                                  font=(FONT, 9, "bold"))
                elif d == today:
                    lbl.configure(bg=SURFACE_2, fg=ACCENT,
                                  font=(FONT, 9, "bold"))
                else:
                    lbl.configure(bg=SURFACE, fg=FG, font=(FONT, 9))
                lbl.bind("<Button-1>", lambda e, dd=d: pick(dd))

    render()

    pop.update_idletasks()
    x = entry_widget.winfo_rootx()
    y = entry_widget.winfo_rooty() + entry_widget.winfo_height() + 2
    pop.geometry(f"+{x}+{y}")

    pop.bind("<Escape>", lambda e: (pop.grab_release(), pop.destroy()))
    pop.grab_set()
    try:
        pop.focus_set()
    except Exception:
        pass


def card_frame(parent, title, bg=None, title_fg=None, **grid_kwargs):
    bg = bg or SURFACE
    title_fg = title_fg or MUTED
    outer = tk.Frame(parent, bg=bg,
                     highlightbackground=BORDER, highlightthickness=1)
    outer.grid(sticky="nsew", **grid_kwargs)
    inner = tk.Frame(outer, bg=bg, padx=12, pady=12)
    inner.pack(fill="both", expand=True)
    tk.Label(inner, text=title, bg=bg, fg=title_fg,
             font=F_CAPS).pack(anchor="w", pady=(0, 8))
    return inner


# ------------------------------------------------------------------ autofit
def attach_autofit(tree, min_width=60, max_width=600, pad=28):
    """Double-click any column heading to auto-fit that column's width."""
    measure = TkFont(font=F_BODY)

    def _autofit(col_id):
        try:
            list(tree["columns"]).index(col_id)
        except ValueError:
            return
        raw = str(tree.heading(col_id, "text"))
        text = raw.replace(" ▲", "").replace(" ▼", "")
        widest = measure.measure(text)
        for iid in tree.get_children(""):
            w = measure.measure(str(tree.set(iid, col_id)))
            if w > widest:
                widest = w
        new_w = max(min_width, min(widest + pad, max_width))
        tree.column(col_id, width=new_w)

    def _on_dbl(event):
        if tree.identify_region(event.x, event.y) != "heading":
            return
        col = tree.identify_column(event.x)
        try:
            i = int(col[1:]) - 1
            _autofit(tree["columns"][i])
        except (ValueError, IndexError):
            pass
        return "break"

    tree.bind("<Double-1>", _on_dbl, add="+")


# ------------------------------------------------------------------ cascade helpers
class DeletionCancelled(Exception):
    pass


def _prompt_cascade_teams(team_names, matches, orphan_count):
    """Modal listing of all matches affected by deleting 1+ teams."""
    win = Toplevel(root)
    win.title(f"Remove {len(team_names)} team(s) — affected matches")
    win.configure(bg=BG)
    win.transient(root)
    center_window(win, 780, 520)
    win.minsize(600, 400)
    win.grab_set()
    win.bind("<Escape>", lambda e: win.destroy())

    plural = len(team_names) > 1
    header = (f"Remove {len(team_names)} teams" if plural
              else f'Remove "{team_names[0]}"')

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 10))
    tk.Label(head, text=header, bg=BG, fg=FG,
             font=F_TITLE).pack(anchor="w")

    lines = []
    if plural:
        lines.append(f"These {len(team_names)} teams appear in "
                     f"{len(matches)} match(es) in total.")
    else:
        lines.append(f"This team appears in {len(matches)} match(es).")
    if orphan_count:
        lines.append(f"{orphan_count} player(s) currently on "
                     f"{'these teams' if plural else 'this team'} "
                     f"will become unassigned.")
    lines.append("Confirming below will delete the matches listed (and "
                 "their rosters and period data) along with the team"
                 f"{'s' if plural else ''}. This cannot be undone.")
    tk.Label(head, text="\n".join(lines), bg=BG, fg=MUTED, font=F_SMALL,
             justify="left", wraplength=720
             ).pack(anchor="w", pady=(4, 0))

    shell = tk.Frame(win, bg=BORDER)
    shell.pack(fill="both", expand=True, padx=22, pady=(0, 10))
    tree = ttk.Treeview(
        shell, show="headings", selectmode="none",
        columns=["ID", "Date", "Home", "Score", "Away", "Tournament"])
    sb = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w in zip(["ID", "Date", "Home", "Score", "Away", "Tournament"],
                      [55, 100, 130, 70, 130, 140]):
        tree.heading(col, text=col, anchor="w")
        tree.column(col, width=w, minwidth=40, anchor="w",
                    stretch=(col in ("Home", "Away", "Tournament")))
    tree.tag_configure("row_even", background=SURFACE)
    tree.tag_configure("row_odd",  background=STRIPE)
    for i, m in enumerate(matches):
        tree.insert("", "end", values=m,
                    tags=("row_even" if i % 2 == 0 else "row_odd",))

    actions = tk.Frame(win, bg=BG)
    actions.pack(fill="x", padx=22, pady=(0, 20))

    result = [False]
    def on_confirm():
        result[0] = True
        win.destroy()

    label = (f"Delete {len(team_names)} teams + {len(matches)} match(es)"
             if plural
             else f"Delete team + {len(matches)} match(es)")
    make_button(actions, label, on_confirm, danger=True, anchor="center"
                ).pack(side="right")
    make_button(actions, "Cancel", win.destroy, anchor="center"
                ).pack(side="right", padx=(0, 8))

    win.wait_window()
    return result[0]


def cascade_delete_teams_bulk(conn, team_ids):
    """Cascade delete for 1+ teams. One aggregated prompt for the batch."""
    if not team_ids:
        return
    ph = ",".join("?" * len(team_ids))
    team_names = [r[0] for r in conn.execute(
        f"SELECT TeamName FROM Teams WHERE TeamID IN ({ph})", team_ids
    ).fetchall()]

    matches = conn.execute(f"""
        SELECT m.MatchID,
               COALESCE(m.MatchDate, '-'),
               ht.TeamName,
               COALESCE(m.MatchHScore, '-') || ' – ' ||
               COALESCE(m.MatchAScore, '-'),
               at.TeamName,
               COALESCE(t.TournamentName, '—')
        FROM Matches m
        JOIN Teams ht ON m.MatchHome = ht.TeamID
        JOIN Teams at ON m.MatchAway = at.TeamID
        LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
        WHERE m.MatchHome IN ({ph}) OR m.MatchAway IN ({ph})
        ORDER BY COALESCE(m.MatchDate, ''), m.MatchID
    """, team_ids + team_ids).fetchall()

    orphan_count = conn.execute(
        f"SELECT COUNT(*) FROM Players WHERE TeamID IN ({ph})", team_ids
    ).fetchone()[0]

    if matches:
        if not _prompt_cascade_teams(team_names, matches, orphan_count):
            raise DeletionCancelled()
        match_ids = [m[0] for m in matches]
        mph = ",".join("?" * len(match_ids))
        conn.execute(f"DELETE FROM MatchPeriods WHERE MatchID IN ({mph})",
                     match_ids)
        conn.execute(f"DELETE FROM MatchRoster WHERE MatchID IN ({mph})",
                     match_ids)
        conn.execute(f"DELETE FROM Matches WHERE MatchID IN ({mph})",
                     match_ids)

    conn.execute(f"UPDATE Players SET TeamID = NULL WHERE TeamID IN ({ph})",
                 team_ids)
    conn.execute(f"DELETE FROM MatchRoster WHERE TeamID IN ({ph})", team_ids)


def cascade_delete_team(conn, team_id):
    """Single-team wrapper used by edit_team as pre_delete."""
    cascade_delete_teams_bulk(conn, [team_id])


# ------------------------------------------------------------------ delete helper
def perform_delete(table, id_col, rid, pre_delete=None):
    """Single entry point for record deletion.

    Returns (True, None) on success, (False, error_message) on IntegrityError.
    Raises DeletionCancelled if the caller's pre_delete opted out.
    A timestamped backup is taken before every delete so accidental losses
    can be recovered from the backups/ folder.
    """
    _backup_db(f"delete_{table.lower()}")
    try:
        with connect_db() as conn:
            if pre_delete:
                pre_delete(conn, rid)
            conn.execute(f"DELETE FROM {table} WHERE {id_col} = ?", (rid,))
        return True, None
    except sqlite3.IntegrityError as exc:
        return False, str(exc)


def perform_delete_bulk(table, id_col, rids, pre_delete=None, bulk_handler=None):
    """Delete multiple records in one transaction with one backup.

    bulk_handler(conn, rids) runs once before the delete loop (used for teams
    to show a single aggregated cascade prompt). pre_delete(conn, rid) runs
    per record. Raises DeletionCancelled if bulk_handler cancels; otherwise
    returns (deleted_count, errors_list).
    """
    if not rids:
        return 0, []
    _backup_db(f"bulk_{table.lower()}")
    deleted = 0
    errors = []
    try:
        with connect_db() as conn:
            if bulk_handler:
                bulk_handler(conn, rids)
            for rid in rids:
                try:
                    if pre_delete:
                        pre_delete(conn, rid)
                    conn.execute(f"DELETE FROM {table} WHERE {id_col} = ?",
                                 (rid,))
                    deleted += 1
                except sqlite3.IntegrityError as exc:
                    errors.append((rid, str(exc)))
    except DeletionCancelled:
        raise
    except Exception as exc:
        errors.append((None, str(exc)))
    return deleted, errors


def delete_row_direct(table, id_col, rid, label, pre_delete=None):
    """Ask confirmation, then delete a single record in one step."""
    if not messagebox.askyesno(
            "Delete", f"Delete {label}?\nThis cannot be undone."):
        return
    try:
        ok, err = perform_delete(table, id_col, rid, pre_delete)
    except DeletionCancelled:
        set_status("Deletion cancelled.")
        return
    if ok:
        set_status(f"Deleted {label}.")
        root.event_generate("<<DataChanged>>")
    else:
        set_status(f"Cannot delete: {err}", error=True)
        messagebox.showerror(
            "Cannot delete",
            f"This record is still referenced by other records.\n\n{err}")


def _check_requires(requires, count):
    if requires is None:
        return True
    if requires == "one":
        return count == 1
    if requires == "two":
        return count == 2
    if requires == "many":
        return count >= 1
    return True


def _clean_match_deps(conn, mid):
    """Remove everything that FKs into Matches(MatchID)."""
    conn.execute("DELETE FROM MatchPeriods WHERE MatchID = ?", (mid,))
    conn.execute("DELETE FROM MatchRoster WHERE MatchID = ?", (mid,))


# ------------------------------------------------------------------ filters
class CompareFilters:
    def __init__(self, tournament_id=None, date_from=None, date_to=None):
        self.tournament_id = tournament_id
        self.date_from = date_from
        self.date_to = date_to

    def sql_fragment(self, alias="m"):
        parts = []
        params = {}
        if self.tournament_id is not None:
            parts.append(f"{alias}.TournamentID = :f_tid")
            params["f_tid"] = self.tournament_id
        if self.date_from:
            parts.append(f"{alias}.MatchDate >= :f_df")
            params["f_df"] = self.date_from
        if self.date_to:
            parts.append(f"{alias}.MatchDate <= :f_dt")
            params["f_dt"] = self.date_to
        sql = (" AND " + " AND ".join(parts)) if parts else ""
        return sql, params


# ------------------------------------------------------------------ points helpers
def team_points_sql(conn, team_id, filters=None):
    f_sql, f_params = (filters.sql_fragment("m") if filters else ("", {}))
    wp = SETTINGS["win_points"]
    dp = SETTINGS["draw_points"]
    lp = SETTINGS["loss_points"]
    return conn.execute(f"""
        SELECT COALESCE(SUM(CASE
          WHEN m.MatchHome = :tid AND m.MatchHScore > m.MatchAScore THEN {wp}
          WHEN m.MatchAway = :tid AND m.MatchAScore > m.MatchHScore THEN {wp}
          WHEN m.MatchHScore = m.MatchAScore THEN {dp}
          ELSE {lp} END), 0)
        FROM Matches m
        WHERE (m.MatchHome = :tid OR m.MatchAway = :tid)
          AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
          {f_sql}
    """, {"tid": team_id, **f_params}).fetchone()[0]


def club_points_sql(conn, club_id, filters=None):
    f_sql, f_params = (filters.sql_fragment("m") if filters else ("", {}))
    wp = SETTINGS["win_points"]
    dp = SETTINGS["draw_points"]
    lp = SETTINGS["loss_points"]
    return conn.execute(f"""
        SELECT COALESCE(SUM(CASE
          WHEN m.MatchHome IN (SELECT TeamID FROM Teams WHERE ClubID = :cid)
            AND m.MatchHScore > m.MatchAScore THEN {wp}
          WHEN m.MatchAway IN (SELECT TeamID FROM Teams WHERE ClubID = :cid)
            AND m.MatchAScore > m.MatchHScore THEN {wp}
          WHEN m.MatchHScore = m.MatchAScore THEN {dp}
          ELSE {lp} END), 0)
        FROM Matches m
        WHERE (m.MatchHome IN (SELECT TeamID FROM Teams WHERE ClubID = :cid)
            OR m.MatchAway IN (SELECT TeamID FROM Teams WHERE ClubID = :cid))
          AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
          {f_sql}
    """, {"cid": club_id, **f_params}).fetchone()[0]


def player_points_sql(conn, player_id, filters=None):
    """Sum of individual goals scored by a player across rostered matches."""
    f_sql, f_params = (filters.sql_fragment("m") if filters else ("", {}))
    return conn.execute(f"""
        SELECT COALESCE(SUM(r.PlayerPoints), 0)
        FROM MatchRoster r
        JOIN Matches m ON m.MatchID = r.MatchID
        WHERE r.PlayerID = :pid
          AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
          {f_sql}
    """, {"pid": player_id, **f_params}).fetchone()[0]


# ------------------------------------------------------------------ settings dialog
def open_settings():
    win = Toplevel(root)
    win.title("Settings")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.transient(root)
    win.grab_set()
    win.bind("<Escape>", lambda e: win.destroy())

    body = tk.Frame(win, bg=BG, padx=24, pady=22)
    body.pack(fill="both", expand=True)

    tk.Label(body, text="Settings", bg=BG, fg=FG,
             font=F_TITLE).pack(anchor="w")
    tk.Label(body, text="Changes are saved to settings.json and applied "
                        "immediately.",
             bg=BG, fg=MUTED, font=F_SMALL,
             justify="left").pack(anchor="w", pady=(2, 16))

    # --- points
    tk.Label(body, text="POINTS SYSTEM", bg=BG, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(0, 4))
    tk.Label(body, text="Used by the standings and team/club totals.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(0, 6))

    pts_frame = tk.Frame(body, bg=BG)
    pts_frame.pack(fill="x", pady=(0, 14))
    win_var = StringVar(value=str(SETTINGS["win_points"]))
    draw_var = StringVar(value=str(SETTINGS["draw_points"]))
    loss_var = StringVar(value=str(SETTINGS["loss_points"]))
    for i, (label, var) in enumerate((
            ("Win", win_var), ("Draw", draw_var), ("Loss", loss_var))):
        tk.Label(pts_frame, text=label, bg=BG, fg=FG, font=F_BODY,
                 width=6, anchor="w").grid(row=0, column=i * 2,
                                            sticky="w", padx=(0, 6))
        tk.Entry(pts_frame, textvariable=var, bg=SURFACE, fg=FG,
                 insertbackground=FG, relief="flat", highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=ACCENT,
                 font=F_BODY, width=6
                 ).grid(row=0, column=i * 2 + 1, sticky="w",
                        padx=(0, 16), ipady=4)

    # --- display
    tk.Label(body, text="DISPLAY", bg=BG, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(0, 4))

    mon_var = BooleanVar(value=SETTINGS["calendar_starts_monday"])
    tk.Checkbutton(body, text="Calendar week starts on Monday",
                   variable=mon_var, bg=BG, fg=FG,
                   selectcolor=SURFACE, activebackground=BG,
                   activeforeground=FG, font=F_BODY,
                   highlightthickness=0
                   ).pack(anchor="w", pady=2)

    recent_frame = tk.Frame(body, bg=BG)
    recent_frame.pack(fill="x", pady=(6, 14))
    tk.Label(recent_frame, text="Recent matches shown",
             bg=BG, fg=FG, font=F_BODY).pack(side="left")
    recent_var = StringVar(value=str(SETTINGS["recent_matches_count"]))
    tk.Entry(recent_frame, textvariable=recent_var, bg=SURFACE, fg=FG,
             insertbackground=FG, relief="flat", highlightthickness=1,
             highlightbackground=BORDER, highlightcolor=ACCENT,
             font=F_BODY, width=6
             ).pack(side="left", padx=(12, 0), ipady=4)

    # --- behaviour
    tk.Label(body, text="BEHAVIOUR", bg=BG, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(0, 4))

    auto_var = BooleanVar(value=SETTINGS["auto_open_roster_after_match"])
    tk.Checkbutton(body, text="Open roster editor after adding a match",
                   variable=auto_var, bg=BG, fg=FG,
                   selectcolor=SURFACE, activebackground=BG,
                   activeforeground=FG, font=F_BODY,
                   highlightthickness=0
                   ).pack(anchor="w", pady=2)

    # --- backups
    tk.Label(body, text="BACKUPS", bg=BG, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(18, 4))
    tk.Label(body, text=f"Every delete creates a timestamped backup. "
                        f"The newest {MAX_BACKUPS} are kept in "
                        f"\"{BACKUPS_DIR}/\" next to the database.",
             bg=BG, fg=MUTED, font=F_SMALL, justify="left",
             wraplength=480).pack(anchor="w", pady=(0, 6))
    make_small_button(body, "Open backups folder",
                      _open_backups_folder).pack(anchor="w", pady=(0, 6))

    # --- layout
    tk.Label(body, text="LAYOUT", bg=BG, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(18, 4))
    tk.Label(body, text="Reorder sections with ▲ / ▼.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(0, 6))

    local_order = list(SETTINGS["layout_order"])
    layout_holder = tk.Frame(body, bg=BG)
    layout_holder.pack(fill="x", pady=(0, 8))

    def refresh_layout_rows():
        for child in layout_holder.winfo_children():
            child.destroy()
        for i, name in enumerate(local_order):
            row = tk.Frame(layout_holder, bg=SURFACE)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=name.title(), bg=SURFACE, fg=FG,
                     font=F_BODY, anchor="w", padx=10, pady=6
                     ).pack(side="left", fill="x", expand=True)

            def up(i=i):
                if i > 0:
                    local_order[i], local_order[i - 1] = (
                        local_order[i - 1], local_order[i])
                    refresh_layout_rows()

            def down(i=i):
                if i < len(local_order) - 1:
                    local_order[i], local_order[i + 1] = (
                        local_order[i + 1], local_order[i])
                    refresh_layout_rows()

            make_small_button(row, "▼", down).pack(side="right",
                                                    padx=(0, 4), pady=3)
            make_small_button(row, "▲", up).pack(side="right",
                                                  padx=(0, 4), pady=3)

    refresh_layout_rows()

    # --- colours
    tk.Label(body, text="COLOURS", bg=BG, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(12, 4))
    tk.Label(body, text="Click a swatch to pick a colour.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(0, 6))

    local_bg = dict(SETTINGS["section_bg"])
    local_title = dict(SETTINGS["section_title_color"])

    colours_holder = tk.Frame(body, bg=BG)
    colours_holder.pack(fill="x", pady=(0, 8))

    def swatch(parent, initial, on_pick):
        btn = tk.Button(parent, bg=initial, relief="flat", bd=0,
                        highlightthickness=1, highlightbackground=BORDER,
                        width=4, cursor="hand2", command=None)
        def _pick(b=btn):
            _, hexval = colorchooser.askcolor(color=b["bg"], parent=win)
            if hexval:
                b.configure(bg=hexval)
                on_pick(hexval)
        btn.configure(command=_pick)
        return btn

    for section in ("actions", "dashboard", "calendar"):
        row = tk.Frame(colours_holder, bg=BG)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=section.title(), bg=BG, fg=FG, font=F_BODY,
                 width=12, anchor="w").pack(side="left")

        bg_btn = swatch(row, local_bg[section],
                        lambda v, s=section: local_bg.__setitem__(s, v))
        bg_btn.pack(side="left", padx=(0, 4), ipady=6)
        tk.Label(row, text="background", bg=BG, fg=MUTED,
                 font=F_SMALL).pack(side="left", padx=(0, 12))

        t_btn = swatch(row, local_title[section],
                       lambda v, s=section: local_title.__setitem__(s, v))
        t_btn.pack(side="left", padx=(0, 4), ipady=6)
        tk.Label(row, text="title", bg=BG, fg=MUTED,
                 font=F_SMALL).pack(side="left")

    def reset_layout():
        if messagebox.askyesno("Reset layout",
                               "Reset section order to the default?",
                               parent=win):
            local_order[:] = list(DEFAULT_SETTINGS["layout_order"])
            refresh_layout_rows()

    def reset_colours():
        if messagebox.askyesno("Reset colours",
                               "Reset section colours to the default?",
                               parent=win):
            local_bg.update(DEFAULT_SETTINGS["section_bg"])
            local_title.update(DEFAULT_SETTINGS["section_title_color"])
            win.destroy()
            open_settings()

    reset_row = tk.Frame(body, bg=BG)
    reset_row.pack(fill="x", pady=(0, 6))
    make_small_button(reset_row, "Reset layout", reset_layout
                      ).pack(side="left")
    make_small_button(reset_row, "Reset colours", reset_colours
                      ).pack(side="left", padx=(6, 0))

    # --- actions
    actions = tk.Frame(body, bg=BG)
    actions.pack(fill="x", pady=(22, 0))

    def reset():
        if messagebox.askyesno("Reset settings",
                               "Reset all settings to their defaults?",
                               parent=win):
            SETTINGS.clear()
            SETTINGS.update({
                k: (dict(v) if isinstance(v, dict)
                    else list(v) if isinstance(v, list)
                    else v)
                for k, v in DEFAULT_SETTINGS.items()
            })
            save_settings()
            win.destroy()
            refresh_dashboard()
            set_status("Settings reset to defaults.")
            open_settings()

    def save_and_close():
        try:
            wp = int(win_var.get())
            dp = int(draw_var.get())
            lp = int(loss_var.get())
            rn = int(recent_var.get())
        except ValueError:
            messagebox.showwarning(
                "Invalid input",
                "Points and recent-match count must be whole numbers.",
                parent=win)
            return
        if rn < 1 or rn > 100:
            messagebox.showwarning(
                "Invalid input",
                "Recent matches must be between 1 and 100.",
                parent=win)
            return
        SETTINGS["win_points"] = wp
        SETTINGS["draw_points"] = dp
        SETTINGS["loss_points"] = lp
        SETTINGS["calendar_starts_monday"] = mon_var.get()
        SETTINGS["recent_matches_count"] = rn
        SETTINGS["auto_open_roster_after_match"] = auto_var.get()
        SETTINGS["layout_order"] = list(local_order)
        SETTINGS["section_bg"] = dict(local_bg)
        SETTINGS["section_title_color"] = dict(local_title)
        save_settings()
        try:
            rebuild_sections()
        except Exception as exc:
            messagebox.showerror("Rebuild failed",
                                 f"{type(exc).__name__}: {exc}", parent=win)
            return
        set_status("Settings saved.")
        win.destroy()

    make_button(actions, "Save", save_and_close, accent=True, anchor="center"
                ).pack(side="right")
    make_button(actions, "Cancel", win.destroy, anchor="center"
                ).pack(side="right", padx=(0, 8))
    make_button(actions, "Reset to defaults", reset, anchor="center"
                ).pack(side="left")


# ------------------------------------------------------------------ bootstrap
init_db()

root = Tk()
root.title("Tchoukball Stats")
root.configure(bg=BG)
center_window(root, 1000, 780)
root.minsize(900, 640)
root.columnconfigure(0, weight=1)
root.rowconfigure(2, weight=1)
apply_theme(root)

header = tk.Frame(root, bg=BG)
header.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 6))

header_text = tk.Frame(header, bg=BG)
header_text.pack(side="left")
tk.Label(header_text, text="Tchoukball Stats", bg=BG, fg=FG,
         font=(FONT, 20, "bold")).pack(anchor="w")
tk.Label(header_text, text="Manage teams, matches and tournaments.",
         bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

_focus_badge_lbl = tk.Label(header_text, text="", bg=BG, fg=ACCENT,
                            font=F_SMALL)
_focus_badge_lbl.pack(anchor="w", pady=(2, 0))

_focus_btn = None


def _update_focus_badge():
    if _focus_badge_lbl is None:
        return
    tid = SETTINGS.get("focus_tournament_id")
    if tid is None:
        _focus_badge_lbl.configure(text="")
        return
    try:
        tid = int(tid)
    except (ValueError, TypeError):
        SETTINGS["focus_tournament_id"] = None
        save_settings()
        _focus_badge_lbl.configure(text="")
        return
    with connect_db() as conn:
        row = conn.execute(
            "SELECT TournamentName FROM Tournaments WHERE TournamentID = ?",
            (tid,)).fetchone()
    if not row:
        SETTINGS["focus_tournament_id"] = None
        save_settings()
        _focus_badge_lbl.configure(text="")
        return
    _focus_badge_lbl.configure(text=f"⭐ Focus: {row[0]}")


def _sync_focus_btn():
    if _focus_btn is None:
        return
    if SETTINGS.get("focus_tournament_id") is not None:
        _focus_btn.configure(text="Clear focus")
    else:
        _focus_btn.configure(text="⭐ Focus selected")


def _clear_focus_if_matches(conn, rid):
    try:
        rid_int = int(rid)
    except (ValueError, TypeError):
        return
    if SETTINGS.get("focus_tournament_id") == rid_int:
        SETTINGS["focus_tournament_id"] = None
        save_settings()


make_small_button(header, "⚙ Settings", open_settings).pack(
    side="right", anchor="n")

_update_focus_badge()

tk.Frame(root, bg=BORDER, height=1).grid(row=1, column=0, sticky="ew", padx=22)

content_area = tk.Frame(root, bg=BG)
content_area.grid(row=2, column=0, sticky="nsew")
content_area.columnconfigure(0, weight=1)

status_var = StringVar()
status_lbl = tk.Label(root, textvariable=status_var, bg=BG, fg=MUTED,
                      font=F_SMALL, anchor="w", padx=22, pady=6)
status_lbl.grid(row=3, column=0, sticky="ew")

_status_job = None
def set_status(message, error=False):
    global _status_job
    status_var.set(message)
    status_lbl.configure(fg=DANGER if error else MUTED)
    if _status_job is not None:
        root.after_cancel(_status_job)
    _status_job = root.after(6000, _clear_status)

def _clear_status():
    global _status_job
    _status_job = None
    status_var.set("")


# ------------------------------------------------------------------ table viewer
def show_table(title, query, columns, compare_kind=None,
               context_actions=None, double_click_action=None):
    with connect_db() as conn:
        rows = conn.execute(query).fetchall()

    win = Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    center_window(win, 900, 560)
    win.minsize(560, 340)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 8))
    tk.Label(head, text=title, bg=BG, fg=FG, font=F_TITLE).pack(side="left")
    count_lbl = tk.Label(head, text="", bg=BG, fg=MUTED, font=F_SMALL)
    count_lbl.pack(side="right")

    filter_bar = tk.Frame(win, bg=BG)
    filter_bar.pack(fill="x", padx=22, pady=(0, 6))
    tk.Label(filter_bar, text="Filter", bg=BG, fg=MUTED,
             font=F_SMALL).pack(side="left", padx=(0, 6))
    filter_var = StringVar()
    filter_entry = tk.Entry(filter_bar, bg=SURFACE, fg=FG,
                            insertbackground=FG, relief="flat",
                            highlightthickness=1,
                            highlightbackground=BORDER,
                            highlightcolor=ACCENT, font=F_SMALL,
                            textvariable=filter_var, width=40)
    filter_entry.pack(side="left", ipady=4, fill="x", expand=True)

    def _focus_filter(event=None):
        filter_entry.focus_set()
        filter_entry.select_range(0, "end")
        return "break"

    win.bind("<Control-f>", _focus_filter)

    shell = tk.Frame(win, bg=BORDER)
    shell.pack(fill="both", expand=True, padx=22, pady=(0, 8))

    selectmode = "extended" if compare_kind else "browse"
    tree = ttk.Treeview(shell, columns=columns, show="headings",
                        selectmode=selectmode)
    scroll = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)

    for i, col in enumerate(columns):
        longest = max([len(str(col))] +
                      [len(str(r[i])) for r in rows[:200] if r[i] is not None])
        tree.column(col, width=max(90, min(240, longest * 9 + 28)),
                    minwidth=70, anchor="w", stretch=True)

    attach_autofit(tree)
    tree.tag_configure("row_even", background=SURFACE)
    tree.tag_configure("row_odd",  background=STRIPE)

    no_data_lbl = tk.Label(shell, text="No records yet", bg=SURFACE,
                           fg=MUTED, font=F_BODY)

    current_sort = [None, False]

    def _on_heading_click(col):
        if current_sort[0] == col:
            sort_by(col, not current_sort[1])
        else:
            sort_by(col, False)

    def _refresh_heading_labels():
        for c in columns:
            arrow = ""
            if current_sort[0] == c:
                arrow = " ▼" if current_sort[1] else " ▲"
            tree.heading(c, text=str(c) + arrow, anchor="w",
                         command=lambda cc=c: _on_heading_click(cc))

    def sort_by(col, descending):
        items = [(tree.set(iid, col), iid) for iid in tree.get_children("")]
        def key(pair):
            v = pair[0]
            if v == "":
                return (2, "")
            try:
                return (0, float(v))
            except ValueError:
                return (1, v.lower())
        items.sort(key=key, reverse=descending)
        for idx, (_, iid) in enumerate(items):
            tree.move(iid, "", idx)
            tree.item(iid, tags=("row_even" if idx % 2 == 0 else "row_odd",))
        current_sort[0] = col
        current_sort[1] = descending
        _refresh_heading_labels()

    def apply_filter(*_args):
        text = filter_var.get().strip().lower()
        tree.delete(*tree.get_children())
        shown = 0
        for r in rows:
            if text and text not in " ".join(str(x) for x in r).lower():
                continue
            tree.insert("", "end", values=r,
                        tags=("row_even" if shown % 2 == 0 else "row_odd",))
            shown += 1
        if current_sort[0]:
            sort_by(current_sort[0], current_sort[1])
        total = len(rows)
        suffix = "s" if total != 1 else ""
        if text:
            count_lbl.configure(text=f"{shown} of {total} row{suffix}")
        else:
            count_lbl.configure(text=f"{total} row{suffix}")
        if shown == 0:
            no_data_lbl.configure(text="No matching rows" if text
                                  else "No records yet")
            no_data_lbl.place(relx=0.5, rely=0.5, anchor="center")
        else:
            no_data_lbl.place_forget()

    def export_csv():
        import csv
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=win, title="Export CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{title.lower().replace(' ', '_')}.csv")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(columns)
                for iid in tree.get_children(""):
                    w.writerow(tree.item(iid, "values"))
            set_status(f"Exported {len(tree.get_children(''))} rows to {path}.")
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc), parent=win)

    def do_compare():
        sel = tree.selection()
        if len(sel) != 2:
            messagebox.showinfo("Select two rows",
                                "Select exactly two rows to compare.",
                                parent=win)
            return
        ids = [int(tree.item(iid, "values")[0]) for iid in sel]
        open_compare(compare_kind, preselected=(ids[0], ids[1]))

    bar = tk.Frame(win, bg=BG)
    bar.pack(fill="x", padx=22, pady=(0, 18))
    make_small_button(bar, "Export CSV", export_csv).pack(side="right")
    make_small_button(bar, "Close", win.destroy).pack(side="right", padx=(0, 8))
    if compare_kind:
        make_small_button(bar, "Compare selected", do_compare
                          ).pack(side="right", padx=(0, 8))

    _refresh_heading_labels()
    apply_filter()
    filter_var.trace_add("write", apply_filter)

    if context_actions:
        def _show_menu(event):
            iid = tree.identify_row(event.y)
            if iid and iid not in tree.selection():
                tree.selection_set(iid)
            sel = tree.selection()
            if not sel:
                return
            ids = [int(tree.item(i, "values")[0]) for i in sel]
            values = [tree.item(i, "values") for i in sel]
            menu = tk.Menu(win, tearoff=0, bg=SURFACE_2, fg=FG,
                           activebackground=ACCENT,
                           activeforeground="#ffffff", bd=0,
                           relief="flat", font=F_BODY)
            for action in context_actions:
                label, handler, danger, separator, requires = action
                if separator:
                    menu.add_separator()
                enabled = _check_requires(requires, len(ids))
                menu.add_command(
                    label=label,
                    command=lambda h=handler, i=ids, v=values: h(i, v, win),
                    state="normal" if enabled else "disabled")
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
        tree.bind("<Button-3>", _show_menu)
        tree.bind("<Control-Button-1>", _show_menu)

    if double_click_action:
        def _on_dbl(event):
            if tree.identify_region(event.x, event.y) != "cell":
                return
            sel = tree.selection()
            if len(sel) == 1:
                double_click_action(
                    [int(tree.item(sel[0], "values")[0])],
                    [tree.item(sel[0], "values")], win)
        tree.bind("<Double-1>", _on_dbl, add="+")

    tree.bind("<MouseWheel>",
              lambda e: tree.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    tree.bind("<Button-4>", lambda e: tree.yview_scroll(-1, "units"))
    tree.bind("<Button-5>", lambda e: tree.yview_scroll(1, "units"))


# ------------------------------------------------------------------ insert
def insert_row(query, values, success_message):
    try:
        with connect_db() as conn:
            cur = conn.execute(query, values)
            last_id = cur.lastrowid
        set_status(success_message)
        root.event_generate("<<DataChanged>>")
        return last_id
    except sqlite3.IntegrityError as exc:
        set_status(f"Could not save: {exc}", error=True)
        messagebox.showerror("Database error", str(exc))
        return False


# ------------------------------------------------------------------ add forms
def make_form(title, subtitle, fields, on_submit, extra_builder=None):
    win = Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    win.resizable(False, False)
    win.bind("<Escape>", lambda e: win.destroy())
    body = tk.Frame(win, bg=BG, padx=24, pady=22)
    body.pack(fill="both", expand=True)
    tk.Label(body, text=title, bg=BG, fg=FG, font=F_TITLE).pack(anchor="w")
    tk.Label(body, text=subtitle, bg=BG, fg=MUTED, font=F_SMALL
             ).pack(anchor="w", pady=(2, 6))
    widgets = {}
    for field in fields:
        tk.Label(body, text=field["label"], bg=BG, fg=MUTED, font=F_SMALL
                 ).pack(anchor="w", pady=(10, 4))
        if field.get("values") is not None:
            w = ttk.Combobox(body, values=field["values"],
                             state="readonly", font=F_BODY, height=10)
            w.pack(fill="x")
        elif field.get("date"):
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x")
            w = tk.Entry(row, bg=SURFACE, fg=FG, insertbackground=FG,
                         relief="flat", highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT,
                         font=F_BODY, width=30)
            w.pack(side="left", fill="x", expand=True, ipady=7)
            tk.Button(row, text="📅", cursor="hand2",
                      bg=SURFACE_2, fg=FG, activebackground=BORDER,
                      activeforeground=FG, relief="flat", bd=0,
                      highlightthickness=0, padx=8, font=F_BODY,
                      command=lambda e=w, ww=win: open_date_picker(ww, e)
                      ).pack(side="left", padx=(4, 0), ipady=2)
        else:
            w = tk.Entry(body, bg=SURFACE, fg=FG, insertbackground=FG,
                         relief="flat", highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT,
                         font=F_BODY, width=36)
            w.pack(fill="x", ipady=7)
        widgets[field["key"]] = w
        init_val = field.get("initial")
        if init_val:
            if field.get("values") is not None:
                w.set(str(init_val))
            else:
                w.insert(0, str(init_val))
    if extra_builder:
        try:
            extra_builder(win, body, widgets)
        except Exception:
            pass

    def submit():
        values = {}
        for field in fields:
            w = widgets[field["key"]]
            value = w.get().strip()
            if field.get("required") and not value:
                messagebox.showwarning("Missing value",
                                       f"{field['label']} is required.",
                                       parent=win)
                w.focus_set()
                return
            values[field["key"]] = value
        if on_submit(values) is not False:
            win.destroy()
    actions = tk.Frame(body, bg=BG)
    actions.pack(fill="x", pady=(20, 0))
    make_button(actions, "Save", submit, accent=True, anchor="center"
                ).pack(side="right")
    make_button(actions, "Cancel", win.destroy, anchor="center"
                ).pack(side="right", padx=(0, 8))
    win.bind("<Return>", lambda e: submit())


def add_team():
    with connect_db() as conn:
        clubs = conn.execute("SELECT ClubID, ClubName FROM Clubs "
                             "ORDER BY ClubName").fetchall()
    club_opts = ["(none)"] + [f"{cid} · {cname}" for cid, cname in clubs]
    club_of = {f"{cid} · {cname}": cid for cid, cname in clubs}

    def save(v):
        cid = None if v["club"] == "(none)" else club_of[v["club"]]
        return insert_row("INSERT INTO Teams (TeamName, ClubID) VALUES (?, ?)",
                          (v["name"], cid), f'Team "{v["name"]}" added.')

    make_form("New team", "Teams are the sides that play matches.",
              [{"label": "Team name", "key": "name", "required": True},
               {"label": "Club (optional)", "key": "club", "values": club_opts}],
              save)


def add_club():
    make_form("New club", "Clubs group the teams together.",
              [{"label": "Club name", "key": "name", "required": True}],
              lambda v: insert_row(
                  "INSERT INTO Clubs (ClubName) VALUES (?)",
                  (v["name"],), f'Club "{v["name"]}" added.'))


def add_player():
    with connect_db() as conn:
        teams = conn.execute("SELECT TeamID, TeamName FROM Teams "
                             "ORDER BY TeamName").fetchall()
    team_opts = ["(none)"] + [f"{tid} · {tname}" for tid, tname in teams]
    team_of = {f"{tid} · {tname}": tid for tid, tname in teams}

    def save(v):
        tid = None if v["team"] == "(none)" else team_of[v["team"]]
        bd_raw = v["birthday"].strip()
        if bd_raw:
            try:
                datetime.datetime.strptime(bd_raw, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Invalid date",
                                       "Birthday must be in YYYY-MM-DD format.")
                return False
            bd = bd_raw
        else:
            bd = None
        return insert_row(
            "INSERT INTO Players (PlayerName, PlayerSurname, TeamID, "
            "PlayerBirthdate) VALUES (?, ?, ?, ?)",
            (v["fname"], v["sname"], tid, bd),
            f'Player "{v["fname"]}" added.')

    make_form("New player", "First name required; other fields optional.",
              [{"label": "First name", "key": "fname", "required": True},
               {"label": "Surname", "key": "sname"},
               {"label": "Birthday (YYYY-MM-DD)", "key": "birthday",
                "date": True},
               {"label": "Team (optional)", "key": "team", "values": team_opts}],
              save)


def add_tournament():
    def save(v):
        date_raw = v["date"].strip()
        if date_raw:
            try:
                datetime.datetime.strptime(date_raw, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Invalid date",
                                       "Tournament date must be YYYY-MM-DD.")
                return False
        return insert_row(
            "INSERT INTO Tournaments (TournamentName, TournamentDate, "
            "TournamentLocation) VALUES (?, ?, ?)",
            (v["name"], date_raw or None, v["loc"] or None),
            f'Tournament "{v["name"]}" added.')

    make_form("New tournament", "Give your tournament a name, date and place.",
              [{"label": "Tournament name", "key": "name", "required": True},
               {"label": "Date (YYYY-MM-DD)", "key": "date", "date": True},
               {"label": "Location", "key": "loc"}], save)


def add_match(default_date=None):
    with connect_db() as conn:
        teams = conn.execute("SELECT TeamID, TeamName FROM Teams "
                             "ORDER BY TeamName").fetchall()
        tournaments = conn.execute("SELECT TournamentID, TournamentName "
                                   "FROM Tournaments ORDER BY TournamentName"
                                   ).fetchall()
    if not teams:
        messagebox.showinfo("No teams", "Add at least one team first.")
        return
    team_of = {f"{tid} · {name}": tid for tid, name in teams}
    tourn_of = {f"{tid} · {name}": tid for tid, name in tournaments}
    def save(v):
        if v["home"] == v["away"]:
            messagebox.showwarning("Invalid match",
                                   "Home and away teams must be different.")
            return False
        tid = None if v["tournament"] == "(none)" else tourn_of[v["tournament"]]
        scores = []
        for key in ("hs", "as"):
            raw = v[key]
            if raw and not raw.isdigit():
                messagebox.showwarning("Invalid score",
                                       "Scores must be whole numbers.")
                return False
            scores.append(int(raw) if raw else None)
        date_raw = v["date"].strip()
        if date_raw:
            try:
                datetime.datetime.strptime(date_raw, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Invalid date",
                                       "Match date must be YYYY-MM-DD.")
                return False
        period_count = _parse_period_count(v["periods"])
        pm_raw = v["period_minutes"].strip()
        if pm_raw and not pm_raw.isdigit():
            messagebox.showwarning("Invalid minutes",
                                   "Period minutes must be a whole number.")
            return False
        period_minutes = int(pm_raw) if pm_raw else None

        result = insert_row(
            "INSERT INTO Matches (MatchHome, MatchAway, MatchLocation, "
            "MatchHScore, MatchAScore, TournamentID, MatchDate, "
            "PeriodCount, PeriodMinutes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (team_of[v["home"]], team_of[v["away"]],
             v["loc"] or None, scores[0], scores[1], tid, date_raw or None,
             period_count or None, period_minutes),
            "Match added.")
        if result is not False:
            if period_count > 0:
                root.after(120, lambda: open_period_editor(result))
            elif SETTINGS["auto_open_roster_after_match"]:
                root.after(120, lambda: open_roster_editor(result))
        return result
    def _prediction_hook(win, body, widgets):
        pred_lbl = tk.Label(body, text="", bg=BG, fg=ACCENT,
                            font=F_SMALL, wraplength=440, justify="left",
                            anchor="w")
        pred_lbl.pack(fill="x", pady=(8, 0))

        def update(*_):
            h = widgets["home"].get()
            a = widgets["away"].get()
            if (not h or not a or h == a
                    or h not in team_of or a not in team_of):
                pred_lbl.configure(text="")
                return
            try:
                with connect_db() as conn:
                    ratings, _, _ = compute_elo(conn)
                    draw_rate = compute_draw_rate(conn)
                ph, pd, pa = predict_match(team_of[h], team_of[a],
                                            ratings, draw_rate)
                hn = h.split(" · ", 1)[-1]
                an = a.split(" · ", 1)[-1]
                pred_lbl.configure(
                    text=f"Predicted:  {hn} {ph*100:.0f}%   ·   "
                         f"Draw {pd*100:.0f}%   ·   {an} {pa*100:.0f}%")
            except Exception:
                pred_lbl.configure(text="")

        widgets["home"].bind("<<ComboboxSelected>>", update)
        widgets["away"].bind("<<ComboboxSelected>>", update)
        update()

    make_form("New match",
              "Assign to a tournament and record the final score. "
              "Optionally split the match into halves or thirds.",
              [{"label": "Tournament", "key": "tournament",
                "values": ["(none)"] + list(tourn_of)},
               {"label": "Home team", "key": "home",
                "values": list(team_of), "required": True},
               {"label": "Away team", "key": "away",
                "values": list(team_of), "required": True},
               {"label": "Location", "key": "loc"},
               {"label": "Date (YYYY-MM-DD)", "key": "date", "date": True,
                "initial": default_date or ""},
               {"label": "Home score", "key": "hs"},
               {"label": "Away score", "key": "as"},
               {"label": "Periods (e.g. 3, 'Thirds', or blank)",
                "key": "periods"},
               {"label": "Period minutes", "key": "period_minutes"}],
              save, extra_builder=_prediction_hook)


# ------------------------------------------------------------------ editor
def open_editor(title, subtitle, table, id_col, list_query, list_columns,
                list_col_widths, fetch_query, fields, validator=None,
                pre_delete=None, extra_actions=None, preselect_id=None):
    win = Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    center_window(win, 880, 700)
    win.minsize(720, 580)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 12))
    tk.Label(head, text=title, bg=BG, fg=FG, font=F_TITLE).pack(anchor="w")
    tk.Label(head, text=subtitle, bg=BG, fg=MUTED, font=F_SMALL
             ).pack(anchor="w", pady=(2, 0))

    content = tk.Frame(win, bg=BG)
    content.pack(fill="both", expand=True, padx=22, pady=(0, 20))
    actions = tk.Frame(content, bg=BG)
    actions.pack(side="bottom", fill="x", pady=(14, 0))
    form = tk.Frame(content, bg=BG)
    form.pack(side="bottom", fill="x", pady=(14, 0))
    form.columnconfigure(0, weight=1)
    form.columnconfigure(1, weight=1)

    list_shell = tk.Frame(content, bg=BORDER)
    list_shell.pack(side="top", fill="both", expand=True)
    tree = ttk.Treeview(list_shell, columns=list_columns, show="headings",
                        selectmode="browse")
    scroll = ttk.Scrollbar(list_shell, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)

    for col, width in zip(list_columns, list_col_widths):
        tree.heading(col, text=col, anchor="w")
        tree.column(col, width=width, minwidth=50, anchor="w")
    if list_columns:
        tree.column(list_columns[-1], stretch=True)
    attach_autofit(tree)
    tree.tag_configure("row_even", background=SURFACE)
    tree.tag_configure("row_odd",  background=STRIPE)

    widgets = {}
    for i, field in enumerate(fields):
        r, c = divmod(i, 2)
        tk.Label(form, text=field["label"], bg=BG, fg=MUTED, font=F_SMALL
                 ).grid(row=r * 2, column=c, sticky="w", padx=(0, 8), pady=(6, 2))
        if field.get("widget") == "combo":
            w = ttk.Combobox(form, values=[d for d, _ in field["options"]],
                             state="readonly", font=F_BODY, height=10)
            w.grid(row=r * 2 + 1, column=c, sticky="ew", padx=(0, 8))
        elif field.get("widget") == "date":
            cell = tk.Frame(form, bg=BG)
            cell.grid(row=r * 2 + 1, column=c, sticky="ew", padx=(0, 8))
            w = tk.Entry(cell, bg=SURFACE, fg=FG, insertbackground=FG,
                         relief="flat", highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT,
                         font=F_BODY)
            w.pack(side="left", fill="x", expand=True, ipady=6)
            tk.Button(cell, text="📅", cursor="hand2",
                      bg=SURFACE_2, fg=FG, activebackground=BORDER,
                      activeforeground=FG, relief="flat", bd=0,
                      highlightthickness=0, padx=8, font=F_BODY,
                      command=lambda e=w, ww=win: open_date_picker(ww, e)
                      ).pack(side="left", padx=(4, 0), ipady=2)
        else:
            w = tk.Entry(form, bg=SURFACE, fg=FG, insertbackground=FG,
                         relief="flat", highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT,
                         font=F_BODY)
            w.grid(row=r * 2 + 1, column=c, sticky="ew", ipady=6, padx=(0, 8))
        widgets[field["key"]] = w

    current_id = [None]

    def load_list():
        tree.delete(*tree.get_children())
        with connect_db() as conn:
            rows = conn.execute(list_query).fetchall()
        for i, r in enumerate(rows):
            tree.insert("", "end", values=r,
                        tags=("row_even" if i % 2 == 0 else "row_odd",))
        return rows

    def populate():
        sel = tree.selection()
        if not sel:
            current_id[0] = None
            return
        rid = tree.item(sel[0], "values")[0]
        current_id[0] = rid
        with connect_db() as conn:
            row = conn.execute(fetch_query, (rid,)).fetchone()
        if not row:
            return
        for i, field in enumerate(fields):
            w = widgets[field["key"]]
            raw = row[i] if i < len(row) else None
            if field.get("widget") == "combo":
                w.set("")
                for disp, val in field["options"]:
                    if (raw is None and val is None) or \
                       (raw is not None and str(val) == str(raw)):
                        w.set(disp)
                        break
            else:
                w.delete(0, "end")
                if raw is not None:
                    w.insert(0, str(raw))

    def save():
        if current_id[0] is None:
            messagebox.showinfo("Nothing selected",
                                "Select a record in the list first.", parent=win)
            return
        values = {}
        for field in fields:
            w = widgets[field["key"]]
            if field.get("widget") == "combo":
                disp = w.get()
                if not disp:
                    values[field["key"]] = None
                else:
                    val = None
                    for d, v in field["options"]:
                        if d == disp:
                            val = v
                            break
                    values[field["key"]] = val
            else:
                values[field["key"]] = w.get().strip()
            if field.get("required") and values[field["key"]] in (None, ""):
                messagebox.showwarning("Missing value",
                                       f"{field['label']} is required.", parent=win)
                return
            if field.get("parse"):
                values[field["key"]] = field["parse"](values[field["key"]])
            if field.get("numeric"):
                v = values[field["key"]]
                if v == "" or v is None:
                    values[field["key"]] = None
                else:
                    try:
                        values[field["key"]] = int(v)
                    except (ValueError, TypeError):
                        messagebox.showwarning(
                            "Invalid number",
                            f"{field['label']} must be a whole number.", parent=win)
                        return
        if validator:
            err = validator(values)
            if err:
                messagebox.showwarning("Invalid input", err, parent=win)
                return
        set_clause = ", ".join(f"{f['column']} = ?" for f in fields)
        sql = f"UPDATE {table} SET {set_clause} WHERE {id_col} = ?"
        params = tuple(values[f["key"]] for f in fields) + (current_id[0],)
        try:
            with connect_db() as conn:
                conn.execute(sql, params)
        except sqlite3.IntegrityError as exc:
            set_status(f"Could not save: {exc}", error=True)
            messagebox.showerror("Database error", str(exc), parent=win)
            return
        saved_id = current_id[0]
        set_status("Record updated.")
        root.event_generate("<<DataChanged>>")
        load_list()
        for iid in tree.get_children():
            if str(tree.item(iid, "values")[0]) == str(saved_id):
                tree.selection_set(iid)
                tree.see(iid)
                populate()
                break

    def delete():
        if current_id[0] is None:
            messagebox.showinfo("Nothing selected",
                                "Select a record in the list first.", parent=win)
            return
        if not messagebox.askyesno("Delete record",
                                   "Delete the selected record?\n"
                                   "This cannot be undone.", parent=win):
            return
        try:
            ok, err = perform_delete(table, id_col, current_id[0], pre_delete)
        except DeletionCancelled:
            set_status("Deletion cancelled.")
            return
        if not ok:
            set_status(f"Could not delete: {err}", error=True)
            messagebox.showerror("Cannot delete",
                "This record is still referenced by other records.\n\n"
                f"{err}", parent=win)
            return
        current_id[0] = None
        for w in widgets.values():
            if isinstance(w, ttk.Combobox):
                w.set("")
            else:
                w.delete(0, "end")
        set_status("Record deleted.")
        root.event_generate("<<DataChanged>>")
        rows = load_list()
        if rows:
            first = tree.get_children()[0]
            tree.selection_set(first)
            populate()

    make_button(actions, "Save changes", save, accent=True, anchor="center"
                ).pack(side="right")
    make_button(actions, "Delete", delete, danger=True, anchor="center"
                ).pack(side="right", padx=(0, 8))
    make_button(actions, "Close", win.destroy, anchor="center"
                ).pack(side="right", padx=(0, 8))

    if extra_actions:
        for label, handler in extra_actions:
            def _mk_cb(h=handler):
                def cb():
                    if current_id[0] is None:
                        messagebox.showinfo(
                            "Nothing selected",
                            "Select a record in the list first.",
                            parent=win)
                        return
                    h(current_id[0])
                return cb
            make_button(actions, label, _mk_cb(), anchor="center"
                        ).pack(side="left", padx=(0, 8))

    tree.bind("<<TreeviewSelect>>", lambda e: populate())
    tree.bind("<MouseWheel>",
              lambda e: tree.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    tree.bind("<Button-4>", lambda e: tree.yview_scroll(-1, "units"))
    tree.bind("<Button-5>", lambda e: tree.yview_scroll(1, "units"))
    win.bind("<Control-s>", lambda e: save())

    rows = load_list()
    target = None
    if preselect_id is not None:
        for iid in tree.get_children():
            if str(tree.item(iid, "values")[0]) == str(preselect_id):
                target = iid
                break
    if target is None and rows:
        target = tree.get_children()[0]
    if target:
        tree.selection_set(target)
        tree.focus(target)
        populate()


# ------------------------------------------------------------------ edit handlers
def edit_team(preselect_id=None):
    with connect_db() as conn:
        clubs = conn.execute("SELECT ClubID, ClubName FROM Clubs "
                             "ORDER BY ClubName").fetchall()
    club_opts = [("(none)", None)] + [(cname, cid) for cid, cname in clubs]
    open_editor(
        title="Edit teams",
        subtitle="Select a team, change its details, then save.",
        table="Teams", id_col="TeamID",
        list_query="""SELECT t.TeamID, t.TeamName, COALESCE(c.ClubName, '—')
                      FROM Teams t LEFT JOIN Clubs c ON t.ClubID = c.ClubID
                      ORDER BY t.TeamName""",
        list_columns=["ID", "Team", "Club"], list_col_widths=[60, 220, 200],
        fetch_query="SELECT TeamName, ClubID FROM Teams WHERE TeamID = ?",
        fields=[
            {"label": "Team name", "key": "name",
             "column": "TeamName", "required": True},
            {"label": "Club", "key": "club", "column": "ClubID",
             "widget": "combo", "options": club_opts},
        ],
        pre_delete=cascade_delete_team,
        preselect_id=preselect_id,
    )


def edit_club(preselect_id=None):
    open_editor(
        title="Edit clubs",
        subtitle="Select a club, change its name, then save.",
        table="Clubs", id_col="ClubID",
        list_query="SELECT ClubID, ClubName FROM Clubs ORDER BY ClubName",
        list_columns=["ID", "Club name"], list_col_widths=[70, 400],
        fetch_query="SELECT ClubName FROM Clubs WHERE ClubID = ?",
        fields=[{"label": "Club name", "key": "name",
                 "column": "ClubName", "required": True}],
        preselect_id=preselect_id,
    )


def edit_player(preselect_id=None):
    with connect_db() as conn:
        teams = conn.execute("SELECT TeamID, TeamName FROM Teams "
                             "ORDER BY TeamName").fetchall()
    team_opts = [("(none)", None)] + [(tname, tid) for tid, tname in teams]

    def validate_player(v):
        bd = v.get("birthday")
        if bd:
            try:
                datetime.datetime.strptime(bd, "%Y-%m-%d")
            except ValueError:
                return "Birthday must be in YYYY-MM-DD format."
        return None

    open_editor(
        title="Edit players",
        subtitle="Select a player, update the details, then save.",
        table="Players", id_col="PlayerID",
        list_query="""SELECT p.PlayerID, p.PlayerName,
                             COALESCE(p.PlayerSurname, ''),
                             COALESCE(p.PlayerBirthdate, '—'),
                             COALESCE(CAST(
                               strftime('%Y.%m%d', 'now') -
                               strftime('%Y.%m%d', p.PlayerBirthdate)
                               AS INTEGER), '—'),
                             COALESCE(t.TeamName, '—')
                      FROM Players p LEFT JOIN Teams t ON p.TeamID = t.TeamID
                      ORDER BY p.PlayerName, p.PlayerSurname""",
        list_columns=["ID", "First", "Surname", "Birthday", "Age", "Team"],
        list_col_widths=[60, 130, 130, 110, 50, 160],
        fetch_query="SELECT PlayerName, PlayerSurname, PlayerBirthdate, TeamID "
                    "FROM Players WHERE PlayerID = ?",
        fields=[
            {"label": "First name", "key": "fname",
             "column": "PlayerName", "required": True},
            {"label": "Surname", "key": "sname", "column": "PlayerSurname"},
            {"label": "Birthday (YYYY-MM-DD)", "key": "birthday",
             "column": "PlayerBirthdate", "widget": "date"},
            {"label": "Team", "key": "team", "column": "TeamID",
             "widget": "combo", "options": team_opts},
        ],
        validator=validate_player,
        pre_delete=lambda c, pid: c.execute(
            "DELETE FROM MatchRoster WHERE PlayerID = ?", (pid,)),
        preselect_id=preselect_id,
    )


def edit_tournament(preselect_id=None):
    def validate_tournament(v):
        d = v.get("date")
        if d:
            try:
                datetime.datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                return "Tournament date must be in YYYY-MM-DD format."
        return None

    open_editor(
        title="Edit tournaments",
        subtitle="Select a tournament, update its details, then save.",
        table="Tournaments", id_col="TournamentID",
        list_query="""SELECT TournamentID, TournamentName,
                             COALESCE(TournamentDate, ''),
                             COALESCE(TournamentLocation, '')
                      FROM Tournaments
                      ORDER BY TournamentDate DESC, TournamentName""",
        list_columns=["ID", "Name", "Date", "Location"],
        list_col_widths=[60, 220, 130, 220],
        fetch_query="""SELECT TournamentName, TournamentDate,
                              TournamentLocation
                       FROM Tournaments WHERE TournamentID = ?""",
        fields=[
            {"label": "Name", "key": "name", "column": "TournamentName",
             "required": True},
            {"label": "Date (YYYY-MM-DD)", "key": "date",
             "column": "TournamentDate", "widget": "date"},
            {"label": "Location", "key": "loc", "column": "TournamentLocation"},
        ],
        validator=validate_tournament,
        preselect_id=preselect_id,
    )


def edit_match(preselect_id=None):
    with connect_db() as conn:
        teams = conn.execute("SELECT TeamID, TeamName FROM Teams "
                             "ORDER BY TeamName").fetchall()
        tournaments = conn.execute("SELECT TournamentID, TournamentName "
                                   "FROM Tournaments ORDER BY TournamentName"
                                   ).fetchall()
    if not teams:
        messagebox.showinfo("No teams", "Add at least one team first.")
        return
    team_opts = [(name, tid) for tid, name in teams]
    tourn_opts = [("(none)", None)] + [(name, tid) for tid, name in tournaments]
    def validate(v):
        if v["home"] == v["away"]:
            return "Home and away teams must be different."
        d = v.get("date")
        if d:
            try:
                datetime.datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                return "Match date must be in YYYY-MM-DD format."
        return None
    open_editor(
        title="Edit matches",
        subtitle="Select a match, update details, then save.",
        table="Matches", id_col="MatchID",
        list_query="""SELECT m.MatchID,
                             COALESCE(m.MatchDate, '-'),
                             ht.TeamName, at.TeamName,
                             COALESCE(m.MatchHScore, '-') || ' – ' ||
                             COALESCE(m.MatchAScore, '-'),
                             COALESCE(t.TournamentName, '-'),
                             CASE WHEN m.PeriodCount > 0
                                  THEN m.PeriodCount || '×' ||
                                       COALESCE(m.PeriodMinutes, '?')
                                  ELSE '—' END
                      FROM Matches m
                      JOIN Teams ht ON m.MatchHome = ht.TeamID
                      JOIN Teams at ON m.MatchAway = at.TeamID
                      LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
                      ORDER BY m.MatchID DESC""",
        list_columns=["ID", "Date", "Home", "Away", "Score", "Tournament",
                      "Periods"],
        list_col_widths=[55, 110, 130, 130, 80, 140, 80],
        fetch_query="""SELECT MatchHome, MatchAway, TournamentID, MatchLocation,
                              MatchDate, MatchHScore, MatchAScore,
                              PeriodCount, PeriodMinutes
                       FROM Matches WHERE MatchID = ?""",
        fields=[
            {"label": "Home team", "key": "home", "column": "MatchHome",
             "widget": "combo", "options": team_opts, "required": True},
            {"label": "Away team", "key": "away", "column": "MatchAway",
             "widget": "combo", "options": team_opts, "required": True},
            {"label": "Tournament", "key": "tournament",
             "column": "TournamentID", "widget": "combo", "options": tourn_opts},
            {"label": "Location", "key": "loc", "column": "MatchLocation"},
            {"label": "Date (YYYY-MM-DD)", "key": "date",
             "column": "MatchDate", "widget": "date"},
            {"label": "Home score", "key": "hs", "column": "MatchHScore",
             "numeric": True},
            {"label": "Away score", "key": "as", "column": "MatchAScore",
             "numeric": True},
            {"label": "Periods (e.g. 3, 'Thirds', or blank)",
             "key": "periods", "column": "PeriodCount",
             "parse": _parse_period_count_or_none},
            {"label": "Period minutes", "key": "period_minutes",
             "column": "PeriodMinutes", "numeric": True},
        ],
        validator=validate,
        pre_delete=_clean_match_deps,
        extra_actions=[
            ("Edit roster", lambda mid: open_roster_editor(int(mid))),
            ("Edit periods", lambda mid: open_period_editor(int(mid))),
        ],
        preselect_id=preselect_id,
    )


# ------------------------------------------------------------------ browse
def browse_teams():
    wp = SETTINGS["win_points"]
    dp = SETTINGS["draw_points"]
    lp = SETTINGS["loss_points"]

    def _edit(ids, values, w):
        edit_team(preselect_id=ids[0])

    def _delete(ids, values, w):
        label = f'team "{values[0][1]}"' if values else f"team #{ids[0]}"
        delete_row_direct("Teams", "TeamID", ids[0], label,
                          pre_delete=cascade_delete_team)

    show_table("Teams",
               f"""SELECT t.TeamID, t.TeamName, COALESCE(c.ClubName, '—'),
                         COALESCE((SELECT SUM(CASE
                            WHEN MatchHome = t.TeamID AND MatchHScore > MatchAScore THEN {wp}
                            WHEN MatchAway = t.TeamID AND MatchAScore > MatchHScore THEN {wp}
                            WHEN MatchHScore = MatchAScore THEN {dp}
                            ELSE {lp} END)
                          FROM Matches
                          WHERE (MatchHome = t.TeamID OR MatchAway = t.TeamID)
                            AND MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL), 0),
                         COALESCE((SELECT GROUP_CONCAT(
                            CASE
                              WHEN m.MatchHome = t.TeamID AND m.MatchHScore > m.MatchAScore THEN 'W'
                              WHEN m.MatchAway = t.TeamID AND m.MatchAScore > m.MatchHScore THEN 'W'
                              WHEN m.MatchHScore = m.MatchAScore THEN 'D'
                              ELSE 'L'
                            END, ' ')
                          FROM (
                            SELECT MatchHome, MatchAway, MatchHScore, MatchAScore
                            FROM Matches
                            WHERE (MatchHome = t.TeamID OR MatchAway = t.TeamID)
                              AND MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
                            ORDER BY MatchID DESC LIMIT 5
                          ) m), '—')
                  FROM Teams t LEFT JOIN Clubs c ON t.ClubID = c.ClubID
                  ORDER BY t.TeamName""",
               ["ID", "Team", "Club", "Pts", "Form"],
               compare_kind="teams",
               context_actions=[
                   ("Edit team", _edit, False, False, "one"),
                   ("Delete team", _delete, True, True, "one"),
               ],
               double_click_action=_edit)


def browse_clubs():
    wp = SETTINGS["win_points"]
    dp = SETTINGS["draw_points"]
    lp = SETTINGS["loss_points"]

    def _edit(ids, values, w):
        edit_club(preselect_id=ids[0])

    def _delete(ids, values, w):
        label = f'club "{values[0][1]}"' if values else f"club #{ids[0]}"
        delete_row_direct("Clubs", "ClubID", ids[0], label)

    show_table("Clubs",
               f"""SELECT c.ClubID, c.ClubName, COUNT(DISTINCT t.TeamID),
                         COALESCE((SELECT SUM(CASE
                            WHEN MatchHome IN (SELECT TeamID FROM Teams WHERE ClubID = c.ClubID)
                              AND MatchHScore > MatchAScore THEN {wp}
                            WHEN MatchAway IN (SELECT TeamID FROM Teams WHERE ClubID = c.ClubID)
                              AND MatchAScore > MatchHScore THEN {wp}
                            WHEN MatchHScore = MatchAScore THEN {dp}
                            ELSE {lp} END)
                          FROM Matches
                          WHERE (MatchHome IN (SELECT TeamID FROM Teams WHERE ClubID = c.ClubID)
                              OR MatchAway IN (SELECT TeamID FROM Teams WHERE ClubID = c.ClubID))
                            AND MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL), 0)
                  FROM Clubs c LEFT JOIN Teams t ON c.ClubID = t.ClubID
                  GROUP BY c.ClubID ORDER BY c.ClubName""",
               ["ID", "Club", "Teams", "Pts"],
               compare_kind="clubs",
               context_actions=[
                   ("Edit club", _edit, False, False, "one"),
                   ("Delete club", _delete, True, True, "one"),
               ],
               double_click_action=_edit)


def browse_players():
    def _edit(ids, values, w):
        edit_player(preselect_id=ids[0])

    def _delete(ids, values, w):
        label = f'player "{values[0][1]}"' if values else f"player #{ids[0]}"
        delete_row_direct(
            "Players", "PlayerID", ids[0], label,
            pre_delete=lambda c, pid: c.execute(
                "DELETE FROM MatchRoster WHERE PlayerID = ?", (pid,)))

    def _career(ids, values, w):
        open_player_career(ids[0])

    show_table("Players",
               """SELECT p.PlayerID, p.PlayerName,
                         COALESCE(p.PlayerSurname, ''),
                         COALESCE(p.PlayerBirthdate, '—'),
                         COALESCE(CAST(
                           strftime('%Y.%m%d', 'now') -
                           strftime('%Y.%m%d', p.PlayerBirthdate)
                           AS INTEGER), '—'),
                         COALESCE(t.TeamName, '—'),
                         COALESCE((SELECT SUM(PlayerPoints) FROM MatchRoster
                                   WHERE PlayerID = p.PlayerID), 0),
                         COALESCE((SELECT GROUP_CONCAT(
                            CASE
                              WHEN m.MatchHome = m.TeamID AND m.MatchHScore > m.MatchAScore THEN 'W'
                              WHEN m.MatchAway = m.TeamID AND m.MatchAScore > m.MatchHScore THEN 'W'
                              WHEN m.MatchHScore = m.MatchAScore THEN 'D'
                              ELSE 'L'
                            END, ' ')
                          FROM (
                            SELECT m2.MatchID, m2.MatchHome, m2.MatchAway,
                                   m2.MatchHScore, m2.MatchAScore, r2.TeamID
                            FROM MatchRoster r2
                            JOIN Matches m2 ON m2.MatchID = r2.MatchID
                            WHERE r2.PlayerID = p.PlayerID
                              AND m2.MatchHScore IS NOT NULL
                              AND m2.MatchAScore IS NOT NULL
                            ORDER BY m2.MatchID DESC LIMIT 5
                          ) m), '—')
                  FROM Players p LEFT JOIN Teams t ON p.TeamID = t.TeamID
                  ORDER BY p.PlayerName, p.PlayerSurname""",
               ["ID", "First name", "Surname", "Birthday", "Age", "Team",
                "Goals", "Form"],
               compare_kind="players",
               context_actions=[
                   ("Edit player", _edit, False, False, "one"),
                   ("View career", _career, False, True, "one"),
                   ("Delete player", _delete, True, True, "one"),
               ],
               double_click_action=_career)


def browse_tournaments():
    def _edit(ids, values, w):
        edit_tournament(preselect_id=ids[0])

    def _delete(ids, values, w):
        label = (f'tournament "{values[0][1]}"' if values
                 else f"tournament #{ids[0]}")
        delete_row_direct("Tournaments", "TournamentID", ids[0], label,
                          pre_delete=_clear_focus_if_matches)

    show_table("Tournaments",
               "SELECT * FROM Tournaments ORDER BY TournamentDate DESC",
               ["TournamentID", "TournamentName", "TournamentDate",
                "TournamentLocation"],
               context_actions=[
                   ("Edit tournament", _edit, False, False, "one"),
                   ("Delete tournament", _delete, True, True, "one"),
               ],
               double_click_action=_edit)


def browse_matches():
    def _edit(ids, values, w):
        edit_match(preselect_id=ids[0])

    def _roster(ids, values, w):
        open_roster_editor(ids[0])

    def _periods(ids, values, w):
        open_period_editor(ids[0])

    def _delete(ids, values, w):
        delete_row_direct("Matches", "MatchID", ids[0],
                          f"match #{ids[0]}",
                          pre_delete=_clean_match_deps)

    show_table("Matches",
               """SELECT m.MatchID, ht.TeamName, at.TeamName,
                         COALESCE(m.MatchLocation, '-'),
                         COALESCE(m.MatchHScore, '-'),
                         COALESCE(m.MatchAScore, '-'),
                         COALESCE(t.TournamentName, '-'),
                         COALESCE(m.MatchDate, '-'),
                         CASE WHEN m.PeriodCount > 0
                              THEN m.PeriodCount || ' × ' ||
                                   COALESCE(m.PeriodMinutes, '?') || ' min'
                              ELSE '—' END,
                         COALESCE((SELECT GROUP_CONCAT(score, ' · ')
                                   FROM (SELECT COALESCE(HomeScore, 0) || '-' ||
                                                COALESCE(AwayScore, 0) AS score
                                         FROM MatchPeriods
                                         WHERE MatchID = m.MatchID
                                         ORDER BY PeriodNumber)), '—')
                  FROM Matches m
                  JOIN Teams ht ON m.MatchHome = ht.TeamID
                  JOIN Teams at ON m.MatchAway = at.TeamID
                  LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
                  ORDER BY m.MatchID DESC""",
               ["ID", "Home", "Away", "Location", "H", "A", "Tournament",
                "Date", "Periods", "Period scores"],
               compare_kind="matches",
               context_actions=[
                   ("Edit match", _edit, False, False, "one"),
                   ("Edit roster", _roster, False, False, "one"),
                   ("Edit periods", _periods, False, False, "one"),
                   ("Delete match", _delete, True, True, "one"),
               ],
               double_click_action=_edit)


# ------------------------------------------------------------------ remover
def open_remover(title, subtitle, table, id_col, list_query,
                 list_columns, list_col_widths, pre_delete=None,
                 bulk_handler=None):
    win = Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    center_window(win, 860, 540)
    win.minsize(620, 420)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 12))
    tk.Label(head, text=title, bg=BG, fg=FG, font=F_TITLE).pack(anchor="w")
    tk.Label(head, text=subtitle, bg=BG, fg=MUTED, font=F_SMALL
             ).pack(anchor="w", pady=(2, 0))
    tk.Label(head, text="Ctrl-click or Shift-click to select multiple rows.",
             bg=BG, fg=MUTED, font=F_SMALL
             ).pack(anchor="w", pady=(2, 0))
    content = tk.Frame(win, bg=BG)
    content.pack(fill="both", expand=True, padx=22, pady=(0, 20))
    actions = tk.Frame(content, bg=BG)
    actions.pack(side="bottom", fill="x", pady=(14, 0))
    list_shell = tk.Frame(content, bg=BORDER)
    list_shell.pack(side="top", fill="both", expand=True)

    tree = ttk.Treeview(list_shell, columns=list_columns, show="headings",
                        selectmode="extended")
    scroll = ttk.Scrollbar(list_shell, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, width in zip(list_columns, list_col_widths):
        tree.heading(col, text=col, anchor="w")
        tree.column(col, width=width, minwidth=50, anchor="w")
    if list_columns:
        tree.column(list_columns[-1], stretch=True)
    attach_autofit(tree)
    tree.tag_configure("row_even", background=SURFACE)
    tree.tag_configure("row_odd",  background=STRIPE)

    remove_btn = [None]

    def _update_btn(*args):
        if remove_btn[0] is None:
            return
        n = len(tree.selection())
        if n > 1:
            remove_btn[0].configure(text=f"Remove {n} selected")
        else:
            remove_btn[0].configure(text="Remove selected")

    def load_list():
        tree.delete(*tree.get_children())
        with connect_db() as conn:
            rows = conn.execute(list_query).fetchall()
        for i, r in enumerate(rows):
            tree.insert("", "end", values=r,
                        tags=("row_even" if i % 2 == 0 else "row_odd",))
        if rows:
            first = tree.get_children()[0]
            tree.selection_set(first)
            tree.focus(first)
        _update_btn()
        return rows

    def remove():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Nothing selected",
                                "Select at least one record from the list first.",
                                parent=win)
            return
        rids = [tree.item(iid, "values")[0] for iid in sel]
        if len(rids) == 1:
            label = " · ".join(str(v) for v in tree.item(sel[0], "values")[1:])
            msg = f"Remove “{label or rids[0]}”?\nThis cannot be undone."
        else:
            msg = f"Remove {len(rids)} records?\nThis cannot be undone."
        if not messagebox.askyesno("Remove", msg, parent=win):
            return
        try:
            deleted, errors = perform_delete_bulk(
                table, id_col, rids,
                pre_delete=pre_delete, bulk_handler=bulk_handler,
            )
        except DeletionCancelled:
            set_status("Deletion cancelled.")
            return

        if errors and deleted == 0:
            set_status(f"Could not remove: {errors[0][1]}", error=True)
            messagebox.showerror(
                "Cannot remove",
                f"{len(errors)} record(s) could not be removed.\n\n"
                f"{errors[0][1]}", parent=win)
        elif errors:
            set_status(f"{deleted} removed, {len(errors)} skipped.", error=True)
        else:
            set_status(f"{deleted} record(s) removed.")
        root.event_generate("<<DataChanged>>")
        load_list()

    remove_btn[0] = make_button(actions, "Remove selected", remove,
                                 danger=True, anchor="center")
    remove_btn[0].pack(side="right")
    make_button(actions, "Close", win.destroy, anchor="center"
                ).pack(side="right", padx=(0, 8))
    tree.bind("<<TreeviewSelect>>", _update_btn)
    tree.bind("<MouseWheel>",
              lambda e: tree.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    tree.bind("<Button-4>", lambda e: tree.yview_scroll(-1, "units"))
    tree.bind("<Button-5>", lambda e: tree.yview_scroll(1, "units"))
    win.bind("<Delete>", lambda e: remove())
    load_list()


def remove_team():
    open_remover("Remove teams",
                 "Deleting a team also deletes its matches — you'll be asked "
                 "to confirm.",
                 table="Teams", id_col="TeamID",
                 list_query="SELECT TeamID, TeamName FROM Teams ORDER BY TeamName",
                 list_columns=["ID", "Team name"], list_col_widths=[70, 400],
                 bulk_handler=cascade_delete_teams_bulk)

def remove_club():
    open_remover("Remove clubs", "Select a club, then click Remove selected.",
                 table="Clubs", id_col="ClubID",
                 list_query="SELECT ClubID, ClubName FROM Clubs ORDER BY ClubName",
                 list_columns=["ID", "Club name"], list_col_widths=[70, 400])


def remove_player():
    open_remover("Remove players", "Select a player, then click Remove selected.",
                 table="Players", id_col="PlayerID",
                 list_query="""SELECT PlayerID, PlayerName,
                                       COALESCE(PlayerSurname, '')
                                FROM Players ORDER BY PlayerName, PlayerSurname""",
                 list_columns=["ID", "First name", "Surname"],
                 list_col_widths=[70, 200, 200],
                 pre_delete=lambda c, pid: c.execute(
                     "DELETE FROM MatchRoster WHERE PlayerID = ?", (pid,)))


def remove_tournament():
    open_remover("Remove tournaments",
                 "Tournaments used by a match must be unreferenced first.",
                 table="Tournaments", id_col="TournamentID",
                 list_query="""SELECT TournamentID, TournamentName,
                                       COALESCE(TournamentDate, '')
                                FROM Tournaments ORDER BY TournamentDate DESC""",
                 list_columns=["ID", "Name", "Date"],
                 list_col_widths=[60, 260, 140],
                 pre_delete=_clear_focus_if_matches)


def remove_match():
    open_remover("Remove matches", "Select a match, then click Remove selected.",
                 table="Matches", id_col="MatchID",
                 list_query="""SELECT m.MatchID, COALESCE(m.MatchDate, '-'),
                                      ht.TeamName, at.TeamName,
                                      COALESCE(m.MatchHScore, '-') || ' – ' ||
                                      COALESCE(m.MatchAScore, '-')
                               FROM Matches m
                               JOIN Teams ht ON m.MatchHome = ht.TeamID
                               JOIN Teams at ON m.MatchAway = at.TeamID
                               ORDER BY m.MatchID DESC""",
                 list_columns=["ID", "Date", "Home", "Away", "Score"],
                 list_col_widths=[55, 110, 140, 140, 90],
                 pre_delete=_clean_match_deps)


# ------------------------------------------------------------------ roster editor
def open_roster_editor(match_id):
    with connect_db() as conn:
        row = conn.execute("SELECT MatchHome, MatchAway FROM Matches "
                           "WHERE MatchID = ?", (match_id,)).fetchone()
        if not row:
            messagebox.showerror("Match not found",
                                 f"No match with ID {match_id}.")
            return
        home_id, away_id = row
        home_name = conn.execute("SELECT TeamName FROM Teams WHERE TeamID=?",
                                 (home_id,)).fetchone()[0]
        away_name = conn.execute("SELECT TeamName FROM Teams WHERE TeamID=?",
                                 (away_id,)).fetchone()[0]
        home_players = conn.execute(
            "SELECT PlayerID, PlayerName || ' ' || "
            "COALESCE(PlayerSurname, '') FROM Players "
            "WHERE TeamID=? ORDER BY PlayerName, PlayerSurname",
            (home_id,)).fetchall()
        away_players = conn.execute(
            "SELECT PlayerID, PlayerName || ' ' || "
            "COALESCE(PlayerSurname, '') FROM Players "
            "WHERE TeamID=? ORDER BY PlayerName, PlayerSurname",
            (away_id,)).fetchall()
        current = {r[0]: (r[1] or 0) for r in conn.execute(
            "SELECT PlayerID, PlayerPoints FROM MatchRoster "
            "WHERE MatchID = ?", (match_id,)).fetchall()}

    win = Toplevel(root)
    win.title(f"Roster · Match #{match_id}")
    win.configure(bg=BG)
    center_window(win, 820, 580)
    win.minsize(680, 480)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 12))
    tk.Label(head, text=f"Match #{match_id} roster", bg=BG, fg=FG,
             font=F_TITLE).pack(anchor="w")
    tk.Label(head, text="Double-click a player to set their goals "
                        "(leave blank to drop them from the roster).",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

    roster_state = dict(current)

    body = tk.Frame(win, bg=BG)
    body.pack(fill="both", expand=True, padx=22, pady=(0, 12))
    body.columnconfigure(0, weight=1, uniform="half")
    body.columnconfigure(1, weight=1, uniform="half")
    body.rowconfigure(0, weight=1)

    def make_side(col, team_label, players):
        colf = tk.Frame(body, bg=BG)
        colf.grid(row=0, column=col, sticky="nsew",
                  padx=(0, 6) if col == 0 else (6, 0))
        tk.Label(colf, text=team_label, bg=BG, fg=MUTED,
                 font=F_CAPS).pack(anchor="w", pady=(0, 4))
        shell = tk.Frame(colf, bg=BORDER)
        shell.pack(fill="both", expand=True)
        tree = ttk.Treeview(shell, columns=("Player", "Goals"),
                            show="headings", selectmode="browse")
        tree.heading("Player", text="Player", anchor="w")
        tree.heading("Goals", text="Goals", anchor="center")
        tree.column("Player", width=200, anchor="w", stretch=True)
        tree.column("Goals", width=60, anchor="center", stretch=False,
                    minwidth=50)
        sb = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, 1), pady=1)
        tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        tree.tag_configure("row_even", background=SURFACE)
        tree.tag_configure("row_odd",  background=STRIPE)
        return tree

    home_tree = make_side(0, home_name, home_players)
    away_tree = make_side(1, away_name, away_players)

    def refresh():
        for tree, players in ((home_tree, home_players),
                              (away_tree, away_players)):
            tree.delete(*tree.get_children())
            if not players:
                tree.insert("", "end", iid="__empty__",
                            values=("(no players on this team)", ""),
                            tags=("row_even",))
                continue
            for i, (pid, name) in enumerate(players):
                on = pid in roster_state
                vals = (name, roster_state[pid] if on else "")
                tree.insert("", "end", iid=str(pid), values=vals,
                            tags=("row_even" if i % 2 == 0 else "row_odd",))

    def edit_goals(tree, players):
        sel = tree.selection()
        if not sel or sel[0] == "__empty__":
            return
        pid = int(sel[0])
        name = dict(players)[pid]
        cur = roster_state.get(pid)
        initial = "" if cur is None else str(cur)
        result = simpledialog.askstring(
            "Player goals",
            f"Goals scored by {name}?\n\nLeave blank to remove from roster.",
            initialvalue=initial, parent=win)
        if result is None:
            return
        result = result.strip()
        if result == "":
            roster_state.pop(pid, None)
        else:
            if not result.isdigit():
                messagebox.showwarning("Invalid", "Goals must be a whole number.",
                                       parent=win)
                return
            roster_state[pid] = int(result)
        refresh()

    home_tree.bind("<Double-1>", lambda e: edit_goals(home_tree, home_players))
    away_tree.bind("<Double-1>", lambda e: edit_goals(away_tree, away_players))
    refresh()

    actions = tk.Frame(win, bg=BG)
    actions.pack(fill="x", padx=22, pady=(0, 18))

    def save():
        home_dict = dict(home_players)
        away_dict = dict(away_players)
        picks = []
        home_goals = 0
        away_goals = 0
        for pid, goals in roster_state.items():
            if pid in home_dict:
                picks.append((home_id, pid, goals))
                home_goals += goals
            elif pid in away_dict:
                picks.append((away_id, pid, goals))
                away_goals += goals
        try:
            with connect_db() as conn:
                conn.execute("DELETE FROM MatchRoster WHERE MatchID = ?",
                             (match_id,))
                conn.executemany(
                    "INSERT INTO MatchRoster (MatchID, TeamID, PlayerID, "
                    "PlayerPoints) VALUES (?, ?, ?, ?)",
                    [(match_id, tid, pid, goals) for tid, pid, goals in picks])
            set_status(f"Roster saved ({len(picks)} players; "
                       f"home goals {home_goals}, away goals {away_goals}).")
            root.event_generate("<<DataChanged>>")
            win.destroy()
        except sqlite3.IntegrityError as exc:
            set_status(f"Could not save roster: {exc}", error=True)
            messagebox.showerror("Database error", str(exc), parent=win)

    make_button(actions, "Save roster", save, accent=True, anchor="center"
                ).pack(side="right")
    make_button(actions, "Cancel", win.destroy, anchor="center"
                ).pack(side="right", padx=(0, 8))


def open_roster_picker():
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT m.MatchID,
                   COALESCE(m.MatchDate, '-'),
                   ht.TeamName || ' vs ' || at.TeamName,
                   (SELECT COALESCE(SUM(PlayerPoints), 0) FROM MatchRoster r
                    WHERE r.MatchID = m.MatchID),
                   (SELECT COUNT(*) FROM MatchRoster r
                    WHERE r.MatchID = m.MatchID)
            FROM Matches m
            JOIN Teams ht ON m.MatchHome = ht.TeamID
            JOIN Teams at ON m.MatchAway = at.TeamID
            ORDER BY m.MatchID DESC
        """).fetchall()

    win = Toplevel(root)
    win.title("Match rosters")
    win.configure(bg=BG)
    center_window(win, 820, 500)
    win.minsize(620, 380)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 12))
    tk.Label(head, text="Match rosters", bg=BG, fg=FG,
             font=F_TITLE).pack(anchor="w")
    tk.Label(head, text="Select a match to edit its roster.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

    shell = tk.Frame(win, bg=BORDER)
    shell.pack(fill="both", expand=True, padx=22, pady=(0, 10))
    tree = ttk.Treeview(shell, columns=["ID", "Date", "Match", "Goals", "Players"],
                        show="headings", selectmode="browse")
    sb = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w in zip(["ID", "Date", "Match", "Goals", "Players"],
                      [55, 110, 340, 70, 70]):
        tree.heading(col, text=col, anchor="w")
        tree.column(col, width=w, minwidth=40, anchor="w",
                    stretch=(col == "Match"))
    attach_autofit(tree)
    tree.tag_configure("row_even", background=SURFACE)
    tree.tag_configure("row_odd",  background=STRIPE)
    for i, r in enumerate(rows):
        tree.insert("", "end", values=r,
                    tags=("row_even" if i % 2 == 0 else "row_odd",))
    if rows:
        first = tree.get_children()[0]
        tree.selection_set(first)
        tree.focus(first)

    def edit_sel():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Nothing selected",
                                "Select a match first.", parent=win)
            return
        open_roster_editor(int(tree.item(sel[0], "values")[0]))

    actions = tk.Frame(win, bg=BG)
    actions.pack(fill="x", padx=22, pady=(0, 20))
    make_small_button(actions, "Edit roster", edit_sel).pack(side="right")
    make_small_button(actions, "Close", win.destroy).pack(side="right", padx=(0, 8))
    tree.bind("<Double-1>", lambda e: edit_sel())


# ------------------------------------------------------------------ period editor
_WORD_PERIODS = {
    "single": 1, "whole": 1, "one": 1,
    "half": 2, "halves": 2, "two": 2,
    "third": 3, "thirds": 3, "three": 3,
    "quarter": 4, "quarters": 4, "four": 4,
    "fifth": 5, "fifths": 5, "five": 5,
    "sixth": 6, "sixths": 6, "six": 6,
    "seventh": 7, "sevenths": 7, "seven": 7,
    "eighth": 8, "eighths": 8, "eight": 8,
}


def _parse_period_count(s):
    """Extract a period count from arbitrary text.

    Understands plain numbers ("3"), numbered descriptions ("Thirds (3)"),
    and word shortcuts ("Thirds", "Halves", "Quarter").
    Returns 0 for empty, "(none)", or anything with no recognisable count.
    """
    s = (s or "").strip().lower()
    if not s or s in ("(none)", "none"):
        return 0

    first_word = ""
    for ch in s:
        if ch.isalpha():
            first_word += ch
        elif first_word:
            break
    if first_word in _WORD_PERIODS:
        return _WORD_PERIODS[first_word]

    num = ""
    for ch in s:
        if ch.isdigit():
            num += ch
        elif num:
            break
    return int(num) if num else 0


def _parse_period_count_or_none(s):
    """Same as _parse_period_count but returns None instead of 0."""
    n = _parse_period_count(s if isinstance(s, str) else str(s or ""))
    return n if n > 0 else None


def open_period_editor(match_id):
    with connect_db() as conn:
        row = conn.execute(
            "SELECT MatchHome, MatchAway, MatchHScore, MatchAScore, "
            "PeriodCount, PeriodMinutes FROM Matches WHERE MatchID=?",
            (match_id,)).fetchone()
        if not row:
            messagebox.showerror("Match not found",
                                 f"No match with ID {match_id}.")
            return
        home_id, away_id, mh, ma, pcount, pmin = row
        home_name = conn.execute("SELECT TeamName FROM Teams WHERE TeamID=?",
                                 (home_id,)).fetchone()[0]
        away_name = conn.execute("SELECT TeamName FROM Teams WHERE TeamID=?",
                                 (away_id,)).fetchone()[0]
        existing = {r[0]: (r[1] or 0, r[2] or 0, r[3])
                    for r in conn.execute(
            "SELECT PeriodNumber, HomeScore, AwayScore, PeriodMinutes "
            "FROM MatchPeriods WHERE MatchID=? ORDER BY PeriodNumber",
            (match_id,)).fetchall()}

    if not pcount or pcount < 1:
        pcount = max(existing) if existing else 2
    pcount = max(1, min(12, pcount))
    default_min = pmin if pmin else 15

    win = Toplevel(root)
    win.title(f"Periods · Match #{match_id}")
    win.configure(bg=BG)
    center_window(win, 640, 540)
    win.minsize(560, 440)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 12))
    tk.Label(head, text=f"Match #{match_id} periods",
             bg=BG, fg=FG, font=F_TITLE).pack(anchor="w")
    tk.Label(head, text=f"{home_name}   vs   {away_name}",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))
    tk.Label(head, text="Enter the score of each break and its length "
                        "(minutes). Leave a period blank to skip it.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(4, 0))

    count_row = tk.Frame(win, bg=BG)
    count_row.pack(fill="x", padx=22, pady=(0, 8))
    tk.Label(count_row, text="Number of periods", bg=BG, fg=FG,
             font=F_BODY).pack(side="left")
    count_var = StringVar(value=str(pcount))
    ttk.Combobox(count_row, values=[str(i) for i in range(1, 13)],
                 textvariable=count_var, state="readonly",
                 font=F_BODY, width=4).pack(side="left", padx=(12, 0))

    total_lbl = tk.Label(win, text="", bg=BG, fg=MUTED, font=F_BODY)
    total_lbl.pack(anchor="w", padx=22, pady=(0, 6))

    rows_shell = tk.Frame(win, bg=BORDER)
    rows_shell.pack(fill="both", expand=True, padx=22, pady=(0, 10))
    rows_inner = tk.Frame(rows_shell, bg=SURFACE)
    rows_inner.pack(fill="both", expand=True, padx=1, pady=1)

    entries = []

    def make_entry(parent, width, var):
        return tk.Entry(parent, textvariable=var, width=width,
                        bg=SURFACE_2, fg=FG, insertbackground=FG,
                        relief="flat", highlightthickness=1,
                        highlightbackground=BORDER, highlightcolor=ACCENT,
                        font=F_BODY, justify="center")

    def build_rows():
        for child in rows_inner.winfo_children():
            child.destroy()
        entries.clear()
        try:
            n = max(1, min(12, int(count_var.get())))
        except ValueError:
            n = 2
        for i in range(n):
            pnum = i + 1
            base = existing.get(pnum, (0, 0, default_min))
            h_var = StringVar(value=str(base[0]))
            a_var = StringVar(value=str(base[1]))
            m_var = StringVar(value=str(base[2] if base[2] is not None
                                        else default_min))

            row = tk.Frame(rows_inner, bg=SURFACE)
            row.pack(fill="x", padx=10, pady=3)

            tk.Label(row, text=f"Period {pnum}", bg=SURFACE, fg=FG,
                     font=F_BODY, width=10, anchor="w").pack(side="left")
            tk.Label(row, text="Home", bg=SURFACE, fg=MUTED,
                     font=F_SMALL).pack(side="left", padx=(12, 4))
            make_entry(row, 5, h_var).pack(side="left", ipady=3)
            tk.Label(row, text="Away", bg=SURFACE, fg=MUTED,
                     font=F_SMALL).pack(side="left", padx=(10, 4))
            make_entry(row, 5, a_var).pack(side="left", ipady=3)
            tk.Label(row, text="Minutes", bg=SURFACE, fg=MUTED,
                     font=F_SMALL).pack(side="left", padx=(10, 4))
            make_entry(row, 5, m_var).pack(side="left", ipady=3)

            entries.append((h_var, a_var, m_var))
            h_var.trace_add("write", lambda *a: update_total())
            a_var.trace_add("write", lambda *a: update_total())

        update_total()

    def update_total():
        th = ta = 0
        for h_var, a_var, _ in entries:
            try:
                th += int(h_var.get() or 0)
            except ValueError:
                pass
            try:
                ta += int(a_var.get() or 0)
            except ValueError:
                pass
        note = ""
        if mh is not None and ma is not None:
            if th == mh and ta == ma:
                note = f"   ·   matches match total {mh}–{ma} ✓"
            else:
                note = f"   ·   current match total {mh}–{ma}"
        total_lbl.configure(text=f"Period sum: {th}–{ta}{note}")

    count_var.trace_add("write", lambda *a: build_rows())
    build_rows()

    actions = tk.Frame(win, bg=BG)
    actions.pack(fill="x", padx=22, pady=(0, 18))

    def save():
        picks = []
        th = ta = 0
        for i, (h_var, a_var, m_var) in enumerate(entries):
            try:
                h = int(h_var.get() or 0)
                a = int(a_var.get() or 0)
            except ValueError:
                messagebox.showwarning("Invalid score",
                                       "Scores must be whole numbers.",
                                       parent=win)
                return
            try:
                m = int(m_var.get()) if m_var.get().strip() else None
            except ValueError:
                messagebox.showwarning("Invalid minutes",
                                       "Minutes must be whole numbers.",
                                       parent=win)
                return
            picks.append((i + 1, h, a, m))
            th += h
            ta += a
        try:
            with connect_db() as conn:
                conn.execute("DELETE FROM MatchPeriods WHERE MatchID=?",
                             (match_id,))
                conn.executemany(
                    "INSERT INTO MatchPeriods "
                    "(MatchID, PeriodNumber, HomeScore, AwayScore, PeriodMinutes) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [(match_id, pn, h, a, m) for pn, h, a, m in picks])
                conn.execute(
                    "UPDATE Matches SET PeriodCount=?, PeriodMinutes=? "
                    "WHERE MatchID=?",
                    (len(picks),
                     picks[0][3] if picks else None,
                     match_id))
        except sqlite3.IntegrityError as exc:
            set_status(f"Could not save periods: {exc}", error=True)
            messagebox.showerror("Database error", str(exc), parent=win)
            return

        if mh is None or ma is None or mh != th or ma != ta:
            if messagebox.askyesno(
                    "Update match total?",
                    f"Period sum is {th}–{ta}.\n"
                    f"Current match total is "
                    f"{mh if mh is not None else '—'}–"
                    f"{ma if ma is not None else '—'}.\n\n"
                    "Update the match total to match the period sum?",
                    parent=win):
                with connect_db() as conn:
                    conn.execute(
                        "UPDATE Matches SET MatchHScore=?, MatchAScore=? "
                        "WHERE MatchID=?", (th, ta, match_id))

        set_status(f"Periods saved ({len(picks)} periods).")
        root.event_generate("<<DataChanged>>")
        win.destroy()

    make_button(actions, "Save periods", save, accent=True, anchor="center"
                ).pack(side="right")
    make_button(actions, "Cancel", win.destroy, anchor="center"
                ).pack(side="right", padx=(0, 8))


# ------------------------------------------------------------------ comparison renderers


# ------------------------------------------------------------------ roster viewer
def open_roster_viewer():
    win = Toplevel(root)
    win.title("Rosters")
    win.configure(bg=BG)
    center_window(win, 820, 580)
    win.minsize(680, 440)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 10))
    tk.Label(head, text="Rosters", bg=BG, fg=FG, font=F_TITLE).pack(anchor="w")
    tk.Label(head, text="View every player for a team or a club.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

    sel_row = tk.Frame(win, bg=BG)
    sel_row.pack(fill="x", padx=22, pady=(0, 12))

    mode_var = StringVar(value="Team")
    entity_var = StringVar()
    entity_map = {}

    tk.Label(sel_row, text="View by", bg=BG, fg=MUTED, font=F_SMALL
             ).pack(side="left", padx=(0, 6))
    mode_combo = ttk.Combobox(sel_row, values=["Team", "Club"],
                              textvariable=mode_var, state="readonly",
                              font=F_BODY, width=10)
    mode_combo.pack(side="left", padx=(0, 16))

    tk.Label(sel_row, text="Entity", bg=BG, fg=MUTED, font=F_SMALL
             ).pack(side="left", padx=(0, 6))
    entity_combo = ttk.Combobox(sel_row, values=[], textvariable=entity_var,
                                state="readonly", font=F_BODY, width=40)
    entity_combo.pack(side="left")

    shell = tk.Frame(win, bg=BORDER)
    shell.pack(fill="both", expand=True, padx=22, pady=(0, 20))
    columns = ("Name", "Birthday", "Age", "Team")
    tree = ttk.Treeview(shell, columns=columns, show="headings")
    for col, w in zip(columns, [240, 110, 60, 180]):
        tree.heading(col, text=col,
                     anchor="w" if col in ("Name", "Team") else "center")
        tree.column(col, width=w, minwidth=40,
                    anchor="w" if col in ("Name", "Team") else "center",
                    stretch=(col == "Name"))
    attach_autofit(tree)
    sb = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    tree.tag_configure("row_even", background=SURFACE)
    tree.tag_configure("row_odd",  background=STRIPE)

    def refresh_players():
        tree.delete(*tree.get_children())
        label = entity_var.get()
        if label not in entity_map:
            return
        eid = entity_map[label]
        is_team = mode_var.get() == "Team"
        with connect_db() as conn:
            if is_team:
                rows = conn.execute("""
                    SELECT p.PlayerName, COALESCE(p.PlayerSurname, ''),
                           COALESCE(p.PlayerBirthdate, '—'),
                           COALESCE(CAST(strftime('%Y.%m%d','now') -
                                         strftime('%Y.%m%d', p.PlayerBirthdate)
                                         AS INTEGER), '—')
                    FROM Players p WHERE p.TeamID = ?
                    ORDER BY p.PlayerName, p.PlayerSurname
                """, (eid,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT p.PlayerName, COALESCE(p.PlayerSurname, ''),
                           COALESCE(p.PlayerBirthdate, '—'),
                           COALESCE(CAST(strftime('%Y.%m%d','now') -
                                         strftime('%Y.%m%d', p.PlayerBirthdate)
                                         AS INTEGER), '—'),
                           t.TeamName
                    FROM Players p
                    JOIN Teams t ON p.TeamID = t.TeamID
                    WHERE t.ClubID = ?
                    ORDER BY t.TeamName, p.PlayerName, p.PlayerSurname
                """, (eid,)).fetchall()
        for i, r in enumerate(rows):
            full = f"{r[0]} {r[1]}".strip()
            team_name = r[4] if len(r) > 4 else ""
            tree.insert("", "end", values=(full, r[2], r[3], team_name),
                        tags=("row_even" if i % 2 == 0 else "row_odd",))
        if not rows:
            tree.insert("", "end", values=("(no players)", "", "", ""),
                        tags=("row_even",))

    def refresh_entity_list(*_args):
        is_team = mode_var.get() == "Team"
        with connect_db() as conn:
            if is_team:
                rows = conn.execute("SELECT TeamID, TeamName FROM Teams "
                                    "ORDER BY TeamName").fetchall()
            else:
                rows = conn.execute("SELECT ClubID, ClubName FROM Clubs "
                                    "ORDER BY ClubName").fetchall()
        entity_map.clear()
        entity_map.update({f"{eid} · {name}": eid for eid, name in rows})
        entity_combo.configure(values=list(entity_map))
        if entity_map:
            entity_var.set(next(iter(entity_map)))
        else:
            entity_var.set("")
        refresh_players()

    mode_combo.bind("<<ComboboxSelected>>", refresh_entity_list)
    entity_combo.bind("<<ComboboxSelected>>", lambda e: refresh_players())
    refresh_entity_list()


# ------------------------------------------------------------------ elo
DEFAULT_ELO = 1500
ELO_K = 32
PROVISIONAL_K = 64
PROVISIONAL_MATCHES = 10
MARGIN_CAP = 2.0
MARGIN_DIVISOR = 10

# Distinct series colours for line charts (team trajectories)
CHART_COLORS = [
    "#4c8dff", "#6ee7b7", "#fbbf24", "#f472b6",
    "#a78bfa", "#f87171", "#22d3ee", "#fb923c",
    "#a3e635", "#e879f9", "#38bdf8", "#facc15",
]

# Per-period colours for stacked bars (P1, P2, P3, ...)
PERIOD_COLORS = [
    "#4c8dff", "#6ee7b7", "#fbbf24", "#f472b6",
    "#a78bfa", "#f87171", "#22d3ee", "#fb923c",
]


def _k_for_matches(count):
    """Linear taper from PROVISIONAL_K (new teams) down to ELO_K."""
    if count >= PROVISIONAL_MATCHES:
        return ELO_K
    return PROVISIONAL_K - (PROVISIONAL_K - ELO_K) * (count / PROVISIONAL_MATCHES)


def compute_elo(conn, since_date=None, until_date=None, with_history=False):
    """Replay completed matches. Returns (ratings, upsets, stats[, history]).

    history (when with_history=True): {team_id: [(match_index, elo), ...]}
    where match_index is the position in the replay sequence (0-based).
    """
    ratings = {tid: DEFAULT_ELO for tid, in conn.execute(
        "SELECT TeamID FROM Teams").fetchall()}
    teams = {tid: name for tid, name in conn.execute(
        "SELECT TeamID, TeamName FROM Teams").fetchall()}
    upsets = []

    def _blank():
        return {'played': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                'upsets_caused': 0, 'upsets_suffered': 0}
    stats = {tid: _blank() for tid in ratings}
    history = {tid: [] for tid in ratings} if with_history else None

    query = """
        SELECT MatchHome, MatchAway, MatchHScore, MatchAScore, MatchDate
        FROM Matches
        WHERE MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
    """
    params = []
    if since_date:
        query += " AND MatchDate >= ?"
        params.append(since_date)
    if until_date:
        query += " AND MatchDate <= ?"
        params.append(until_date)
    query += " ORDER BY COALESCE(MatchDate, '9999'), MatchID"

    idx = 0
    for home, away, hs, a_s, date in conn.execute(
            query, tuple(params)).fetchall():
        ra = ratings.get(home, DEFAULT_ELO)
        rb = ratings.get(away, DEFAULT_ELO)
        ea = 1 / (1 + 10 ** ((rb - ra) / 400))
        sa = 1.0 if hs > a_s else (0.0 if hs < a_s else 0.5)

        margin = min(MARGIN_CAP, 1 + abs(hs - a_s) / MARGIN_DIVISOR)
        ka = _k_for_matches(stats[home]['played']) * margin
        kb = _k_for_matches(stats[away]['played']) * margin

        if sa == 1.0:
            stats[home]['wins'] += 1
            stats[away]['losses'] += 1
            if ra < rb:
                upsets.append((rb - ra, teams.get(home, "?"),
                               teams.get(away, "?"), f"{hs}–{a_s}", date))
                stats[home]['upsets_caused'] += 1
                stats[away]['upsets_suffered'] += 1
        elif sa == 0.0:
            stats[home]['losses'] += 1
            stats[away]['wins'] += 1
            if rb < ra:
                upsets.append((ra - rb, teams.get(away, "?"),
                               teams.get(home, "?"), f"{a_s}–{hs}", date))
                stats[away]['upsets_caused'] += 1
                stats[home]['upsets_suffered'] += 1
        else:
            stats[home]['draws'] += 1
            stats[away]['draws'] += 1

        ratings[home] = ra + ka * (sa - ea)
        ratings[away] = rb + kb * ((1 - sa) - (1 - ea))

        if with_history:
            history[home].append((idx, ratings[home]))
            history[away].append((idx, ratings[away]))

        stats[home]['played'] += 1
        stats[away]['played'] += 1
        idx += 1

    upsets.sort(key=lambda u: -u[0])
    if with_history:
        return ratings, upsets, stats, history
    return ratings, upsets, stats


def compute_draw_rate(conn, since_date=None, until_date=None):
    query = """
        SELECT SUM(CASE WHEN MatchHScore = MatchAScore THEN 1 ELSE 0 END),
               COUNT(*)
        FROM Matches
        WHERE MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
    """
    params = []
    if since_date:
        query += " AND MatchDate >= ?"
        params.append(since_date)
    if until_date:
        query += " AND MatchDate <= ?"
        params.append(until_date)
    draws, total = conn.execute(query, tuple(params)).fetchone()
    if not total:
        return 0.25
    return draws / total


def list_seasons(conn):
    """Distinct calendar years with completed matches, newest first."""
    rows = conn.execute("""
        SELECT DISTINCT strftime('%Y', MatchDate) AS y
        FROM Matches
        WHERE MatchDate IS NOT NULL
          AND MatchHScore IS NOT NULL
          AND MatchAScore IS NOT NULL
        ORDER BY y DESC
    """).fetchall()
    return [r[0] for r in rows if r[0]]


def predict_match(home_id, away_id, ratings, draw_rate):
    """Return (p_home_win, p_draw, p_away_win), each 0-1."""
    ra = ratings.get(home_id, DEFAULT_ELO)
    rb = ratings.get(away_id, DEFAULT_ELO)
    ea = 1 / (1 + 10 ** ((rb - ra) / 400))
    return (ea * (1 - draw_rate), draw_rate, (1 - ea) * (1 - draw_rate))


def open_elo_trend_window(since, until, title_suffix=""):
    with connect_db() as conn:
        ratings, upsets, stats, history = compute_elo(
            conn, since, until, with_history=True)
        teams = conn.execute(
            "SELECT TeamID, TeamName FROM Teams ORDER BY TeamName"
        ).fetchall()

    teams_with_data = [(tid, name) for tid, name in teams
                       if history.get(tid)]
    teams_with_data.sort(key=lambda t: -ratings.get(t[0], DEFAULT_ELO))

    win = Toplevel(root)
    win.title(f"Elo Trend {title_suffix}".strip())
    win.configure(bg=BG)
    center_window(win, 1100, 680)
    win.minsize(800, 500)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 10))
    tk.Label(head, text=f"Elo Trend {title_suffix}".strip(),
             bg=BG, fg=FG, font=F_TITLE).pack(anchor="w")
    tk.Label(head,
             text=f"{len(teams_with_data)} team(s) · "
                  f"{sum(len(h) for h in history.values())} match data "
                  f"points · dashed line marks the 1500 start",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

    if not teams_with_data:
        tk.Label(win, text="No completed matches in this range.",
                 bg=BG, fg=MUTED, font=F_BODY).pack(padx=22, pady=40)
        return

    shell = tk.Frame(win, bg=BORDER)
    shell.pack(fill="both", expand=True, padx=22, pady=(0, 20))
    canvas = tk.Canvas(shell, bg=SURFACE, highlightthickness=0)
    canvas.pack(fill="both", expand=True, padx=1, pady=1)

    def draw(_e=None):
        canvas.delete("all")
        w = canvas.winfo_width() or 900
        h = canvas.winfo_height() or 500
        pad_l, pad_r, pad_t, pad_b = 62, 30, 24, 40
        legend_rows = (len(teams_with_data) + 3) // 4
        legend_h = legend_rows * 22 + 10
        chart_bottom = h - legend_h - pad_b

        all_points = [p for tid, _ in teams_with_data
                       for p in history[tid]]
        if not all_points:
            return
        x_max = max(p[0] for p in all_points) or 1
        y_min = min(p[1] for p in all_points)
        y_max = max(p[1] for p in all_points)
        y_span = max(y_max - y_min, 100)
        y_mid = (y_max + y_min) / 2
        y_lo = y_mid - y_span * 0.55
        y_hi = y_mid + y_span * 0.55

        def to_px(x_val, y_val):
            px = pad_l + (x_val / x_max) * (w - pad_l - pad_r)
            py = chart_bottom - (y_val - y_lo) / (y_hi - y_lo) * (chart_bottom - pad_t) + pad_t
            return px, py

        # Y grid + labels
        for i in range(5):
            y_val = y_lo + (y_hi - y_lo) * i / 4
            py = chart_bottom - (y_val - y_lo) / (y_hi - y_lo) * (chart_bottom - pad_t) + pad_t
            canvas.create_line(pad_l, py, w - pad_r, py, fill=BORDER, dash=(2, 4))
            canvas.create_text(pad_l - 6, py, text=f"{y_val:.0f}",
                               anchor="e", fill=MUTED, font=(FONT, 8))

        # Start reference at 1500
        if y_lo < 1500 < y_hi:
            _, py = to_px(0, 1500)
            canvas.create_line(pad_l, py, w - pad_r, py,
                               fill="#6b7280", dash=(4, 4))
            canvas.create_text(w - pad_r - 6, py - 8, text="start",
                               anchor="se", fill="#6b7280", font=(FONT, 7))

        # X labels
        n_ticks = min(8, x_max + 1)
        for i in range(n_ticks):
            x_val = i * x_max / max(1, n_ticks - 1)
            px, _ = to_px(x_val, y_lo)
            canvas.create_text(px, chart_bottom + 14, text=f"#{int(x_val)}",
                               fill=MUTED, font=(FONT, 8))

        canvas.create_text(pad_l - 6, pad_t - 8, text="Elo",
                           anchor="se", fill=MUTED, font=F_SMALL)
        canvas.create_text(w - pad_r, chart_bottom + 30, text="match order",
                           anchor="e", fill=MUTED, font=F_SMALL)

        # Lines
        for idx, (tid, name) in enumerate(teams_with_data):
            points = history[tid]
            color = CHART_COLORS[idx % len(CHART_COLORS)]
            if len(points) == 1:
                x_val, y_val = points[0]
                px, py = to_px(x_val, y_val)
                canvas.create_oval(px - 4, py - 4, px + 4, py + 4,
                                   fill=color, outline="")
            else:
                coords = []
                for x_val, y_val in points:
                    px, py = to_px(x_val, y_val)
                    coords.extend([px, py])
                canvas.create_line(*coords, fill=color, width=2)

        # Legend
        legend_y = chart_bottom + pad_b + 6
        cols = 4
        col_w = max(180, (w - pad_l - pad_r) // cols)
        for idx, (tid, name) in enumerate(teams_with_data):
            col = idx % cols
            row = idx // cols
            lx = pad_l + col * col_w
            ly = legend_y + row * 22
            color = CHART_COLORS[idx % len(CHART_COLORS)]
            canvas.create_rectangle(lx, ly, lx + 10, ly + 10,
                                     fill=color, outline="")
            final_elo = ratings.get(tid, DEFAULT_ELO)
            canvas.create_text(lx + 15, ly + 5,
                               text=f"{name} ({final_elo:.0f})",
                               anchor="w", fill=FG, font=F_SMALL)

    canvas.bind("<Configure>", draw)
    win.after(50, draw)


def open_elo_view():
    win = Toplevel(root)
    win.title("Power Rankings")
    win.configure(bg=BG)
    center_window(win, 1040, 740)
    win.minsize(820, 580)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 6))
    tk.Label(head, text="Power Rankings", bg=BG, fg=FG,
             font=F_TITLE).pack(anchor="w")
    tk.Label(head, text="Elo ratings replayed from match history. Every team "
                        "starts at 1500. Wins against stronger teams count "
                        "more; larger margins count more. Teams with fewer "
                        f"than {PROVISIONAL_MATCHES} matches this window are "
                        "provisional (⚠). UC = upsets caused, US = upsets "
                        "suffered.",
             bg=BG, fg=MUTED, font=F_SMALL, wraplength=980, justify="left"
             ).pack(anchor="w", pady=(2, 0))

    with connect_db() as conn:
        teams = conn.execute(
            "SELECT TeamID, TeamName FROM Teams ORDER BY TeamName"
        ).fetchall()
        seasons = list_seasons(conn)

    season_row = tk.Frame(win, bg=BG)
    season_row.pack(fill="x", padx=22, pady=(8, 6))
    tk.Label(season_row, text="Season", bg=BG, fg=MUTED, font=F_SMALL
             ).pack(side="left", padx=(0, 6))
    season_var = StringVar(value="All time")
    season_combo = ttk.Combobox(
        season_row, values=["All time"] + seasons,
        textvariable=season_var, state="readonly",
        font=F_SMALL, width=20)
    season_combo.pack(side="left")

    def open_trend():
        s = season_var.get()
        if s == "All time":
            open_elo_trend_window(None, None, "— All time")
        else:
            open_elo_trend_window(f"{s}-01-01", f"{s}-12-31", f"— {s}")

    make_small_button(season_row, "📈 View trend", open_trend
                       ).pack(side="left", padx=(12, 0))

    table_shell = tk.Frame(win, bg=BORDER)
    table_shell.pack(fill="both", expand=True, padx=22, pady=(4, 8))
    tree = ttk.Treeview(
        table_shell,
        columns=("Rank", "Team", "Elo", "P", "W", "D", "L", "UC", "US"),
        show="headings", selectmode="browse")
    sb = ttk.Scrollbar(table_shell, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w, a in (("Rank", 60, "center"), ("Team", 220, "w"),
                      ("Elo", 70, "center"), ("P", 60, "center"),
                      ("W", 50, "center"), ("D", 50, "center"),
                      ("L", 50, "center"), ("UC", 55, "center"),
                      ("US", 55, "center")):
        tree.heading(col, text=col, anchor=a)
        tree.column(col, width=w, minwidth=40, anchor=a,
                    stretch=(col == "Team"))
    tree.tag_configure("row_even", background=SURFACE)
    tree.tag_configure("row_odd",  background=STRIPE)

    pred_card = tk.Frame(win, bg=SURFACE, highlightbackground=BORDER,
                         highlightthickness=1)
    pred_card.pack(fill="x", padx=22, pady=(0, 8))
    pred_inner = tk.Frame(pred_card, bg=SURFACE, padx=14, pady=12)
    pred_inner.pack(fill="both", expand=True)
    tk.Label(pred_inner, text="PREDICTION TOOL", bg=SURFACE, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(0, 6))

    row = tk.Frame(pred_inner, bg=SURFACE)
    row.pack(fill="x", pady=(0, 6))
    team_labels = [f"{tid} · {name}" for tid, name in teams]
    id_of_label = {f"{tid} · {name}": tid for tid, name in teams}
    home_var = StringVar()
    away_var = StringVar()
    if team_labels:
        home_var.set(team_labels[0])
        away_var.set(team_labels[1] if len(team_labels) > 1 else team_labels[0])

    tk.Label(row, text="Home", bg=SURFACE, fg=FG, font=F_SMALL
             ).pack(side="left", padx=(0, 6))
    home_combo = ttk.Combobox(row, values=team_labels, textvariable=home_var,
                              state="readonly", font=F_SMALL, width=28)
    home_combo.pack(side="left", padx=(0, 12))
    tk.Label(row, text="Away", bg=SURFACE, fg=FG, font=F_SMALL
             ).pack(side="left", padx=(0, 6))
    away_combo = ttk.Combobox(row, values=team_labels, textvariable=away_var,
                              state="readonly", font=F_SMALL, width=28)
    away_combo.pack(side="left")

    result_lbl = tk.Label(pred_inner, text="", bg=SURFACE, fg=ACCENT,
                          font=(FONT, 12, "bold"), anchor="w")
    result_lbl.pack(fill="x", pady=(4, 0))

    up_card = tk.Frame(win, bg=SURFACE, highlightbackground=BORDER,
                       highlightthickness=1)
    up_card.pack(fill="x", padx=22, pady=(0, 18))
    up_inner = tk.Frame(up_card, bg=SURFACE, padx=14, pady=10)
    up_inner.pack(fill="both", expand=True)
    tk.Label(up_inner, text="BIGGEST UPSETS (HIGHER-RATED TEAM LOST)",
             bg=SURFACE, fg=MUTED, font=F_CAPS).pack(anchor="w", pady=(0, 4))
    up_list = tk.Frame(up_inner, bg=SURFACE)
    up_list.pack(fill="x")

    state = {"ratings": {}, "upsets": [], "stats": {}, "draw_rate": 0.25}

    def get_range():
        s = season_var.get()
        if s == "All time":
            return None, None
        return f"{s}-01-01", f"{s}-12-31"

    def refresh_prediction(*_):
        h = id_of_label.get(home_var.get())
        a = id_of_label.get(away_var.get())
        if h is None or a is None:
            result_lbl.configure(text="")
            return
        if h == a:
            result_lbl.configure(text="Pick two different teams.")
            return
        ph, pd, pa = predict_match(h, a, state["ratings"],
                                    state["draw_rate"])
        hn = home_var.get().split(" · ", 1)[-1]
        an = away_var.get().split(" · ", 1)[-1]
        result_lbl.configure(
            text=f"{hn} {ph*100:.0f}%   ·   Draw {pd*100:.0f}%   ·   "
                 f"{an} {pa*100:.0f}%")

    def reload():
        since, until = get_range()
        with connect_db() as conn:
            ratings, upsets, stats = compute_elo(conn, since, until)
            draw_rate = compute_draw_rate(conn, since, until)
        state["ratings"] = ratings
        state["upsets"] = upsets
        state["stats"] = stats
        state["draw_rate"] = draw_rate

        tree.delete(*tree.get_children())
        sorted_teams = sorted(teams,
                              key=lambda t: -ratings.get(t[0], DEFAULT_ELO))
        blank = {"played": 0, "wins": 0, "draws": 0, "losses": 0,
                 "upsets_caused": 0, "upsets_suffered": 0}
        for i, (tid, name) in enumerate(sorted_teams):
            elo = ratings.get(tid, DEFAULT_ELO)
            st = stats.get(tid, blank)
            marker = " ⚠" if st["played"] < PROVISIONAL_MATCHES else ""
            tree.insert(
                "", "end",
                values=(f"#{i + 1}", name, f"{elo:.0f}",
                        f"{st['played']}{marker}",
                        st["wins"], st["draws"], st["losses"],
                        st["upsets_caused"], st["upsets_suffered"]),
                tags=("row_even" if i % 2 == 0 else "row_odd",))

        for child in up_list.winfo_children():
            child.destroy()
        if upsets:
            for gap, winner, loser, score, date in upsets[:3]:
                line = tk.Frame(up_list, bg=SURFACE)
                line.pack(fill="x", pady=1)
                tk.Label(line, text=f"{winner}  beat  {loser}",
                         bg=SURFACE, fg=FG, font=F_SMALL,
                         anchor="w").pack(side="left")
                tk.Label(line, text=f"{score}   ·   Elo gap {gap:.0f}"
                                    f"   ·   {date or '—'}",
                         bg=SURFACE, fg=MUTED, font=F_SMALL,
                         anchor="e").pack(side="right")
        else:
            tk.Label(up_list, text="No upsets recorded in this window.",
                     bg=SURFACE, fg=MUTED, font=F_SMALL
                     ).pack(anchor="w")

        refresh_prediction()

    season_combo.bind("<<ComboboxSelected>>", lambda e: reload())
    home_combo.bind("<<ComboboxSelected>>", refresh_prediction)
    away_combo.bind("<<ComboboxSelected>>", refresh_prediction)

    reload()
    attach_autofit(tree)


# ------------------------------------------------------------------ records
def _compute_team_streaks(conn):
    """Returns dict: category -> (value, team_name)."""
    teams = {tid: name for tid, name in conn.execute(
        "SELECT TeamID, TeamName FROM Teams").fetchall()}
    results_by_team = {}
    for home, away, hs, a_s in conn.execute("""
        SELECT MatchHome, MatchAway, MatchHScore, MatchAScore
        FROM Matches
        WHERE MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
        ORDER BY COALESCE(MatchDate, '9999'), MatchID
    """).fetchall():
        results_by_team.setdefault(home, []).append((hs, a_s))
        results_by_team.setdefault(away, []).append((a_s, hs))

    best = {"win": (0, None), "unbeaten": (0, None),
            "lose": (0, None), "draw": (0, None)}
    for tid, results in results_by_team.items():
        cur_w = cur_u = cur_l = cur_d = 0
        top_w = top_u = top_l = top_d = 0
        for my, opp in results:
            if my > opp:
                cur_w += 1
                cur_u += 1
                cur_l = cur_d = 0
                top_w = max(top_w, cur_w)
                top_u = max(top_u, cur_u)
            elif my < opp:
                cur_l += 1
                cur_w = cur_u = cur_d = 0
                top_l = max(top_l, cur_l)
            else:
                cur_d += 1
                cur_w = cur_l = 0
                cur_u += 1
                top_d = max(top_d, cur_d)
                top_u = max(top_u, cur_u)
        for cat, val in (("win", top_w), ("unbeaten", top_u),
                         ("lose", top_l), ("draw", top_d)):
            if val > best[cat][0]:
                best[cat] = (val, teams.get(tid, "?"))

    return best


def open_record_book():
    win = Toplevel(root)
    win.title("Record Book")
    win.configure(bg=BG)
    center_window(win, 1020, 800)
    win.minsize(820, 600)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 6))
    tk.Label(head, text="Record Book", bg=BG, fg=FG,
             font=F_TITLE).pack(anchor="w")
    tk.Label(head, text="All-time extremes from your match history.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

    outer = tk.Frame(win, bg=BG)
    outer.pack(fill="both", expand=True, pady=(6, 0))
    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, yscrollincrement=16)
    sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    content = tk.Frame(canvas, bg=BG)
    wid = canvas.create_window((0, 0), window=content, anchor="nw")

    def _rc(_e=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(wid, width=canvas.winfo_width())

    content.bind("<Configure>", _rc)
    canvas.bind("<Configure>", _rc)
    canvas.bind("<MouseWheel>",
                lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    with connect_db() as conn:
        streaks = _compute_team_streaks(conn)

        biggest = conn.execute("""
            SELECT ABS(MatchHScore-MatchAScore),
                   CASE WHEN MatchHScore > MatchAScore THEN ht.TeamName
                        ELSE at.TeamName END,
                   CASE WHEN MatchHScore > MatchAScore THEN at.TeamName
                        ELSE ht.TeamName END,
                   MatchHScore || '–' || MatchAScore,
                   COALESCE(MatchDate, '—')
            FROM Matches m
            JOIN Teams ht ON ht.TeamID = m.MatchHome
            JOIN Teams at ON at.TeamID = m.MatchAway
            WHERE MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
            ORDER BY ABS(MatchHScore-MatchAScore) DESC LIMIT 1
        """).fetchone()

        highest = conn.execute("""
            SELECT MatchHScore + MatchAScore,
                   ht.TeamName || ' vs ' || at.TeamName,
                   MatchHScore || '–' || MatchAScore,
                   COALESCE(MatchDate, '—')
            FROM Matches m
            JOIN Teams ht ON ht.TeamID = m.MatchHome
            JOIN Teams at ON at.TeamID = m.MatchAway
            WHERE MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
            ORDER BY MatchHScore + MatchAScore DESC LIMIT 1
        """).fetchone()

        lowest = conn.execute("""
            SELECT MatchHScore + MatchAScore,
                   ht.TeamName || ' vs ' || at.TeamName,
                   MatchHScore || '–' || MatchAScore,
                   COALESCE(MatchDate, '—')
            FROM Matches m
            JOIN Teams ht ON ht.TeamID = m.MatchHome
            JOIN Teams at ON at.TeamID = m.MatchAway
            WHERE MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
            ORDER BY MatchHScore + MatchAScore ASC LIMIT 1
        """).fetchone()

        top_period = conn.execute("""
            SELECT MAX(mp.HomeScore, mp.AwayScore),
                   CASE WHEN mp.HomeScore > mp.AwayScore THEN ht.TeamName
                        ELSE at.TeamName END,
                   CASE WHEN mp.HomeScore > mp.AwayScore THEN at.TeamName
                        ELSE ht.TeamName END,
                   mp.PeriodNumber,
                   COALESCE(m.MatchDate, '—')
            FROM MatchPeriods mp
            JOIN Matches m ON m.MatchID = mp.MatchID
            JOIN Teams ht ON ht.TeamID = m.MatchHome
            JOIN Teams at ON at.TeamID = m.MatchAway
            ORDER BY MAX(mp.HomeScore, mp.AwayScore) DESC LIMIT 1
        """).fetchone()

        best_player_match = conn.execute("""
            SELECT r.PlayerPoints,
                   p.PlayerName || ' ' || COALESCE(p.PlayerSurname, ''),
                   COALESCE(t.TeamName, '—'),
                   COALESCE(m.MatchDate, '—')
            FROM MatchRoster r
            JOIN Players p ON p.PlayerID = r.PlayerID
            JOIN Matches m ON m.MatchID = r.MatchID
            LEFT JOIN Teams t ON t.TeamID = r.TeamID
            ORDER BY r.PlayerPoints DESC, m.MatchID DESC LIMIT 1
        """).fetchone()

        best_player_year = conn.execute("""
            SELECT SUM(r.PlayerPoints),
                   p.PlayerName || ' ' || COALESCE(p.PlayerSurname, ''),
                   strftime('%Y', m.MatchDate)
            FROM MatchRoster r
            JOIN Players p ON p.PlayerID = r.PlayerID
            JOIN Matches m ON m.MatchID = r.MatchID
            WHERE m.MatchDate IS NOT NULL
            GROUP BY p.PlayerID, strftime('%Y', m.MatchDate)
            ORDER BY SUM(r.PlayerPoints) DESC LIMIT 1
        """).fetchone()

        best_player_career = conn.execute("""
            SELECT SUM(r.PlayerPoints),
                   p.PlayerName || ' ' || COALESCE(p.PlayerSurname, '')
            FROM MatchRoster r
            JOIN Players p ON p.PlayerID = r.PlayerID
            GROUP BY p.PlayerID
            ORDER BY SUM(r.PlayerPoints) DESC LIMIT 1
        """).fetchone()

        most_matches_team = conn.execute("""
            SELECT COUNT(*), t.TeamName
            FROM Teams t
            JOIN Matches m ON (m.MatchHome=t.TeamID OR m.MatchAway=t.TeamID)
                          AND m.MatchHScore IS NOT NULL
            GROUP BY t.TeamID
            ORDER BY COUNT(*) DESC LIMIT 1
        """).fetchone()

    records = []
    if streaks["win"][1]:
        records.append(("🏆", "LONGEST WIN STREAK", streaks["win"][0],
                        f"{streaks['win'][1]} — consecutive wins"))
    if streaks["unbeaten"][1]:
        records.append(("🛡", "LONGEST UNBEATEN",
                        streaks["unbeaten"][0],
                        f"{streaks['unbeaten'][1]} — wins or draws"))
    if streaks["lose"][1]:
        records.append(("📉", "LONGEST LOSING STREAK",
                        streaks["lose"][0],
                        f"{streaks['lose'][1]} — consecutive losses"))
    if streaks["draw"][1]:
        records.append(("🤝", "LONGEST DRAWING STREAK",
                        streaks["draw"][0],
                        f"{streaks['draw'][1]} — consecutive draws"))
    if biggest and biggest[1]:
        records.append(("💥", "BIGGEST WIN", f"+{biggest[0]}",
                        f"{biggest[1]} beat {biggest[2]} {biggest[3]}"
                        f"   ·   {biggest[4]}"))
    if highest and highest[1]:
        records.append(("🎯", "HIGHEST-SCORING MATCH", highest[0],
                        f"{highest[1]} {highest[2]}   ·   {highest[3]}"))
    if lowest and lowest[1]:
        records.append(("🧊", "LOWEST-SCORING MATCH", lowest[0],
                        f"{lowest[1]} {lowest[2]}   ·   {lowest[3]}"))
    if top_period and top_period[1]:
        records.append(("⚡", "HIGHEST SINGLE-PERIOD SCORE",
                        top_period[0],
                        f"{top_period[1]} scored {top_period[0]} in "
                        f"P{top_period[3]} against {top_period[2]}"
                        f"   ·   {top_period[4]}"))
    if best_player_match and best_player_match[0]:
        records.append(("🎖", "MOST GOALS IN ONE MATCH",
                        best_player_match[0],
                        f"{best_player_match[1]} ({best_player_match[2]})"
                        f"   ·   {best_player_match[3]}"))
    if best_player_year and best_player_year[0]:
        records.append(("📅", f"MOST GOALS IN A YEAR ({best_player_year[2]})",
                        best_player_year[0],
                        f"{best_player_year[1]}"))
    if best_player_career and best_player_career[0]:
        records.append(("👑", "MOST CAREER GOALS",
                        best_player_career[0], best_player_career[1]))
    if most_matches_team and most_matches_team[0]:
        records.append(("🎽", "MOST MATCHES PLAYED", most_matches_team[0],
                        f"{most_matches_team[1]}"))

    grid = tk.Frame(content, bg=BG)
    grid.pack(fill="x", padx=22, pady=(0, 20))
    grid.columnconfigure(0, weight=1, uniform="rec")
    grid.columnconfigure(1, weight=1, uniform="rec")

    def make_card(parent, row, col, icon, title, value, context):
        card = tk.Frame(parent, bg=SURFACE,
                        highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=row, column=col, sticky="nsew",
                  padx=(0, 6) if col == 0 else (6, 0), pady=4)
        inner = tk.Frame(card, bg=SURFACE, padx=14, pady=12)
        inner.pack(fill="both", expand=True)
        hdr = tk.Frame(inner, bg=SURFACE)
        hdr.pack(fill="x")
        tk.Label(hdr, text=icon, bg=SURFACE, fg=ACCENT,
                 font=(FONT, 14)).pack(side="left")
        tk.Label(hdr, text=title, bg=SURFACE, fg=MUTED,
                 font=F_CAPS).pack(side="left", padx=(6, 0))
        tk.Label(inner, text=str(value), bg=SURFACE, fg=FG,
                 font=(FONT, 24, "bold")).pack(anchor="w", pady=(4, 0))
        tk.Label(inner, text=context, bg=SURFACE, fg=MUTED,
                 font=F_SMALL, wraplength=420, justify="left"
                 ).pack(anchor="w", pady=(4, 0))

    if not records:
        tk.Label(content, text="No records yet — add matches to populate.",
                 bg=BG, fg=MUTED, font=F_BODY
                 ).pack(padx=22, pady=20, anchor="w")
    else:
        for i, (icon, title, value, context) in enumerate(records):
            r, c = divmod(i, 2)
            make_card(grid, r, c, icon, title, value, context)


# ------------------------------------------------------------------ period splits chart
def _render_period_splits(parent, period_rows):
    """period_rows: (TeamID, TeamName, PeriodNumber, Goals)"""
    card = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER,
                    highlightthickness=1)
    card.pack(fill="x", padx=22, pady=(0, 12))
    inner = tk.Frame(card, bg=SURFACE, padx=12, pady=10)
    inner.pack(fill="both", expand=True)
    tk.Label(inner, text="TEAM · GOALS BY PERIOD",
             bg=SURFACE, fg=MUTED, font=F_CAPS
             ).pack(anchor="w", pady=(0, 6))

    if not period_rows:
        tk.Label(inner,
                 text="No period data yet. Matches recorded with periods "
                      "will appear here as a stacked bar per team.",
                 bg=SURFACE, fg=MUTED, font=F_SMALL, wraplength=800,
                 justify="left").pack(anchor="w", pady=8)
        return

    teams = []
    data = {}
    max_period = 1
    for _tid, team, period, goals in period_rows:
        if team not in data:
            data[team] = {}
            teams.append(team)
        data[team][period] = goals or 0
        max_period = max(max_period, period)

    totals = {t: sum(data[t].values()) for t in teams}
    max_total = max(totals.values()) or 1

    row_h = 28
    pad = 14
    label_w = 160
    legend_h = 24
    chart_h = pad + len(teams) * row_h + legend_h + pad

    canvas = tk.Canvas(inner, bg=SURFACE, highlightthickness=0,
                       height=chart_h)
    canvas.pack(fill="x")

    def draw(_e=None):
        canvas.delete("all")
        w = canvas.winfo_width() or 900
        bar_max = max(w - label_w - pad * 2 - 50, 100)

        for i, team in enumerate(teams):
            y = pad + i * row_h + row_h // 2
            canvas.create_text(pad, y, text=team, anchor="w",
                               fill=FG, font=F_SMALL)
            total = totals[team] or 1
            bar_len = (total / max_total) * bar_max
            bar_x = label_w

            for period in sorted(data[team]):
                goals = data[team][period]
                if goals == 0:
                    continue
                seg_w = (goals / total) * bar_len
                color = PERIOD_COLORS[(period - 1) % len(PERIOD_COLORS)]
                canvas.create_rectangle(
                    bar_x, y - row_h // 2 + 6,
                    bar_x + seg_w, y + row_h // 2 - 6,
                    fill=color, outline="")
                if seg_w > 26:
                    canvas.create_text(bar_x + seg_w / 2, y,
                                       text=str(goals), fill="#ffffff",
                                       font=(FONT, 8, "bold"))
                bar_x += seg_w

            canvas.create_text(bar_x + 8, y, text=str(totals[team]),
                               anchor="w", fill=MUTED, font=F_SMALL)

        legend_y = pad + len(teams) * row_h + 10
        legend_x = pad
        for period in range(1, max_period + 1):
            color = PERIOD_COLORS[(period - 1) % len(PERIOD_COLORS)]
            canvas.create_rectangle(legend_x, legend_y - 6,
                                     legend_x + 12, legend_y + 6,
                                     fill=color, outline="")
            canvas.create_text(legend_x + 18, legend_y,
                               text=f"Period {period}",
                               anchor="w", fill=MUTED, font=F_SMALL)
            legend_x += 90

    canvas.bind("<Configure>", draw)
    canvas.after(50, draw)


# ------------------------------------------------------------------ stats overview
def open_stats_view():
    win = Toplevel(root)
    win.title("Stats")
    win.configure(bg=BG)
    center_window(win, 1020, 780)
    win.minsize(820, 580)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 6))
    tk.Label(head, text="Stats", bg=BG, fg=FG, font=F_TITLE).pack(anchor="w")
    tk.Label(head, text="All the numbers at a glance — scroll for more.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

    outer = tk.Frame(win, bg=BG)
    outer.pack(fill="both", expand=True, pady=(6, 0))

    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0,
                       yscrollincrement=16)
    scrollbar = ttk.Scrollbar(outer, orient="vertical",
                              command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    content = tk.Frame(canvas, bg=BG)
    win_id = canvas.create_window((0, 0), window=content, anchor="nw")

    def _on_configure(_e=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(win_id, width=canvas.winfo_width())

    content.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", _on_configure)
    canvas.bind("<MouseWheel>",
                lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    with connect_db() as conn:
        ov = conn.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN MatchHScore IS NOT NULL
                            AND MatchAScore IS NOT NULL THEN 1 ELSE 0 END),
                   COALESCE(SUM(CASE WHEN MatchHScore IS NOT NULL
                                       AND MatchAScore IS NOT NULL
                                     THEN MatchHScore + MatchAScore
                                     ELSE 0 END), 0),
                   SUM(CASE WHEN MatchHScore = MatchAScore
                            AND MatchHScore IS NOT NULL THEN 1 ELSE 0 END)
            FROM Matches
        """).fetchone()
        _total, completed, total_goals, total_draws = ov

        home_away = conn.execute("""
            SELECT t.TeamName,
                   COALESCE(h.w,0)||'-'||COALESCE(h.d,0)||'-'||COALESCE(h.l,0),
                   COALESCE(a.w,0)||'-'||COALESCE(a.d,0)||'-'||COALESCE(a.l,0)
            FROM Teams t
            LEFT JOIN (
              SELECT MatchHome AS tid,
                     SUM(CASE WHEN MatchHScore>MatchAScore THEN 1 ELSE 0 END) w,
                     SUM(CASE WHEN MatchHScore=MatchAScore THEN 1 ELSE 0 END) d,
                     SUM(CASE WHEN MatchHScore<MatchAScore THEN 1 ELSE 0 END) l
              FROM Matches WHERE MatchHScore IS NOT NULL
              GROUP BY MatchHome
            ) h ON h.tid = t.TeamID
            LEFT JOIN (
              SELECT MatchAway AS tid,
                     SUM(CASE WHEN MatchAScore>MatchHScore THEN 1 ELSE 0 END) w,
                     SUM(CASE WHEN MatchAScore=MatchHScore THEN 1 ELSE 0 END) d,
                     SUM(CASE WHEN MatchAScore<MatchHScore THEN 1 ELSE 0 END) l
              FROM Matches WHERE MatchHScore IS NOT NULL
              GROUP BY MatchAway
            ) a ON a.tid = t.TeamID
            WHERE h.w IS NOT NULL OR a.w IS NOT NULL
            ORDER BY t.TeamName
        """).fetchall()

        averages = conn.execute("""
            SELECT t.TeamName,
                   ROUND(AVG(CASE WHEN m.MatchHome=t.TeamID
                                  THEN m.MatchHScore ELSE m.MatchAScore END), 1),
                   ROUND(AVG(CASE WHEN m.MatchHome=t.TeamID
                                  THEN m.MatchAScore ELSE m.MatchHScore END), 1),
                   ROUND(AVG(CASE WHEN m.MatchHome=t.TeamID
                                  THEN m.MatchHScore-m.MatchAScore
                                  ELSE m.MatchAScore-m.MatchHScore END), 1),
                   COUNT(m.MatchID)
            FROM Teams t
            JOIN Matches m ON (m.MatchHome=t.TeamID OR m.MatchAway=t.TeamID)
                          AND m.MatchHScore IS NOT NULL
                          AND m.MatchAScore IS NOT NULL
            GROUP BY t.TeamID
            ORDER BY t.TeamName
        """).fetchall()

        monthly = conn.execute("""
            SELECT strftime('%Y-%m', MatchDate),
                   COUNT(*),
                   ROUND(AVG(ABS(MatchHScore-MatchAScore)), 1),
                   SUM(MatchHScore + MatchAScore)
            FROM Matches
            WHERE MatchDate IS NOT NULL
              AND MatchHScore IS NOT NULL
              AND MatchAScore IS NOT NULL
            GROUP BY strftime('%Y-%m', MatchDate)
            ORDER BY strftime('%Y-%m', MatchDate) DESC
        """).fetchall()

        goal_share_raw = conn.execute("""
            SELECT p.PlayerID,
                   p.PlayerName || ' ' || COALESCE(p.PlayerSurname, ''),
                   COALESCE(t.TeamName, '—'),
                   COALESCE(SUM(r.PlayerPoints), 0),
                   COALESCE((
                     SELECT SUM(CASE WHEN m2.MatchHome = r2.TeamID
                                     THEN m2.MatchHScore
                                     WHEN m2.MatchAway = r2.TeamID
                                     THEN m2.MatchAScore
                                     ELSE 0 END)
                     FROM MatchRoster r2
                     JOIN Matches m2 ON m2.MatchID = r2.MatchID
                     WHERE r2.PlayerID = p.PlayerID
                       AND m2.MatchHScore IS NOT NULL
                       AND m2.MatchAScore IS NOT NULL
                   ), 0)
            FROM Players p
            JOIN MatchRoster r ON r.PlayerID = p.PlayerID
            LEFT JOIN Teams t ON p.TeamID = t.TeamID
            GROUP BY p.PlayerID
            HAVING SUM(r.PlayerPoints) > 0
            ORDER BY SUM(r.PlayerPoints) DESC
            LIMIT 15
        """).fetchall()
        goal_share = []
        for _pid, name, team, goals, team_goals in goal_share_raw:
            share = (f"{(goals / team_goals * 100):.1f}%"
                     if team_goals else "—")
            goal_share.append((name, team, goals, team_goals, share))

        best_match = conn.execute("""
            SELECT p.PlayerName || ' ' || COALESCE(p.PlayerSurname, ''),
                   COALESCE(t.TeamName, '—'),
                   r.PlayerPoints,
                   COALESCE(opp.TeamName, '—'),
                   COALESCE(m.MatchDate, '—')
            FROM MatchRoster r
            JOIN Players p ON p.PlayerID = r.PlayerID
            JOIN Matches m ON m.MatchID = r.MatchID
            LEFT JOIN Teams t ON t.TeamID = r.TeamID
            LEFT JOIN Teams opp ON opp.TeamID = CASE
                WHEN m.MatchHome = r.TeamID THEN m.MatchAway
                ELSE m.MatchHome END
            WHERE r.PlayerPoints > 0
            ORDER BY r.PlayerPoints DESC, m.MatchID DESC
            LIMIT 10
        """).fetchall()

        top_count = conn.execute("""
            WITH match_top AS (
              SELECT MatchID, MAX(PlayerPoints) AS top
              FROM MatchRoster
              WHERE PlayerPoints > 0
              GROUP BY MatchID
            )
            SELECT p.PlayerName || ' ' || COALESCE(p.PlayerSurname, ''),
                   COALESCE(t.TeamName, '—'),
                   COUNT(*)
            FROM MatchRoster r
            JOIN match_top mt
              ON mt.MatchID = r.MatchID AND r.PlayerPoints = mt.top
            JOIN Players p ON p.PlayerID = r.PlayerID
            LEFT JOIN Teams t ON t.TeamID = p.TeamID
            GROUP BY r.PlayerID
            ORDER BY COUNT(*) DESC, p.PlayerName
            LIMIT 10
        """).fetchall()

        blowouts = conn.execute("""
            SELECT COALESCE(m.MatchDate, '—'),
                   ht.TeamName,
                   m.MatchHScore || '–' || m.MatchAScore,
                   at.TeamName,
                   ABS(m.MatchHScore-m.MatchAScore),
                   COALESCE(t.TournamentName, '—')
            FROM Matches m
            JOIN Teams ht ON ht.TeamID = m.MatchHome
            JOIN Teams at ON at.TeamID = m.MatchAway
            LEFT JOIN Tournaments t ON t.TournamentID = m.TournamentID
            WHERE m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
            ORDER BY ABS(m.MatchHScore-m.MatchAScore) DESC, m.MatchID DESC
            LIMIT 10
        """).fetchall()

        thrillers = conn.execute("""
            SELECT COALESCE(m.MatchDate, '—'),
                   ht.TeamName,
                   m.MatchHScore || '–' || m.MatchAScore,
                   at.TeamName,
                   ABS(m.MatchHScore-m.MatchAScore)
            FROM Matches m
            JOIN Teams ht ON ht.TeamID = m.MatchHome
            JOIN Teams at ON at.TeamID = m.MatchAway
            WHERE m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
              AND ABS(m.MatchHScore-m.MatchAScore) > 0
            ORDER BY ABS(m.MatchHScore-m.MatchAScore) ASC, m.MatchID DESC
            LIMIT 10
        """).fetchall()

        highest = conn.execute("""
            SELECT COALESCE(m.MatchDate, '—'),
                   ht.TeamName,
                   m.MatchHScore || '–' || m.MatchAScore,
                   at.TeamName,
                   m.MatchHScore + m.MatchAScore
            FROM Matches m
            JOIN Teams ht ON ht.TeamID = m.MatchHome
            JOIN Teams at ON at.TeamID = m.MatchAway
            WHERE m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
            ORDER BY m.MatchHScore + m.MatchAScore DESC, m.MatchID DESC
            LIMIT 10
        """).fetchall()

        lowest = conn.execute("""
            SELECT COALESCE(m.MatchDate, '—'),
                   ht.TeamName,
                   m.MatchHScore || '–' || m.MatchAScore,
                   at.TeamName,
                   m.MatchHScore + m.MatchAScore
            FROM Matches m
            JOIN Teams ht ON ht.TeamID = m.MatchHome
            JOIN Teams at ON at.TeamID = m.MatchAway
            WHERE m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
            ORDER BY m.MatchHScore + m.MatchAScore ASC, m.MatchID DESC
            LIMIT 10
        """).fetchall()

        period_splits = conn.execute("""
            SELECT t.TeamID, t.TeamName, mp.PeriodNumber,
                   SUM(CASE WHEN m.MatchHome = t.TeamID
                            THEN mp.HomeScore ELSE mp.AwayScore END)
            FROM Teams t
            JOIN Matches m ON (m.MatchHome = t.TeamID OR m.MatchAway = t.TeamID)
            JOIN MatchPeriods mp ON mp.MatchID = m.MatchID
            WHERE m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
            GROUP BY t.TeamID, mp.PeriodNumber
            ORDER BY t.TeamName, mp.PeriodNumber
        """).fetchall()

    overview_row = tk.Frame(content, bg=BG)
    overview_row.pack(fill="x", padx=22, pady=(0, 12))
    for i in range(4):
        overview_row.columnconfigure(i, weight=1, uniform="ov")

    def ov_card(parent, col, title, value):
        card = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER,
                        highlightthickness=1)
        card.grid(row=0, column=col, sticky="nsew",
                  padx=(0 if col == 0 else 6, 0))
        inner = tk.Frame(card, bg=SURFACE, padx=12, pady=10)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=title, bg=SURFACE, fg=MUTED,
                 font=F_CAPS).pack(anchor="w")
        tk.Label(inner, text=str(value), bg=SURFACE, fg=FG,
                 font=(FONT, 18, "bold")).pack(anchor="w", pady=(2, 0))

    avg_gpm = (total_goals / completed) if completed else 0
    draw_pct = (total_draws / completed * 100) if completed else 0
    ov_card(overview_row, 0, "MATCHES", f"{completed} played")
    ov_card(overview_row, 1, "TOTAL GOALS", total_goals)
    ov_card(overview_row, 2, "AVG / MATCH", f"{avg_gpm:.1f}")
    ov_card(overview_row, 3, "DRAWS", f"{total_draws} ({draw_pct:.0f}%)")

    def _section(title, cols, widths, rows, anchors=None):
        card = tk.Frame(content, bg=SURFACE,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=22, pady=(0, 12))
        inner = tk.Frame(card, bg=SURFACE, padx=12, pady=10)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=title, bg=SURFACE, fg=MUTED,
                 font=F_CAPS).pack(anchor="w", pady=(0, 6))
        shell = tk.Frame(inner, bg=BORDER)
        shell.pack(fill="both", expand=True)
        h = min(max(len(rows), 2), 8)
        tree = ttk.Treeview(shell, columns=cols, show="headings",
                            height=h, selectmode="browse")
        sc = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sc.set)
        sc.pack(side="right", fill="y", padx=(0, 1), pady=1)
        tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        for i, (c, w) in enumerate(zip(cols, widths)):
            a = anchors[i] if anchors else ("w" if i == 0 else "center")
            tree.heading(c, text=c, anchor=a)
            tree.column(c, width=w, minwidth=50, anchor=a,
                        stretch=(i == 0))
        tree.tag_configure("row_even", background=SURFACE)
        tree.tag_configure("row_odd",  background=STRIPE)
        if rows:
            for i, r in enumerate(rows):
                tree.insert("", "end", values=r,
                            tags=("row_even" if i % 2 == 0 else "row_odd",))
        else:
            tree.insert("", "end", values=["—"] * len(cols),
                        tags=("row_even",))
        attach_autofit(tree)

    _section("TEAM · HOME VS AWAY",
             ["Team", "Home (W-D-L)", "Away (W-D-L)"],
             [300, 160, 160], home_away,
             anchors=["w", "center", "center"])
    _section("TEAM · SCORING AVERAGES",
             ["Team", "PF/match", "PA/match", "+/–", "Matches"],
             [260, 100, 100, 80, 80], averages,
             anchors=["w", "center", "center", "center", "center"])
    _section("ACTIVITY · BY MONTH",
             ["Month", "Matches", "Avg Margin", "Total Goals"],
             [220, 100, 120, 120], monthly,
             anchors=["w", "center", "center", "center"])
    _section("PLAYER · GOAL SHARE (TOP 15)",
             ["Player", "Team", "Goals", "Team Goals", "Share"],
             [200, 140, 80, 100, 80], goal_share,
             anchors=["w", "w", "center", "center", "center"])
    _section("PLAYER · BEST SINGLE MATCH",
             ["Player", "Team", "Goals", "Opponent", "Date"],
             [200, 140, 70, 140, 100], best_match,
             anchors=["w", "w", "center", "w", "center"])
    _section("PLAYER · MOST TIMES AS TOP SCORER",
             ["Player", "Team", "Times"],
             [260, 160, 80], top_count,
             anchors=["w", "w", "center"])
    _section("MATCH · BIGGEST BLOWOUTS",
             ["Date", "Home", "Score", "Away", "Margin", "Tournament"],
             [100, 160, 80, 160, 70, 160], blowouts,
             anchors=["center", "w", "center", "w", "center", "w"])
    _section("MATCH · THRILLERS (CLOSEST)",
             ["Date", "Home", "Score", "Away", "Margin"],
             [100, 180, 80, 180, 70], thrillers,
             anchors=["center", "w", "center", "w", "center"])
    _section("MATCH · HIGHEST SCORING",
             ["Date", "Home", "Score", "Away", "Total"],
             [100, 180, 80, 180, 70], highest,
             anchors=["center", "w", "center", "w", "center"])
    _section("MATCH · LOWEST SCORING",
             ["Date", "Home", "Score", "Away", "Total"],
             [100, 180, 80, 180, 70], lowest,
             anchors=["center", "w", "center", "w", "center"])

    _render_period_splits(content, period_splits)


# ------------------------------------------------------------------ player career
def open_player_career(player_id):
    with connect_db() as conn:
        p = conn.execute("""
            SELECT p.PlayerName, COALESCE(p.PlayerSurname, ''),
                   COALESCE(p.PlayerBirthdate, '—'), p.TeamID,
                   COALESCE(t.TeamName, '—')
            FROM Players p LEFT JOIN Teams t ON p.TeamID = t.TeamID
            WHERE p.PlayerID = ?
        """, (player_id,)).fetchone()
        if not p:
            messagebox.showerror("Player not found",
                                 f"No player with ID {player_id}.")
            return

        stats = conn.execute("""
            SELECT COUNT(DISTINCT r.MatchID),
                   COALESCE(SUM(r.PlayerPoints), 0),
                   COALESCE(MAX(r.PlayerPoints), 0),
                   COALESCE(SUM(CASE WHEN
                     (m.MatchHome = r.TeamID AND m.MatchHScore > m.MatchAScore) OR
                     (m.MatchAway = r.TeamID AND m.MatchAScore > m.MatchHScore)
                     THEN 1 ELSE 0 END), 0)
            FROM MatchRoster r
            JOIN Matches m ON m.MatchID = r.MatchID
            WHERE r.PlayerID = ?
              AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
        """, (player_id,)).fetchone()
        matches_played, total_goals, best_match, total_wins = stats

        form = conn.execute("""
            SELECT CASE
                WHEN m.MatchHome = r.TeamID AND m.MatchHScore > m.MatchAScore THEN 'W'
                WHEN m.MatchAway = r.TeamID AND m.MatchAScore > m.MatchHScore THEN 'W'
                WHEN m.MatchHScore = m.MatchAScore THEN 'D'
                ELSE 'L'
            END
            FROM MatchRoster r
            JOIN Matches m ON m.MatchID = r.MatchID
            WHERE r.PlayerID = ?
              AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
            ORDER BY m.MatchID DESC LIMIT 5
        """, (player_id,)).fetchall()
        form_line = "  ".join(f[0] for f in form) or "—"

        tourn_rows = conn.execute("""
            SELECT COALESCE(t.TournamentName, '(no tournament)'),
                   COUNT(DISTINCT r.MatchID),
                   COALESCE(SUM(r.PlayerPoints), 0)
            FROM MatchRoster r
            JOIN Matches m ON m.MatchID = r.MatchID
            LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
            WHERE r.PlayerID = ?
              AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
            GROUP BY m.TournamentID
            ORDER BY COALESCE(t.TournamentDate, '9999') DESC
        """, (player_id,)).fetchall()

        period_rows = conn.execute("""
            SELECT mp.PeriodNumber,
                   COUNT(DISTINCT mp.MatchID),
                   COALESCE(SUM(CASE WHEN r.TeamID = m.MatchHome
                                     THEN mp.HomeScore ELSE mp.AwayScore END), 0)
            FROM MatchRoster r
            JOIN Matches m ON m.MatchID = r.MatchID
            JOIN MatchPeriods mp ON mp.MatchID = m.MatchID
            WHERE r.PlayerID = ?
            GROUP BY mp.PeriodNumber
            ORDER BY mp.PeriodNumber
        """, (player_id,)).fetchall()

    full_name = f"{p[0]} {p[1]}".strip()
    age_str = "—"
    if p[2] and p[2] != "—":
        try:
            bd = datetime.datetime.strptime(p[2], "%Y-%m-%d").date()
            today = datetime.date.today()
            age_str = str(today.year - bd.year -
                          ((today.month, today.day) < (bd.month, bd.day)))
        except ValueError:
            age_str = "—"

    gpm = (total_goals / matches_played) if matches_played else 0

    win = Toplevel(root)
    win.title(f"Career · {full_name}")
    win.configure(bg=BG)
    center_window(win, 860, 680)
    win.minsize(700, 560)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 10))
    tk.Label(head, text=full_name, bg=BG, fg=FG,
             font=(FONT, 20, "bold")).pack(anchor="w")
    sub_bits = [f"Team: {p[4]}", f"Age: {age_str}"]
    if p[2] and p[2] != "—":
        sub_bits.append(f"Birthday: {p[2]}")
    tk.Label(head, text="   ·   ".join(sub_bits), bg=BG, fg=MUTED,
             font=F_SMALL).pack(anchor="w", pady=(2, 0))

    metrics = tk.Frame(win, bg=BG)
    metrics.pack(fill="x", padx=22, pady=(6, 12))
    for i in range(4):
        metrics.columnconfigure(i, weight=1, uniform="met")

    def metric_card(parent, col, title, value):
        card = tk.Frame(parent, bg=SURFACE,
                        highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=col, sticky="nsew",
                  padx=(0, 4) if col < 3 else (0, 0))
        inner = tk.Frame(card, bg=SURFACE, padx=12, pady=10)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=title, bg=SURFACE, fg=MUTED,
                 font=F_CAPS).pack(anchor="w")
        tk.Label(inner, text=str(value), bg=SURFACE, fg=FG,
                 font=(FONT, 18, "bold")).pack(anchor="w", pady=(2, 0))

    metric_card(metrics, 0, "MATCHES", matches_played)
    metric_card(metrics, 1, "GOALS", total_goals)
    metric_card(metrics, 2, "GOALS / MATCH", f"{gpm:.2f}")
    metric_card(metrics, 3, "BEST MATCH", best_match)

    form_row = tk.Frame(win, bg=BG)
    form_row.pack(fill="x", padx=22, pady=(0, 12))
    tk.Label(form_row, text="RECENT FORM", bg=BG, fg=MUTED,
             font=F_CAPS).pack(side="left", padx=(0, 12))
    tk.Label(form_row, text=form_line, bg=BG, fg=ACCENT,
             font=(FONT, 11, "bold")).pack(side="left")

    body = tk.Frame(win, bg=BG)
    body.pack(fill="both", expand=True, padx=22, pady=(0, 20))
    body.columnconfigure(0, weight=1, uniform="cbody")
    body.columnconfigure(1, weight=1, uniform="cbody")
    body.rowconfigure(0, weight=1)

    tourn_card = tk.Frame(body, bg=SURFACE,
                          highlightbackground=BORDER, highlightthickness=1)
    tourn_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    tourn_inner = tk.Frame(tourn_card, bg=SURFACE, padx=10, pady=10)
    tourn_inner.pack(fill="both", expand=True)
    tk.Label(tourn_inner, text="BY TOURNAMENT", bg=SURFACE, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(0, 6))
    t_shell = tk.Frame(tourn_inner, bg=BORDER)
    t_shell.pack(fill="both", expand=True)
    tourn_tree = ttk.Treeview(t_shell, columns=("Tournament", "Matches", "Goals"),
                              show="headings", selectmode="browse")
    t_sb = ttk.Scrollbar(t_shell, orient="vertical", command=tourn_tree.yview)
    tourn_tree.configure(yscrollcommand=t_sb.set)
    t_sb.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tourn_tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w in zip(["Tournament", "Matches", "Goals"], [220, 80, 80]):
        tourn_tree.heading(col, text=col,
                            anchor="w" if col == "Tournament" else "center")
        tourn_tree.column(col, width=w, minwidth=50,
                          anchor="w" if col == "Tournament" else "center",
                          stretch=(col == "Tournament"))
    tourn_tree.tag_configure("row_even", background=SURFACE)
    tourn_tree.tag_configure("row_odd",  background=STRIPE)
    if tourn_rows:
        for i, r in enumerate(tourn_rows):
            tourn_tree.insert("", "end", values=r,
                              tags=("row_even" if i % 2 == 0 else "row_odd",))
    else:
        tourn_tree.insert("", "end",
                          values=("(no completed matches)", "", ""),
                          tags=("row_even",))

    period_card = tk.Frame(body, bg=SURFACE,
                           highlightbackground=BORDER, highlightthickness=1)
    period_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    period_inner = tk.Frame(period_card, bg=SURFACE, padx=10, pady=10)
    period_inner.pack(fill="both", expand=True)
    tk.Label(period_inner, text="GOALS BY PERIOD", bg=SURFACE, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(0, 6))
    p_shell = tk.Frame(period_inner, bg=BORDER)
    p_shell.pack(fill="both", expand=True)
    period_tree = ttk.Treeview(p_shell, columns=("Period", "Matches", "Team goals"),
                                show="headings", selectmode="browse")
    p_sb = ttk.Scrollbar(p_shell, orient="vertical", command=period_tree.yview)
    period_tree.configure(yscrollcommand=p_sb.set)
    p_sb.pack(side="right", fill="y", padx=(0, 1), pady=1)
    period_tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w in zip(["Period", "Matches", "Team goals"], [100, 90, 120]):
        period_tree.heading(col, text=col,
                             anchor="w" if col == "Period" else "center")
        period_tree.column(col, width=w, minwidth=50,
                           anchor="w" if col == "Period" else "center",
                           stretch=(col == "Period"))
    period_tree.tag_configure("row_even", background=SURFACE)
    period_tree.tag_configure("row_odd",  background=STRIPE)
    if period_rows:
        for i, r in enumerate(period_rows):
            period_tree.insert("", "end",
                               values=(f"Period {r[0]}", r[1], r[2]),
                               tags=("row_even" if i % 2 == 0 else "row_odd",))
    else:
        period_tree.insert("", "end",
                            values=("(no period data)", "", ""),
                            tags=("row_even",))


# ------------------------------------------------------------------ leaders view
def open_leaders_view():
    win = Toplevel(root)
    win.title("Leaders")
    win.configure(bg=BG)
    center_window(win, 1000, 640)
    win.minsize(800, 520)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 10))
    tk.Label(head, text="Leaders", bg=BG, fg=FG, font=F_TITLE).pack(anchor="w")
    tk.Label(head, text="Top scorers and best teams — filter by tournament "
                        "or view all-time.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

    with connect_db() as conn:
        tournaments = conn.execute(
            "SELECT TournamentID, TournamentName FROM Tournaments "
            "ORDER BY COALESCE(TournamentDate, '9999') DESC, TournamentName"
        ).fetchall()

    filter_row = tk.Frame(win, bg=BG)
    filter_row.pack(fill="x", padx=22, pady=(0, 12))
    tk.Label(filter_row, text="Tournament", bg=BG, fg=MUTED,
             font=F_SMALL).pack(side="left", padx=(0, 6))
    tourn_var = StringVar(value="All tournaments")
    labels = ["All tournaments"] + [
        f"{tid} · {tname}" for tid, tname in tournaments]
    id_map = {"All tournaments": None}
    for tid, tname in tournaments:
        id_map[f"{tid} · {tname}"] = tid
    combo = ttk.Combobox(filter_row, values=labels, textvariable=tourn_var,
                         state="readonly", font=F_SMALL, width=30)
    combo.pack(side="left")

    body = tk.Frame(win, bg=BG)
    body.pack(fill="both", expand=True, padx=22, pady=(0, 20))
    body.columnconfigure(0, weight=1, uniform="lead")
    body.columnconfigure(1, weight=1, uniform="lead")
    body.rowconfigure(0, weight=1)

    # --- top scorers
    scorers_card = tk.Frame(body, bg=SURFACE,
                            highlightbackground=BORDER, highlightthickness=1)
    scorers_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    scorers_inner = tk.Frame(scorers_card, bg=SURFACE, padx=10, pady=10)
    scorers_inner.pack(fill="both", expand=True)
    tk.Label(scorers_inner, text="TOP SCORERS", bg=SURFACE, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(0, 6))
    scorers_shell = tk.Frame(scorers_inner, bg=BORDER)
    scorers_shell.pack(fill="both", expand=True)
    scorers_tree = ttk.Treeview(
        scorers_shell, columns=("Player", "Team", "Goals", "Matches"),
        show="headings", selectmode="browse")
    sc_scroll = ttk.Scrollbar(scorers_shell, orient="vertical",
                              command=scorers_tree.yview)
    scorers_tree.configure(yscrollcommand=sc_scroll.set)
    sc_scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
    scorers_tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w in zip(["Player", "Team", "Goals", "Matches"],
                      [180, 150, 60, 70]):
        scorers_tree.heading(
            col, text=col,
            anchor="w" if col in ("Player", "Team") else "center")
        scorers_tree.column(
            col, width=w, minwidth=40,
            anchor="w" if col in ("Player", "Team") else "center",
            stretch=(col == "Player"))
    scorers_tree.tag_configure("row_even", background=SURFACE)
    scorers_tree.tag_configure("row_odd",  background=STRIPE)

    # --- top teams
    teams_card = tk.Frame(body, bg=SURFACE,
                          highlightbackground=BORDER, highlightthickness=1)
    teams_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    teams_inner = tk.Frame(teams_card, bg=SURFACE, padx=10, pady=10)
    teams_inner.pack(fill="both", expand=True)
    tk.Label(teams_inner, text="TOP TEAMS", bg=SURFACE, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(0, 6))
    teams_shell = tk.Frame(teams_inner, bg=BORDER)
    teams_shell.pack(fill="both", expand=True)
    teams_tree = ttk.Treeview(
        teams_shell, columns=("Team", "P", "W", "D", "L", "Pts"),
        show="headings", selectmode="browse")
    tm_scroll = ttk.Scrollbar(teams_shell, orient="vertical",
                              command=teams_tree.yview)
    teams_tree.configure(yscrollcommand=tm_scroll.set)
    tm_scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
    teams_tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w in zip(["Team", "P", "W", "D", "L", "Pts"],
                      [180, 50, 50, 50, 50, 60]):
        teams_tree.heading(
            col, text=col, anchor="w" if col == "Team" else "center")
        teams_tree.column(
            col, width=w, minwidth=40,
            anchor="w" if col == "Team" else "center",
            stretch=(col == "Team"))
    teams_tree.tag_configure("row_even", background=SURFACE)
    teams_tree.tag_configure("row_odd",  background=STRIPE)

    def load():
        tid = id_map.get(tourn_var.get())
        filter_sql = ""
        params = {}
        if tid is not None:
            filter_sql = "AND m.TournamentID = :tid"
            params["tid"] = tid

        wp = SETTINGS["win_points"]
        dp = SETTINGS["draw_points"]
        lp = SETTINGS["loss_points"]

        with connect_db() as conn:
            scorers = conn.execute(f"""
                SELECT p.PlayerName || ' ' || COALESCE(p.PlayerSurname, ''),
                       COALESCE(t.TeamName, '—'),
                       SUM(r.PlayerPoints),
                       COUNT(DISTINCT r.MatchID)
                FROM MatchRoster r
                JOIN Matches m ON m.MatchID = r.MatchID
                JOIN Players p ON p.PlayerID = r.PlayerID
                LEFT JOIN Teams t ON t.TeamID = r.TeamID
                WHERE r.PlayerPoints > 0
                  {filter_sql}
                GROUP BY r.PlayerID
                ORDER BY SUM(r.PlayerPoints) DESC,
                         COUNT(DISTINCT r.MatchID) ASC
                LIMIT 25
            """, params).fetchall()

            teams = conn.execute(f"""
                SELECT t.TeamName,
                       COUNT(m.MatchID),
                       SUM(CASE WHEN (m.MatchHome=t.TeamID AND m.MatchHScore>m.MatchAScore)
                                  OR (m.MatchAway=t.TeamID AND m.MatchAScore>m.MatchHScore)
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN m.MatchHScore=m.MatchAScore THEN 1 ELSE 0 END),
                       SUM(CASE WHEN (m.MatchHome=t.TeamID AND m.MatchHScore<m.MatchAScore)
                                  OR (m.MatchAway=t.TeamID AND m.MatchAScore<m.MatchHScore)
                                THEN 1 ELSE 0 END)
                FROM Teams t
                JOIN Matches m ON (m.MatchHome=t.TeamID OR m.MatchAway=t.TeamID)
                              AND m.MatchHScore IS NOT NULL
                              AND m.MatchAScore IS NOT NULL
                              {filter_sql}
                GROUP BY t.TeamID
            """, params).fetchall()

        scorers_tree.delete(*scorers_tree.get_children())
        if scorers:
            for i, r in enumerate(scorers):
                scorers_tree.insert(
                    "", "end", values=r,
                    tags=("row_even" if i % 2 == 0 else "row_odd",))
        else:
            scorers_tree.insert("", "end",
                                values=("(no goals recorded)", "", "", ""),
                                tags=("row_even",))

        teams_tree.delete(*teams_tree.get_children())
        parsed = []
        for team, played, won, drawn, lost in teams:
            won = won or 0
            drawn = drawn or 0
            lost = lost or 0
            pts = won * wp + drawn * dp + lost * lp
            parsed.append((team, played, won, drawn, lost, pts))
        parsed.sort(key=lambda r: (-r[5], -r[2], r[0].lower()))

        if parsed:
            for i, r in enumerate(parsed[:25]):
                teams_tree.insert(
                    "", "end", values=r,
                    tags=("row_even" if i % 2 == 0 else "row_odd",))
        else:
            teams_tree.insert("", "end",
                              values=("(no matches)", "", "", "", "", ""),
                              tags=("row_even",))

    combo.bind("<<ComboboxSelected>>", lambda e: load())
    load()


# ------------------------------------------------------------------ comparison renderers
def render_comparison_table(parent, header_a, header_b, rows):
    hdr = tk.Frame(parent, bg=SURFACE)
    hdr.pack(fill="x", pady=(0, 6))
    tk.Label(hdr, text="", bg=SURFACE, width=22).pack(side="left")
    tk.Label(hdr, text=header_a, bg=SURFACE, fg=ACCENT,
             font=(FONT, 12, "bold")).pack(side="left", fill="x", expand=True)
    tk.Label(hdr, text=header_b, bg=SURFACE, fg=ACCENT,
             font=(FONT, 12, "bold")).pack(side="left", fill="x", expand=True)
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(0, 4))
    for i, (label, va, vb) in enumerate(rows):
        bg_row = STRIPE if i % 2 else SURFACE
        r = tk.Frame(parent, bg=bg_row)
        r.pack(fill="x", pady=1)
        tk.Label(r, text=label, bg=bg_row, fg=MUTED, font=F_BODY,
                 anchor="w", padx=10, pady=6, width=22
                 ).pack(side="left")
        tk.Label(r, text=str(va), bg=bg_row, fg=FG, font=F_BODY,
                 anchor="center").pack(side="left", fill="x", expand=True)
        tk.Label(r, text=str(vb), bg=bg_row, fg=FG, font=F_BODY,
                 anchor="center").pack(side="left", fill="x", expand=True)


def render_team_comparison(parent, a_id, b_id, filters=None):
    filters = filters or CompareFilters()
    with connect_db() as conn:
        a_name = conn.execute("SELECT TeamName FROM Teams WHERE TeamID=?",
                              (a_id,)).fetchone()[0]
        b_name = conn.execute("SELECT TeamName FROM Teams WHERE TeamID=?",
                              (b_id,)).fetchone()[0]

        f_sql, f_params = filters.sql_fragment("m")

        def record(tid):
            return conn.execute(f"""
                SELECT COUNT(*),
                       SUM(CASE WHEN (m.MatchHome=:tid AND m.MatchHScore>m.MatchAScore)
                                  OR (m.MatchAway=:tid AND m.MatchAScore>m.MatchHScore)
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN m.MatchHScore=m.MatchAScore THEN 1 ELSE 0 END),
                       SUM(CASE WHEN (m.MatchHome=:tid AND m.MatchHScore<m.MatchAScore)
                                  OR (m.MatchAway=:tid AND m.MatchAScore<m.MatchHScore)
                                THEN 1 ELSE 0 END),
                       COALESCE(SUM(CASE WHEN m.MatchHome=:tid THEN m.MatchHScore
                                         WHEN m.MatchAway=:tid THEN m.MatchAScore
                                         ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN m.MatchHome=:tid THEN m.MatchAScore
                                         WHEN m.MatchAway=:tid THEN m.MatchHScore
                                         ELSE 0 END), 0)
                FROM Matches m
                WHERE (m.MatchHome=:tid OR m.MatchAway=:tid)
                  AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
                  {f_sql}
            """, {"tid": tid, **f_params}).fetchone()

        a = record(a_id)
        b = record(b_id)
        a_pts = team_points_sql(conn, a_id, filters)
        b_pts = team_points_sql(conn, b_id, filters)

        h2h = conn.execute(f"""
            SELECT COUNT(*),
                   SUM(CASE WHEN (m.MatchHome=:aid AND m.MatchHScore>m.MatchAScore)
                              OR (m.MatchAway=:aid AND m.MatchAScore>m.MatchHScore)
                            THEN 1 ELSE 0 END),
                   SUM(CASE WHEN m.MatchHScore=m.MatchAScore THEN 1 ELSE 0 END),
                   SUM(CASE WHEN (m.MatchHome=:aid AND m.MatchHScore<m.MatchAScore)
                              OR (m.MatchAway=:aid AND m.MatchAScore<m.MatchHScore)
                            THEN 1 ELSE 0 END)
            FROM Matches m
            WHERE ((m.MatchHome=:aid AND m.MatchAway=:bid)
                OR (m.MatchHome=:bid AND m.MatchAway=:aid))
              AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
              {f_sql}
        """, {"aid": a_id, "bid": b_id, **f_params}).fetchone()

    def sd(v):
        return 0 if v is None else v

    rows = [
        ("Matches played",     sd(a[0]), sd(b[0])),
        ("Wins",               sd(a[1]), sd(b[1])),
        ("Draws",              sd(a[2]), sd(b[2])),
        ("Losses",             sd(a[3]), sd(b[3])),
        ("Points",             a_pts, b_pts),
        ("Points scored",      sd(a[4]), sd(b[4])),
    ]
    render_comparison_table(parent, a_name, b_name, rows)


def render_club_comparison(parent, a_id, b_id, filters=None):
    filters = filters or CompareFilters()
    with connect_db() as conn:
        a_name = conn.execute("SELECT ClubName FROM Clubs WHERE ClubID=?",
                              (a_id,)).fetchone()[0]
        b_name = conn.execute("SELECT ClubName FROM Clubs WHERE ClubID=?",
                              (b_id,)).fetchone()[0]

        def club_stats(cid):
            team_ids = [r[0] for r in conn.execute(
                "SELECT TeamID FROM Teams WHERE ClubID=?", (cid,)).fetchall()]
            if not team_ids:
                return (0, 0, 0, 0, 0, 0)
            ph = ",".join("?" * len(team_ids))
            n_players = conn.execute(
                f"SELECT COUNT(*) FROM Players WHERE TeamID IN ({ph})",
                team_ids).fetchone()[0]
            f_sql, f_params = filters.sql_fragment("m")
            in_ph = ",".join(f":t{i}" for i in range(len(team_ids)))
            in_params = {f"t{i}": tid for i, tid in enumerate(team_ids)}
            params = {**in_params, **f_params}
            row = conn.execute(f"""
                SELECT COUNT(*),
                       SUM(CASE WHEN (m.MatchHome IN ({in_ph})
                                      AND m.MatchHScore>m.MatchAScore)
                                  OR (m.MatchAway IN ({in_ph})
                                      AND m.MatchAScore>m.MatchHScore)
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN m.MatchHScore=m.MatchAScore
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN (m.MatchHome IN ({in_ph})
                                      AND m.MatchHScore<m.MatchAScore)
                                  OR (m.MatchAway IN ({in_ph})
                                      AND m.MatchAScore<m.MatchHScore)
                                THEN 1 ELSE 0 END)
                FROM Matches m
                WHERE (m.MatchHome IN ({in_ph}) OR m.MatchAway IN ({in_ph}))
                  AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
                  {f_sql}
            """, params).fetchone()
            return (len(team_ids), n_players) + row

        a = club_stats(a_id)
        b = club_stats(b_id)
        a_pts = club_points_sql(conn, a_id, filters)
        b_pts = club_points_sql(conn, b_id, filters)

    def sd(v):
        return 0 if v is None else v

    rows = [
        ("Teams in club",     a[0], b[0]),
        ("Players in club",   a[1], b[1]),
        ("Matches played",    sd(a[2]), sd(b[2])),
        ("Wins",              sd(a[3]), sd(b[3])),
        ("Draws",             sd(a[4]), sd(b[4])),
        ("Losses",            sd(a[5]), sd(b[5])),
        ("Points",            a_pts, b_pts),
    ]
    render_comparison_table(parent, a_name, b_name, rows)


def render_player_comparison(parent, a_id, b_id, filters=None):
    filters = filters or CompareFilters()
    with connect_db() as conn:
        f_sql, f_params = filters.sql_fragment("m")

        def get_player(pid):
            return conn.execute("""
                SELECT p.PlayerName, COALESCE(p.PlayerSurname, ''),
                       COALESCE(t.TeamName, '—'), p.TeamID,
                       COALESCE(p.PlayerBirthdate, '—'),
                       COALESCE(CAST(strftime('%Y.%m%d','now') -
                                     strftime('%Y.%m%d', p.PlayerBirthdate)
                                     AS INTEGER), '—')
                FROM Players p LEFT JOIN Teams t ON p.TeamID = t.TeamID
                WHERE p.PlayerID=?
            """, (pid,)).fetchone()

        def team_record(tid):
            if tid is None:
                return (0, 0, 0, 0)
            return conn.execute(f"""
                SELECT COUNT(*),
                       SUM(CASE WHEN (m.MatchHome=:tid AND m.MatchHScore>m.MatchAScore)
                                  OR (m.MatchAway=:tid AND m.MatchAScore>m.MatchHScore)
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN m.MatchHScore=m.MatchAScore THEN 1 ELSE 0 END),
                       SUM(CASE WHEN (m.MatchHome=:tid AND m.MatchHScore<m.MatchAScore)
                                  OR (m.MatchAway=:tid AND m.MatchAScore<m.MatchHScore)
                                THEN 1 ELSE 0 END)
                FROM Matches m
                WHERE (m.MatchHome=:tid OR m.MatchAway=:tid)
                  AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
                  {f_sql}
            """, {"tid": tid, **f_params}).fetchone()

        a = get_player(a_id)
        b = get_player(b_id)
        a_tr = team_record(a[3])
        b_tr = team_record(b[3])
        a_goals = player_points_sql(conn, a_id, filters)
        b_goals = player_points_sql(conn, b_id, filters)

    def full_name(p):
        return (p[0] + (" " + p[1] if p[1] else "")).strip()

    def sd(v):
        return 0 if v is None else v

    rows = [
        ("Team",               a[2], b[2]),
        ("Birthday",           a[4], b[4]),
        ("Age",                a[5], b[5]),
        ("Goals scored",       a_goals, b_goals),
        ("Team matches",       sd(a_tr[0]), sd(b_tr[0])),
        ("Team wins",          sd(a_tr[1]), sd(b_tr[1])),
        ("Team draws",         sd(a_tr[2]), sd(b_tr[2])),
        ("Team losses",        sd(a_tr[3]), sd(b_tr[3])),
    ]
    render_comparison_table(parent, full_name(a), full_name(b), rows)


def render_match_comparison(parent, a_id, b_id):
    with connect_db() as conn:
        def get_match(mid):
            return conn.execute("""
                SELECT ht.TeamName, at.TeamName,
                       COALESCE(m.MatchLocation, '—'),
                       m.MatchHScore, m.MatchAScore,
                       COALESCE(t.TournamentName, '—'),
                       COALESCE(m.MatchDate, '—'),
                       CASE WHEN m.PeriodCount > 0
                            THEN m.PeriodCount || ' × ' ||
                                 COALESCE(m.PeriodMinutes, '?') || ' min'
                            ELSE '—' END
                FROM Matches m
                JOIN Teams ht ON m.MatchHome = ht.TeamID
                JOIN Teams at ON m.MatchAway = at.TeamID
                LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
                WHERE m.MatchID=?
            """, (mid,)).fetchone()
        a = get_match(a_id)
        b = get_match(b_id)

    def score_label(hs, as_):
        return "—" if hs is None or as_ is None else f"{hs} – {as_}"

    def margin(hs, as_):
        return "—" if hs is None or as_ is None else abs(hs - as_)

    def total(hs, as_):
        return "—" if hs is None or as_ is None else hs + as_

    def period_scores(mid):
        with connect_db() as conn:
            rows = conn.execute(
                "SELECT PeriodNumber, COALESCE(HomeScore, 0), "
                "COALESCE(AwayScore, 0) FROM MatchPeriods "
                "WHERE MatchID = ? ORDER BY PeriodNumber",
                (mid,)).fetchall()
        if not rows:
            return "—"
        return " · ".join(f"P{pn} {h}-{a}" for pn, h, a in rows)

    rows = [
        ("Home team",    a[0], b[0]),
        ("Away team",    a[1], b[1]),
        ("Score",        score_label(a[3], a[4]), score_label(b[3], b[4])),
        ("Total points", total(a[3], a[4]), total(b[3], b[4])),
        ("Margin",       margin(a[3], a[4]), margin(b[3], b[4])),
        ("Tournament",   a[5], b[5]),
        ("Location",     a[2], b[2]),
        ("Date",         a[6], b[6]),
        ("Periods",      a[7], b[7]),
        ("Period scores", period_scores(a_id), period_scores(b_id)),
    ]
    render_comparison_table(parent, f"Match #{a_id}", f"Match #{b_id}", rows)


# ------------------------------------------------------------------ compare window
def open_compare(kind, preselected=None):
    win = Toplevel(root)
    win.title(f"Compare {kind.title()}")
    win.configure(bg=BG)
    center_window(win, 920, 700)
    win.minsize(760, 580)
    win.bind("<Escape>", lambda e: win.destroy())

    with connect_db() as conn:
        if kind == "teams":
            options = conn.execute(
                "SELECT TeamID, TeamName FROM Teams ORDER BY TeamName").fetchall()
        elif kind == "clubs":
            options = conn.execute(
                "SELECT ClubID, ClubName FROM Clubs ORDER BY ClubName").fetchall()
        elif kind == "players":
            options = conn.execute(
                "SELECT PlayerID, PlayerName || ' ' || "
                "COALESCE(PlayerSurname, '') "
                "FROM Players ORDER BY PlayerName, PlayerSurname").fetchall()
        else:
            options = conn.execute("""
                SELECT m.MatchID,
                       COALESCE(m.MatchDate, '?') || ' · ' ||
                       ht.TeamName || ' vs ' || at.TeamName
                FROM Matches m
                JOIN Teams ht ON m.MatchHome = ht.TeamID
                JOIN Teams at ON m.MatchAway = at.TeamID
                ORDER BY m.MatchID DESC
            """).fetchall()
        tournaments = conn.execute(
            "SELECT TournamentID, TournamentName FROM Tournaments "
            "ORDER BY COALESCE(TournamentDate, '9999') DESC, TournamentName"
        ).fetchall()

    if len(options) < 2:
        messagebox.showinfo("Not enough records",
                            f"Add at least two {kind} to compare.", parent=win)
        win.destroy()
        return

    labels = [f"{oid} · {name}" for oid, name in options]
    id_of = {f"{oid} · {name}": oid for oid, name in options}
    id_to_label = dict(zip([o[0] for o in options], labels))

    default_a = labels[0]
    default_b = labels[1]
    if preselected:
        default_a = id_to_label.get(preselected[0], labels[0])
        default_b = id_to_label.get(preselected[1], labels[1])

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 10))
    tk.Label(head, text=f"Compare {kind.title()}", bg=BG, fg=FG,
             font=F_TITLE).pack(anchor="w")
    tk.Label(head, text="Pick two records to see a side-by-side breakdown.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

    sel_row = tk.Frame(win, bg=BG)
    sel_row.pack(fill="x", padx=22, pady=(0, 8))
    sel_row.columnconfigure(1, weight=1)
    sel_row.columnconfigure(3, weight=1)

    tk.Label(sel_row, text="A", bg=BG, fg=MUTED,
             font=F_CAPS).grid(row=0, column=0, sticky="w")
    var_a = StringVar(value=default_a)
    combo_a = ttk.Combobox(sel_row, values=labels, textvariable=var_a,
                           state="readonly", font=F_BODY)
    combo_a.grid(row=0, column=1, sticky="ew", padx=(6, 16), ipady=3)

    tk.Label(sel_row, text="vs", bg=BG, fg=MUTED,
             font=F_CAPS).grid(row=0, column=2, sticky="w")
    var_b = StringVar(value=default_b)
    combo_b = ttk.Combobox(sel_row, values=labels, textvariable=var_b,
                           state="readonly", font=F_BODY)
    combo_b.grid(row=0, column=3, sticky="ew", padx=(16, 0), ipady=3)

    if kind != "matches":
        filter_row = tk.Frame(win, bg=BG)
        filter_row.pack(fill="x", padx=22, pady=(0, 12))

        tk.Label(filter_row, text="Tournament", bg=BG, fg=MUTED,
                 font=F_SMALL).pack(side="left", padx=(0, 6))
        tourn_var = StringVar(value="All tournaments")
        tourn_labels = ["All tournaments"] + [
            f"{tid} · {tname}" for tid, tname in tournaments]
        tourn_map = {"All tournaments": None}
        for tid, tname in tournaments:
            tourn_map[f"{tid} · {tname}"] = tid
        tourn_combo = ttk.Combobox(filter_row, values=tourn_labels,
                                   textvariable=tourn_var, state="readonly",
                                   font=F_SMALL, width=26)
        tourn_combo.pack(side="left", padx=(0, 16))

        tk.Label(filter_row, text="From", bg=BG, fg=MUTED, font=F_SMALL
                 ).pack(side="left", padx=(0, 6))
        date_from_entry = tk.Entry(filter_row, bg=SURFACE, fg=FG,
                                    insertbackground=FG, relief="flat",
                                    highlightthickness=1,
                                    highlightbackground=BORDER,
                                    highlightcolor=ACCENT, font=F_SMALL,
                                    width=12)
        date_from_entry.pack(side="left", padx=(0, 12), ipady=4)

        tk.Label(filter_row, text="To", bg=BG, fg=MUTED, font=F_SMALL
                 ).pack(side="left", padx=(0, 6))
        date_to_entry = tk.Entry(filter_row, bg=SURFACE, fg=FG,
                                  insertbackground=FG, relief="flat",
                                  highlightthickness=1,
                                  highlightbackground=BORDER,
                                  highlightcolor=ACCENT, font=F_SMALL,
                                  width=12)
        date_to_entry.pack(side="left", padx=(0, 12), ipady=4)

        def clear_filters():
            tourn_var.set("All tournaments")
            date_from_entry.delete(0, "end")
            date_to_entry.delete(0, "end")
            render()

        make_small_button(filter_row, "Clear", clear_filters).pack(side="left")

        def validate_date(entry):
            v = entry.get().strip()
            if not v:
                return True
            try:
                datetime.datetime.strptime(v, "%Y-%m-%d")
                return True
            except ValueError:
                messagebox.showwarning("Invalid date",
                                       "Dates must be YYYY-MM-DD.", parent=win)
                entry.delete(0, "end")
                return False

        def on_date_change(entry):
            if validate_date(entry):
                render()

        date_from_entry.bind("<FocusOut>", lambda e: on_date_change(date_from_entry))
        date_to_entry.bind("<FocusOut>", lambda e: on_date_change(date_to_entry))
        date_from_entry.bind("<Return>", lambda e: on_date_change(date_from_entry))
        date_to_entry.bind("<Return>", lambda e: on_date_change(date_to_entry))
        tourn_combo.bind("<<ComboboxSelected>>", lambda e: render())

        def get_filters():
            tid = tourn_map.get(tourn_var.get())
            df = date_from_entry.get().strip() or None
            dt = date_to_entry.get().strip() or None
            return CompareFilters(tid, df, dt)
    else:
        def get_filters():
            return None

    result_shell = tk.Frame(win, bg=BORDER)
    result_shell.pack(fill="both", expand=True, padx=22, pady=(0, 20))
    result_inner = tk.Frame(result_shell, bg=SURFACE)
    result_inner.pack(fill="both", expand=True, padx=1, pady=1)

    body = [None]

    def render():
        if body[0]:
            body[0].destroy()
        b = tk.Frame(result_inner, bg=SURFACE, padx=18, pady=16)
        b.pack(fill="both", expand=True)
        body[0] = b
        if var_a.get() not in id_of or var_b.get() not in id_of:
            return
        a_id = id_of[var_a.get()]
        b_id = id_of[var_b.get()]
        filters = get_filters()
        if kind == "teams":
            render_team_comparison(b, a_id, b_id, filters)
        elif kind == "clubs":
            render_club_comparison(b, a_id, b_id, filters)
        elif kind == "players":
            render_player_comparison(b, a_id, b_id, filters)
        else:
            render_match_comparison(b, a_id, b_id)

    combo_a.bind("<<ComboboxSelected>>", lambda e: render())
    combo_b.bind("<<ComboboxSelected>>", lambda e: render())
    render()


# ------------------------------------------------------------------ top action row
_section_widgets = {}


def build_actions_section(parent):
    bg = SETTINGS["section_bg"]["actions"]
    title_fg = SETTINGS["section_title_color"]["actions"]

    action_row = tk.Frame(parent, bg=bg,
                          highlightbackground=BORDER, highlightthickness=1)
    for i in range(4):
        action_row.columnconfigure(i, weight=1, uniform="act")

    FUNC_BLOCKS = [
        ("BROWSE", [("Teams",       browse_teams),
                    ("Clubs",       browse_clubs),
                    ("Players",     browse_players),
                    ("Rosters",     open_roster_viewer),
                    ("Leaders",     open_leaders_view),
                    ("Stats",       open_stats_view),
                    ("Power Rankings", open_elo_view),
                    ("Records",     open_record_book),
                    ("Matches",     browse_matches),
                    ("Tournaments", browse_tournaments)]),
        ("ADD",    [("Team",        add_team),
                    ("Club",        add_club),
                    ("Player",      add_player),
                    ("Match",       add_match),
                    ("Tournament",  add_tournament)]),
        ("EDIT",   [("Teams",       edit_team),
                    ("Clubs",       edit_club),
                    ("Players",     edit_player),
                    ("Matches",     edit_match),
                    ("Tournaments", edit_tournament),
                    ("Match rosters", open_roster_picker)]),
        ("REMOVE", [("Team",        remove_team),
                    ("Club",        remove_club),
                    ("Player",      remove_player),
                    ("Match",       remove_match),
                    ("Tournament",  remove_tournament)]),
    ]
    for i, (title, items) in enumerate(FUNC_BLOCKS):
        padx = (0 if i == 0 else 6, 0 if i == 3 else 6)
        inner = card_frame(action_row, title, bg=bg, title_fg=title_fg,
                           row=0, column=i, padx=padx, pady=0)
        for label, cmd in items:
            make_small_button(inner, label, cmd,
                              danger=(title == "REMOVE")).pack(fill="x", pady=2)
    return action_row


# ------------------------------------------------------------------ calendar
cal_state = {
    "year": datetime.date.today().year,
    "month": datetime.date.today().month,
    "selected": datetime.date.today().isoformat(),
}
_calendar_counts_cache = {}
cal_month_lbl = None
cal_cells = None
cal_details_lbl = None
cal_tree = None
cal_day_labels = None


def invalidate_calendar_cache():
    _calendar_counts_cache.clear()


def build_calendar_section(parent):
    global cal_month_lbl, cal_cells, cal_details_lbl, cal_tree, cal_day_labels

    bg = SETTINGS["section_bg"]["calendar"]
    title_fg = SETTINGS["section_title_color"]["calendar"]

    cal_card = tk.Frame(parent, bg=bg, highlightbackground=BORDER,
                        highlightthickness=1)

    cal_header = tk.Frame(cal_card, bg=bg)
    cal_header.pack(fill="x", padx=12, pady=(10, 6))
    tk.Label(cal_header, text="MATCH CALENDAR", bg=bg, fg=title_fg,
             font=F_CAPS).pack(side="left")
    cal_month_lbl = tk.Label(cal_header, text="", bg=bg, fg=FG,
                             font=(FONT, 11, "bold"))
    cal_month_lbl.pack(side="left", padx=(14, 0))
    cal_nav = tk.Frame(cal_header, bg=bg)
    cal_nav.pack(side="right")

    cal_body = tk.Frame(cal_card, bg=bg)
    cal_body.pack(fill="x", padx=12, pady=(0, 10))
    cal_body.columnconfigure(0, weight=0)
    cal_body.columnconfigure(1, weight=1)
    cal_body.rowconfigure(0, weight=1)

    cal_grid = tk.Frame(cal_body, bg=bg)
    cal_grid.grid(row=0, column=0, sticky="nw", padx=(0, 14))

    cal_day_labels = []
    for i, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        lbl = tk.Label(cal_grid, text=name, bg=bg, fg=title_fg,
                       font=F_SMALL, width=4)
        lbl.grid(row=0, column=i, padx=1, pady=(0, 3))
        cal_day_labels.append(lbl)

    cal_cells = []
    for w in range(6):
        row = []
        for d in range(7):
            lbl = tk.Label(cal_grid, text="", bg=bg, fg=FG,
                           font=F_SMALL, width=4, height=1)
            lbl.grid(row=w + 1, column=d, padx=1, pady=1)
            lbl._iso = None
            row.append(lbl)
        cal_cells.append(row)

    cal_details = tk.Frame(cal_body, bg=bg)
    cal_details.grid(row=0, column=1, sticky="nsew")
    cal_details_lbl = tk.Label(cal_details, text="", bg=bg, fg=FG,
                               font=(FONT, 10, "bold"), anchor="w")
    cal_details_lbl.pack(fill="x", pady=(0, 4))

    cal_tree = ttk.Treeview(cal_details,
                            columns=["Home", "Score", "Away", "Tournament"],
                            show="headings", height=3)
    for col, w in zip(["Home", "Score", "Away", "Tournament"],
                      [130, 60, 130, 130]):
        cal_tree.heading(col, text=col, anchor="w")
        cal_tree.column(col, width=w, minwidth=40, anchor="w",
                        stretch=(col in ("Home", "Away", "Tournament")))
    cal_tree.pack(fill="both", expand=True)
    cal_tree.tag_configure("row_even", background=bg)
    cal_tree.tag_configure("row_odd",  background=STRIPE)

    cal_empty_lbl = tk.Label(cal_details, text="No matches on this day",
                             bg=bg, fg=title_fg, font=F_SMALL)
    cal_empty_lbl.place_forget()

    cal_add_btn = tk.Button(cal_details, text="+ Add match on this date",
                            command=lambda: None,
                            bg=ACCENT, fg="#ffffff",
                            activebackground=ACCENT_HI, activeforeground="#ffffff",
                            relief="flat", bd=0, highlightthickness=0,
                            padx=12, pady=6, cursor="hand2", font=F_SMALL)
    cal_add_btn.place_forget()

    make_small_button(cal_nav, "‹", _cal_prev).pack(side="left", padx=2)
    make_small_button(cal_nav, "Today", _cal_today).pack(side="left", padx=2)
    make_small_button(cal_nav, "›", _cal_next).pack(side="left", padx=2)

    cal_tree._empty_lbl = cal_empty_lbl
    cal_tree._add_btn = cal_add_btn
    return cal_card


def _cal_click(iso):
    if not iso:
        return
    cal_state["selected"] = iso
    load_calendar()


def _cal_prev():
    y, m = cal_state["year"], cal_state["month"]
    if m == 1:
        cal_state["year"], cal_state["month"] = y - 1, 12
    else:
        cal_state["month"] = m - 1
    load_calendar()


def _cal_next():
    y, m = cal_state["year"], cal_state["month"]
    if m == 12:
        cal_state["year"], cal_state["month"] = y + 1, 1
    else:
        cal_state["month"] = m + 1
    load_calendar()


def _cal_today():
    t = datetime.date.today()
    cal_state["year"] = t.year
    cal_state["month"] = t.month
    cal_state["selected"] = t.isoformat()
    load_calendar()


def load_calendar():
    y, m = cal_state["year"], cal_state["month"]
    first = datetime.date(y, m, 1)
    next_m = (datetime.date(y + 1, 1, 1) if m == 12
              else datetime.date(y, m + 1, 1))
    cal_month_lbl.configure(text=first.strftime("%B %Y"))

    cache_key = (y, m)
    if cache_key in _calendar_counts_cache:
        counts = _calendar_counts_cache[cache_key]
    else:
        with connect_db() as conn:
            counts = dict(conn.execute(
                "SELECT MatchDate, COUNT(*) FROM Matches "
                "WHERE MatchDate >= ? AND MatchDate < ? "
                "GROUP BY MatchDate",
                (first.isoformat(), next_m.isoformat())).fetchall())
        _calendar_counts_cache[cache_key] = counts

    names = (["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
             if SETTINGS["calendar_starts_monday"]
             else ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
    for i, n in enumerate(names):
        cal_day_labels[i].configure(text=n)

    start_offset = first.weekday()
    if not SETTINGS["calendar_starts_monday"]:
        start_offset = (start_offset + 1) % 7

    days_in_month = (next_m - first).days
    today_iso = datetime.date.today().isoformat()
    sel_iso = cal_state["selected"]

    for w in range(6):
        for d in range(7):
            idx = w * 7 + d
            day_num = idx - start_offset + 1
            lbl = cal_cells[w][d]
            if day_num < 1 or day_num > days_in_month:
                lbl.configure(text="", bg=SURFACE, fg=SURFACE, cursor="")
                lbl._iso = None
                lbl.unbind("<Button-1>")
                continue
            this_date = datetime.date(y, m, day_num)
            this_iso = this_date.isoformat()
            count = counts.get(this_iso, 0)
            lbl._iso = this_iso
            lbl.configure(text=str(day_num), cursor="hand2")
            if this_iso == sel_iso:
                lbl.configure(bg=ACCENT, fg="#ffffff", font=(FONT, 9, "bold"))
            elif this_iso == today_iso:
                lbl.configure(bg=SURFACE_2, fg=ACCENT, font=(FONT, 9, "bold"))
            elif count > 0:
                lbl.configure(bg=SURFACE_2, fg=FG, font=(FONT, 9, "bold"))
            else:
                lbl.configure(bg=SURFACE, fg=MUTED, font=F_SMALL)
            lbl.bind("<Button-1>", lambda e, iso=this_iso: _cal_click(iso))

    sel = cal_state["selected"]
    try:
        sd = datetime.date.fromisoformat(sel)
        cal_details_lbl.configure(text=sd.strftime("%A, %d %B %Y"))
    except ValueError:
        cal_details_lbl.configure(text="")

    cal_tree.delete(*cal_tree.get_children())
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT ht.TeamName,
                   COALESCE(m.MatchHScore, '-') || ' – ' ||
                   COALESCE(m.MatchAScore, '-'),
                   at.TeamName,
                   COALESCE(t.TournamentName, '—')
            FROM Matches m
            JOIN Teams ht ON m.MatchHome = ht.TeamID
            JOIN Teams at ON m.MatchAway = at.TeamID
            LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
            WHERE m.MatchDate = ?
            ORDER BY m.MatchID
        """, (sel,)).fetchall()
    empty_lbl = getattr(cal_tree, "_empty_lbl", None)
    add_btn = getattr(cal_tree, "_add_btn", None)
    if rows:
        if empty_lbl:
            empty_lbl.place_forget()
        if add_btn:
            add_btn.place_forget()
        for i, r in enumerate(rows):
            cal_tree.insert("", "end", values=r,
                            tags=("row_even" if i % 2 == 0 else "row_odd",))
    else:
        if empty_lbl:
            empty_lbl.place(relx=0.5, rely=0.4, anchor="center")
        if add_btn:
            add_btn.configure(command=lambda d=sel: add_match(default_date=d))
            add_btn.place(relx=0.5, rely=0.6, anchor="center")


# ------------------------------------------------------------------ dashboard
tournaments_tree = None
recent_tree = None
progress_tree = None
progress_subtitle = None


def build_dashboard_section(parent):
    global tournaments_tree, recent_tree, progress_tree, progress_subtitle

    bg = SETTINGS["section_bg"]["dashboard"]
    title_fg = SETTINGS["section_title_color"]["dashboard"]

    dashboard = tk.Frame(parent, bg=BG)
    dashboard.columnconfigure(0, weight=1, uniform="dash")
    dashboard.columnconfigure(1, weight=1, uniform="dash")
    dashboard.rowconfigure(0, weight=1, uniform="drow")
    dashboard.rowconfigure(1, weight=1, uniform="drow")

    tourn_inner = card_frame(dashboard, "TOURNAMENTS", bg=bg,
                             title_fg=title_fg,
                             row=0, column=0, padx=(0, 6), pady=(0, 6))
    recent_inner = card_frame(dashboard, "RECENT MATCHES", bg=bg,
                              title_fg=title_fg,
                              row=0, column=1, padx=(6, 0), pady=(0, 6))
    progress_inner = card_frame(dashboard, "TOURNAMENT PROGRESS", bg=bg,
                                title_fg=title_fg,
                                row=1, column=0, columnspan=2,
                                padx=0, pady=(6, 0))

    t_shell = tk.Frame(tourn_inner, bg=BORDER)
    t_shell.pack(fill="both", expand=True)
    tournaments_tree = ttk.Treeview(
        t_shell, columns=["Name", "Date", "Matches"],
        show="headings", selectmode="browse")
    t_scroll = ttk.Scrollbar(t_shell, orient="vertical",
                             command=tournaments_tree.yview)
    tournaments_tree.configure(yscrollcommand=t_scroll.set)
    t_scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tournaments_tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w in zip(["Name", "Date", "Matches"], [260, 110, 70]):
        tournaments_tree.heading(col, text=col, anchor="w")
        tournaments_tree.column(col, width=w, minwidth=50, anchor="w",
                                stretch=(col == "Name"))
    tournaments_tree.tag_configure("row_even", background=SURFACE)
    tournaments_tree.tag_configure("row_odd",  background=STRIPE)
    tournaments_tree.bind("<<TreeviewSelect>>", on_tournament_select)

    global _focus_btn
    focus_row = tk.Frame(tourn_inner, bg=bg)
    focus_row.pack(fill="x", pady=(6, 0))

    def toggle_focus():
        sel = tournaments_tree.selection()
        current = SETTINGS.get("focus_tournament_id")
        if current is not None:
            SETTINGS["focus_tournament_id"] = None
        else:
            if not sel:
                messagebox.showinfo(
                    "No tournament selected",
                    "Select a tournament in the list to focus on it.",
                    parent=root)
                return
            try:
                SETTINGS["focus_tournament_id"] = int(sel[0])
            except (ValueError, TypeError):
                return
        save_settings()
        _update_focus_badge()
        refresh_dashboard()

    _focus_btn = make_small_button(focus_row, "⭐ Focus selected",
                                    toggle_focus)
    _focus_btn.pack(side="right")
    _sync_focus_btn()

    r_shell = tk.Frame(recent_inner, bg=BORDER)
    r_shell.pack(fill="both", expand=True)
    recent_tree = ttk.Treeview(
        r_shell, columns=["Date", "Home", "Away", "Score", "Tourn."],
        show="headings", selectmode="none")
    r_scroll = ttk.Scrollbar(r_shell, orient="vertical",
                             command=recent_tree.yview)
    recent_tree.configure(yscrollcommand=r_scroll.set)
    r_scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
    recent_tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w in zip(["Date", "Home", "Away", "Score", "Tourn."],
                      [95, 120, 120, 70, 120]):
        recent_tree.heading(col, text=col, anchor="w")
        recent_tree.column(col, width=w, minwidth=50, anchor="w",
                           stretch=(col in ("Home", "Away", "Tourn.")))
    recent_tree.tag_configure("row_even", background=SURFACE)
    recent_tree.tag_configure("row_odd",  background=STRIPE)

    progress_subtitle = tk.Label(
        progress_inner,
        text="Select a tournament above to see standings.",
        bg=bg, fg=title_fg, font=F_SMALL)
    progress_subtitle.pack(anchor="w", pady=(0, 6))
    p_shell = tk.Frame(progress_inner, bg=BORDER)
    p_shell.pack(fill="both", expand=True)
    progress_tree = ttk.Treeview(
        p_shell, columns=["Team", "P", "W", "D", "L", "Pts"],
        show="headings", selectmode="none")
    p_scroll = ttk.Scrollbar(p_shell, orient="vertical",
                             command=progress_tree.yview)
    progress_tree.configure(yscrollcommand=p_scroll.set)
    p_scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
    progress_tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w in zip(["Team", "P", "W", "D", "L", "Pts"],
                      [280, 60, 60, 60, 60, 70]):
        progress_tree.heading(col, text=col,
                              anchor="w" if col == "Team" else "center")
        progress_tree.column(col, width=w, minwidth=40,
                             anchor="w" if col == "Team" else "center",
                             stretch=(col == "Team"))
    progress_tree.tag_configure("row_even", background=SURFACE)
    progress_tree.tag_configure("row_odd",  background=STRIPE)

    return dashboard


def load_tournaments():
    prev = tournaments_tree.selection()
    prev_id = prev[0] if prev else None
    tournaments_tree.delete(*tournaments_tree.get_children())
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT t.TournamentID, t.TournamentName,
                   COALESCE(t.TournamentDate, '-'),
                   COUNT(m.MatchID)
            FROM Tournaments t
            LEFT JOIN Matches m ON m.TournamentID = t.TournamentID
            GROUP BY t.TournamentID
            ORDER BY COALESCE(t.TournamentDate, '9999') DESC, t.TournamentName
        """).fetchall()
    for i, (tid, name, date, count) in enumerate(rows):
        tournaments_tree.insert("", "end", iid=str(tid),
                                values=(name, date, count),
                                tags=("row_even" if i % 2 == 0 else "row_odd",))
    focus_id = SETTINGS.get("focus_tournament_id")
    target = None
    if prev_id and tournaments_tree.exists(prev_id):
        target = prev_id
    elif focus_id is not None and tournaments_tree.exists(str(focus_id)):
        target = str(focus_id)
    elif rows:
        target = str(rows[0][0])
    if target:
        tournaments_tree.selection_set(target)
        tournaments_tree.focus(target)
    _sync_focus_btn()
    on_tournament_select()


def load_recent():
    recent_tree.delete(*recent_tree.get_children())
    limit = int(SETTINGS["recent_matches_count"])
    focus_id = SETTINGS.get("focus_tournament_id")
    try:
        focus_id = int(focus_id) if focus_id is not None else None
    except (ValueError, TypeError):
        focus_id = None
    where = ""
    params = (limit,)
    if focus_id is not None:
        where = "WHERE m.TournamentID = ?"
        params = (focus_id, limit)
    with connect_db() as conn:
        rows = conn.execute(f"""
            SELECT COALESCE(m.MatchDate, '-'),
                   ht.TeamName, at.TeamName,
                   COALESCE(m.MatchHScore, '-') || ' – ' ||
                   COALESCE(m.MatchAScore, '-'),
                   COALESCE(t.TournamentName, '-')
            FROM Matches m
            JOIN Teams ht ON m.MatchHome = ht.TeamID
            JOIN Teams at ON m.MatchAway = at.TeamID
            LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
            {where}
            ORDER BY m.MatchID DESC LIMIT ?
        """, params).fetchall()
    for i, row in enumerate(rows):
        recent_tree.insert("", "end", values=row,
                           tags=("row_even" if i % 2 == 0 else "row_odd",))


def load_progress(tournament_id=None):
    progress_tree.delete(*progress_tree.get_children())
    if tournament_id is None:
        progress_subtitle.configure(
            text="Select a tournament above to see standings.")
        return
    with connect_db() as conn:
        name_row = conn.execute(
            "SELECT TournamentName FROM Tournaments WHERE TournamentID = ?",
            (tournament_id,)).fetchone()
        if not name_row:
            progress_subtitle.configure(text="Tournament not found.")
            return
        tname = name_row[0]
        rows = conn.execute("""
            SELECT t.TeamName,
                   COUNT(m.MatchID),
                   SUM(CASE WHEN (m.MatchHome=t.TeamID AND m.MatchHScore>m.MatchAScore)
                              OR (m.MatchAway=t.TeamID AND m.MatchAScore>m.MatchHScore)
                            THEN 1 ELSE 0 END),
                   SUM(CASE WHEN m.MatchHScore=m.MatchAScore THEN 1 ELSE 0 END),
                   SUM(CASE WHEN (m.MatchHome=t.TeamID AND m.MatchHScore<m.MatchAScore)
                              OR (m.MatchAway=t.TeamID AND m.MatchAScore<m.MatchHScore)
                            THEN 1 ELSE 0 END)
            FROM Teams t
            JOIN Matches m ON (m.MatchHome=t.TeamID OR m.MatchAway=t.TeamID)
                          AND m.TournamentID = ?
                          AND m.MatchHScore IS NOT NULL
                          AND m.MatchAScore IS NOT NULL
            GROUP BY t.TeamID
        """, (tournament_id,)).fetchall()
    if not rows:
        progress_subtitle.configure(text=f"{tname} – no completed matches yet.")
        return
    progress_subtitle.configure(text=f"Standings for {tname}")
    wp = SETTINGS["win_points"]
    dp = SETTINGS["draw_points"]
    lp = SETTINGS["loss_points"]
    parsed = []
    for team, played, won, drawn, lost in rows:
        pts = ((won or 0) * wp) + ((drawn or 0) * dp) + ((lost or 0) * lp)
        parsed.append((team, played, won or 0, drawn or 0, lost or 0, pts))
    parsed.sort(key=lambda r: (-r[5], -r[2], r[0].lower()))
    for i, r in enumerate(parsed):
        progress_tree.insert("", "end", values=r,
                             tags=("row_even" if i % 2 == 0 else "row_odd",))


def on_tournament_select(event=None):
    sel = tournaments_tree.selection()
    if not sel:
        load_progress(None)
        return
    try:
        tid = int(sel[0])
    except ValueError:
        return
    load_progress(tid)


def refresh_dashboard():
    invalidate_calendar_cache()
    _update_focus_badge()
    _sync_focus_btn()
    load_tournaments()
    load_recent()
    load_calendar()


def rebuild_sections():
    for widget in list(_section_widgets.values()):
        widget.destroy()
    _section_widgets.clear()

    for i in range(5):
        content_area.rowconfigure(i, weight=0)

    builders = {
        "actions":   build_actions_section,
        "dashboard": build_dashboard_section,
        "calendar":  build_calendar_section,
    }
    for i, name in enumerate(SETTINGS["layout_order"]):
        builder = builders.get(name)
        if not builder:
            continue
        frame = builder(content_area)
        frame.grid(row=i, column=0, sticky="nsew", padx=22, pady=6)
        content_area.rowconfigure(i, weight=(1 if name == "dashboard" else 0))
        _section_widgets[name] = frame

    refresh_dashboard()


root.bind("<<DataChanged>>", lambda e: refresh_dashboard())

rebuild_sections()

# ------------------------------------------------------------------ global shortcuts
def _shortcut_new_match(event=None):
    focused = root.focus_get()
    if focused is None:
        return
    if focused.winfo_toplevel() is root:
        add_match()

def _shortcut_quit(event=None):
    focused = root.focus_get()
    if focused is None:
        return
    if focused.winfo_toplevel() is root:
        root.destroy()

root.bind("<Control-n>", _shortcut_new_match)
root.bind("<Control-q>", _shortcut_quit)

root.mainloop()