import datetime
import os
import numpy as np
import pandas as pd
import requests
from scipy.stats import nbinom
import streamlit as st

st.set_page_config(
    page_title="Ultimate Mobile Capper Engine", page_icon="🎯", layout="centered"
)

st.title("🎯 Pro Auto-Capping Engine")
st.caption(
    "1,000,000 Sims | Persistent CLV Log | Novig Odds | Dynamic Dispersion"
)

# Initialize Session State
if "sim_data" not in st.session_state:
    st.session_state.sim_data = None

# Plate Appearance Weights for Batting Order 1-9
PA_WEIGHTS = np.array([1.12, 1.08, 1.05, 1.02, 0.98, 0.95, 0.93, 0.90, 0.87])
PA_WEIGHTS = PA_WEIGHTS / np.sum(PA_WEIGHTS)
LEAGUE_AVG_OPS = 0.720
LEAGUE_AVG_ERA = 4.10


# DYNAMIC RUN VARIANCE (OVERDISPERSION) AUTOMATION ENGINE
def calculate_dynamic_dispersion(
    park_factor: float,
    wind_parallel_mph: float,
    home_sp_era: float,
    away_sp_era: float,
    home_sp_ip: float,
    away_sp_ip: float,
    home_bp_rating: float,
    away_bp_rating: float,
) -> float:
    base_dispersion = 1.30
    adj = 0.0

    if park_factor >= 1.10:
        adj += 0.10
    elif park_factor <= 0.93:
        adj -= 0.05

    if wind_parallel_mph >= 8.0:
        adj += 0.05
    elif wind_parallel_mph <= -8.0:
        adj -= 0.03

    avg_era = (home_sp_era + away_sp_era) / 2.0
    avg_ip = (home_sp_ip + away_sp_ip) / 2.0

    if avg_era <= 3.40 and avg_ip >= 5.8:
        adj -= 0.08
    elif avg_era >= 4.70 or avg_ip <= 4.2:
        adj += 0.08

    if max(home_bp_rating, away_bp_rating) >= 1.15:
        adj += 0.05

    final_dispersion = base_dispersion + adj
    return round(min(1.60, max(1.10, final_dispersion)), 2)


# ODDS & BETTING MATH HELPER FUNCTIONS
def american_to_decimal(american_odds: int) -> float:
    if american_odds > 0:
        return 1.0 + (american_odds / 100.0)
    elif american_odds < 0:
        return 1.0 + (100.0 / abs(american_odds))
    return 1.0


def calculate_ev_and_kelly(
    model_prob: float, american_odds: int, kelly_fraction: float = 0.25
):
    if american_odds == 0:
        return 0.0, 0.0, 0.0
    dec_odds = american_to_decimal(american_odds)
    implied_prob = 1.0 / dec_odds
    b = dec_odds - 1.0

    ev = (model_prob * b) - (1.0 - model_prob)
    ev_pct = ev * 100.0

    full_kelly = (b * model_prob - (1.0 - model_prob)) / b if b > 0 else 0.0
    kelly_units = max(0.0, full_kelly * kelly_fraction * 100.0)

    return (
        round(implied_prob * 100.0, 1),
        round(ev_pct, 2),
        round(kelly_units, 2),
    )


# CLOSING LINE VALUE (CLV) CALCULATOR
def calculate_clv(pick_type: str, taken_val: float, closing_val: float):
    if "Moneyline" in pick_type or "ML" in pick_type:
        dec_taken = american_to_decimal(int(taken_val))
        dec_close = american_to_decimal(int(closing_val))
        prob_taken = 1.0 / dec_taken
        prob_close = 1.0 / dec_close
        clv_edge_pct = (prob_close - prob_taken) * 100.0
        return round(clv_edge_pct, 2), f"{clv_edge_pct:+.2f}% Implied Prob"

    elif "Over" in pick_type:
        diff = closing_val - taken_val
        return round(diff, 2), f"{diff:+.1f} Points"

    elif "Under" in pick_type:
        diff = taken_val - closing_val
        return round(diff, 2), f"{diff:+.1f} Points"

    return 0.0, "N/A"


# BAYESIAN SMALL-SAMPLE PITCHER REGRESSION
def calculate_regressed_era(
    actual_era: float, season_ip: float, stabilization_ip: float = 30.0
) -> float:
    if season_ip <= 0:
        return LEAGUE_AVG_ERA
    weight = season_ip / (season_ip + stabilization_ip)
    regressed = (weight * actual_era) + ((1.0 - weight) * LEAGUE_AVG_ERA)
    return round(regressed, 2)


# NOVIG-PRIORITIZED LIVE ODDS API AUTO-FETCH FUNCTION
@st.cache_data(ttl=900)
def fetch_live_sportsbook_odds(
    sport_key: str, api_key: str, target_book: str = "novig"
):
    if not api_key:
        return {}

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=us,us_ex&markets=h2h,totals&oddsFormat=american"
    odds_map = {}

    try:
        res = requests.get(url, timeout=5).json()
        if isinstance(res, list):
            for game in res:
                h_team = game.get("home_team")
                a_team = game.get("away_team")
                match_key = f"{h_team} vs {a_team}".lower()

                bookmakers = game.get("bookmakers", [])
                if bookmakers:
                    selected_book = None
                    for b in bookmakers:
                        if b.get("key") == target_book:
                            selected_book = b
                            break

                    if not selected_book:
                        selected_book = bookmakers[0]

                    h2h_home, h2h_away = -110, -110
                    tot_line, tot_over, tot_under = 8.5, -110, -110

                    for m in selected_book.get("markets", []):
                        if m["key"] == "h2h":
                            for out in m.get("outcomes", []):
                                if out["name"] == h_team:
                                    h2h_home = out["price"]
                                elif out["name"] == a_team:
                                    h2h_away = out["price"]
                        elif m["key"] == "totals":
                            outcomes = m.get("outcomes", [])
                            if outcomes:
                                tot_line = outcomes[0].get("point", 8.5)
                                for out in outcomes:
                                    if out["name"] == "Over":
                                        tot_over = out["price"]
                                    elif out["name"] == "Under":
                                        tot_under = out["price"]

                    odds_map[match_key] = {
                        "home_ml": h2h_home,
                        "away_ml": h2h_away,
                        "total_line": tot_line,
                        "over_odds": tot_over,
                        "under_odds": tot_under,
                        "bookmaker": selected_book.get("title", "Consensus"),
                    }
    except Exception:
        pass

    return odds_map


# 30 MLB Teams
MLB_TEAMS = {
    "Arizona Diamondbacks": {
        "id": 109,
        "park_factor": 0.99,
        "base_runs": 4.6,
        "lat": 33.4455,
        "lon": -112.0667,
        "azimuth": 20,
        "dome": True,
    },
    "Atlanta Braves": {
        "id": 144,
        "park_factor": 1.01,
        "base_runs": 4.9,
        "lat": 33.8907,
        "lon": -84.4677,
        "azimuth": 125,
        "dome": False,
    },
    "Baltimore Orioles": {
        "id": 110,
        "park_factor": 0.98,
        "base_runs": 4.7,
        "lat": 39.2839,
        "lon": -76.6216,
        "azimuth": 22.5,
        "dome": False,
    },
    "Boston Red Sox": {
        "id": 111,
        "park_factor": 1.06,
        "base_runs": 4.8,
        "lat": 42.3467,
        "lon": -71.0972,
        "azimuth": 45,
        "dome": False,
    },
    "Chicago Cubs": {
        "id": 112,
        "park_factor": 1.01,
        "base_runs": 4.5,
        "lat": 41.9484,
        "lon": -87.6553,
        "azimuth": 45,
        "dome": False,
    },
    "Chicago White Sox": {
        "id": 145,
        "park_factor": 1.02,
        "base_runs": 3.8,
        "lat": 41.8299,
        "lon": -87.6338,
        "azimuth": 135,
        "dome": False,
    },
    "Cincinnati Reds": {
        "id": 113,
        "park_factor": 1.05,
        "base_runs": 4.4,
        "lat": 39.0979,
        "lon": -84.5082,
        "azimuth": 115,
        "dome": False,
    },
    "Cleveland Guardians": {
        "id": 114,
        "park_factor": 0.99,
        "base_runs": 4.4,
        "lat": 41.4962,
        "lon": -81.6852,
        "azimuth": 0,
        "dome": False,
    },
    "Colorado Rockies": {
        "id": 115,
        "park_factor": 1.18,
        "base_runs": 4.3,
        "lat": 39.7559,
        "lon": -104.9942,
        "azimuth": 10,
        "dome": False,
    },
    "Detroit Tigers": {
        "id": 116,
        "park_factor": 0.97,
        "base_runs": 4.2,
        "lat": 42.3390,
        "lon": -83.0485,
        "azimuth": 160,
        "dome": False,
    },
    "Houston Astros": {
        "id": 117,
        "park_factor": 0.99,
        "base_runs": 4.7,
        "lat": 29.7573,
        "lon": -95.3555,
        "azimuth": 35,
        "dome": True,
    },
    "Kansas City Royals": {
        "id": 118,
        "park_factor": 1.02,
        "base_runs": 4.5,
        "lat": 39.0517,
        "lon": -94.4803,
        "azimuth": 45,
        "dome": False,
    },
    "Los Angeles Angels": {
        "id": 108,
        "park_factor": 1.00,
        "base_runs": 4.3,
        "lat": 33.8003,
        "lon": -117.8827,
        "azimuth": 60,
        "dome": False,
    },
    "Los Angeles Dodgers": {
        "id": 119,
        "park_factor": 0.97,
        "base_runs": 5.1,
        "lat": 34.0739,
        "lon": -118.2400,
        "azimuth": 25,
        "dome": False,
    },
    "Miami Marlins": {
        "id": 146,
        "park_factor": 0.95,
        "base_runs": 3.9,
        "lat": 25.7781,
        "lon": -80.2197,
        "azimuth": 70,
        "dome": True,
    },
    "Milwaukee Brewers": {
        "id": 158,
        "park_factor": 1.01,
        "base_runs": 4.6,
        "lat": 43.0280,
        "lon": -87.9712,
        "azimuth": 120,
        "dome": True,
    },
    "Minnesota Twins": {
        "id": 142,
        "park_factor": 1.01,
        "base_runs": 4.5,
        "lat": 44.9817,
        "lon": -93.2778,
        "azimuth": 80,
        "dome": False,
    },
    "New York Mets": {
        "id": 121,
        "park_factor": 0.96,
        "base_runs": 4.4,
        "lat": 40.7571,
        "lon": -73.8458,
        "azimuth": 25,
        "dome": False,
    },
    "New York Yankees": {
        "id": 147,
        "park_factor": 1.02,
        "base_runs": 4.8,
        "lat": 40.8296,
        "lon": -73.9262,
        "azimuth": 60,
        "dome": False,
    },
    "Oakland Athletics": {
        "id": 133,
        "park_factor": 0.96,
        "base_runs": 4.0,
        "lat": 37.7516,
        "lon": -122.2005,
        "azimuth": 60,
        "dome": False,
    },
    "Philadelphia Phillies": {
        "id": 143,
        "park_factor": 1.03,
        "base_runs": 4.8,
        "lat": 39.9061,
        "lon": -75.1665,
        "azimuth": 10,
        "dome": False,
    },
    "Pittsburgh Pirates": {
        "id": 134,
        "park_factor": 0.98,
        "base_runs": 4.1,
        "lat": 40.4469,
        "lon": -80.0057,
        "azimuth": 115,
        "dome": False,
    },
    "San Diego Padres": {
        "id": 135,
        "park_factor": 0.92,
        "base_runs": 4.5,
        "lat": 32.7076,
        "lon": -117.1570,
        "azimuth": 10,
        "dome": False,
    },
    "San Francisco Giants": {
        "id": 137,
        "park_factor": 0.95,
        "base_runs": 4.2,
        "lat": 37.7786,
        "lon": -122.3893,
        "azimuth": 80,
        "dome": False,
    },
    "Seattle Mariners": {
        "id": 136,
        "park_factor": 0.93,
        "base_runs": 4.1,
        "lat": 47.5914,
        "lon": -122.3325,
        "azimuth": 40,
        "dome": True,
    },
    "St. Louis Cardinals": {
        "id": 138,
        "park_factor": 0.98,
        "base_runs": 4.2,
        "lat": 38.6226,
        "lon": -90.1928,
        "azimuth": 60,
        "dome": False,
    },
    "Tampa Bay Rays": {
        "id": 139,
        "park_factor": 0.96,
        "base_runs": 4.3,
        "lat": 27.7682,
        "lon": -82.6534,
        "azimuth": 50,
        "dome": True,
    },
    "Texas Rangers": {
        "id": 140,
        "park_factor": 1.02,
        "base_runs": 4.6,
        "lat": 32.7473,
        "lon": -97.0825,
        "azimuth": 130,
        "dome": True,
    },
    "Toronto Blue Jays": {
        "id": 141,
        "park_factor": 1.01,
        "base_runs": 4.4,
        "lat": 43.6414,
        "lon": -79.3894,
        "azimuth": 0,
        "dome": True,
    },
    "Washington Nationals": {
        "id": 120,
        "park_factor": 1.00,
        "base_runs": 4.2,
        "lat": 38.8730,
        "lon": -77.0074,
        "azimuth": 20,
        "dome": False,
    },
}

NBA_TEAMS = {
    "Boston Celtics": {"off_rating": 118.5, "def_rating": 110.2, "pace": 98.5},
    "Oklahoma City Thunder": {
        "off_rating": 117.2,
        "def_rating": 109.8,
        "pace": 99.1,
    },
    "Denver Nuggets": {"off_rating": 117.8, "def_rating": 112.4, "pace": 97.2},
    "Minnesota Timberwolves": {
        "off_rating": 114.5,
        "def_rating": 108.5,
        "pace": 97.8,
    },
    "Milwaukee Bucks": {"off_rating": 116.8, "def_rating": 114.2, "pace": 100.1},
    "Los Angeles Lakers": {
        "off_rating": 115.2,
        "def_rating": 113.8,
        "pace": 100.8,
    },
    "Golden State Warriors": {
        "off_rating": 115.8,
        "def_rating": 112.9,
        "pace": 99.8,
    },
    "New York Knicks": {"off_rating": 116.2, "def_rating": 111.5, "pace": 96.5},
    "Dallas Mavericks": {"off_rating": 117.0, "def_rating": 113.5, "pace": 98.2},
    "Philadelphia 76ers": {
        "off_rating": 115.5,
        "def_rating": 112.0,
        "pace": 97.5,
    },
    "Phoenix Suns": {"off_rating": 116.0, "def_rating": 113.2, "pace": 98.0},
    "Miami Heat": {"off_rating": 113.2, "def_rating": 111.0, "pace": 96.2},
    "LA Clippers": {"off_rating": 116.4, "def_rating": 111.8, "pace": 97.0},
    "Cleveland Cavaliers": {
        "off_rating": 114.8,
        "def_rating": 110.5,
        "pace": 97.2,
    },
    "Indiana Pacers": {"off_rating": 119.5, "def_rating": 118.2, "pace": 102.1},
    "Sacramento Kings": {
        "off_rating": 116.5,
        "def_rating": 115.0,
        "pace": 99.2,
    },
    "Orlando Magic": {"off_rating": 112.5, "def_rating": 109.5, "pace": 97.5},
    "New Orleans Pelicans": {
        "off_rating": 115.0,
        "def_rating": 112.2,
        "pace": 98.1,
    },
    "Chicago Bulls": {"off_rating": 113.0, "def_rating": 114.5, "pace": 96.8},
    "Atlanta Hawks": {"off_rating": 116.2, "def_rating": 117.5, "pace": 101.2},
    "Houston Rockets": {"off_rating": 113.8, "def_rating": 111.2, "pace": 98.8},
    "Memphis Grizzlies": {
        "off_rating": 111.5,
        "def_rating": 112.0,
        "pace": 99.5,
    },
    "Brooklyn Nets": {"off_rating": 113.5, "def_rating": 115.2, "pace": 97.6},
    "Toronto Raptors": {"off_rating": 113.0, "def_rating": 115.8, "pace": 98.9},
    "Utah Jazz": {"off_rating": 114.2, "def_rating": 118.0, "pace": 99.8},
    "Washington Wizards": {
        "off_rating": 110.2,
        "def_rating": 118.5,
        "pace": 102.5,
    },
    "Portland Trail Blazers": {
        "off_rating": 109.8,
        "def_rating": 116.2,
        "pace": 98.2,
    },
    "San Antonio Spurs": {
        "off_rating": 110.5,
        "def_rating": 116.0,
        "pace": 101.0,
    },
    "Charlotte Hornets": {
        "off_rating": 109.5,
        "def_rating": 117.2,
        "pace": 98.5,
    },
    "Detroit Pistons": {"off_rating": 109.0, "def_rating": 116.8, "pace": 98.8},
}


def calculate_air_density(
    temp_f: float, pressure_hpa: float, humidity_pct: float
):
    temp_c = (temp_f - 32.0) * (5.0 / 9.0)
    temp_k = temp_c + 273.15
    p_pascal = pressure_hpa * 100.0
    e_sat = 610.78 * (10 ** ((7.5 * temp_c) / (237.3 + temp_c)))
    p_v = (humidity_pct / 100.0) * e_sat
    p_d = p_pascal - p_v
    return (p_d / (287.058 * temp_k)) + (p_v / (461.495 * temp_k))


@st.cache_data(ttl=1800)
def fetch_bullpen_fatigue(team_id: int, game_date: datetime.date):
    d1 = game_date - datetime.timedelta(days=1)
    d3 = game_date - datetime.timedelta(days=3)
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={d3.strftime('%Y-%m-%d')}&endDate={d1.strftime('%Y-%m-%d')}&teamId={team_id}"

    weighted_pitches = 0.0
    try:
        res = requests.get(url, timeout=5).json()
        for d in res.get("dates", []):
            g_date = datetime.datetime.strptime(d["date"], "%Y-%m-%d").date()
            days_ago = (game_date - g_date).days
            weight = 1.0 if days_ago == 1 else (0.6 if days_ago == 2 else 0.3)

            for game in d.get("games", []):
                game_pk = game.get("gamePk")
                if not game_pk:
                    continue
                box_url = (
                    f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
                )
                box_res = requests.get(box_url, timeout=4).json()

                teams_data = box_res.get("teams", {})
                our_team_data = None
                if (
                    teams_data.get("home", {}).get("team", {}).get("id")
                    == team_id
                ):
                    our_team_data = teams_data.get("home")
                elif (
                    teams_data.get("away", {}).get("team", {}).get("id")
                    == team_id
                ):
                    our_team_data = teams_data.get("away")

                if our_team_data:
                    pitchers = our_team_data.get("pitchers", [])
                    relievers = pitchers[1:] if len(pitchers) > 1 else []
                    players = our_team_data.get("players", {})

                    for p_id in relievers:
                        p_key = f"ID{p_id}"
                        p_stats = (
                            players.get(p_key, {})
                            .get("stats", {})
                            .get("pitching", {})
                        )
                        pitches = p_stats.get("numberOfPitches", 0)
                        weighted_pitches += pitches * weight
    except Exception:
        pass

    if weighted_pitches == 0:
        return 1.00, 0.0

    mult = 1.00 + ((weighted_pitches - 90.0) / 350.0)
    mult = max(0.85, min(1.25, mult))
    return round(mult, 2), round(weighted_pitches, 1)


@st.cache_data(ttl=1800)
def fetch_high_leverage_reliever_status(team_id: int, game_date: datetime.date):
    d1 = game_date - datetime.timedelta(days=1)
    d2 = game_date - datetime.timedelta(days=2)

    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={d2.strftime('%Y-%m-%d')}&endDate={d1.strftime('%Y-%m-%d')}&teamId={team_id}"

    pitcher_log = {}
    closer_penalty = 0.0
    warning_msgs = []

    try:
        res = requests.get(url, timeout=5).json()
        for d in res.get("dates", []):
            g_date = datetime.datetime.strptime(d["date"], "%Y-%m-%d").date()
            is_d1 = g_date == d1

            for game in d.get("games", []):
                game_pk = game.get("gamePk")
                if not game_pk:
                    continue
                box_url = (
                    f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
                )
                box_res = requests.get(box_url, timeout=4).json()
                teams_data = box_res.get("teams", {})

                our_data = None
                if (
                    teams_data.get("home", {}).get("team", {}).get("id")
                    == team_id
                ):
                    our_data = teams_data.get("home")
                elif (
                    teams_data.get("away", {}).get("team", {}).get("id")
                    == team_id
                ):
                    our_data = teams_data.get("away")

                if our_data:
                    pitchers = our_data.get("pitchers", [])
                    relievers = pitchers[1:] if len(pitchers) > 1 else []
                    players = our_data.get("players", {})

                    high_leverage_ids = relievers[-2:] if len(relievers) >= 2 else relievers

                    for p_id in high_leverage_ids:
                        p_key = f"ID{p_id}"
                        p_obj = players.get(p_key, {})
                        p_name = p_obj.get("person", {}).get("fullName", f"Pitcher {p_id}")
                        p_stats = p_obj.get("stats", {}).get("pitching", {})
                        pitches = p_stats.get("numberOfPitches", 0)
                        saves = p_stats.get("saves", 0)
                        holds = p_stats.get("holds", 0)

                        if p_id not in pitcher_log:
                            pitcher_log[p_id] = {
                                "name": p_name,
                                "d1_pitches": 0,
                                "d2_pitches": 0,
                                "is_closer": saves > 0 or holds > 0,
                            }

                        if is_d1:
                            pitcher_log[p_id]["d1_pitches"] += pitches
                        else:
                            pitcher_log[p_id]["d2_pitches"] += pitches

        for p_id, pdata in pitcher_log.items():
            name = pdata["name"]
            d1_p = pdata["d1_pitches"]
            d2_p = pdata["d2_pitches"]

            if d1_p > 0 and d2_p > 0:
                closer_penalty += 0.06
                warning_msgs.append(
                    f"⚠️ `{name}` pitched back-to-back days ({d1_p} p. yesterday, {d2_p} p. 2 days ago)"
                )
            elif d1_p >= 25:
                closer_penalty += 0.04
                warning_msgs.append(
                    f"⚠️ `{name}` heavy workload yesterday ({d1_p} pitches)"
                )

    except Exception:
        pass

    closer_penalty = min(0.15, closer_penalty)
    status_text = (
        " | ".join(warning_msgs)
        if warning_msgs
        else "🟢 High-leverage relievers fully rested."
    )

    return round(closer_penalty, 2), status_text


@st.cache_data(ttl=1800)
def fetch_batch_player_ops(person_ids: list):
    if not person_ids:
        return {}

    pid_str = ",".join(str(p) for p in person_ids)
    url = f"https://statsapi.mlb.com/api/v1/people?personIds={pid_str}&hydrate=stats(group=[hitting],type=[season])"

    ops_map = {}
    try:
        res = requests.get(url, timeout=4).json()
        people = res.get("people", [])
        for p in people:
            pid = p.get("id")
            stats = p.get("stats", [])
            p_ops = LEAGUE_AVG_OPS
            if stats:
                splits = stats[0].get("splits", [])
                if splits:
                    stat_obj = splits[0].get("stat", {})
                    p_ops = float(stat_obj.get("ops", LEAGUE_AVG_OPS))
            ops_map[pid] = p_ops
    except Exception:
        pass

    return ops_map


@st.cache_data(ttl=1800)
def fetch_mlb_game_details(
    game_date: datetime.date, home_team: str, away_team: str, selected_game_idx: int = 0
):
    date_str = game_date.strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}&hydrate=probablePitcher,team,officials"

    data = {
        "start_time_str": "7:05 PM",
        "game_hour": 19,
        "home_sp_name": "TBD Starter",
        "home_sp_era": 3.80,
        "home_sp_reg_era": 3.80,
        "home_sp_season_ip": 0.0,
        "home_sp_hand": "R",
        "home_sp_ip_gs": 5.2,
        "away_sp_name": "TBD Starter",
        "away_sp_era": 4.10,
        "away_sp_reg_era": 4.10,
        "away_sp_season_ip": 0.0,
        "away_sp_hand": "R",
        "away_sp_ip_gs": 5.2,
        "home_platoon_adv": 0.0,
        "away_platoon_adv": 0.0,
        "home_lineup_ops_mult": 1.00,
        "away_lineup_ops_mult": 1.00,
        "home_lineup": [],
        "away_lineup": [],
        "umpire_name": "Unknown / Standard Zone",
        "lineups_official": False,
        "found": False,
        "total_games_today": 1,
        "game_start_times": [],
    }

    try:
        res = requests.get(url, timeout=5).json()
        dates = res.get("dates", [])
        if dates:
            matching_games = []
            for g in dates[0].get("games", []):
                h_name = g.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
                a_name = g.get("teams", {}).get("away", {}).get("team", {}).get("name", "")

                if (
                    home_team.lower() in h_name.lower()
                    or h_name.lower() in home_team.lower()
                ):
                    matching_games.append(g)

            if matching_games:
                data["total_games_today"] = len(matching_games)
                for mg in matching_games:
                    dt = datetime.datetime.fromisoformat(mg.get("gameDate", "").replace("Z", "+00:00"))
                    dt_local = dt.astimezone()
                    data["game_start_times"].append(dt_local.strftime("%I:%M %p").lstrip("0"))

                target_game_idx = min(selected_game_idx, len(matching_games) - 1)
                g = matching_games[target_game_idx]

                data["found"] = True
                game_pk = g.get("gamePk")

                g_date_utc = g.get("gameDate")
                if g_date_utc:
                    dt = datetime.datetime.fromisoformat(g_date_utc.replace("Z", "+00:00"))
                    dt_local = dt.astimezone()
                    data["start_time_str"] = dt_local.strftime("%I:%M %p").lstrip("0")
                    data["game_hour"] = dt_local.hour

                officials = g.get("officials", [])
                for off in officials:
                    if off.get("officialType") == "Home Plate":
                        data["umpire_name"] = off.get("person", {}).get("fullName", "Unknown")
                        break

                # Home SP
                h_sp = g.get("teams", {}).get("home", {}).get("probablePitcher", {})
                if h_sp:
                    data["home_sp_name"] = h_sp.get("fullName", "TBD")
                    h_id = h_sp.get("id")
                    if h_id:
                        p_url = f"https://statsapi.mlb.com/api/v1/people/{h_id}?hydrate=stats(group=[pitching],type=[season,statSplits],sitCodes=[sp])"
                        p_res = requests.get(p_url, timeout=3).json()
                        people = p_res.get("people", [])
                        if people:
                            data["home_sp_hand"] = people[0].get("pitchHand", {}).get("code", "R")
                            if people[0].get("stats"):
                                season_era = 3.80
                                season_ip = 0.0
                                exact_sp_ip = None
                                fallback_ip = 5.0

                                for st_group in people[0]["stats"]:
                                    st_type = st_group.get("type", {}).get("displayName", "")
                                    splits = st_group.get("splits", [])
                                    if st_type == "season" and splits:
                                        s_obj = splits[0].get("stat", {})
                                        season_era = float(s_obj.get("era", 3.80))
                                        season_ip = float(s_obj.get("inningsPitched", 0))
                                        gs = s_obj.get("gamesStarted", 0)
                                        if gs > 0:
                                            fallback_ip = season_ip / gs
                                    elif st_type == "statSplits" and splits:
                                        for s in splits:
                                            s_obj = s.get("stat", {})
                                            sp_gs = s_obj.get("gamesStarted", 0)
                                            sp_ip = float(s_obj.get("inningsPitched", 0))
                                            if sp_gs > 0:
                                                exact_sp_ip = sp_ip / sp_gs

                                final_ip = exact_sp_ip if exact_sp_ip is not None else fallback_ip
                                data["home_sp_era"] = season_era
                                data["home_sp_season_ip"] = season_ip
                                data["home_sp_reg_era"] = calculate_regressed_era(season_era, season_ip)
                                data["home_sp_ip_gs"] = round(min(7.0, max(2.0, final_ip)), 2)

                # Away SP
                a_sp = g.get("teams", {}).get("away", {}).get("probablePitcher", {})
                if a_sp:
                    data["away_sp_name"] = a_sp.get("fullName", "TBD")
                    a_id = a_sp.get("id")
                    if a_id:
                        p_url = f"https://statsapi.mlb.com/api/v1/people/{a_id}?hydrate=stats(group=[pitching],type=[season,statSplits],sitCodes=[sp])"
                        p_res = requests.get(p_url, timeout=3).json()
                        people = p_res.get("people", [])
                        if people:
                            data["away_sp_hand"] = people[0].get("pitchHand", {}).get("code", "R")
                            if people[0].get("stats"):
                                season_era = 4.10
                                season_ip = 0.0
                                exact_sp_ip = None
                                fallback_ip = 5.0

                                for st_group in people[0]["stats"]:
                                    st_type = st_group.get("type", {}).get("displayName", "")
                                    splits = st_group.get("splits", [])
                                    if st_type == "season" and splits:
                                        s_obj = splits[0].get("stat", {})
                                        season_era = float(s_obj.get("era", 4.10))
                                        season_ip = float(s_obj.get("inningsPitched", 0))
                                        gs = s_obj.get("gamesStarted", 0)
                                        if gs > 0:
                                            fallback_ip = season_ip / gs
                                    elif st_type == "statSplits" and splits:
                                        for s in splits:
                                            s_obj = s.get("stat", {})
                                            sp_gs = s_obj.get("gamesStarted", 0)
                                            sp_ip = float(s_obj.get("inningsPitched", 0))
                                            if sp_gs > 0:
                                                exact_sp_ip = sp_ip / sp_gs

                                final_ip = exact_sp_ip if exact_sp_ip is not None else fallback_ip
                                data["away_sp_era"] = season_era
                                data["away_sp_season_ip"] = season_ip
                                data["away_sp_reg_era"] = calculate_regressed_era(season_era, season_ip)
                                data["away_sp_ip_gs"] = round(min(7.0, max(2.0, final_ip)), 2)

                # SCRAPE OFFICIAL 1-9 BATTING LINEUPS
                if game_pk:
                    box_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
                    box_res = requests.get(box_url, timeout=4).json()
                    teams_box = box_res.get("teams", {})

                    h_order = teams_box.get("home", {}).get("battingOrder", [])
                    h_players = teams_box.get("home", {}).get("players", {})

                    a_order = teams_box.get("away", {}).get("battingOrder", [])
                    a_players = teams_box.get("away", {}).get("players", {})

                    if len(h_order) >= 9 and len(a_order) >= 9:
                        data["lineups_official"] = True
                        all_hitter_ids = h_order[:9] + a_order[:9]
                        ops_lookup = fetch_batch_player_ops(all_hitter_ids)

                        # Home Lineup
                        h_ops_list = []
                        for idx, p_id in enumerate(h_order[:9], 1):
                            p_obj = h_players.get(f"ID{p_id}", {})
                            name = p_obj.get("person", {}).get("fullName", f"Batter {idx}")
                            bats = p_obj.get("batSide", {}).get("code", "R")
                            pos = p_obj.get("position", {}).get("abbreviation", "DH")
                            p_ops = ops_lookup.get(p_id, LEAGUE_AVG_OPS)
                            h_ops_list.append(p_ops)

                            data["home_lineup"].append(
                                {
                                    "order": idx,
                                    "name": name,
                                    "bats": bats,
                                    "pos": pos,
                                    "ops": p_ops,
                                }
                            )

                        # Away Lineup
                        a_ops_list = []
                        for idx, p_id in enumerate(a_order[:9], 1):
                            p_obj = a_players.get(f"ID{p_id}", {})
                            name = p_obj.get("person", {}).get("fullName", f"Batter {idx}")
                            bats = p_obj.get("batSide", {}).get("code", "R")
                            pos = p_obj.get("position", {}).get("abbreviation", "DH")
                            p_ops = ops_lookup.get(p_id, LEAGUE_AVG_OPS)
                            a_ops_list.append(p_ops)

                            data["away_lineup"].append(
                                {
                                    "order": idx,
                                    "name": name,
                                    "bats": bats,
                                    "pos": pos,
                                    "ops": p_ops,
                                }
                            )

                        h_rel_ops = np.array(h_ops_list) / LEAGUE_AVG_OPS
                        data["home_lineup_ops_mult"] = round(float(np.sum(PA_WEIGHTS * h_rel_ops)), 3)

                        a_rel_ops = np.array(a_ops_list) / LEAGUE_AVG_OPS
                        data["away_lineup_ops_mult"] = round(float(np.sum(PA_WEIGHTS * a_rel_ops)), 3)

                if data["lineups_official"]:
                    h_fav = sum(
                        1
                        for b in data["home_lineup"]
                        if b["bats"] == "S" or b["bats"] != data["away_sp_hand"]
                    )
                    data["home_platoon_adv"] = round((h_fav - 4.5) * 0.08, 2)

                    a_fav = sum(
                        1
                        for b in data["away_lineup"]
                        if b["bats"] == "S" or b["bats"] != data["home_sp_hand"]
                    )
                    data["away_platoon_adv"] = round((a_fav - 4.5) * 0.08, 2)
                else:
                    if data["away_sp_hand"] == "L":
                        data["home_platoon_adv"] = 0.25
                    if data["home_sp_hand"] == "L":
                        data["away_platoon_adv"] = 0.25
    except Exception:
        pass
    return data


def fetch_game_time_weather(
    lat: float, lon: float, game_date: datetime.date, game_hour: int
):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
    try:
        res = requests.get(url, timeout=4).json()
        times = res["hourly"]["time"]
        target_iso = f"{game_date.strftime('%Y-%m-%d')}T{game_hour:02d}:00"
        if target_iso in times:
            idx = times.index(target_iso)
            return {
                "temp_f": res["hourly"]["temperature_2m"][idx],
                "humidity_pct": res["hourly"]["relative_humidity_2m"][idx],
                "pressure_hpa": res["hourly"]["surface_pressure"][idx],
                "wind_mph": res["hourly"]["wind_speed_10m"][idx],
                "wind_dir_deg": res["hourly"]["wind_direction_10m"][idx],
            }
    except Exception:
        pass
    return {
        "temp_f": 72.0,
        "humidity_pct": 50.0,
        "pressure_hpa": 1013.25,
        "wind_mph": 0.0,
        "wind_dir_deg": 0,
    }


def sim_negative_binomial(mu: float, phi: float, size: int):
    p = 1.0 / phi
    n = mu / (phi - 1.0)
    return np.random.negative_binomial(n, p, size)


# TOP LEVEL APP NAVIGATION TABS (PERMANENT LOG ACCESS)
tab_sim, tab_logger = st.tabs(
    ["🎯 Game Simulator", "📝 Wager Log & CLV Tracker"]
)

# TAB 1: GAME SIMULATOR
with tab_sim:
    sport = st.radio(
        "Select Sport", ["MLB (Baseball)", "NBA (Basketball)"], horizontal=True
    )

    odds_api_key = st.text_input(
        "🔑 The Odds API Key (Optional for Live Book Odds)",
        value="",
        type="password",
        help="Paste your free API key from the-odds-api.com to auto-fetch live Novig lines directly.",
    )

    if sport == "MLB (Baseball)":
        team_names = list(MLB_TEAMS.keys())
        col1, col2 = st.columns(2)
        with col1:
            home_team = st.selectbox("Home Team", team_names, index=4)
        with col2:
            away_team = st.selectbox("Away Team", team_names, index=18)

        st.markdown("### 🕒 Game Date & Doubleheader Selector")
        game_date = st.date_input("Game Date", datetime.date.today())

        initial_details = fetch_mlb_game_details(game_date, home_team, away_team, 0)
        selected_game_idx = 0

        if initial_details["total_games_today"] > 1:
            st.info(f"⚾ **DOUBLEHEADER DETECTED:** {home_team} vs {away_team} play 2 games on this date!")
            game_opts = [
                f"Game {i+1} ({t})"
                for i, t in enumerate(initial_details["game_start_times"])
            ]
            dh_selection = st.radio("Select Game to Simulate:", game_opts, horizontal=True)
            selected_game_idx = game_opts.index(dh_selection)

        details = fetch_mlb_game_details(game_date, home_team, away_team, selected_game_idx)
        home_bp_mult, home_bp_workload = fetch_bullpen_fatigue(
            MLB_TEAMS[home_team]["id"], game_date
        )
        away_bp_mult, away_bp_workload = fetch_bullpen_fatigue(
            MLB_TEAMS[away_team]["id"], game_date
        )

        home_closer_pen, home_closer_msg = fetch_high_leverage_reliever_status(
            MLB_TEAMS[home_team]["id"], game_date
        )
        away_closer_pen, away_closer_msg = fetch_high_leverage_reliever_status(
            MLB_TEAMS[away_team]["id"], game_date
        )

        st.info(
            f"⚡ **Start:** `{details['start_time_str']}` | **Umpire:** `{details['umpire_name']}`\n\n"
            f"**3-Day Bullpen Workload:** {home_team} = `{home_bp_workload:.0f}` pitches | {away_team} = `{away_bp_workload:.0f}` pitches"
        )

        if home_closer_pen > 0 or away_closer_pen > 0:
            st.warning(
                f"🔥 **HIGH-LEVERAGE / CLOSER REST WARNINGS:**\n\n"
                f"• **{home_team}:** {home_closer_msg} (Penalty: +{home_closer_pen:.2f})\n\n"
                f"• **{away_team}:** {away_closer_msg} (Penalty: +{away_closer_pen:.2f})"
            )

        if details["lineups_official"]:
            st.success(
                f"🟢 **Official 1-9 Lineups Confirmed!**\n\n"
                f"• {home_team} Lineup Quality: `{details['home_lineup_ops_mult']:.3f}x` | "
                f"{away_team} Lineup Quality: `{details['away_lineup_ops_mult']:.3f}x`"
            )
        else:
            st.warning("🟡 **Lineups Pending** (Using Baseline Team Offense)")

        stadium_info = MLB_TEAMS[home_team]
        park_factor = stadium_info["park_factor"]

        if stadium_info["dome"]:
            weather_desc = "Indoor Stadium / Dome (72°F, 0 mph)"
            weather_multiplier = 1.0
            eff_wind_parallel = 0.0
        else:
            w = fetch_game_time_weather(
                stadium_info["lat"],
                stadium_info["lon"],
                game_date,
                details["game_hour"],
            )
            rho = calculate_air_density(
                w["temp_f"], w["pressure_hpa"], w["humidity_pct"]
            )

            air_density_impact = 1.0 + ((1.225 - rho) * 0.65)
            wind_to_deg = (w["wind_dir_deg"] + 180) % 360
            angle_diff_rad = np.radians(wind_to_deg - stadium_info["azimuth"])

            eff_wind_parallel = w["wind_mph"] * np.cos(angle_diff_rad)
            eff_wind_cross = w["wind_mph"] * np.sin(angle_diff_rad)

            parallel_factor = eff_wind_parallel * 0.012
            crosswind_drag = abs(eff_wind_cross) * 0.003

            wind_factor = 1.0 + parallel_factor - crosswind_drag
            weather_multiplier = air_density_impact * wind_factor

            wind_label = "Outward" if eff_wind_parallel >= 0 else "Inward"
            weather_desc = (
                f"{w['temp_f']:.1f}°F | Air Density ρ = {rho:.3f} kg/m³ | "
                f"Net {eff_wind_parallel:.1f} mph {wind_label} (Crosswind Drag: -{crosswind_drag*100:.1f}%)"
            )

        auto_dispersion = calculate_dynamic_dispersion(
            park_factor=park_factor,
            wind_parallel_mph=eff_wind_parallel,
            home_sp_era=details["home_sp_reg_era"],
            away_sp_era=details["away_sp_reg_era"],
            home_sp_ip=details["home_sp_ip_gs"],
            away_sp_ip=details["away_sp_ip_gs"],
            home_bp_rating=home_bp_mult + home_closer_pen,
            away_bp_rating=away_bp_mult + away_closer_pen,
        )

        with st.form("capping_form"):
            st.markdown("### ⚾ Starters & Bayesian ERA Stabilization")
            col_sp1, col_sp2 = st.columns(2)

            with col_sp1:
                st.caption(
                    f"Announced: **{details['home_sp_name']}** ({details['home_sp_hand']}HP | `{details['home_sp_season_ip']:.1f} IP` Season)"
                )
                home_sp_xfip = st.number_input(
                    f"{home_team} Starter ERA (Regressed)",
                    value=float(details["home_sp_reg_era"]),
                    step=0.05,
                    help=f"Raw ERA: {details['home_sp_era']:.2f}. Regressed toward 4.10 using Bayesian stabilization."
                )
                home_sp_ip = st.number_input(
                    f"{home_team} Starter Expected IP",
                    value=float(details["home_sp_ip_gs"]),
                    step=0.1,
                )
                home_bullpen_rating = st.slider(
                    f"{home_team} Bullpen Rating (Adj: +{home_closer_pen:.2f})",
                    0.80,
                    1.35,
                    float(home_bp_mult + home_closer_pen),
                    0.05,
                )
                home_platoon_advantage = st.slider(
                    f"{home_team} Platoon Advantage",
                    -0.5,
                    0.5,
                    float(details["home_platoon_adv"]),
                    0.05,
                )

            with col_sp2:
                st.caption(
                    f"Announced: **{details['away_sp_name']}** ({details['away_sp_hand']}HP | `{details['away_sp_season_ip']:.1f} IP` Season)"
                )
                away_sp_xfip = st.number_input(
                    f"{away_team} Starter ERA (Regressed)",
                    value=float(details["away_sp_reg_era"]),
                    step=0.05,
                    help=f"Raw ERA: {details['away_sp_era']:.2f}. Regressed toward 4.10 using Bayesian stabilization."
                )
                away_sp_ip = st.number_input(
                    f"{away_team} Starter Expected IP",
                    value=float(details["away_sp_ip_gs"]),
                    step=0.1,
                )
                away_bullpen_rating = st.slider(
                    f"{away_team} Bullpen Rating (Adj: +{away_closer_pen:.2f})",
                    0.80,
                    1.35,
                    float(away_bp_mult + away_closer_pen),
                    0.05,
                )
                away_platoon_advantage = st.slider(
                    f"{away_team} Platoon Advantage",
                    -0.5,
                    0.5,
                    float(details["away_platoon_adv"]),
                    0.05,
                )

            if details["lineups_official"]:
                with st.expander("📋 View Confirmed 1-9 Lineups & Season OPS"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**{home_team} Order:**")
                        for b in details["home_lineup"]:
                            st.caption(
                                f"{b['order']}. {b['name']} ({b['bats']}) - {b['pos']} | OPS: `{b['ops']:.3f}`"
                            )
                    with c2:
                        st.write(f"**{away_team} Order:**")
                        for b in details["away_lineup"]:
                            st.caption(
                                f"{b['order']}. {b['name']} ({b['bats']}) - {b['pos']} | OPS: `{b['ops']:.3f}`"
                            )

            dispersion = st.slider(
                f"Run Variance Ratio (Auto-Calculated: {auto_dispersion})",
                1.05,
                1.80,
                float(auto_dispersion),
                step=0.05,
                help="Automated using Park Factor, Aerodynamics, SP Quality, and Bullpen Workload.",
            )

            home_base_runs = (
                MLB_TEAMS[home_team]["base_runs"] * details["home_lineup_ops_mult"]
            ) + home_platoon_advantage
            away_base_runs = (
                MLB_TEAMS[away_team]["base_runs"] * details["away_lineup_ops_mult"]
            ) + away_platoon_advantage

            w_away_sp = min(0.85, max(0.20, away_sp_ip / 9.0))
            w_away_bp = 1.0 - w_away_sp
            away_pitching_mult = (w_away_sp * (away_sp_xfip / LEAGUE_AVG_ERA)) + (
                w_away_bp * away_bullpen_rating
            )

            w_home_sp = min(0.85, max(0.20, home_sp_ip / 9.0))
            w_home_bp = 1.0 - w_home_sp
            home_pitching_mult = (w_home_sp * (home_sp_xfip / LEAGUE_AVG_ERA)) + (
                w_home_bp * home_bullpen_rating
            )

            home_xr = (
                home_base_runs * away_pitching_mult * park_factor * weather_multiplier
            )
            away_xr = (
                away_base_runs * home_pitching_mult * park_factor * weather_multiplier
            )

            home_f5 = home_xr * 0.55
            away_f5 = away_xr * 0.55

            num_sims = st.select_slider(
                "Monte Carlo Iterations",
                [100000, 500000, 1000000, 2500000],
                value=1000000,
            )
            submitted = st.form_submit_button("🔥 Run 1,000,000 Game Simulation")

    else:  # NBA
        nba_team_names = list(NBA_TEAMS.keys())
        col1, col2 = st.columns(2)
        with col1:
            home_team = st.selectbox("Home Team", nba_team_names, index=0)
            h_data = NBA_TEAMS[home_team]
            home_off_rating = float(h_data["off_rating"])
            home_def_rating = float(h_data["def_rating"])
            home_rest = "Normal Rest"
        with col2:
            away_team = st.selectbox("Away Team", nba_team_names, index=5)
            a_data = NBA_TEAMS[away_team]
            away_off_rating = float(a_data["off_rating"])
            away_def_rating = float(a_data["def_rating"])
            away_rest = "Normal Rest"

        with st.form("nba_form"):
            st.markdown("### ⚙️ Game Environment & Pace")
            c_p1, c_p2 = st.columns(2)
            avg_pace = (h_data["pace"] + a_data["pace"]) / 2.0
            with c_p1:
                game_pace = st.number_input("Projected Game Pace", value=float(avg_pace), step=0.5)
            with c_p2:
                home_court_adv = st.number_input("Home Court Advantage", value=2.5, step=0.5)

            nba_std = st.slider("Game Variance (Std Dev)", 8.0, 15.0, 11.5, step=0.5)
            LEAGUE_AVG_RATING = 114.0

            home_pts = ((home_off_rating * away_def_rating / LEAGUE_AVG_RATING) * (game_pace / 100.0) + home_court_adv)
            away_pts = (away_off_rating * home_def_rating / LEAGUE_AVG_RATING) * (game_pace / 100.0)
            home_1h = home_pts * 0.50
            away_1h = away_pts * 0.50

            num_sims = st.select_slider(
                "Monte Carlo Iterations",
                [100000, 500000, 1000000, 2500000],
                value=1000000,
            )
            submitted = st.form_submit_button("🔥 Run 1,000,000 Game Simulation")

    # Run Simulation and save results to Session State
    if submitted:
        if sport == "MLB (Baseball)":
            sim_home = sim_negative_binomial(home_xr, dispersion, num_sims)
            sim_away = sim_negative_binomial(away_xr, dispersion, num_sims)
            sim_home_f5 = sim_negative_binomial(home_f5, dispersion * 0.8, num_sims)
            sim_away_f5 = sim_negative_binomial(away_f5, dispersion * 0.8, num_sims)

            info_msg = (
                f"⚾ **Scheduled Time:** {details['start_time_str']} | **Starters:** {details['home_sp_name']} ({home_sp_ip:.1f} IP) vs {details['away_sp_name']} ({away_sp_ip:.1f} IP)\n\n"
                f"🌤️ **Aerodynamics:** {weather_desc} (Multiplier = **{weather_multiplier:.3f}x**)\n\n"
                f"**Final Projected Runs:** {home_team} = **{home_xr:.2f}** | {away_team} = **{away_xr:.2f}**"
            )
        else:
            sim_home = np.random.normal(home_pts, nba_std, num_sims)
            sim_away = np.random.normal(away_pts, nba_std, num_sims)
            sim_home_1h = np.random.normal(home_1h, nba_std * 0.7, num_sims)
            sim_away_1h = np.random.normal(away_1h, nba_std * 0.7, num_sims)

            info_msg = (
                f"🏀 **NBA Environment:** Pace = **{game_pace:.1f} possessions** | Home Court = **+{home_court_adv} pts**\n\n"
                f"**Projected Full Game Points:** {home_team} = **{home_pts:.1f}** | {away_team} = **{away_pts:.1f}**"
            )

        mean_h, mean_a = np.mean(sim_home), np.mean(sim_away)
        p_home_win = np.mean(sim_home > sim_away)
        diff = sim_home - sim_away

        st.session_state.sim_data = {
            "sport": sport,
            "home_team": home_team,
            "away_team": away_team,
            "mean_h": mean_h,
            "mean_a": mean_a,
            "p_home_win": p_home_win,
            "diff": diff,
            "num_sims": num_sims,
            "info_msg": info_msg,
            "sim_home": sim_home,
            "sim_away": sim_away,
            "sim_home_split": sim_home_f5 if sport == "MLB (Baseball)" else sim_home_1h,
            "sim_away_split": sim_away_f5 if sport == "MLB (Baseball)" else sim_away_1h,
            "game_date": game_date if sport == "MLB (Baseball)" else datetime.date.today(),
            "odds_api_key": odds_api_key,
        }

    # RENDER SIMULATION RESULTS FROM SESSION STATE
    if st.session_state.sim_data is not None:
        data = st.session_state.sim_data

        st.info(data["info_msg"])

        st.subheader(f"1. Projected Scoreboard ({data['num_sims']:,} Sims)")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric(f"{data['home_team']}", f"{data['mean_h']:.2f}")
        with col_s2:
            st.metric(f"{data['away_team']}", f"{data['mean_a']:.2f}")
        with col_s3:
            st.metric("Combined Total", f"{data['mean_h'] + data['mean_a']:.2f}")

        st.markdown("---")

        tab_full, tab_chart, tab_split, tab_ev, tab_export = st.tabs(
            [
                "📊 Game Script",
                "📈 Distribution Chart",
                "⏱️ F5 / 1H Splits",
                "💰 +EV & Betting Edge",
                "📋 Export Card",
            ]
        )

        with tab_full:
            st.write(f"**{data['home_team']} Win Probability:** `{data['p_home_win']*100:.2f}%`")
            st.write(
                f"**80% Total Range:** `{np.percentile(data['sim_home'] + data['sim_away'], 10):.1f}` to `{np.percentile(data['sim_home'] + data['sim_away'], 90):.1f}`"
            )
            if data["sport"] == "MLB (Baseball)":
                st.write(f"• **Win by 2+ Runs:** `{np.mean(data['diff'] >= 2)*100:.2f}%`")
                st.write(f"• **1-Run Game Probability:** `{np.mean(np.abs(data['diff']) == 1)*100:.2f}%`")
            else:
                st.write(
                    f"• **Clutch Finish (≤ 5 pts margin):** `{np.mean(np.abs(data['diff']) <= 5)*100:.2f}%`"
                )
                st.write(f"• **Blowout Finish (12+ pts):** `{np.mean(np.abs(data['diff']) >= 12)*100:.2f}%`")

        with tab_chart:
            st.markdown("### Interactive Point Differential Distribution")
            diffs = np.round(data["diff"])
            min_d, max_d = int(np.percentile(diffs, 1)), int(np.percentile(diffs, 99))
            bins, counts = np.unique(
                diffs[(diffs >= min_d) & (diffs <= max_d)], return_counts=True
            )
            chart_df = pd.DataFrame(
                {
                    "Margin (Home - Away)": bins.astype(int),
                    "Simulated Frequency": counts / data["num_sims"],
                }
            ).set_index("Margin (Home - Away)")
            st.bar_chart(chart_df)

        with tab_split:
            if data["sport"] == "MLB (Baseball)":
                st.markdown("### First 5 Innings (F5) Projections")
                st.write(
                    f"• **F5 Projected Score:** {data['home_team']} `{np.mean(data['sim_home_split']):.2f}` – {data['away_team']} `{np.mean(data['sim_away_split']):.2f}`"
                )
                st.write(
                    f"• **F5 Home Lead Probability:** `{np.mean(data['sim_home_split'] > data['sim_away_split'])*100:.2f}%`"
                )
            else:
                st.markdown("### 1st Half (1H) Projections")
                st.write(
                    f"• **1H Projected Score:** {data['home_team']} `{np.mean(data['sim_home_split']):.2f}` – {data['away_team']} `{np.mean(data['sim_away_split']):.2f}`"
                )
                st.write(
                    f"• **1H Home Lead Probability:** `{np.mean(data['sim_home_split'] > data['sim_away_split'])*100:.2f}%`"
                )

        with tab_ev:
            st.markdown("### 💰 Live +EV Betting Edge & Kelly Unit Sizing")

            sport_api_key = (
                "baseball_mlb" if data["sport"] == "MLB (Baseball)" else "basketball_nba"
            )
            live_odds_map = fetch_live_sportsbook_odds(
                sport_api_key, data.get("odds_api_key", ""), target_book="novig"
            )

            match_search_key = (
                f"{data['home_team']} vs {data['away_team']}".lower()
            )
            matched_odds = live_odds_map.get(match_search_key, {})

            if matched_odds:
                st.success(
                    f"⚡ **Auto-Fetched Live Odds from `{matched_odds.get('bookmaker', 'Sportsbook')}`**"
                )
                default_h_ml = matched_odds["home_ml"]
                default_a_ml = matched_odds["away_ml"]
                default_tot_line = float(matched_odds["total_line"])
                default_over = matched_odds["over_odds"]
                default_under = matched_odds["under_odds"]
            else:
                if data.get("odds_api_key"):
                    st.caption(
                        "ℹ️ *Live odds not posted yet for this matchup. Using manual baseline.*"
                    )
                else:
                    st.caption(
                        "💡 *Paste a free key from `the-odds-api.com` in the field above to auto-fetch live Novig lines!*"
                    )

                sim_totals = data["sim_home"] + data["sim_away"]
                default_h_ml = -110
                default_a_ml = -110
                default_tot_line = round(float(np.mean(sim_totals)) * 2) / 2
                default_over = -110
                default_under = -110

            kelly_choice = st.selectbox(
                "Kelly Sizing Risk Level",
                [
                    "Quarter Kelly (0.25x) - Recommended",
                    "Half Kelly (0.50x) - Aggressive",
                    "Full Kelly (1.00x) - Maximum Variance",
                ],
            )
            k_frac = (
                0.25
                if "Quarter" in kelly_choice
                else (0.50 if "Half" in kelly_choice else 1.00)
            )

            st.markdown("---")
            st.markdown("#### 1. Moneyline +EV Edge")
            c_odds1, c_odds2 = st.columns(2)
            with c_odds1:
                home_ml = st.number_input(
                    f"{data['home_team']} Moneyline Odds",
                    value=int(default_h_ml),
                    step=5,
                )
            with c_odds2:
                away_ml = st.number_input(
                    f"{data['away_team']} Moneyline Odds",
                    value=int(default_a_ml),
                    step=5,
                )

            h_imp, h_ev, h_units = calculate_ev_and_kelly(
                data["p_home_win"], home_ml, k_frac
            )
            a_imp, a_ev, a_units = calculate_ev_and_kelly(
                1.0 - data["p_home_win"], away_ml, k_frac
            )

            col_ml_h, col_ml_a = st.columns(2)
            with col_ml_h:
                st.markdown(f"**🏠 {data['home_team']} (`{home_ml:+d}`)**")
                st.caption(f"Model: `{data['p_home_win']*100:.1f}%` | Book: `{h_imp}%`")
                if h_ev > 0:
                    st.success(f"🔥 **+{h_ev}% EV** | Bet: `{h_units} U`")
                else:
                    st.error(f"❌ `{h_ev}% EV` (No Edge)")

            with col_ml_a:
                st.markdown(f"**✈️ {data['away_team']} (`{away_ml:+d}`)**")
                st.caption(f"Model: `{(1.0 - data['p_home_win'])*100:.1f}%` | Book: `{a_imp}%`")
                if a_ev > 0:
                    st.success(f"🔥 **+{a_ev}% EV** | Bet: `{a_units} U`")
                else:
                    st.error(f"❌ `{a_ev}% EV` (No Edge)")

            st.markdown("---")
            st.markdown("#### 2. Game Total (Over / Under) +EV Edge")

            sim_totals = data["sim_home"] + data["sim_away"]

            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                total_line = st.number_input(
                    "Sportsbook Line",
                    value=float(default_tot_line),
                    step=0.5,
                )
            with col_t2:
                over_odds = st.number_input("Over Odds", value=int(default_over), step=5)
            with col_t3:
                under_odds = st.number_input("Under Odds", value=int(default_under), step=5)

            p_over = float(np.mean(sim_totals > total_line))
            p_under = float(np.mean(sim_totals < total_line))

            o_imp, o_ev, o_units = calculate_ev_and_kelly(p_over, over_odds, k_frac)
            u_imp, u_ev, u_units = calculate_ev_and_kelly(p_under, under_odds, k_frac)

            col_ou1, col_ou2 = st.columns(2)
            with col_ou1:
                st.markdown(f"**📈 OVER `{total_line}` (`{over_odds:+d}`)**")
                st.caption(f"Model: `{p_over*100:.1f}%` | Book: `{o_imp}%`")
                if o_ev > 0:
                    st.success(f"🔥 **+{o_ev}% EV** | Bet: `{o_units} U`")
                else:
                    st.error(f"❌ `{o_ev}% EV` (No Edge)")

            with col_ou2:
                st.markdown(f"**📉 UNDER `{total_line}` (`{under_odds:+d}`)**")
                st.caption(f"Model: `{p_under*100:.1f}%` | Book: `{u_imp}%`")
                if u_ev > 0:
                    st.success(f"🔥 **+{u_ev}% EV** | Bet: `{u_units} U`")
                else:
                    st.error(f"❌ `{u_ev}% EV` (No Edge)")

        with tab_export:
            st.markdown("### 📋 Copy/Paste Matchup Summary Card")
            export_text = (
                f"🎯 CAPPING REPORT ({data['sport']})\n"
                f"Date: {data['game_date'].strftime('%Y-%m-%d')} | Matchup: {data['home_team']} vs {data['away_team']}\n"
                f"----------------------------------------\n"
                f"• Projected Final Score: {data['home_team']} {data['mean_h']:.2f} - {data['away_team']} {data['mean_a']:.2f}\n"
                f"• Projected Game Total: {data['mean_h'] + data['mean_a']:.2f}\n"
                f"• {data['home_team']} Win Prob: {data['p_home_win']*100:.1f}%\n"
                f"----------------------------------------\n"
                f"Simulated over {data['num_sims']:,} Monte Carlo iterations."
            )
            st.code(export_text, language="text")


# TAB 2: STANDALONE PERMANENT WAGER LOG & CLV TRACKER
with tab_logger:
    st.markdown("### 📝 Wager & Closing Line Value (CLV) Log")
    st.caption("Log any past game, enter actual scores, and view performance metrics without running simulations.")

    # Auto-populate defaults if a simulation is active in Session State
    active_data = st.session_state.sim_data
    default_matchup = f"{active_data['home_team']} vs {active_data['away_team']}" if active_data else "Mets vs Braves"
    default_sport = active_data["sport"] if active_data else "MLB (Baseball)"

    with st.form("standalone_clv_log_form"):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            log_date = st.date_input("Game Date", datetime.date.today())
            log_sport = st.selectbox("Sport", ["MLB (Baseball)", "NBA (Basketball)"], index=0 if default_sport == "MLB (Baseball)" else 1)
            matchup_name = st.text_input("Matchup Name", value=default_matchup)
        with col_m2:
            wager_pick = st.selectbox(
                "Wager Choice",
                [
                    "Home Team Moneyline",
                    "Away Team Moneyline",
                    "Over Total",
                    "Under Total",
                    "Pass / Calibration Only",
                ],
            )
            line_taken = st.number_input("Line/Odds You Bet (e.g. -120 or 8.5)", value=-110.0, step=5.0)
            closing_line = st.number_input("Closing Line/Odds at Start (e.g. -140 or 9.0)", value=-110.0, step=5.0)

        st.markdown("---")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            units_staked = st.number_input("Units Risked", value=1.0, step=0.25)
        with col_s2:
            actual_home = st.number_input("Actual Home Score", value=0, step=1)
        with col_s3:
            actual_away = st.number_input("Actual Away Score", value=0, step=1)

        log_btn = st.form_submit_button("💾 Save Wager & Calculate CLV")

        if log_btn:
            proj_h = active_data["mean_h"] if active_data else 0.0
            proj_a = active_data["mean_a"] if active_data else 0.0

            err_h = round(abs(proj_h - actual_home), 2)
            err_a = round(abs(proj_a - actual_away), 2)
            clv_val, clv_str = calculate_clv(wager_pick, line_taken, closing_line)

            actual_total = actual_home + actual_away
            p_result = "N/A"
            net_units = 0.0

            if "Home Team" in wager_pick or "Away Team" in wager_pick or "Moneyline" in wager_pick:
                home_won = actual_home > actual_away
                is_home_pick = "Home" in wager_pick
                if home_won == is_home_pick:
                    p_result = "WIN"
                    b_mult = (american_to_decimal(int(line_taken)) - 1.0)
                    net_units = round(units_staked * b_mult, 2)
                else:
                    p_result = "LOSS"
                    net_units = -round(units_staked, 2)
            elif "Over" in wager_pick:
                if actual_total > line_taken:
                    p_result = "WIN"
                    net_units = round(units_staked * 0.91, 2)
                elif actual_total < line_taken:
                    p_result = "LOSS"
                    net_units = -round(units_staked, 2)
                else:
                    p_result = "PUSH"
            elif "Under" in wager_pick:
                if actual_total < line_taken:
                    p_result = "WIN"
                    net_units = round(units_staked * 0.91, 2)
                elif actual_total > line_taken:
                    p_result = "LOSS"
                    net_units = -round(units_staked, 2)
                else:
                    p_result = "PUSH"

            file_path = "model_calibration_log.csv"
            log_data = {
                "Date": [str(log_date)],
                "Sport": [log_sport],
                "Matchup": [matchup_name],
                "Pick": [wager_pick],
                "Line_Taken": [line_taken],
                "Closing_Line": [closing_line],
                "CLV_Edge": [clv_val],
                "Result": [p_result],
                "Net_Units": [net_units],
                "Proj_Home": [round(proj_h, 2)],
                "Proj_Away": [round(proj_a, 2)],
                "Actual_Home": [actual_home],
                "Actual_Away": [actual_away],
                "Error_Home": [err_h],
                "Error_Away": [err_a],
            }
            df_new = pd.DataFrame(log_data)
            if os.path.exists(file_path):
                df_new.to_csv(file_path, mode="a", header=False, index=False)
            else:
                df_new.to_csv(file_path, index=False)

            if clv_val > 0:
                st.success(f"🔥 **WINNING CLV!** Beat closing line by `{clv_str}` | Wager: `{p_result}` (`{net_units:+.2f} U`)")
            else:
                st.warning(f"📉 **Negative CLV:** `{clv_str}` | Wager: `{p_result}` (`{net_units:+.2f} U`)")

    # STANDALONE DISPLAY OF SAVED WAGER HISTORY & METRICS
    file_path = "model_calibration_log.csv"
    if os.path.exists(file_path):
        df_history = pd.read_csv(file_path)
        st.markdown("---")
        st.markdown("#### 📊 Portfolio & CLV Performance Metrics")

        if len(df_history) > 0:
            c_m1, c_m2, c_m3 = st.columns(3)

            valid_clv = df_history[df_history["Pick"] != "Pass / Calibration Only"]
            avg_clv = valid_clv["CLV_Edge"].mean() if len(valid_clv) > 0 and "CLV_Edge" in valid_clv.columns else 0.0
            total_pnl = df_history["Net_Units"].sum() if "Net_Units" in df_history.columns else 0.0

            wins = len(df_history[df_history["Result"] == "WIN"])
            losses = len(df_history[df_history["Result"] == "LOSS"])
            win_rate = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else 0.0

            with c_m1:
                st.metric("Avg CLV Edge", f"{avg_clv:+.2f}")
            with c_m2:
                st.metric("Win Rate", f"{win_rate:.1f}%", f"{wins}W - {losses}L")
            with c_m3:
                st.metric("Net Profit", f"{total_pnl:+.2f} U")

        st.markdown("#### Saved Wager History")
        st.dataframe(df_history)

        csv_bytes = df_history.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Betting Log to Phone (.csv)",
            data=csv_bytes,
            file_name=f"capper_clv_log_{datetime.date.today()}.csv",
            mime="text/csv",
        )
    else:
        st.caption("ℹ️ *No saved logs found yet. Fill out the form above to log your first play!*")
