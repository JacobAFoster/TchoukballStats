"""Dialog windows: Settings, generic editors, roster management, and statistics views."""

import sqlite3
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, colorchooser, StringVar, Toplevel
from config import (BG, SURFACE, SURFACE_2, STRIPE, BORDER, FG, MUTED, ACCENT, ACCENT_HI, DANGER,
                    DANGER_BG, FONT, F_TITLE, F_BODY, F_SMALL, F_CAPS, DEFAULT_SETTINGS, MAX_BACKUPS, BACKUPS_DIR)
from database import connect_db, backup_db, open_backups_folder, save_settings
from models import (parse_period_count, parse_period_count_or_none, compute_elo, compute_draw_rate, 
                    predict_match, CompareFilters, team_points_sql, club_points_sql, player_points_sql)
from ui_components import center_window, make_button, make_small_button, attach_autofit


def open_settings_dialog(root, settings, refresh_cb, rebuild_cb, status_cb):
    win = Toplevel(root)
    win.title("Settings")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.transient(root)
    win.grab_set()
    win.bind("<Escape>", lambda e: win.destroy())

    body = tk.Frame(win, bg=BG, padx=24, pady=22)
    body.pack(fill="both", expand=True)

    tk.Label(body, text="Settings", bg=BG, fg=FG, font=F_TITLE).pack(anchor="w")
    tk.Label(body, text="Configure match scoring, card layout, colors, and backups.", bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 16))

    win_var = StringVar(value=str(settings.get("win_points", 3)))
    draw_var = StringVar(value=str(settings.get("draw_points", 1)))
    loss_var = StringVar(value=str(settings.get("loss_points", 0)))

    # --- Section: Match Points ---
    tk.Label(body, text="LEAGUE POINTS CONFIGURATION", bg=BG, fg=MUTED, font=F_CAPS).pack(anchor="w", pady=(0, 6))
    pts_frame = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1, padx=12, pady=12)
    pts_frame.pack(fill="x", pady=(0, 14))

    for i, (lbl, var) in enumerate((("Win Points", win_var), ("Draw Points", draw_var), ("Loss Points", loss_var))):
        row_frame = tk.Frame(pts_frame, bg=SURFACE)
        row_frame.pack(fill="x", pady=4)
        tk.Label(row_frame, text=lbl, bg=SURFACE, fg=FG, font=F_BODY, width=12, anchor="w").pack(side="left")
        tk.Entry(row_frame, textvariable=var, bg=BG, fg=FG, insertbackground=FG, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, font=F_BODY, width=8).pack(side="left", ipady=4, padx=4)

    # --- Section: Action Card Order ---
    tk.Label(body, text="ACTION CARD ORDER", bg=BG, fg=MUTED, font=F_CAPS).pack(anchor="w", pady=(0, 6))
    order_frame = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1, padx=12, pady=12)
    order_frame.pack(fill="x", pady=(0, 14))

    card_options = ["BROWSE", "ADD", "EDIT", "REMOVE"]
    current_order = settings.get("action_card_order", ["BROWSE", "ADD", "EDIT", "REMOVE"])
    
    order_vars = []
    for i in range(4):
        row_f = tk.Frame(order_frame, bg=SURFACE)
        row_f.pack(fill="x", pady=3)
        tk.Label(row_f, text=f"Position {i+1}", bg=SURFACE, fg=FG, font=F_BODY, width=12, anchor="w").pack(side="left")
        
        initial_val = current_order[i] if i < len(current_order) else card_options[i]
        cb_var = StringVar(value=initial_val)
        combo = ttk.Combobox(row_f, values=card_options, textvariable=cb_var, state="readonly", font=F_BODY, width=15)
        combo.pack(side="left", padx=4)
        order_vars.append(cb_var)

    # --- Section: Theme & Colors ---
    tk.Label(body, text="THEME & COLORS", bg=BG, fg=MUTED, font=F_CAPS).pack(anchor="w", pady=(0, 6))
    color_frame = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1, padx=12, pady=12)
    color_frame.pack(fill="x", pady=(0, 14))

    if "section_bg" not in settings:
        settings["section_bg"] = dict(DEFAULT_SETTINGS.get("section_bg", {"actions": SURFACE}))
    if "main_bg" not in settings:
        settings["main_bg"] = DEFAULT_SETTINGS.get("main_bg", BG)

    action_bg_var = StringVar(value=settings["section_bg"].get("actions", SURFACE))
    main_bg_var = StringVar(value=settings.get("main_bg", BG))

    def pick_color(var, preview_lbl, title):
        chosen = colorchooser.askcolor(initialcolor=var.get(), title=title, parent=win)
        if chosen[1]:
            var.set(chosen[1])
            preview_lbl.configure(bg=chosen[1])

    # Action Card BG row
    ac_row = tk.Frame(color_frame, bg=SURFACE)
    ac_row.pack(fill="x", pady=4)
    tk.Label(ac_row, text="Action Card BG", bg=SURFACE, fg=FG, font=F_BODY, width=14, anchor="w").pack(side="left")
    action_preview = tk.Label(ac_row, text="", bg=action_bg_var.get(), width=4, relief="solid", bd=1)
    action_preview.pack(side="left", padx=(0, 8), ipady=4)
    make_small_button(ac_row, "Pick Color...", lambda: pick_color(action_bg_var, action_preview, "Choose Action Card Color")).pack(side="left")

    # Main BG row
    mb_row = tk.Frame(color_frame, bg=SURFACE)
    mb_row.pack(fill="x", pady=4)
    tk.Label(mb_row, text="Main Background", bg=SURFACE, fg=FG, font=F_BODY, width=14, anchor="w").pack(side="left")
    main_preview = tk.Label(mb_row, text="", bg=main_bg_var.get(), width=4, relief="solid", bd=1)
    main_preview.pack(side="left", padx=(0, 8), ipady=4)
    make_small_button(mb_row, "Pick Color...", lambda: pick_color(main_bg_var, main_preview, "Choose Main Background Color")).pack(side="left")

    def reset_colors():
        default_act = DEFAULT_SETTINGS.get("section_bg", {}).get("actions", SURFACE)
        default_main = DEFAULT_SETTINGS.get("main_bg", BG)
        action_bg_var.set(default_act)
        action_preview.configure(bg=default_act)
        main_bg_var.set(default_main)
        main_preview.configure(bg=default_main)

    reset_row = tk.Frame(color_frame, bg=SURFACE)
    reset_row.pack(fill="x", pady=(8, 0))
    make_small_button(reset_row, "↺ Reset Colors to Default", reset_colors, danger=True).pack(anchor="w")

    # --- Section: Database Maintenance ---
    tk.Label(body, text="DATABASE & BACKUPS", bg=BG, fg=MUTED, font=F_CAPS).pack(anchor="w", pady=(0, 6))
    db_frame = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1, padx=12, pady=12)
    db_frame.pack(fill="x", pady=(0, 16))

    def trigger_backup():
        path = backup_db("manual")
        if path:
            messagebox.showinfo("Backup Successful", f"Database backed up successfully to:\n{path}", parent=win)
            status_cb("Manual database backup created.")
        else:
            messagebox.showerror("Backup Failed", "Could not create database backup.", parent=win)

    db_actions = tk.Frame(db_frame, bg=SURFACE)
    db_actions.pack(fill="x")
    make_button(db_actions, "Create Backup Now", trigger_backup, accent=False, anchor="center").pack(side="left", padx=(0, 8))
    make_button(db_actions, "Open Backups Folder", open_backups_folder, accent=False, anchor="center").pack(side="left")

    # --- Save / Cancel Actions ---
    actions = tk.Frame(body, bg=BG)
    actions.pack(fill="x", pady=(10, 0))

    def save_and_close():
        try:
            new_order = [v.get() for v in order_vars]
            if len(set(new_order)) != 4:
                messagebox.showwarning("Invalid Layout", "Each action card position must be unique.", parent=win)
                return

            settings["win_points"] = int(win_var.get())
            settings["draw_points"] = int(draw_var.get())
            settings["loss_points"] = int(loss_var.get())
            settings["action_card_order"] = new_order
            settings["section_bg"]["actions"] = action_bg_var.get()
            settings["main_bg"] = main_bg_var.get()
        except ValueError:
            messagebox.showwarning("Invalid Input", "Points must be valid integers.", parent=win)
            return
        save_settings(settings)
        rebuild_cb()
        status_cb("Settings saved successfully.")
        win.destroy()

    make_button(actions, "Save Changes", save_and_close, accent=True, anchor="center").pack(side="right")
    make_button(actions, "Cancel", win.destroy, anchor="center").pack(side="right", padx=(0, 8))


def make_form(root, title, subtitle, fields, on_submit, extra_builder=None):
    win = Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    win.resizable(False, False)
    win.bind("<Escape>", lambda e: win.destroy())
    body = tk.Frame(win, bg=BG, padx=24, pady=22)
    body.pack(fill="both", expand=True)
    tk.Label(body, text=title, bg=BG, fg=FG, font=F_TITLE).pack(anchor="w")
    tk.Label(body, text=subtitle, bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 6))
    
    widgets = {}
    for field in fields:
        tk.Label(body, text=field["label"], bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(10, 4))
        if field.get("values") is not None:
            w = ttk.Combobox(body, values=field["values"], state="readonly", font=F_BODY, height=10)
            w.pack(fill="x")
        else:
            w = tk.Entry(body, bg=SURFACE, fg=FG, insertbackground=FG, relief="flat",
                         highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, font=F_BODY, width=36)
            w.pack(fill="x", ipady=7)
        widgets[field["key"]] = w
        if field.get("initial"):
            w.set(str(field["initial"])) if field.get("values") else w.insert(0, str(field["initial"]))

    if extra_builder:
        extra_builder(win, body, widgets)

    def submit():
        values = {}
        for field in fields:
            v = widgets[field["key"]].get().strip()
            if field.get("required") and not v:
                messagebox.showwarning("Missing value", f"{field['label']} is required.", parent=win)
                return
            values[field["key"]] = v
        if on_submit(values) is not False:
            win.destroy()

    actions = tk.Frame(body, bg=BG)
    actions.pack(fill="x", pady=(20, 0))
    make_button(actions, "Save", submit, accent=True, anchor="center").pack(side="right")
    make_button(actions, "Cancel", win.destroy, anchor="center").pack(side="right", padx=(0, 8))

def open_match_roster_dialog(root, match_id, status_cb):
    win = Toplevel(root)
    win.title(f"Manage Roster for Match #{match_id}")
    win.configure(bg=BG)
    win.geometry("500x450")
    win.transient(root)
    win.grab_set()

    body = tk.Frame(win, bg=BG, padx=16, pady=16)
    body.pack(fill="both", expand=True)

    tk.Label(body, text=f"Match #{match_id} Roster", bg=BG, fg=FG, font=F_TITLE).pack(anchor="w", pady=(0, 4))
    tk.Label(body, text="Assign players to this match.", bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(0, 12))

    # Fetch match teams and players
    with connect_db() as conn:
        match_info = conn.execute("SELECT MatchHome, MatchAway FROM Matches WHERE MatchID = ?", (match_id,)).fetchone()
        if not match_info:
            messagebox.showerror("Error", "Match not found.", parent=win)
            win.destroy()
            return
        home_id, away_id = match_info
        
        # Get players belonging to home or away teams
        players = conn.execute("""
            SELECT p.PlayerID, p.PlayerName || ' ' || COALESCE(p.PlayerSurname,''), t.TeamName,
                   EXISTS(SELECT 1 FROM MatchRoster mr WHERE mr.MatchID = ? AND mr.PlayerID = p.PlayerID) as is_rostered
            FROM Players p
            JOIN Teams t ON p.TeamID = t.TeamID
            WHERE p.TeamID IN (?, ?)
        """, (match_id, home_id, away_id)).fetchall()

    shell = tk.Frame(body, bg=BORDER)
    shell.pack(fill="both", expand=True, pady=(0, 12))

    tree = ttk.Treeview(shell, columns=("ID", "Player", "Team", "Rostered"), show="headings", selectmode="browse")
    scroll = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
    tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)

    tree.heading("ID", text="ID")
    tree.heading("Player", text="Player Name")
    tree.heading("Team", text="Team")
    tree.heading("Rostered", text="Status")
    tree.column("ID", width=40, anchor="w")
    tree.column("Player", width=180, anchor="w")
    tree.column("Team", width=120, anchor="w")
    tree.column("Rostered", width=80, anchor="center")

    def load_tree():
        tree.delete(*tree.get_children())
        with connect_db() as conn:
            rows = conn.execute("""
                SELECT p.PlayerID, p.PlayerName || ' ' || COALESCE(p.PlayerSurname,''), t.TeamName,
                       CASE WHEN EXISTS(SELECT 1 FROM MatchRoster mr WHERE mr.MatchID = ? AND mr.PlayerID = p.PlayerID) 
                            THEN 'In Roster' ELSE '-' END as status, t.TeamID
                FROM Players p
                JOIN Teams t ON p.TeamID = t.TeamID
                WHERE p.TeamID IN (?, ?)
            """, (match_id, home_id, away_id)).fetchall()
        for r in rows:
            tree.insert("", "end", values=(r[0], r[1], r[2], r[3]), tags=(r[4],))

    load_tree()

    def toggle_roster():
        selected = tree.selection()
        if not selected:
            return
        item_vals = tree.item(selected[0], "values")
        player_id = int(item_vals[0])
        team_id = [r[4] for r in tree.get_children("") if tree.item(r, "values")[0] == str(player_id)] # get team id
        
        with connect_db() as conn:
            exists = conn.execute("SELECT 1 FROM MatchRoster WHERE MatchID = ? AND PlayerID = ?", (match_id, player_id)).fetchone()
            if exists:
                conn.execute("DELETE FROM MatchRoster WHERE MatchID = ? AND PlayerID = ?", (match_id, player_id))
                status_cb("Player removed from match roster.")
            else:
                # Need team_id for the player
                t_row = conn.execute("SELECT TeamID FROM Players WHERE PlayerID = ?", (player_id,)).fetchone()
                conn.execute("INSERT INTO MatchRoster (MatchID, TeamID, PlayerID, PlayerPoints) VALUES (?, ?, ?, 0)", 
                             (match_id, t_row[0], player_id))
                status_cb("Player added to match roster.")
        load_tree()

    btn_frame = tk.Frame(body, bg=BG)
    btn_frame.pack(fill="x")
    make_button(btn_frame, "Toggle Roster Status", toggle_roster, accent=True).pack(side="left")
    make_small_button(btn_frame, "Close", win.destroy).pack(side="right")