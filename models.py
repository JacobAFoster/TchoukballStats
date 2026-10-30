"""Domain logic: Elo ratings, predictions, streaks, points, and period parsers."""

import datetime

DEFAULT_ELO = 1500
ELO_K = 32
PROVISIONAL_K = 64
PROVISIONAL_MATCHES = 10
MARGIN_CAP = 2.0
MARGIN_DIVISOR = 10

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


def parse_period_count(s):
    s = (s or "").strip().lower()
    if not s or s in ("(none)", "none"):
        return 0
    first_word = "".join(ch for ch in s if ch.isalpha())
    if first_word in _WORD_PERIODS:
        return _WORD_PERIODS[first_word]
    num = "".join(ch for ch in s if ch.isdigit())
    return int(num) if num else 0


def parse_period_count_or_none(s):
    n = parse_period_count(s if isinstance(s, str) else str(s or ""))
    return n if n > 0 else None


def team_points_sql(conn, team_id, settings, filters=None):
    f_sql, f_params = filters.sql_fragment("m") if filters else ("", {})
    wp, dp, lp = settings["win_points"], settings["draw_points"], settings["loss_points"]
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


def club_points_sql(conn, club_id, settings, filters=None):
    f_sql, f_params = filters.sql_fragment("m") if filters else ("", {})
    wp, dp, lp = settings["win_points"], settings["draw_points"], settings["loss_points"]
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
    f_sql, f_params = filters.sql_fragment("m") if filters else ("", {})
    return conn.execute(f"""
        SELECT COALESCE(SUM(r.PlayerPoints), 0)
        FROM MatchRoster r
        JOIN Matches m ON m.MatchID = r.MatchID
        WHERE r.PlayerID = :pid
          AND m.MatchHScore IS NOT NULL AND m.MatchAScore IS NOT NULL
          {f_sql}
    """, {"pid": player_id, **f_params}).fetchone()[0]


def _k_for_matches(count):
    if count >= PROVISIONAL_MATCHES:
        return ELO_K
    return PROVISIONAL_K - (PROVISIONAL_K - ELO_K) * (count / PROVISIONAL_MATCHES)


def compute_elo(conn, since_date=None, until_date=None, with_history=False):
    ratings = {tid: DEFAULT_ELO for tid, in conn.execute("SELECT TeamID FROM Teams").fetchall()}
    teams = {tid: name for tid, name in conn.execute("SELECT TeamID, TeamName FROM Teams").fetchall()}
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
    for home, away, hs, a_s, date in conn.execute(query, tuple(params)).fetchall():
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
                upsets.append((rb - ra, teams.get(home, "?"), teams.get(away, "?"), f"{hs}–{a_s}", date))
                stats[home]['upsets_caused'] += 1
                stats[away]['upsets_suffered'] += 1
        elif sa == 0.0:
            stats[home]['losses'] += 1
            stats[away]['wins'] += 1
            if rb < ra:
                upsets.append((ra - rb, teams.get(away, "?"), teams.get(home, "?"), f"{a_s}–{hs}", date))
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
        SELECT SUM(CASE WHEN MatchHScore = MatchAScore THEN 1 ELSE 0 END), COUNT(*)
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
    return (draws / total) if total else 0.25


def predict_match(home_id, away_id, ratings, draw_rate):
    ra = ratings.get(home_id, DEFAULT_ELO)
    rb = ratings.get(away_id, DEFAULT_ELO)
    ea = 1 / (1 + 10 ** ((rb - ra) / 400))
    return (ea * (1 - draw_rate), draw_rate, (1 - ea) * (1 - draw_rate))


def compute_team_streaks(conn):
    teams = {tid: name for tid, name in conn.execute("SELECT TeamID, TeamName FROM Teams").fetchall()}
    results_by_team = {}
    for home, away, hs, a_s in conn.execute("""
        SELECT MatchHome, MatchAway, MatchHScore, MatchAScore
        FROM Matches
        WHERE MatchHScore IS NOT NULL AND MatchAScore IS NOT NULL
        ORDER BY COALESCE(MatchDate, '9999'), MatchID
    """).fetchall():
        results_by_team.setdefault(home, []).append((hs, a_s))
        results_by_team.setdefault(away, []).append((a_s, hs))

    best = {"win": (0, None), "unbeaten": (0, None), "lose": (0, None), "draw": (0, None)}
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
        for cat, val in (("win", top_w), ("unbeaten", top_u), ("lose", top_l), ("draw", top_d)):
            if val > best[cat][0]:
                best[cat] = (val, teams.get(tid, "?"))
    return best