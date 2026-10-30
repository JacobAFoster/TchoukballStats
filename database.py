"""Database connection context, migrations, automated backups, and settings storage."""

import sqlite3
import datetime
import json
import os
import sys
import shutil
from contextlib import contextmanager
from tkinter import messagebox
from config import DB_NAME, SETTINGS_FILE, BACKUPS_DIR, MAX_BACKUPS, DEFAULT_SETTINGS


@contextmanager
def connect_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with connect_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS Clubs (
          ClubID   INTEGER PRIMARY KEY,
          ClubName TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS Teams (
          TeamID   INTEGER PRIMARY KEY,
          TeamName TEXT NOT NULL UNIQUE,
          ClubID   INTEGER REFERENCES Clubs(ClubID)
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

        MIGRATIONS = [
            ("Matches",     "TournamentID",    "ALTER TABLE Matches ADD COLUMN TournamentID INTEGER"),
            ("Matches",     "MatchDate",       "ALTER TABLE Matches ADD COLUMN MatchDate TEXT"),
            ("Teams",       "ClubID",          "ALTER TABLE Teams ADD COLUMN ClubID INTEGER"),
            ("Players",     "TeamID",          "ALTER TABLE Players ADD COLUMN TeamID INTEGER"),
            ("Players",     "PlayerBirthdate", "ALTER TABLE Players ADD COLUMN PlayerBirthdate TEXT"),
            ("MatchRoster", "PlayerPoints",    "ALTER TABLE MatchRoster ADD COLUMN PlayerPoints INTEGER DEFAULT 0"),
            ("Matches",     "PeriodCount",     "ALTER TABLE Matches ADD COLUMN PeriodCount INTEGER"),
            ("Matches",     "PeriodMinutes",   "ALTER TABLE Matches ADD COLUMN PeriodMinutes INTEGER"),
        ]
        for table, column, ddl in MIGRATIONS:
            existing = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
            if column not in existing:
                conn.execute(ddl)

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


def backup_db(reason="auto"):
    if not os.path.exists(DB_NAME):
        return None
    try:
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_reason = "".join(c for c in reason if c.isalnum() or c in "-_")[:20]
        name = f"{stamp}_{safe_reason}.db" if safe_reason else f"{stamp}.db"
        dest = os.path.join(BACKUPS_DIR, name)
        shutil.copy2(DB_NAME, dest)
        entries = sorted(
            (os.path.join(BACKUPS_DIR, f) for f in os.listdir(BACKUPS_DIR) if f.endswith(".db")),
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


def open_backups_folder():
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


def _is_hex_colour(value):
    if not isinstance(value, str):
        return False
    if len(value) not in (4, 7) or not value.startswith("#"):
        return False
    return all(c in "0123456789abcdefABCDEF" for c in value[1:])


def _validate_layout_and_colours(merged):
    valid_sections = ["actions", "dashboard"]
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
            cleaned[section] = colour if _is_hex_colour(colour) else default_colour
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


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError as exc:
        messagebox.showerror("Could not save settings", str(exc))


# --- Inserts ---
def add_club(club_name):
    with connect_db() as conn:
        conn.execute("INSERT INTO Clubs (ClubName) VALUES (?)", (club_name,))

def add_team(team_name, club_id=None):
    with connect_db() as conn:
        conn.execute("INSERT INTO Teams (TeamName, ClubID) VALUES (?, ?)", (team_name, club_id))

def add_player(name, surname, team_id, birthdate):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO Players (PlayerName, PlayerSurname, TeamID, PlayerBirthdate)
            VALUES (?, ?, ?, ?)
        """, (name, surname, team_id, birthdate))

def add_tournament(name, date, location):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO Tournaments (TournamentName, TournamentDate, TournamentLocation)
            VALUES (?, ?, ?)
        """, (name, date, location))

def add_match(home_id, away_id, location, tournament_id, date, period_count, period_minutes):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO Matches (MatchHome, MatchAway, MatchLocation, TournamentID, MatchDate, PeriodCount, PeriodMinutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (home_id, away_id, location, tournament_id, date, period_count, period_minutes))


# --- Deletions ---
def delete_club(club_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM Clubs WHERE ClubID = ?", (club_id,))

def delete_team(team_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM Teams WHERE TeamID = ?", (team_id,))

def delete_player(player_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM Players WHERE PlayerID = ?", (player_id,))

def delete_tournament(tournament_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM Tournaments WHERE TournamentID = ?", (tournament_id,))

def delete_match(match_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM Matches WHERE MatchID = ?", (match_id,))
        conn.execute("DELETE FROM MatchPeriods WHERE MatchID = ?", (match_id,))
        conn.execute("DELETE FROM MatchRoster WHERE MatchID = ?", (match_id,))


# --- Updates ---
def update_club(club_id, name):
    with connect_db() as conn:
        conn.execute("UPDATE Clubs SET ClubName = ? WHERE ClubID = ?", (name, club_id))

def update_team(team_id, name, club_id):
    with connect_db() as conn:
        conn.execute("UPDATE Teams SET TeamName = ?, ClubID = ? WHERE TeamID = ?", (name, club_id, team_id))

def update_player(player_id, fname, lname, team_id, birthdate):
    with connect_db() as conn:
        conn.execute("""
            UPDATE Players 
            SET PlayerName = ?, PlayerSurname = ?, TeamID = ?, PlayerBirthdate = ?
            WHERE PlayerID = ?
        """, (fname, lname, team_id, birthdate, player_id))

def update_tournament(tournament_id, name, date, location):
    with connect_db() as conn:
        conn.execute("""
            UPDATE Tournaments 
            SET TournamentName = ?, TournamentDate = ?, TournamentLocation = ?
            WHERE TournamentID = ?
        """, (name, date, location, tournament_id))

def update_match(match_id, home_id, away_id, location, tournament_id, date, period_count, period_minutes):
    with connect_db() as conn:
        conn.execute("""
            UPDATE Matches 
            SET MatchHome = ?, MatchAway = ?, MatchLocation = ?, TournamentID = ?, MatchDate = ?, PeriodCount = ?, PeriodMinutes = ?
            WHERE MatchID = ?
        """, (home_id, away_id, location, tournament_id, date, period_count, period_minutes, match_id))