"""Tchoukball Stats – dark-themed Tkinter dashboard with tournaments."""

from tkinter import *
from tkinter import ttk, messagebox
import tkinter as tk
import sqlite3

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


# ------------------------------------------------------------------ database
def init_db():
    with sqlite3.connect(DB) as conn:
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
          PlayerID      INTEGER PRIMARY KEY,
          PlayerName    TEXT NOT NULL,
          PlayerSurname TEXT,
          TeamID        INTEGER REFERENCES Teams(TeamID)
        );
        CREATE TABLE IF NOT EXISTS Tournaments (
          TournamentID       INTEGER PRIMARY KEY,
          TournamentName     TEXT NOT NULL UNIQUE,
          TournamentDate     TEXT,
          TournamentLocation TEXT
        );
        CREATE TABLE IF NOT EXISTS Matches (
          MatchID       INTEGER PRIMARY KEY,
          MatchHome     INTEGER NOT NULL,
          MatchAway     INTEGER NOT NULL,
          MatchLocation TEXT,
          MatchHScore   INTEGER,
          MatchAScore   INTEGER,
          TournamentID  INTEGER,
          MatchDate     TEXT,
          FOREIGN KEY (MatchHome) REFERENCES Teams(TeamID),
          FOREIGN KEY (MatchAway) REFERENCES Teams(TeamID),
          FOREIGN KEY (TournamentID) REFERENCES Tournaments(TournamentID)
        );
        CREATE TABLE IF NOT EXISTS MatchRoster (
          MatchID  INTEGER NOT NULL,
          TeamID   INTEGER NOT NULL,
          PlayerID INTEGER NOT NULL,
          PRIMARY KEY (MatchID, PlayerID),
          FOREIGN KEY (MatchID)  REFERENCES Matches(MatchID),
          FOREIGN KEY (TeamID)   REFERENCES Teams(TeamID),
          FOREIGN KEY (PlayerID) REFERENCES Players(PlayerID)
        );
        """)
        # --- migrate older DBs
        cols = [r[1] for r in conn.execute("PRAGMA table_info(Matches)")]
        if "TournamentID" not in cols:
            conn.execute("ALTER TABLE Matches ADD COLUMN TournamentID INTEGER")
        if "MatchDate" not in cols:
            conn.execute("ALTER TABLE Matches ADD COLUMN MatchDate TEXT")
        cols = [r[1] for r in conn.execute("PRAGMA table_info(Teams)")]
        if "ClubID" not in cols:
            conn.execute("ALTER TABLE Teams ADD COLUMN ClubID INTEGER")
        cols = [r[1] for r in conn.execute("PRAGMA table_info(Players)")]
        if "TeamID" not in cols:
            conn.execute("ALTER TABLE Players ADD COLUMN TeamID INTEGER")


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


def card_frame(parent, title, **grid_kwargs):
    outer = tk.Frame(parent, bg=SURFACE,
                     highlightbackground=BORDER, highlightthickness=1)
    outer.grid(sticky="nsew", **grid_kwargs)
    inner = tk.Frame(outer, bg=SURFACE, padx=12, pady=12)
    inner.pack(fill="both", expand=True)
    tk.Label(inner, text=title, bg=SURFACE, fg=MUTED,
             font=F_CAPS).pack(anchor="w", pady=(0, 8))
    return inner


# ------------------------------------------------------------------ bootstrap
init_db()

root = Tk()
root.title("Tchoukball Stats")
root.configure(bg=BG)
center_window(root, 1080, 860)
root.minsize(960, 740)
apply_theme(root)

header = tk.Frame(root, bg=BG)
header.pack(fill="x", padx=22, pady=(18, 10))
tk.Label(header, text="Tchoukball Stats", bg=BG, fg=FG,
         font=(FONT, 20, "bold")).pack(anchor="w")
tk.Label(header, text="Manage teams, matches and tournaments.",
         bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))
tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=22)

status_var = StringVar()
status_lbl = tk.Label(root, textvariable=status_var, bg=BG, fg=MUTED,
                      font=F_SMALL, anchor="w", padx=22, pady=6)
status_lbl.pack(fill="x", side="bottom")

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
def show_table(title, query, columns, compare_kind=None):
    with sqlite3.connect(DB) as conn:
        rows = conn.execute(query).fetchall()

    win = Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    center_window(win, 880, 520)
    win.minsize(560, 320)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 12))
    tk.Label(head, text=title, bg=BG, fg=FG, font=F_TITLE).pack(side="left")
    tk.Label(head, text=f"{len(rows)} row{'s' if len(rows) != 1 else ''}",
             bg=BG, fg=MUTED, font=F_SMALL).pack(side="right")

    shell = tk.Frame(win, bg=BORDER)
    shell.pack(fill="both", expand=True, padx=22,
               pady=(0, 10) if compare_kind else (0, 20))

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
        tree.heading(col, text=col, anchor="w",
                     command=lambda c=col: sort_by(c, False))
        tree.column(col, width=max(90, min(240, longest * 9 + 28)),
                    minwidth=70, anchor="w", stretch=True)

    tree.tag_configure("row_even", background=SURFACE)
    tree.tag_configure("row_odd",  background=STRIPE)
    for i, row in enumerate(rows):
        tree.insert("", "end", values=row,
                    tags=("row_even" if i % 2 == 0 else "row_odd",))

    if not rows:
        tk.Label(shell, text="No records yet", bg=SURFACE, fg=MUTED,
                 font=F_BODY).place(relx=0.5, rely=0.5, anchor="center")

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
        tree.heading(col, command=lambda: sort_by(col, not descending))

    if compare_kind:
        bar = tk.Frame(win, bg=BG)
        bar.pack(fill="x", padx=22, pady=(0, 20))
        def do_compare():
            sel = tree.selection()
            if len(sel) != 2:
                messagebox.showinfo("Select two rows",
                                    "Select exactly two rows to compare.",
                                    parent=win)
                return
            ids = [int(tree.item(iid, "values")[0]) for iid in sel]
            open_compare(compare_kind, preselected=(ids[0], ids[1]))
        make_small_button(bar, "Compare selected", do_compare).pack(side="right")
        make_small_button(bar, "Close", win.destroy).pack(side="right", padx=(0, 8))

    tree.bind("<MouseWheel>",
              lambda e: tree.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    tree.bind("<Button-4>", lambda e: tree.yview_scroll(-1, "units"))
    tree.bind("<Button-5>", lambda e: tree.yview_scroll(1, "units"))


# ------------------------------------------------------------------ insert
def insert_row(query, values, success_message):
    try:
        with sqlite3.connect(DB) as conn:
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
def make_form(title, subtitle, fields, on_submit):
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
        else:
            w = tk.Entry(body, bg=SURFACE, fg=FG, insertbackground=FG,
                         relief="flat", highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT,
                         font=F_BODY, width=36)
            w.pack(fill="x", ipady=7)
        widgets[field["key"]] = w
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
    with sqlite3.connect(DB) as conn:
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
    with sqlite3.connect(DB) as conn:
        teams = conn.execute("SELECT TeamID, TeamName FROM Teams "
                             "ORDER BY TeamName").fetchall()
    team_opts = ["(none)"] + [f"{tid} · {tname}" for tid, tname in teams]
    team_of = {f"{tid} · {tname}": tid for tid, tname in teams}

    def save(v):
        tid = None if v["team"] == "(none)" else team_of[v["team"]]
        return insert_row(
            "INSERT INTO Players (PlayerName, PlayerSurname, TeamID) "
            "VALUES (?, ?, ?)",
            (v["fname"], v["sname"], tid), f'Player "{v["fname"]}" added.')

    make_form("New player", "First name required; team optional.",
              [{"label": "First name", "key": "fname", "required": True},
               {"label": "Surname", "key": "sname"},
               {"label": "Team (optional)", "key": "team", "values": team_opts}],
              save)


def add_tournament():
    make_form("New tournament", "Give your tournament a name, date and place.",
              [{"label": "Tournament name", "key": "name", "required": True},
               {"label": "Date (YYYY-MM-DD)", "key": "date"},
               {"label": "Location", "key": "loc"}],
              lambda v: insert_row(
                  "INSERT INTO Tournaments (TournamentName, TournamentDate, "
                  "TournamentLocation) VALUES (?, ?, ?)",
                  (v["name"], v["date"] or None, v["loc"] or None),
                  f'Tournament "{v["name"]}" added.'))


def add_match():
    with sqlite3.connect(DB) as conn:
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
        result = insert_row(
            "INSERT INTO Matches (MatchHome, MatchAway, MatchLocation, "
            "MatchHScore, MatchAScore, TournamentID, MatchDate) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (team_of[v["home"]], team_of[v["away"]],
             v["loc"] or None, scores[0], scores[1], tid, v["date"] or None),
            "Match added.")
        if result is not False:
            root.after(120, lambda: open_roster_editor(result))
        return result
    make_form("New match", "Assign to a tournament and record the final score.",
              [{"label": "Tournament", "key": "tournament",
                "values": ["(none)"] + list(tourn_of)},
               {"label": "Home team", "key": "home",
                "values": list(team_of), "required": True},
               {"label": "Away team", "key": "away",
                "values": list(team_of), "required": True},
               {"label": "Location", "key": "loc"},
               {"label": "Date (YYYY-MM-DD)", "key": "date"},
               {"label": "Home score", "key": "hs"},
               {"label": "Away score", "key": "as"}],
              save)


# ------------------------------------------------------------------ editor window
def open_editor(title, subtitle, table, id_col, list_query, list_columns,
                list_col_widths, fetch_query, fields, validator=None,
                pre_delete=None):
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
        with sqlite3.connect(DB) as conn:
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
        with sqlite3.connect(DB) as conn:
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
                                "Select a record in the list first.",
                                parent=win)
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
                                       f"{field['label']} is required.",
                                       parent=win)
                return
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
                            f"{field['label']} must be a whole number.",
                            parent=win)
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
            with sqlite3.connect(DB) as conn:
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
                                "Select a record in the list first.",
                                parent=win)
            return
        if not messagebox.askyesno("Delete record",
                                   "Delete the selected record?\n"
                                   "This cannot be undone.", parent=win):
            return
        try:
            with sqlite3.connect(DB) as conn:
                if pre_delete:
                    pre_delete(conn, current_id[0])
                conn.execute(f"DELETE FROM {table} WHERE {id_col} = ?",
                             (current_id[0],))
        except sqlite3.IntegrityError as exc:
            set_status(f"Could not delete: {exc}", error=True)
            messagebox.showerror(
                "Cannot delete",
                "This record is still referenced by other records.\n\n"
                f"{exc}", parent=win)
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

    tree.bind("<<TreeviewSelect>>", lambda e: populate())
    tree.bind("<MouseWheel>",
              lambda e: tree.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    tree.bind("<Button-4>", lambda e: tree.yview_scroll(-1, "units"))
    tree.bind("<Button-5>", lambda e: tree.yview_scroll(1, "units"))
    win.bind("<Control-s>", lambda e: save())

    rows = load_list()
    if rows:
        first = tree.get_children()[0]
        tree.selection_set(first)
        tree.focus(first)
        populate()


# ------------------------------------------------------------------ edit handlers
def edit_team():
    with sqlite3.connect(DB) as conn:
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
        pre_delete=lambda c, tid: c.execute(
            "DELETE FROM MatchRoster WHERE TeamID = ?", (tid,)),
    )


def edit_club():
    open_editor(
        title="Edit clubs",
        subtitle="Select a club, change its name, then save.",
        table="Clubs", id_col="ClubID",
        list_query="SELECT ClubID, ClubName FROM Clubs ORDER BY ClubName",
        list_columns=["ID", "Club name"], list_col_widths=[70, 400],
        fetch_query="SELECT ClubName FROM Clubs WHERE ClubID = ?",
        fields=[{"label": "Club name", "key": "name",
                 "column": "ClubName", "required": True}],
    )


def edit_player():
    with sqlite3.connect(DB) as conn:
        teams = conn.execute("SELECT TeamID, TeamName FROM Teams "
                             "ORDER BY TeamName").fetchall()
    team_opts = [("(none)", None)] + [(tname, tid) for tid, tname in teams]
    open_editor(
        title="Edit players",
        subtitle="Select a player, update the details, then save.",
        table="Players", id_col="PlayerID",
        list_query="""SELECT p.PlayerID, p.PlayerName,
                             COALESCE(p.PlayerSurname, ''),
                             COALESCE(t.TeamName, '—')
                      FROM Players p LEFT JOIN Teams t ON p.TeamID = t.TeamID
                      ORDER BY p.PlayerName, p.PlayerSurname""",
        list_columns=["ID", "First", "Surname", "Team"],
        list_col_widths=[60, 170, 170, 170],
        fetch_query="SELECT PlayerName, PlayerSurname, TeamID "
                    "FROM Players WHERE PlayerID = ?",
        fields=[
            {"label": "First name", "key": "fname",
             "column": "PlayerName", "required": True},
            {"label": "Surname", "key": "sname", "column": "PlayerSurname"},
            {"label": "Team", "key": "team", "column": "TeamID",
             "widget": "combo", "options": team_opts},
        ],
        pre_delete=lambda c, pid: c.execute(
            "DELETE FROM MatchRoster WHERE PlayerID = ?", (pid,)),
    )


def edit_tournament():
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
             "column": "TournamentDate"},
            {"label": "Location", "key": "loc", "column": "TournamentLocation"},
        ],
    )


def edit_match():
    with sqlite3.connect(DB) as conn:
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
                             COALESCE(t.TournamentName, '-')
                      FROM Matches m
                      JOIN Teams ht ON m.MatchHome = ht.TeamID
                      JOIN Teams at ON m.MatchAway = at.TeamID
                      LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
                      ORDER BY m.MatchID DESC""",
        list_columns=["ID", "Date", "Home", "Away", "Score", "Tournament"],
        list_col_widths=[55, 110, 130, 130, 80, 160],
        fetch_query="""SELECT MatchHome, MatchAway, MatchLocation,
                              MatchHScore, MatchAScore, TournamentID, MatchDate
                       FROM Matches WHERE MatchID = ?""",
        fields=[
            {"label": "Home team", "key": "home", "column": "MatchHome",
             "widget": "combo", "options": team_opts, "required": True},
            {"label": "Away team", "key": "away", "column": "MatchAway",
             "widget": "combo", "options": team_opts, "required": True},
            {"label": "Tournament", "key": "tournament",
             "column": "TournamentID", "widget": "combo", "options": tourn_opts},
            {"label": "Location", "key": "loc", "column": "MatchLocation"},
            {"label": "Date (YYYY-MM-DD)", "key": "date", "column": "MatchDate"},
            {"label": "Home score", "key": "hs", "column": "MatchHScore",
             "numeric": True},
            {"label": "Away score", "key": "as", "column": "MatchAScore",
             "numeric": True},
        ],
        validator=validate,
        pre_delete=lambda c, mid: c.execute(
            "DELETE FROM MatchRoster WHERE MatchID = ?", (mid,)),
    )


# ------------------------------------------------------------------ browse handlers
def browse_teams():
    show_table("Teams",
               """SELECT t.TeamID, t.TeamName, COALESCE(c.ClubName, '—')
                  FROM Teams t LEFT JOIN Clubs c ON t.ClubID = c.ClubID
                  ORDER BY t.TeamName""",
               ["ID", "Team", "Club"], compare_kind="teams")


def browse_clubs():
    show_table("Clubs",
               """SELECT c.ClubID, c.ClubName, COUNT(t.TeamID)
                  FROM Clubs c LEFT JOIN Teams t ON c.ClubID = t.ClubID
                  GROUP BY c.ClubID ORDER BY c.ClubName""",
               ["ID", "Club", "Teams"], compare_kind="clubs")


def browse_players():
    show_table("Players",
               """SELECT p.PlayerID, p.PlayerName,
                         COALESCE(p.PlayerSurname, ''),
                         COALESCE(t.TeamName, '—')
                  FROM Players p LEFT JOIN Teams t ON p.TeamID = t.TeamID
                  ORDER BY p.PlayerName, p.PlayerSurname""",
               ["ID", "First name", "Surname", "Team"], compare_kind="players")


def browse_tournaments():
    show_table("Tournaments",
               "SELECT * FROM Tournaments ORDER BY TournamentDate DESC",
               ["TournamentID", "TournamentName", "TournamentDate",
                "TournamentLocation"])


def browse_matches():
    show_table("Matches",
               """SELECT m.MatchID, ht.TeamName, at.TeamName,
                         COALESCE(m.MatchLocation, '-'),
                         COALESCE(m.MatchHScore, '-'),
                         COALESCE(m.MatchAScore, '-'),
                         COALESCE(t.TournamentName, '-'),
                         COALESCE(m.MatchDate, '-')
                  FROM Matches m
                  JOIN Teams ht ON m.MatchHome = ht.TeamID
                  JOIN Teams at ON m.MatchAway = at.TeamID
                  LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
                  ORDER BY m.MatchID DESC""",
               ["ID", "Home", "Away", "Location", "H", "A", "Tournament", "Date"],
               compare_kind="matches")


# ------------------------------------------------------------------ remover window
def open_remover(title, subtitle, table, id_col, list_query,
                 list_columns, list_col_widths, pre_delete=None):
    win = Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    center_window(win, 860, 520)
    win.minsize(620, 400)
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
    tree.tag_configure("row_even", background=SURFACE)
    tree.tag_configure("row_odd",  background=STRIPE)

    def load_list():
        tree.delete(*tree.get_children())
        with sqlite3.connect(DB) as conn:
            rows = conn.execute(list_query).fetchall()
        for i, r in enumerate(rows):
            tree.insert("", "end", values=r,
                        tags=("row_even" if i % 2 == 0 else "row_odd",))
        if rows:
            first = tree.get_children()[0]
            tree.selection_set(first)
            tree.focus(first)
        return rows

    def remove():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Nothing selected",
                                "Select a record from the list first.",
                                parent=win)
            return
        rid = tree.item(sel[0], "values")[0]
        label = " · ".join(str(v) for v in tree.item(sel[0], "values")[1:])
        if not messagebox.askyesno(
                "Remove record",
                f"Remove “{label or rid}”?\nThis cannot be undone.",
                parent=win):
            return
        try:
            with sqlite3.connect(DB) as conn:
                if pre_delete:
                    pre_delete(conn, rid)
                conn.execute(f"DELETE FROM {table} WHERE {id_col} = ?", (rid,))
        except sqlite3.IntegrityError as exc:
            set_status(f"Could not remove: {exc}", error=True)
            messagebox.showerror(
                "Cannot remove",
                "This record is still referenced by other records.\n\n"
                f"{exc}", parent=win)
            return
        set_status("Record removed.")
        root.event_generate("<<DataChanged>>")
        load_list()

    make_button(actions, "Remove selected", remove,
                danger=True, anchor="center").pack(side="right")
    make_button(actions, "Close", win.destroy, anchor="center"
                ).pack(side="right", padx=(0, 8))
    tree.bind("<MouseWheel>",
              lambda e: tree.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    tree.bind("<Button-4>", lambda e: tree.yview_scroll(-1, "units"))
    tree.bind("<Button-5>", lambda e: tree.yview_scroll(1, "units"))
    win.bind("<Delete>", lambda e: remove())
    load_list()


def remove_team():
    open_remover("Remove teams",
                 "Teams used in a match must be unreferenced first.",
                 table="Teams", id_col="TeamID",
                 list_query="SELECT TeamID, TeamName FROM Teams ORDER BY TeamName",
                 list_columns=["ID", "Team name"], list_col_widths=[70, 400],
                 pre_delete=lambda c, tid: c.execute(
                     "DELETE FROM MatchRoster WHERE TeamID = ?", (tid,)))


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
                 list_col_widths=[60, 260, 140])


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
                 pre_delete=lambda c, mid: c.execute(
                     "DELETE FROM MatchRoster WHERE MatchID = ?", (mid,)))


# ------------------------------------------------------------------ rosters
def open_roster_editor(match_id):
    with sqlite3.connect(DB) as conn:
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
            "WHERE TeamID=? ORDER BY PlayerName", (home_id,)).fetchall()
        away_players = conn.execute(
            "SELECT PlayerID, PlayerName || ' ' || "
            "COALESCE(PlayerSurname, '') FROM Players "
            "WHERE TeamID=? ORDER BY PlayerName", (away_id,)).fetchall()
        current = {r[0] for r in conn.execute(
            "SELECT PlayerID FROM MatchRoster WHERE MatchID = ?",
            (match_id,)).fetchall()}

    win = Toplevel(root)
    win.title(f"Roster · Match #{match_id}")
    win.configure(bg=BG)
    center_window(win, 760, 540)
    win.minsize(640, 440)
    win.bind("<Escape>", lambda e: win.destroy())

    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=22, pady=(20, 12))
    tk.Label(head, text=f"Match #{match_id} roster", bg=BG, fg=FG,
             font=F_TITLE).pack(anchor="w")
    tk.Label(head, text="Ctrl-click to select multiple players per side.",
             bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

    body = tk.Frame(win, bg=BG)
    body.pack(fill="both", expand=True, padx=22, pady=(0, 12))
    body.columnconfigure(0, weight=1, uniform="half")
    body.columnconfigure(1, weight=1, uniform="half")
    body.rowconfigure(0, weight=1)

    def make_list(col, team_name, players):
        colf = tk.Frame(body, bg=BG)
        colf.grid(row=0, column=col, sticky="nsew",
                  padx=(0, 6) if col == 0 else (6, 0))
        tk.Label(colf, text=team_name, bg=BG, fg=MUTED,
                 font=F_CAPS).pack(anchor="w", pady=(0, 4))
        shell = tk.Frame(colf, bg=BORDER)
        shell.pack(fill="both", expand=True)
        lb = tk.Listbox(shell, selectmode="multiple", exportselection=False,
                        bg=SURFACE, fg=FG, selectbackground=ACCENT,
                        selectforeground="#ffffff", activestyle="none",
                        relief="flat", bd=0, highlightthickness=0,
                        font=F_BODY)
        sb = ttk.Scrollbar(shell, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        id_list = []
        if not players:
            lb.insert("end", "(no players on this team)")
            lb.itemconfig(0, foreground=MUTED)
        for i, (pid, name) in enumerate(players):
            lb.insert("end", name)
            id_list.append(pid)
            if pid in current:
                lb.selection_set(i)
        return lb, id_list

    home_lb, home_ids = make_list(0, home_name, home_players)
    away_lb, away_ids = make_list(1, away_name, away_players)

    actions = tk.Frame(win, bg=BG)
    actions.pack(fill="x", padx=22, pady=(0, 18))

    def save():
        picks = [(home_id, home_ids[i]) for i in home_lb.curselection()
                 if i < len(home_ids)]
        picks += [(away_id, away_ids[i]) for i in away_lb.curselection()
                  if i < len(away_ids)]
        try:
            with sqlite3.connect(DB) as conn:
                conn.execute("DELETE FROM MatchRoster WHERE MatchID = ?",
                             (match_id,))
                conn.executemany(
                    "INSERT INTO MatchRoster (MatchID, TeamID, PlayerID) "
                    "VALUES (?, ?, ?)",
                    [(match_id, tid, pid) for tid, pid in picks])
            set_status(f"Roster saved ({len(picks)} players).")
            root.event_generate("<<DataChanged>>")
            win.destroy()
        except sqlite3.IntegrityError as exc:
            set_status(f"Could not save roster: {exc}", error=True)

    make_button(actions, "Save roster", save, accent=True, anchor="center"
                ).pack(side="right")
    make_button(actions, "Cancel", win.destroy, anchor="center"
                ).pack(side="right", padx=(0, 8))


def open_roster_picker():
    with sqlite3.connect(DB) as conn:
        rows = conn.execute("""
            SELECT m.MatchID,
                   COALESCE(m.MatchDate, '-'),
                   ht.TeamName || ' vs ' || at.TeamName,
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
    center_window(win, 780, 500)
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
    tree = ttk.Treeview(shell, columns=["ID", "Date", "Match", "Players"],
                        show="headings", selectmode="browse")
    sb = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    for col, w in zip(["ID", "Date", "Match", "Players"],
                      [55, 110, 380, 80]):
        tree.heading(col, text=col, anchor="w")
        tree.column(col, width=w, minwidth=40, anchor="w",
                    stretch=(col == "Match"))
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
    make_small_button(actions, "Close", win.destroy).pack(
        side="right", padx=(0, 8))
    tree.bind("<Double-1>", lambda e: edit_sel())


# ------------------------------------------------------------------ comparison
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


def render_team_comparison(parent, a_id, b_id):
    with sqlite3.connect(DB) as conn:
        a_name = conn.execute("SELECT TeamName FROM Teams WHERE TeamID=?",
                              (a_id,)).fetchone()[0]
        b_name = conn.execute("SELECT TeamName FROM Teams WHERE TeamID=?",
                              (b_id,)).fetchone()[0]

        def record(tid):
            return conn.execute("""
                SELECT COUNT(*),
                       SUM(CASE WHEN (MatchHome=? AND MatchHScore>MatchAScore)
                                  OR (MatchAway=? AND MatchAScore>MatchHScore)
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN MatchHScore=MatchAScore
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN (MatchHome=? AND MatchHScore<MatchAScore)
                                  OR (MatchAway=? AND MatchAScore<MatchHScore)
                                THEN 1 ELSE 0 END),
                       COALESCE(SUM(CASE WHEN MatchHome=? THEN MatchHScore
                                         WHEN MatchAway=? THEN MatchAScore
                                         ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN MatchHome=? THEN MatchAScore
                                         WHEN MatchAway=? THEN MatchHScore
                                         ELSE 0 END), 0)
                FROM Matches
                WHERE (MatchHome=? OR MatchAway=?)
                  AND MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
            """, (tid, tid, tid, tid, tid, tid, tid, tid, tid, tid)).fetchone()

        a = record(a_id)
        b = record(b_id)

        h2h = conn.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN (MatchHome=? AND MatchHScore>MatchAScore)
                              OR (MatchAway=? AND MatchAScore>MatchHScore)
                            THEN 1 ELSE 0 END),
                   SUM(CASE WHEN MatchHScore=MatchAScore
                            THEN 1 ELSE 0 END),
                   SUM(CASE WHEN (MatchHome=? AND MatchHScore<MatchAScore)
                              OR (MatchAway=? AND MatchAScore<MatchHScore)
                            THEN 1 ELSE 0 END)
            FROM Matches
            WHERE ((MatchHome=? AND MatchAway=?)
                OR (MatchHome=? AND MatchAway=?))
              AND MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
        """, (a_id, a_id, a_id, a_id, b_id, b_id, a_id)).fetchone()

    def sd(v):
        return 0 if v is None else v

    rows = [
        ("Matches played",     sd(a[0]), sd(b[0])),
        ("Wins",               sd(a[1]), sd(b[1])),
        ("Draws",              sd(a[2]), sd(b[2])),
        ("Losses",             sd(a[3]), sd(b[3])),
        ("Points scored",      sd(a[4]), sd(b[4])),
        ("Points conceded",    sd(a[5]), sd(b[5])),
        ("Point difference",   sd(a[4]) - sd(a[5]), sd(b[4]) - sd(b[5])),
        ("Head-to-head matches", sd(h2h[0]), sd(h2h[0])),
        ("Head-to-head wins",  sd(h2h[1]), sd(h2h[3])),
        ("Head-to-head draws", sd(h2h[2]), sd(h2h[2])),
    ]
    render_comparison_table(parent, a_name, b_name, rows)


def render_club_comparison(parent, a_id, b_id):
    with sqlite3.connect(DB) as conn:
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
            row = conn.execute(f"""
                SELECT COUNT(*),
                       SUM(CASE WHEN (MatchHome IN ({ph})
                                      AND MatchHScore>MatchAScore)
                                  OR (MatchAway IN ({ph})
                                      AND MatchAScore>MatchHScore)
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN MatchHScore=MatchAScore
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN (MatchHome IN ({ph})
                                      AND MatchHScore<MatchAScore)
                                  OR (MatchAway IN ({ph})
                                      AND MatchAScore<MatchHScore)
                                THEN 1 ELSE 0 END)
                FROM Matches
                WHERE (MatchHome IN ({ph}) OR MatchAway IN ({ph}))
                  AND MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
            """, team_ids * 6).fetchone()
            return (len(team_ids), n_players) + row

        a = club_stats(a_id)
        b = club_stats(b_id)

    def sd(v):
        return 0 if v is None else v

    rows = [
        ("Teams in club",     a[0], b[0]),
        ("Players in club",   a[1], b[1]),
        ("Matches played",    sd(a[2]), sd(b[2])),
        ("Wins",              sd(a[3]), sd(b[3])),
        ("Draws",             sd(a[4]), sd(b[4])),
        ("Losses",            sd(a[5]), sd(b[5])),
    ]
    render_comparison_table(parent, a_name, b_name, rows)


def render_player_comparison(parent, a_id, b_id):
    with sqlite3.connect(DB) as conn:
        def get_player(pid):
            return conn.execute("""
                SELECT p.PlayerName, COALESCE(p.PlayerSurname, ''),
                       COALESCE(t.TeamName, '—'), p.TeamID
                FROM Players p LEFT JOIN Teams t ON p.TeamID = t.TeamID
                WHERE p.PlayerID=?
            """, (pid,)).fetchone()

        def team_record(tid):
            if tid is None:
                return (0, 0, 0, 0)
            return conn.execute("""
                SELECT COUNT(*),
                       SUM(CASE WHEN (MatchHome=? AND MatchHScore>MatchAScore)
                                  OR (MatchAway=? AND MatchAScore>MatchHScore)
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN MatchHScore=MatchAScore
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN (MatchHome=? AND MatchHScore<MatchAScore)
                                  OR (MatchAway=? AND MatchAScore<MatchHScore)
                                THEN 1 ELSE 0 END)
                FROM Matches
                WHERE (MatchHome=? OR MatchAway=?)
                  AND MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
            """, (tid, tid, tid, tid, tid, tid)).fetchone()

        a = get_player(a_id)
        b = get_player(b_id)
        a_tr = team_record(a[3])
        b_tr = team_record(b[3])

    def full_name(p):
        return (p[0] + (" " + p[1] if p[1] else "")).strip()

    def sd(v):
        return 0 if v is None else v

    rows = [
        ("Team",               a[2], b[2]),
        ("Team matches",       sd(a_tr[0]), sd(b_tr[0])),
        ("Team wins",          sd(a_tr[1]), sd(b_tr[1])),
        ("Team draws",         sd(a_tr[2]), sd(b_tr[2])),
        ("Team losses",        sd(a_tr[3]), sd(b_tr[3])),
        ("Per-player stats",   "not tracked", "not tracked"),
    ]
    render_comparison_table(parent, full_name(a), full_name(b), rows)


def render_match_comparison(parent, a_id, b_id):
    with sqlite3.connect(DB) as conn:
        def get_match(mid):
            return conn.execute("""
                SELECT ht.TeamName, at.TeamName,
                       COALESCE(m.MatchLocation, '—'),
                       m.MatchHScore, m.MatchAScore,
                       COALESCE(t.TournamentName, '—'),
                       COALESCE(m.MatchDate, '—')
                FROM Matches m
                JOIN Teams ht ON m.MatchHome = ht.TeamID
                JOIN Teams at ON m.MatchAway = at.TeamID
                LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
                WHERE m.MatchID=?
            """, (mid,)).fetchone()
        a = get_match(a_id)
        b = get_match(b_id)

    def score_label(hs, as_):
        if hs is None or as_ is None:
            return "—"
        return f"{hs} – {as_}"

    def margin(hs, as_):
        if hs is None or as_ is None:
            return "—"
        return abs(hs - as_)

    def total(hs, as_):
        if hs is None or as_ is None:
            return "—"
        return hs + as_

    rows = [
        ("Home team",    a[0], b[0]),
        ("Away team",    a[1], b[1]),
        ("Score",        score_label(a[3], a[4]), score_label(b[3], b[4])),
        ("Total points", total(a[3], a[4]), total(b[3], b[4])),
        ("Margin",       margin(a[3], a[4]), margin(b[3], b[4])),
        ("Tournament",   a[5], b[5]),
        ("Location",     a[2], b[2]),
        ("Date",         a[6], b[6]),
    ]
    header_a = f"Match #{a_id}"
    header_b = f"Match #{b_id}"
    render_comparison_table(parent, header_a, header_b, rows)


def open_compare(kind, preselected=None):
    win = Toplevel(root)
    win.title(f"Compare {kind.title()}")
    win.configure(bg=BG)
    center_window(win, 920, 640)
    win.minsize(760, 520)
    win.bind("<Escape>", lambda e: win.destroy())

    with sqlite3.connect(DB) as conn:
        if kind == "teams":
            options = conn.execute(
                "SELECT TeamID, TeamName FROM Teams ORDER BY TeamName"
            ).fetchall()
        elif kind == "clubs":
            options = conn.execute(
                "SELECT ClubID, ClubName FROM Clubs ORDER BY ClubName"
            ).fetchall()
        elif kind == "players":
            options = conn.execute(
                "SELECT PlayerID, PlayerName || "
                "' ' || COALESCE(PlayerSurname, '') "
                "FROM Players ORDER BY PlayerName, PlayerSurname"
            ).fetchall()
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

    if len(options) < 2:
        messagebox.showinfo("Not enough records",
                            f"Add at least two {kind} to compare.",
                            parent=win)
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
    sel_row.pack(fill="x", padx=22, pady=(0, 12))
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
        if kind == "teams":
            render_team_comparison(b, a_id, b_id)
        elif kind == "clubs":
            render_club_comparison(b, a_id, b_id)
        elif kind == "players":
            render_player_comparison(b, a_id, b_id)
        else:
            render_match_comparison(b, a_id, b_id)

    combo_a.bind("<<ComboboxSelected>>", lambda e: render())
    combo_b.bind("<<ComboboxSelected>>", lambda e: render())
    render()


# ------------------------------------------------------------------ top action row
action_row = tk.Frame(root, bg=BG)
action_row.pack(fill="x", padx=22, pady=(14, 8))
for i in range(4):
    action_row.columnconfigure(i, weight=1, uniform="act")

FUNC_BLOCKS = [
    ("BROWSE", [("Teams",       browse_teams),
                ("Clubs",       browse_clubs),
                ("Players",     browse_players),
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
    padx = (0, 6) if i == 0 else (6, 0) if i == 3 else (6, 6)
    inner = card_frame(action_row, title, row=0, column=i, padx=padx, pady=0)
    for label, cmd in items:
        make_small_button(inner, label, cmd,
                          danger=(title == "REMOVE")).pack(fill="x", pady=2)


# ------------------------------------------------------------------ compare strip
compare_row = tk.Frame(root, bg=BG)
compare_row.pack(fill="x", padx=22, pady=(4, 10))
tk.Label(compare_row, text="COMPARE", bg=BG, fg=MUTED,
         font=F_CAPS).pack(side="left", padx=(0, 12))
for label, cmd in (("Teams",   lambda: open_compare("teams")),
                   ("Clubs",   lambda: open_compare("clubs")),
                   ("Players", lambda: open_compare("players")),
                   ("Matches", lambda: open_compare("matches"))):
    make_small_button(compare_row, label, cmd).pack(side="left", padx=(0, 6))


# ------------------------------------------------------------------ dashboard
dashboard = tk.Frame(root, bg=BG)
dashboard.pack(fill="both", expand=True, padx=22, pady=(0, 4))
dashboard.columnconfigure(0, weight=1, uniform="dash")
dashboard.columnconfigure(1, weight=1, uniform="dash")
dashboard.rowconfigure(0, weight=1, uniform="drow")
dashboard.rowconfigure(1, weight=1, uniform="drow")

tourn_inner = card_frame(dashboard, "TOURNAMENTS",
                         row=0, column=0, padx=(0, 6), pady=(0, 6))
recent_inner = card_frame(dashboard, "RECENT MATCHES",
                          row=0, column=1, padx=(6, 0), pady=(0, 6))
progress_inner = card_frame(dashboard, "TOURNAMENT PROGRESS",
                            row=1, column=0, columnspan=2, padx=0, pady=(6, 0))

t_shell = tk.Frame(tourn_inner, bg=BORDER)
t_shell.pack(fill="both", expand=True)
tournaments_tree = ttk.Treeview(t_shell,
                                columns=["Name", "Date", "Matches"],
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

r_shell = tk.Frame(recent_inner, bg=BORDER)
r_shell.pack(fill="both", expand=True)
recent_tree = ttk.Treeview(r_shell,
                           columns=["Date", "Home", "Away", "Score", "Tourn."],
                           show="headings", selectmode="none")
r_scroll = ttk.Scrollbar(r_shell, orient="vertical", command=recent_tree.yview)
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

progress_subtitle = tk.Label(progress_inner,
                             text="Select a tournament above to see standings.",
                             bg=SURFACE, fg=MUTED, font=F_SMALL)
progress_subtitle.pack(anchor="w", pady=(0, 6))
p_shell = tk.Frame(progress_inner, bg=BORDER)
p_shell.pack(fill="both", expand=True)
progress_tree = ttk.Treeview(p_shell,
                             columns=["Team", "P", "W", "D", "L", "Pts"],
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


# ------------------------------------------------------------------ dashboard loaders
def load_tournaments():
    prev = tournaments_tree.selection()
    prev_id = prev[0] if prev else None
    tournaments_tree.delete(*tournaments_tree.get_children())
    with sqlite3.connect(DB) as conn:
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
    if prev_id and tournaments_tree.exists(prev_id):
        tournaments_tree.selection_set(prev_id)
    elif rows:
        first_id = str(rows[0][0])
        tournaments_tree.selection_set(first_id)
        tournaments_tree.focus(first_id)
    on_tournament_select()


def load_recent():
    recent_tree.delete(*recent_tree.get_children())
    with sqlite3.connect(DB) as conn:
        rows = conn.execute("""
            SELECT COALESCE(m.MatchDate, '-'),
                   ht.TeamName, at.TeamName,
                   COALESCE(m.MatchHScore, '-') || ' – ' ||
                   COALESCE(m.MatchAScore, '-'),
                   COALESCE(t.TournamentName, '-')
            FROM Matches m
            JOIN Teams ht ON m.MatchHome = ht.TeamID
            JOIN Teams at ON m.MatchAway = at.TeamID
            LEFT JOIN Tournaments t ON m.TournamentID = t.TournamentID
            ORDER BY m.MatchID DESC LIMIT 10
        """).fetchall()
    for i, row in enumerate(rows):
        recent_tree.insert("", "end", values=row,
                           tags=("row_even" if i % 2 == 0 else "row_odd",))


def load_progress(tournament_id=None):
    progress_tree.delete(*progress_tree.get_children())
    if tournament_id is None:
        progress_subtitle.configure(
            text="Select a tournament above to see standings.")
        return
    with sqlite3.connect(DB) as conn:
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
    parsed = []
    for team, played, won, drawn, lost in rows:
        pts = (won or 0) * 2 + (drawn or 0)
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
    load_tournaments()
    load_recent()


tournaments_tree.bind("<<TreeviewSelect>>", on_tournament_select)
root.bind("<<DataChanged>>", lambda e: refresh_dashboard())

refresh_dashboard()

root.mainloop()