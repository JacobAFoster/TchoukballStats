"""Main application entry point and main window layout for Tchoukball Stats."""

import datetime
import tkinter as tk
from tkinter import ttk, StringVar, messagebox
from config import BG, BORDER, FG, MUTED, ACCENT, FONT, F_SMALL, F_TITLE, F_CAPS, STRIPE, SURFACE
from database import (init_db, load_settings, save_settings, connect_db, 
                      add_club, add_team, add_player, add_tournament, add_match,
                      delete_club, delete_team, delete_player, delete_tournament, delete_match,
                      update_club, update_team, update_player, update_tournament, update_match)
from ui_components import center_window, apply_theme, make_small_button, card_frame
from dialogs import open_settings_dialog, make_form, open_match_roster_dialog


class TchoukballStatsApp:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.settings["layout_order"] = ["actions"]
        self.status_job = None

        init_db()
        self.setup_window()
        self.setup_ui()
        self.rebuild_sections()

    def setup_window(self):
        self.root.title("Tchoukball Stats")
        self.root.configure(bg=BG)
        center_window(self.root, 1000, 780)
        self.root.minsize(900, 640)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        apply_theme(self.root)

    def setup_ui(self):
        header = tk.Frame(self.root, bg=BG)
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 6))

        header_text = tk.Frame(header, bg=BG)
        header_text.pack(side="left")
        tk.Label(header_text, text="Tchoukball Stats", bg=BG, fg=FG, font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(header_text, text="Manage teams, matches and tournaments.", bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(2, 0))

        self.focus_badge_lbl = tk.Label(header_text, text="", bg=BG, fg=ACCENT, font=F_SMALL)
        self.focus_badge_lbl.pack(anchor="w", pady=(2, 0))

        make_small_button(header, "⚙ Settings", self.open_settings).pack(side="right", anchor="n")
        self._update_focus_badge()

        tk.Frame(self.root, bg=BORDER, height=1).grid(row=1, column=0, sticky="ew", padx=22)

        self.content_area = tk.Frame(self.root, bg=BG)
        self.content_area.grid(row=2, column=0, sticky="nsew")
        self.content_area.columnconfigure(0, weight=1)

        self.status_var = StringVar()
        self.status_lbl = tk.Label(self.root, textvariable=self.status_var, bg=BG, fg=MUTED, font=F_SMALL, anchor="w", padx=22, pady=6)
        self.status_lbl.grid(row=3, column=0, sticky="ew")

        self.root.bind("<<DataChanged>>", lambda e: self.refresh_dashboard())
        self.root.bind("<Control-q>", lambda e: self.root.destroy())

    def set_status(self, message, error=False):
        self.status_var.set(message)
        self.status_lbl.configure(fg="#ff6b6b" if error else MUTED)
        if self.status_job:
            self.root.after_cancel(self.status_job)
        self.status_job = self.root.after(6000, lambda: self.status_var.set(""))

    def open_settings(self):
        open_settings_dialog(self.root, self.settings, self.refresh_dashboard, self.rebuild_sections, self.set_status)

    def _update_focus_badge(self):
        tid = self.settings.get("focus_tournament_id")
        if tid is None:
            self.focus_badge_lbl.configure(text="")
            return
        with connect_db() as conn:
            row = conn.execute("SELECT TournamentName FROM Tournaments WHERE TournamentID = ?", (tid,)).fetchone()
        if not row:
            self.settings["focus_tournament_id"] = None
            save_settings(self.settings)
            self.focus_badge_lbl.configure(text="")
            return
        self.focus_badge_lbl.configure(text=f"⭐ Focus: {row[0]}")

    # --- Generic Browser Dialog ---
    def open_browser_window(self, title, columns, query, on_right_click=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=BG)
        win.geometry("680x440")
        win.transient(self.root)
        win.grab_set()

        body = tk.Frame(win, bg=BG, padx=16, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=title, bg=BG, fg=FG, font=F_TITLE).pack(anchor="w", pady=(0, 4))
        if on_right_click:
            tk.Label(body, text="💡 Tip: Right-click any row for more options.", bg=BG, fg=MUTED, font=F_SMALL).pack(anchor="w", pady=(0, 10))
        else:
            tk.Label(body, text="", bg=BG, fg=BG, font=F_SMALL).pack(anchor="w", pady=(0, 10))

        shell = tk.Frame(body, bg=BORDER)
        shell.pack(fill="both", expand=True, pady=(0, 12))

        tree = ttk.Treeview(shell, columns=columns, show="headings", selectmode="browse")
        scroll = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
        tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)

        for col in columns:
            tree.heading(col, text=col, anchor="w")
            tree.column(col, width=120, anchor="w")

        tree.tag_configure("row_even", background=SURFACE)
        tree.tag_configure("row_odd", background=STRIPE)

        with connect_db() as conn:
            rows = conn.execute(query).fetchall()
        for i, r in enumerate(rows):
            tree.insert("", "end", values=r, tags=("row_even" if i % 2 == 0 else "row_odd",))

        if on_right_click:
            def show_context_menu(event):
                item = tree.identify_row(event.y)
                if item:
                    tree.selection_set(item)
                    row_values = tree.item(item, "values")
                    menu = tk.Menu(win, tearoff=0, bg=SURFACE, fg=FG)
                    on_right_click(menu, row_values, win)
                    menu.tk_popup(event.x_root, event.y_root)

            tree.bind("<Button-3>", show_context_menu)
            tree.bind("<Button-2>", show_context_menu)

        actions = tk.Frame(body, bg=BG)
        actions.pack(fill="x")
        make_small_button(actions, "Close", win.destroy).pack(side="right")

    # --- Player Profile Window ---
    def show_player_profile(self, player_id):
        with connect_db() as conn:
            p = conn.execute("""
                SELECT p.PlayerName, p.PlayerSurname, p.TeamID, COALESCE(t.TeamName, 'None'), 
                       COALESCE(c.ClubName, 'None'), COALESCE(p.PlayerBirthdate, 'Not Specified')
                FROM Players p
                LEFT JOIN Teams t ON p.TeamID = t.TeamID
                LEFT JOIN Clubs c ON t.ClubID = c.ClubID
                WHERE p.PlayerID = ?
            """, (player_id,)).fetchone()
            
            matches = conn.execute("""
                SELECT m.MatchID, 
                       t1.TeamName || ' vs ' || t2.TeamName, 
                       COALESCE(m.MatchDate, 'No Date'),
                       m.MatchHome, m.MatchAway
                FROM MatchRoster mr
                JOIN Matches m ON mr.MatchID = m.MatchID
                JOIN Teams t1 ON m.MatchHome = t1.TeamID
                JOIN Teams t2 ON m.MatchAway = t2.TeamID
                WHERE mr.PlayerID = ?
            """, (player_id,)).fetchall()

        if not p:
            messagebox.showerror("Error", "Player not found.", parent=self.root)
            return

        player_team_id = p[2]
        appearances = len(matches)

        # Calculates match goals if present in schema, default fallback
        match_scores = []
        wins, losses, draws = 0, 0, 0

        for m in matches:
            goals = m[5] if len(m) > 5 else 0
            match_scores.append((m[1], m[2], goals))
            
            # Record calculation if scores exist on match
            if len(m) > 7 and m[6] is not None and m[7] is not None:
                home_score, away_score = m[6], m[7]
                if player_team_id == m[3]:  # Player is on Home team
                    if home_score > away_score: wins += 1
                    elif home_score < away_score: losses += 1
                    else: draws += 1
                elif player_team_id == m[4]:  # Player is on Away team
                    if away_score > home_score: wins += 1
                    elif away_score < home_score: losses += 1
                    else: draws += 1

        total_goals = sum(s[2] for s in match_scores) if appearances > 0 else 0
        avg_goals = round(total_goals / appearances, 1) if appearances > 0 else 0.0

        highest_game = max(match_scores, key=lambda x: x[2]) if match_scores else None
        lowest_game = min(match_scores, key=lambda x: x[2]) if match_scores else None

        win = tk.Toplevel(self.root)
        win.title(f"Player Profile: {p[0]} {p[1] or ''}")
        win.configure(bg=BG)
        win.geometry("580x620")
        win.transient(self.root)
        win.grab_set()

        body = tk.Frame(win, bg=BG, padx=16, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=f"👤 {p[0]} {p[1] or ''}", bg=BG, fg=FG, font=F_TITLE).pack(anchor="w", pady=(0, 10))

        details_frame = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=14)
        details_frame.pack(fill="x", pady=(0, 14))

        # Profile Details Grid
        tk.Label(details_frame, text=f"Club: {p[4]}", bg=SURFACE, fg=FG, font=(FONT, 10)).grid(row=0, column=0, sticky="w", pady=3, padx=6)
        tk.Label(details_frame, text=f"Team: {p[3]}", bg=SURFACE, fg=FG, font=(FONT, 10)).grid(row=0, column=1, sticky="w", pady=3, padx=6)
        
        tk.Label(details_frame, text=f"Birthdate: {p[5]}", bg=SURFACE, fg=FG, font=(FONT, 10)).grid(row=1, column=0, sticky="w", pady=3, padx=6)
        tk.Label(details_frame, text="Position: Shooter / Wing", bg=SURFACE, fg=FG, font=(FONT, 10)).grid(row=1, column=1, sticky="w", pady=3, padx=6)

        tk.Label(details_frame, text=f"Appearances: {appearances}", bg=SURFACE, fg=FG, font=(FONT, 10)).grid(row=2, column=0, sticky="w", pady=3, padx=6)
        tk.Label(details_frame, text=f"Win/Loss Record: {wins}W - {losses}L - {draws}D", bg=SURFACE, fg=FG, font=(FONT, 10)).grid(row=2, column=1, sticky="w", pady=3, padx=6)

        tk.Label(details_frame, text=f"Total Points: {total_goals}", bg=SURFACE, fg=ACCENT, font=(FONT, 10, "bold")).grid(row=3, column=0, sticky="w", pady=(8, 3), padx=6)
        tk.Label(details_frame, text=f"Avg Points/Match: {avg_goals}", bg=SURFACE, fg=ACCENT, font=(FONT, 10, "bold")).grid(row=3, column=1, sticky="w", pady=(8, 3), padx=6)

        high_text = f"{highest_game[2]} pts ({highest_game[0]})" if highest_game else "N/A"
        low_text = f"{lowest_game[2]} pts ({lowest_game[0]})" if lowest_game else "N/A"

        tk.Label(details_frame, text=f"🔥 Highest Score: {high_text}", bg=SURFACE, fg=FG, font=(FONT, 9)).grid(row=4, column=0, columnspan=2, sticky="w", pady=3, padx=6)
        tk.Label(details_frame, text=f"❄️ Lowest Score: {low_text}", bg=SURFACE, fg=FG, font=(FONT, 9)).grid(row=5, column=0, columnspan=2, sticky="w", pady=3, padx=6)

        tk.Label(body, text="Match Roster History", bg=BG, fg=FG, font=(FONT, 11, "bold")).pack(anchor="w", pady=(0, 6))

        shell = tk.Frame(body, bg=BORDER)
        shell.pack(fill="both", expand=True, pady=(0, 12))

        tree = ttk.Treeview(shell, columns=["Match", "Date", "Points"], show="headings", selectmode="browse")
        scroll = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y", padx=(0, 1), pady=1)
        tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)

        tree.heading("Match", text="Matchup", anchor="w")
        tree.heading("Date", text="Date", anchor="w")
        tree.heading("Points", text="Points", anchor="w")
        
        tree.column("Match", width=260, anchor="w")
        tree.column("Date", width=110, anchor="w")
        tree.column("Points", width=70, anchor="w")

        tree.tag_configure("row_even", background=SURFACE)
        tree.tag_configure("row_odd", background=STRIPE)

        for i, m in enumerate(match_scores):
            tree.insert("", "end", values=(m[0], m[1], m[2]), tags=("row_even" if i % 2 == 0 else "row_odd",))

        actions = tk.Frame(body, bg=BG)
        actions.pack(fill="x")
        make_small_button(actions, "Close", win.destroy).pack(side="right")

    # --- Browse Handlers ---
    def browse_teams(self):
        self.open_browser_window("Browse Teams", ["ID", "Team Name", "Club ID"], "SELECT TeamID, TeamName, ClubID FROM Teams")

    def browse_clubs(self):
        self.open_browser_window("Browse Clubs", ["ID", "Club Name"], "SELECT ClubID, ClubName FROM Clubs")

    def browse_players(self):
        query = """
            SELECT p.PlayerID, p.PlayerName, COALESCE(p.PlayerSurname, ''), COALESCE(t.TeamName, 'No Team') 
            FROM Players p
            LEFT JOIN Teams t ON p.TeamID = t.TeamID
        """
        columns = ["ID", "First Name", "Surname", "Team"]

        def player_right_click(menu, row_values, window):
            player_id = row_values[0]
            player_name = f"{row_values[1]} {row_values[2]}"
            menu.add_command(label=f"👤 View Profile: {player_name}", command=lambda: [window.destroy(), self.show_player_profile(player_id)])

        self.open_browser_window("Browse Players", columns, query, on_right_click=player_right_click)

    def browse_tournaments(self):
        self.open_browser_window("Browse Tournaments", ["ID", "Name", "Date", "Location"], "SELECT TournamentID, TournamentName, TournamentDate, TournamentLocation FROM Tournaments")

    def browse_matches(self):
        self.open_browser_window("Browse Matches", ["ID", "Home ID", "Away ID", "Date", "Tournament ID"], "SELECT MatchID, MatchHome, MatchAway, MatchDate, TournamentID FROM Matches")

    def browse_rosters(self):
        self.open_browser_window("View Rosters", ["Match ID", "Player Name", "Team"], """
            SELECT m.MatchID, p.PlayerName || ' ' || COALESCE(p.PlayerSurname,''), t.TeamName 
            FROM MatchRoster mr
            JOIN Players p ON mr.PlayerID = p.PlayerID
            JOIN Matches m ON mr.MatchID = m.MatchID
            JOIN Teams t ON p.TeamID = t.TeamID
        """)

    # --- ADD Form Prompts ---
    def prompt_add_club(self):
        def on_submit(values):
            try:
                add_club(values["name"])
                self.set_status("Club added successfully.")
                self.root.event_generate("<<DataChanged>>")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
        make_form(self.root, "Add Club", "Enter the new club name.", [
            {"label": "Club Name", "key": "name", "required": True}
        ], on_submit)

    def prompt_add_team(self):
        with connect_db() as conn:
            clubs = conn.execute("SELECT ClubID, ClubName FROM Clubs").fetchall()
        club_map = {c[1]: c[0] for c in clubs}
        club_names = ["(None)"] + list(club_map.keys())

        def on_submit(values):
            try:
                c_id = club_map.get(values["club"]) if values["club"] != "(None)" else None
                add_team(values["name"], c_id)
                self.set_status("Team added successfully.")
                self.root.event_generate("<<DataChanged>>")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)

        make_form(self.root, "Add Team", "Enter team details.", [
            {"label": "Team Name", "key": "name", "required": True},
            {"label": "Club", "key": "club", "values": club_names, "initial": club_names[0]}
        ], on_submit)

    def prompt_add_player(self):
        with connect_db() as conn:
            teams = conn.execute("SELECT TeamID, TeamName FROM Teams").fetchall()
        team_map = {t[1]: t[0] for t in teams}
        team_names = ["(None)"] + list(team_map.keys())

        def on_submit(values):
            try:
                t_id = team_map.get(values["team"]) if values["team"] != "(None)" else None
                add_player(values["fname"], values["lname"], t_id, values["birthdate"] or None)
                self.set_status("Player added successfully.")
                self.root.event_generate("<<DataChanged>>")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)

        make_form(self.root, "Add Player", "Enter player details.", [
            {"label": "First Name", "key": "fname", "required": True},
            {"label": "Surname", "key": "lname"},
            {"label": "Team", "key": "team", "values": team_names, "initial": team_names[0]},
            {"label": "Birthdate (YYYY-MM-DD)", "key": "birthdate"}
        ], on_submit)

    def prompt_add_tournament(self):
        def on_submit(values):
            try:
                add_tournament(values["name"], values["date"] or None, values["location"] or None)
                self.set_status("Tournament added successfully.")
                self.root.event_generate("<<DataChanged>>")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)

        make_form(self.root, "Add Tournament", "Enter tournament details.", [
            {"label": "Tournament Name", "key": "name", "required": True},
            {"label": "Date (YYYY-MM-DD)", "key": "date"},
            {"label": "Location", "key": "location"}
        ], on_submit)

    def prompt_add_match(self):
        with connect_db() as conn:
            teams = conn.execute("SELECT TeamID, TeamName FROM Teams").fetchall()
            tourns = conn.execute("SELECT TournamentID, TournamentName FROM Tournaments").fetchall()
        
        team_map = {t[1]: t[0] for t in teams}
        team_names = list(team_map.keys())
        if not team_names:
            messagebox.showwarning("Missing Teams", "Please add at least two teams before creating a match.")
            return

        tourn_map = {t[1]: t[0] for t in tourns}
        tourn_names = ["(None)"] + list(tourn_map.keys())

        def on_submit(values):
            try:
                h_id = team_map[values["home"]]
                a_id = team_map[values["away"]]
                if h_id == a_id:
                    raise ValueError("Home and Away teams must be different.")
                t_id = tourn_map.get(values["tourn"]) if values["tourn"] != "(None)" else None
                p_count = int(values["periods"]) if values["periods"].isdigit() else 2
                p_mins = int(values["minutes"]) if values["minutes"].isdigit() else 10
                
                add_match(h_id, a_id, values["location"] or None, t_id, values["date"] or None, p_count, p_mins)
                self.set_status("Match added successfully.")
                self.root.event_generate("<<DataChanged>>")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)

        make_form(self.root, "Add Match", "Enter match fixture details.", [
            {"label": "Home Team", "key": "home", "values": team_names, "initial": team_names[0]},
            {"label": "Away Team", "key": "away", "values": team_names, "initial": team_names[min(1, len(team_names)-1)]},
            {"label": "Tournament", "key": "tourn", "values": tourn_names, "initial": tourn_names[0]},
            {"label": "Date (YYYY-MM-DD)", "key": "date"},
            {"label": "Location", "key": "location"},
            {"label": "Period Count", "key": "periods", "initial": "2"},
            {"label": "Period Minutes", "key": "minutes", "initial": "10"}
        ], on_submit)

    # --- Remove Handlers ---
    def remove_item_prompt(self, title, query, delete_cb):
        with connect_db() as conn:
            items = conn.execute(query).fetchall()
        if not items:
            messagebox.showinfo("Empty", f"No {title.lower()}s available to remove.", parent=self.root)
            return

        item_map = {str(row[1]): row[0] for row in items}
        item_names = list(item_map.keys())

        def on_submit(values):
            name = values["item"]
            item_id = item_map.get(name)
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{name}'?", parent=self.root):
                try:
                    delete_cb(item_id)
                    self.set_status(f"{title} removed successfully.")
                    self.root.event_generate("<<DataChanged>>")
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=self.root)

        make_form(self.root, f"Remove {title}", f"Select {title.lower()} to remove.", [
            {"label": title, "key": "item", "values": item_names, "initial": item_names[0]}
        ], on_submit)

    # --- Edit Handlers ---
    def edit_selector(self, title, query, edit_callback):
        with connect_db() as conn:
            items = conn.execute(query).fetchall()
        if not items:
            messagebox.showinfo("Empty", f"No {title.lower()}s available to edit.", parent=self.root)
            return
        item_map = {str(row[1]): row[0] for row in items}
        item_names = list(item_map.keys())

        def on_submit(values):
            item_id = item_map.get(values["item"])
            edit_callback(item_id)

        make_form(self.root, f"Edit {title}", f"Select {title.lower()} to edit.", [
            {"label": title, "key": "item", "values": item_names, "initial": item_names[0]}
        ], on_submit)

    def prompt_edit_club(self):
        def do_edit(club_id):
            with connect_db() as conn:
                row = conn.execute("SELECT ClubName FROM Clubs WHERE ClubID = ?", (club_id,)).fetchone()
            def on_submit(values):
                try:
                    update_club(club_id, values["name"])
                    self.set_status("Club updated successfully.")
                    self.root.event_generate("<<DataChanged>>")
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=self.root)
            make_form(self.root, "Edit Club", "Update club name.", [
                {"label": "Club Name", "key": "name", "required": True, "initial": row[0]}
            ], on_submit)
        self.edit_selector("Club", "SELECT ClubID, ClubName FROM Clubs", do_edit)

    def prompt_edit_team(self):
        def do_edit(team_id):
            with connect_db() as conn:
                team = conn.execute("SELECT TeamName, ClubID FROM Teams WHERE TeamID = ?", (team_id,)).fetchone()
                clubs = conn.execute("SELECT ClubID, ClubName FROM Clubs").fetchall()
            club_map = {c[1]: c[0] for c in clubs}
            club_names = ["(None)"] + list(club_map.keys())
            current_club_name = "(None)"
            for cn, cid in club_map.items():
                if cid == team[1]:
                    current_club_name = cn
                    break

            def on_submit(values):
                try:
                    c_id = club_map.get(values["club"]) if values["club"] != "(None)" else None
                    update_team(team_id, values["name"], c_id)
                    self.set_status("Team updated successfully.")
                    self.root.event_generate("<<DataChanged>>")
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=self.root)

            make_form(self.root, "Edit Team", "Update team details.", [
                {"label": "Team Name", "key": "name", "required": True, "initial": team[0]},
                {"label": "Club", "key": "club", "values": club_names, "initial": current_club_name}
            ], on_submit)
        self.edit_selector("Team", "SELECT TeamID, TeamName FROM Teams", do_edit)

    def prompt_edit_player(self):
        def do_edit(player_id):
            with connect_db() as conn:
                p = conn.execute("SELECT PlayerName, PlayerSurname, TeamID, PlayerBirthdate FROM Players WHERE PlayerID = ?", (player_id,)).fetchone()
                teams = conn.execute("SELECT TeamID, TeamName FROM Teams").fetchall()
            team_map = {t[1]: t[0] for t in teams}
            team_names = ["(None)"] + list(team_map.keys())
            cur_team = "(None)"
            for tn, tid in team_map.items():
                if tid == p[2]:
                    cur_team = tn
                    break

            def on_submit(values):
                try:
                    t_id = team_map.get(values["team"]) if values["team"] != "(None)" else None
                    update_player(player_id, values["fname"], values["lname"], t_id, values["birthdate"] or None)
                    self.set_status("Player updated successfully.")
                    self.root.event_generate("<<DataChanged>>")
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=self.root)

            make_form(self.root, "Edit Player", "Update player details.", [
                {"label": "First Name", "key": "fname", "required": True, "initial": p[0]},
                {"label": "Surname", "key": "lname", "initial": p[1] or ""},
                {"label": "Team", "key": "team", "values": team_names, "initial": cur_team},
                {"label": "Birthdate (YYYY-MM-DD)", "key": "birthdate", "initial": p[3] or ""}
            ], on_submit)
        self.edit_selector("Player", "SELECT PlayerID, PlayerName || ' ' || COALESCE(PlayerSurname,'') FROM Players", do_edit)

    def prompt_edit_tournament(self):
        def do_edit(tourn_id):
            with connect_db() as conn:
                t = conn.execute("SELECT TournamentName, TournamentDate, TournamentLocation FROM Tournaments WHERE TournamentID = ?", (tourn_id,)).fetchone()

            def on_submit(values):
                try:
                    update_tournament(tourn_id, values["name"], values["date"] or None, values["location"] or None)
                    self.set_status("Tournament updated successfully.")
                    self.root.event_generate("<<DataChanged>>")
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=self.root)

            make_form(self.root, "Edit Tournament", "Update tournament details.", [
                {"label": "Tournament Name", "key": "name", "required": True, "initial": t[0]},
                {"label": "Date (YYYY-MM-DD)", "key": "date", "initial": t[1] or ""},
                {"label": "Location", "key": "location", "initial": t[2] or ""}
            ], on_submit)
        self.edit_selector("Tournament", "SELECT TournamentID, TournamentName FROM Tournaments", do_edit)

    def prompt_edit_match(self):
        match_query = """
            SELECT m.MatchID, 
                   t1.TeamName || ' vs ' || t2.TeamName || ' (' || COALESCE(m.MatchDate, 'No Date') || ')'
            FROM Matches m
            JOIN Teams t1 ON m.MatchHome = t1.TeamID
            JOIN Teams t2 ON m.MatchAway = t2.TeamID
        """
        def do_edit(match_id):
            with connect_db() as conn:
                m = conn.execute("SELECT MatchHome, MatchAway, MatchLocation, TournamentID, MatchDate, PeriodCount, PeriodMinutes FROM Matches WHERE MatchID = ?", (match_id,)).fetchone()
                teams = conn.execute("SELECT TeamID, TeamName FROM Teams").fetchall()
                tourns = conn.execute("SELECT TournamentID, TournamentName FROM Tournaments").fetchall()

            team_map = {t[1]: t[0] for t in teams}
            team_names = list(team_map.keys())
            if not team_names:
                messagebox.showwarning("Missing Teams", "No teams available.")
                return

            tourn_map = {t[1]: t[0] for t in tourns}
            tourn_names = ["(None)"] + list(tourn_map.keys())

            cur_home, cur_away, cur_tourn = "", "", "(None)"
            for tn, tid in team_map.items():
                if tid == m[0]: cur_home = tn
                if tid == m[1]: cur_away = tn
            for tn, tid in tourn_map.items():
                if tid == m[3]: cur_tourn = tn

            def on_submit(values):
                try:
                    h_id = team_map[values["home"]]
                    a_id = team_map[values["away"]]
                    if h_id == a_id:
                        raise ValueError("Home and Away teams must be different.")
                    t_id = tourn_map.get(values["tourn"]) if values["tourn"] != "(None)" else None
                    p_count = int(values["periods"]) if values["periods"].isdigit() else 2
                    p_mins = int(values["minutes"]) if values["minutes"].isdigit() else 10

                    update_match(match_id, h_id, a_id, values["location"] or None, t_id, values["date"] or None, p_count, p_mins)
                    self.set_status("Match updated successfully.")
                    self.root.event_generate("<<DataChanged>>")
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=self.root)

            make_form(self.root, "Edit Match", "Update match fixture details.", [
                {"label": "Home Team", "key": "home", "values": team_names, "initial": cur_home},
                {"label": "Away Team", "key": "away", "values": team_names, "initial": cur_away},
                {"label": "Tournament", "key": "tourn", "values": tourn_names, "initial": cur_tourn},
                {"label": "Date (YYYY-MM-DD)", "key": "date", "initial": m[4] or ""},
                {"label": "Location", "key": "location", "initial": m[2] or ""},
                {"label": "Period Count", "key": "periods", "initial": str(m[5])},
                {"label": "Period Minutes", "key": "minutes", "initial": str(m[6])}
            ], on_submit)
        
        self.edit_selector("Match", match_query, do_edit)

    def prompt_edit_rosters(self):
        match_query = """
            SELECT m.MatchID, 
                   t1.TeamName || ' vs ' || t2.TeamName || ' (' || COALESCE(m.MatchDate, 'No Date') || ')'
            FROM Matches m
            JOIN Teams t1 ON m.MatchHome = t1.TeamID
            JOIN Teams t2 ON m.MatchAway = t2.TeamID
        """
        def do_edit(match_id):
            open_match_roster_dialog(self.root, match_id, self.set_status)
        
        self.edit_selector("Match Roster", match_query, do_edit)

    def build_actions_section(self, parent):
        main_bg = self.settings.get("main_bg", BG)
        card_bg = self.settings["section_bg"]["actions"]
        title_fg = self.settings["section_title_color"]["actions"]

        action_row = tk.Frame(parent, bg=main_bg)
        
        order = self.settings.get("action_card_order", ["BROWSE", "ADD", "EDIT", "REMOVE"])
        BLOCK_MAP = {
            "BROWSE": [
                ("Teams", self.browse_teams), 
                ("Clubs", self.browse_clubs), 
                ("Players", self.browse_players), 
                ("Rosters", self.browse_rosters), 
                ("Matches", self.browse_matches), 
                ("Tournaments", self.browse_tournaments)
            ],
            "ADD": [
                ("Team", self.prompt_add_team), 
                ("Club", self.prompt_add_club), 
                ("Player", self.prompt_add_player), 
                ("Match", self.prompt_add_match), 
                ("Tournament", self.prompt_add_tournament)
            ],
            "EDIT": [
                ("Teams", self.prompt_edit_team), 
                ("Clubs", self.prompt_edit_club), 
                ("Players", self.prompt_edit_player), 
                ("Matches", self.prompt_edit_match), 
                ("Tournaments", self.prompt_edit_tournament), 
                ("Match rosters", self.prompt_edit_rosters)
            ],
            "REMOVE": [
                ("Team", lambda: self.remove_item_prompt("Team", "SELECT TeamID, TeamName FROM Teams", delete_team)), 
                ("Club", lambda: self.remove_item_prompt("Club", "SELECT ClubID, ClubName FROM Clubs", delete_club)), 
                ("Player", lambda: self.remove_item_prompt("Player", "SELECT PlayerID, PlayerName || ' ' || COALESCE(PlayerSurname,'') FROM Players", delete_player)), 
                ("Match", lambda: self.remove_item_prompt("Match", "SELECT MatchID, 'Match #' || MatchID FROM Matches", delete_match)), 
                ("Tournament", lambda: self.remove_item_prompt("Tournament", "SELECT TournamentID, TournamentName FROM Tournaments", delete_tournament))
            ],
        }

        FUNC_BLOCKS = [(title, BLOCK_MAP[title]) for title in order if title in BLOCK_MAP]

        for i in range(len(FUNC_BLOCKS)):
            action_row.columnconfigure(i, weight=1, uniform="act")

        for i, (title, items) in enumerate(FUNC_BLOCKS):
            padx = (0 if i == 0 else 6, 0 if i == len(FUNC_BLOCKS) - 1 else 6)
            
            card = tk.Frame(action_row, bg=card_bg, highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=padx, pady=0)
            
            inner = tk.Frame(card, bg=card_bg, padx=12, pady=12)
            inner.pack(fill="both", expand=True)

            if title:
                tk.Label(inner, text=title.upper(), bg=card_bg, fg=title_fg, font=F_CAPS).pack(anchor="w", pady=(0, 8))

            for label, cmd in items:
                make_small_button(inner, label, cmd, danger=(title == "REMOVE")).pack(fill="x", pady=2)
                
        return action_row

    def rebuild_sections(self):
        for child in self.content_area.winfo_children():
            child.destroy()

        main_bg = self.settings.get("main_bg", BG)
        self.root.configure(bg=main_bg)
        self.content_area.configure(bg=main_bg)

        builders = {"actions": self.build_actions_section}
        active_layout = [s for s in self.settings["layout_order"] if s in builders]
        
        for i, name in enumerate(active_layout):
            builder = builders.get(name)
            if not builder:
                continue
            frame = builder(self.content_area)
            frame.grid(row=i, column=0, sticky="nsew", padx=22, pady=6)
            self.content_area.rowconfigure(i, weight=0)

        self.refresh_dashboard()

    def refresh_dashboard(self):
        self._update_focus_badge()


if __name__ == "__main__":
    root = tk.Tk()
    app = TchoukballStatsApp(root)
    root.mainloop()