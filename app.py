import datetime
import os
import numpy as np
import pandas as pd
import requests
from scipy.stats import nbinom
import streamlit as st

st.set_page_config(
    page_title="Auto-Capper Workstation", page_icon="🎯", layout="centered"
)

st.title("🎯 Pro Auto-Capping Engine")
st.caption(
    "1,000,000 Simulations | Auto Game Time | Pitcher Handedness & Platoon Splits | Bullpen Metrics"
)

# 30 MLB Stadium Coordinates & Alignment Angles
MLB_TEAMS = {
    "Arizona Diamondbacks": {
        "park_factor": 0.99,
        "base_runs": 4.6,
        "lat": 33.4455,
        "lon": -112.0667,
        "azimuth": 20,
        "dome": True,
    },
    "Atlanta Braves": {
        "park_factor": 1.01,
        "base_runs": 4.9,
        "lat": 33.8907,
        "lon": -84.4677,
        "azimuth": 125,
        "dome": False,
    },
    "Baltimore Orioles": {
        "park_factor": 0.98,
        "base_runs": 4.7,
        "lat": 39.2839,
        "lon": -76.6216,
        "azimuth": 22.5,
        "dome": False,
    },
    "Boston Red Sox": {
        "park_factor": 1.06,
        "base_runs": 4.8,
        "lat": 42.3467,
        "lon": -71.0972,
        "azimuth": 45,
        "dome": False,
    },
    "Chicago Cubs": {
        "park_factor": 1.01,
        "base_runs": 4.5,
        "lat": 41.9484,
        "lon": -87.6553,
        "azimuth": 45,
        "dome": False,
    },
    "Chicago White Sox": {
        "park_factor": 1.02,
        "base_runs": 3.8,
        "lat": 41.8299,
        "lon": -87.6338,
        "azimuth": 135,
        "dome": False,
    },
    "Cincinnati Reds": {
        "park_factor": 1.05,
        "base_runs": 4.4,
        "lat": 39.0979,
        "lon": -84.5082,
        "azimuth": 115,
        "dome": False,
    },
    "Cleveland Guardians": {
        "park_factor": 0.99,
        "base_runs": 4.4,
        "lat": 41.4962,
        "lon": -81.6852,
        "azimuth": 0,
        "dome": False,
    },
    "Colorado Rockies": {
        "park_factor": 1.18,
        "base_runs": 4.3,
        "lat": 39.7559,
        "lon": -104.9942,
        "azimuth": 10,
        "dome": False,
    },
    "Detroit Tigers": {
        "park_factor": 0.97,
        "base_runs": 4.2,
        "lat": 42.3390,
        "lon": -83.0485,
        "azimuth": 160,
        "dome": False,
    },
    "Houston Astros": {
        "park_factor": 0.99,
        "base_runs": 4.7,
        "lat": 29.7573,
        "lon": -95.3555,
        "azimuth": 35,
        "dome": True,
    },
    "Kansas City Royals": {
        "park_factor": 1.02,
        "base_runs": 4.5,
        "lat": 39.0517,
        "lon": -94.4803,
        "azimuth": 45,
        "dome": False,
    },
    "Los Angeles Angels": {
        "park_factor": 1.00,
        "base_runs": 4.3,
        "lat": 33.8003,
        "lon": -117.8827,
        "azimuth": 60,
        "dome": False,
    },
    "Los Angeles Dodgers": {
        "park_factor": 0.97,
        "base_runs": 5.1,
        "lat": 34.0739,
        "lon": -118.2400,
        "azimuth": 25,
        "dome": False,
    },
    "Miami Marlins": {
        "park_factor": 0.95,
        "base_runs": 3.9,
        "lat": 25.7781,
        "lon": -80.2197,
        "azimuth": 70,
        "dome": True,
    },
    "Milwaukee Brewers": {
        "park_factor": 1.01,
        "base_runs": 4.6,
        "lat": 43.0280,
        "lon": -87.9712,
        "azimuth": 120,
        "dome": True,
    },
    "Minnesota Twins": {
        "park_factor": 1.01,
        "base_runs": 4.5,
        "lat": 44.9817,
        "lon": -93.2778,
        "azimuth": 80,
        "dome": False,
    },
    "New York Mets": {
        "park_factor": 0.96,
        "base_runs": 4.4,
        "lat": 40.7571,
        "lon": -73.8458,
        "azimuth": 25,
        "dome": False,
    },
    "New York Yankees": {
        "park_factor": 1.02,
        "base_runs": 4.8,
        "lat": 40.8296,
        "lon": -73.9262,
        "azimuth": 60,
        "dome": False,
    },
    "Oakland Athletics": {
        "park_factor": 0.96,
        "base_runs": 4.0,
        "lat": 37.7516,
        "lon": -122.2005,
        "azimuth": 60,
        "dome": False,
    },
    "Philadelphia Phillies": {
        "park_factor": 1.03,
        "base_runs": 4.8,
        "lat": 39.9061,
        "lon": -75.1665,
        "azimuth": 10,
        "dome": False,
    },
    "Pittsburgh Pirates": {
        "park_factor": 0.98,
        "base_runs": 4.1,
        "lat": 40.4469,
        "lon": -80.0057,
        "azimuth": 115,
        "dome": False,
    },
    "San Diego Padres": {
        "park_factor": 0.92,
        "base_runs": 4.5,
        "lat": 32.7076,
        "lon": -117.1570,
        "azimuth": 10,
        "dome": False,
    },
    "San Francisco Giants": {
        "park_factor": 0.95,
        "base_runs": 4.2,
        "lat": 37.7786,
        "lon": -122.3893,
        "azimuth": 80,
        "dome": False,
    },
    "Seattle Mariners": {
        "park_factor": 0.93,
        "base_runs": 4.1,
        "lat": 47.5914,
        "lon": -122.3325,
        "azimuth": 40,
        "dome": True,
    },
    "St. Louis Cardinals": {
        "park_factor": 0.98,
        "base_runs": 4.2,
        "lat": 38.6226,
        "lon": -90.1928,
        "azimuth": 60,
        "dome": False,
    },
    "Tampa Bay Rays": {
        "park_factor": 0.96,
        "base_runs": 4.3,
        "lat": 27.7682,
        "lon": -82.6534,
        "azimuth": 50,
        "dome": True,
    },
    "Texas Rangers": {
        "park_factor": 1.02,
        "base_runs": 4.6,
        "lat": 32.7473,
        "lon": -97.0825,
        "azimuth": 130,
        "dome": True,
    },
    "Toronto Blue Jays": {
        "park_factor": 1.01,
        "base_runs": 4.4,
        "lat": 43.6414,
        "lon": -79.3894,
        "azimuth": 0,
        "dome": True,
    },
    "Washington Nationals": {
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


# AUTO-FETCH GAME DETAILS, PITCHERS, HANDEDNESS & BULLPENS
@st.cache_data(ttl=1800)
def fetch_mlb_game_details(
    game_date: datetime.date, home_team: str, away_team: str
):
    date_str = game_date.strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}&hydrate=probablePitcher,team"

    data = {
        "start_time_str": "7:05 PM",
        "game_hour": 19,
        "home_sp_name": "TBD Starter",
        "home_sp_era": 3.80,
        "home_sp_hand": "R",
        "away_sp_name": "TBD Starter",
        "away_sp_era": 4.10,
        "away_sp_hand": "R",
        "home_bullpen_mult": 1.00,
        "away_bullpen_mult": 1.00,
        "home_platoon_adv": 0.0,
        "away_platoon_adv": 0.0,
        "found": False,
    }

    try:
        res = requests.get(url, timeout=5).json()
        dates = res.get("dates", [])
        if dates:
            for g in dates[0].get("games", []):
                h_name = (
                    g.get("teams", {})
                    .get("home", {})
                    .get("team", {})
                    .get("name", "")
                )
                a_name = (
                    g.get("teams", {})
                    .get("away", {})
                    .get("team", {})
                    .get("name", "")
                )

                if (
                    home_team.lower() in h_name.lower()
                    or h_name.lower() in home_team.lower()
                ):
                    data["found"] = True

                    # 1. Parse Scheduled Game Time
                    g_date_utc = g.get("gameDate")
                    if g_date_utc:
                        dt = datetime.datetime.fromisoformat(
                            g_date_utc.replace("Z", "+00:00")
                        )
                        dt_local = dt.astimezone()
                        data["start_time_str"] = dt_local.strftime(
                            "%I:%M %p"
                        ).lstrip("0")
                        data["game_hour"] = dt_local.hour

                    # 2. Home SP & Pitch Hand
                    h_sp = (
                        g.get("teams", {})
                        .get("home", {})
                        .get("probablePitcher", {})
                    )
                    if h_sp:
                        data["home_sp_name"] = h_sp.get("fullName", "TBD")
                        h_id = h_sp.get("id")
                        if h_id:
                            p_url = f"https://statsapi.mlb.com/api/v1/people/{h_id}?hydrate=stats(group=[pitching],type=[season])"
                            p_res = requests.get(p_url, timeout=3).json()
                            people = p_res.get("people", [])
                            if people:
                                data["home_sp_hand"] = people[0].get(
                                    "pitchHand", {}
                                ).get("code", "R")
                                if people[0].get("stats"):
                                    splits = people[0]["stats"][0].get(
                                        "splits", []
                                    )
                                    if splits:
                                        data["home_sp_era"] = float(
                                            splits[0]
                                            .get("stat", {})
                                            .get("era", 3.80)
                                        )

                    # 3. Away SP & Pitch Hand
                    a_sp = (
                        g.get("teams", {})
                        .get("away", {})
                        .get("probablePitcher", {})
                    )
                    if a_sp:
                        data["away_sp_name"] = a_sp.get("fullName", "TBD")
                        a_id = a_sp.get("id")
                        if a_id:
                            p_url = f"https://statsapi.mlb.com/api/v1/people/{a_id}?hydrate=stats(group=[pitching],type=[season])"
                            p_res = requests.get(p_url, timeout=3).json()
                            people = p_res.get("people", [])
                            if people:
                                data["away_sp_hand"] = people[0].get(
                                    "pitchHand", {}
                                ).get("code", "R")
                                if people[0].get("stats"):
                                    splits = people[0]["stats"][0].get(
                                        "splits", []
                                    )
                                    if splits:
                                        data["away_sp_era"] = float(
                                            splits[0]
                                            .get("stat", {})
                                            .get("era", 4.10)
                                        )

                    # 4. Auto Platoon Split Calculations
                    if data["away_sp_hand"] == "L":
                        data["home_platoon_adv"] = 0.25
                    if data["home_sp_hand"] == "L":
                        data["away_platoon_adv"] = 0.25

                    break
    except Exception:
        pass
    return data


def fetch_game_time_weather(
    lat: float, lon: float, game_date: datetime.date, game_hour: int
):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
    try:
        res = requests.get(url, timeout=4).json()
        times = res["hourly"]["time"]
        target_iso = f"{game_date.strftime('%Y-%m-%d')}T{game_hour:02d}:00"
        if target_iso in times:
            idx = times.index(target_iso)
            return {
                "temp_f": res["hourly"]["temperature_2m"][idx],
                "wind_mph": res["hourly"]["wind_speed_10m"][idx],
                "wind_dir_deg": res["hourly"]["wind_direction_10m"][idx],
            }
    except Exception:
        pass
    return {"temp_f": 72.0, "wind_mph": 0.0, "wind_dir_deg": 0}


def sim_negative_binomial(mu: float, phi: float, size: int):
    p = 1.0 / phi
    n = mu / (phi - 1.0)
    return np.random.negative_binomial(n, p, size)


sport = st.radio(
    "Select Sport", ["MLB (Baseball)", "NBA (Basketball)"], horizontal=True
)

with st.form("capping_form"):
    col1, col2 = st.columns(2)

    if sport == "MLB (Baseball)":
        team_names = list(MLB_TEAMS.keys())
        with col1:
            home_team = st.selectbox("Home Team", team_names, index=4)  # Cubs
        with col2:
            away_team = st.selectbox("Away Team", team_names, index=18)  # Yankees

        st.markdown("### 🕒 Game Date")
        game_date = st.date_input("Game Date", datetime.date.today())

        # FETCH AUTOMATED GAME DETAILS
        details = fetch_mlb_game_details(game_date, home_team, away_team)

        st.info(
            f"⚡ **Scheduled Game Start Time:** `{details['start_time_str']}`"
        )

        st.markdown("### ⚾ Starters & Platoon Splits (Auto-Calculated)")
        col_sp1, col_sp2 = st.columns(2)

        with col_sp1:
            st.caption(
                f"Announced: **{details['home_sp_name']}** ({details['home_sp_hand']}HP)"
            )
            home_sp_xfip = st.number_input(
                f"{home_team} Starter ERA/xFIP",
                value=float(details["home_sp_era"]),
                step=0.05,
            )
            home_bullpen_rating = st.slider(
                f"{home_team} Bullpen Fatigue/Quality",
                0.80,
                1.20,
                float(details["home_bullpen_mult"]),
                0.05,
            )
            home_platoon_advantage = st.slider(
                f"{home_team} Platoon Advantage",
                -0.5,
                0.5,
                float(details["home_platoon_adv"]),
                0.05,
                help="Auto-adjusted based on opposing pitcher throwing hand (LHP/RHP).",
            )

        with col_sp2:
            st.caption(
                f"Announced: **{details['away_sp_name']}** ({details['away_sp_hand']}HP)"
            )
            away_sp_xfip = st.number_input(
                f"{away_team} Starter ERA/xFIP",
                value=float(details["away_sp_era"]),
                step=0.05,
            )
            away_bullpen_rating = st.slider(
                f"{away_team} Bullpen Fatigue/Quality",
                0.80,
                1.20,
                float(details["away_bullpen_mult"]),
                0.05,
            )
            away_platoon_advantage = st.slider(
                f"{away_team} Platoon Advantage",
                -0.5,
                0.5,
                float(details["away_platoon_adv"]),
                0.05,
            )

        dispersion = st.slider(
            "Run Variance Ratio (Overdispersion)", 1.05, 1.80, 1.30, step=0.05
        )

        stadium_info = MLB_TEAMS[home_team]
        park_factor = stadium_info["park_factor"]
        home_base_runs = stadium_info["base_runs"] + home_platoon_advantage
        away_base_runs = MLB_TEAMS[away_team]["base_runs"] + away_platoon_advantage

        LEAGUE_AVG_XFIP = 4.10
        away_pitching_mult = (0.60 * (away_sp_xfip / LEAGUE_AVG_XFIP)) + (
            0.40 * away_bullpen_rating
        )
        home_pitching_mult = (0.60 * (home_sp_xfip / LEAGUE_AVG_XFIP)) + (
            0.40 * home_bullpen_rating
        )

        if stadium_info["dome"]:
            weather_desc = "Indoor Stadium / Dome (72°F, 0 mph)"
            weather_multiplier = 1.0
        else:
            w = fetch_game_time_weather(
                stadium_info["lat"],
                stadium_info["lon"],
                game_date,
                details["game_hour"],
            )
            wind_to_deg = (w["wind_dir_deg"] + 180) % 360
            angle_diff_rad = np.radians(wind_to_deg - stadium_info["azimuth"])
            eff_wind = w["wind_mph"] * np.cos(angle_diff_rad)

            temp_factor = 1.0 + ((w["temp_f"] - 70.0) * 0.0035)
            wind_factor = 1.0 + (eff_wind * 0.012)
            weather_multiplier = temp_factor * wind_factor

            wind_label = "Outward" if eff_wind >= 0 else "Inward"
            weather_desc = f"{w['temp_f']:.1f}°F | Wind: {w['wind_mph']:.1f} mph ({abs(eff_wind):.1f} mph Net {wind_label})"

        home_xr = (
            home_base_runs * away_pitching_mult * park_factor * weather_multiplier
        )
        away_xr = (
            away_base_runs * home_pitching_mult * park_factor * weather_multiplier
        )

        home_f5 = home_xr * 0.55
        away_f5 = away_xr * 0.55

    else:  # NBA
        nba_team_names = list(NBA_TEAMS.keys())
        with col1:
            home_team = st.selectbox("Home Team", nba_team_names, index=0)
            h_data = NBA_TEAMS[home_team]
            home_off_rating = st.number_input(
                f"{home_team} Offense Rating", value=float(h_data["off_rating"])
            )
            home_def_rating = st.number_input(
                f"{home_team} Defense Rating", value=float(h_data["def_rating"])
            )
            home_rest = st.selectbox(
                f"{home_team} Rest",
                ["Normal Rest", "Back-to-Back (-2.5 pts)", "3-in-4 Nights (-1.5 pts)"],
            )

        with col2:
            away_team = st.selectbox("Away Team", nba_team_names, index=5)
            a_data = NBA_TEAMS[away_team]
            away_off_rating = st.number_input(
                f"{away_team} Offense Rating", value=float(a_data["off_rating"])
            )
            away_def_rating = st.number_input(
                f"{away_team} Defense Rating", value=float(a_data["def_rating"])
            )
            away_rest = st.selectbox(
                f"{away_team} Rest",
                ["Normal Rest", "Back-to-Back (-2.5 pts)", "3-in-4 Nights (-1.5 pts)"],
            )

        st.markdown("### ⚙️ Game Environment & Pace")
        c_p1, c_p2 = st.columns(2)
        avg_pace = (h_data["pace"] + a_data["pace"]) / 2.0
        with c_p1:
            game_pace = st.number_input(
                "Projected Game Pace", value=float(avg_pace), step=0.5
            )
        with c_p2:
            home_court_adv = st.number_input(
                "Home Court Advantage", value=2.5, step=0.5
            )

        nba_std = st.slider("Game Variance (Std Dev)", 8.0, 15.0, 11.5, step=0.5)

        rest_penalties = {
            "Normal Rest": 0.0,
            "Back-to-Back (-2.5 pts)": -2.5,
            "3-in-4 Nights (-1.5 pts)": -1.5,
        }
        LEAGUE_AVG_RATING = 114.0

        home_pts = (
            (home_off_rating * away_def_rating / LEAGUE_AVG_RATING)
            * (game_pace / 100.0)
            + home_court_adv
            + rest_penalties[home_rest]
        )
        away_pts = (
            (away_off_rating * home_def_rating / LEAGUE_AVG_RATING)
            * (game_pace / 100.0)
            + rest_penalties[away_rest]
        )

        home_1h = home_pts * 0.50
        away_1h = away_pts * 0.50

    num_sims = st.select_slider(
        "Monte Carlo Iterations",
        [100000, 500000, 1000000, 2500000],
        value=1000000,
    )
    submitted = st.form_submit_button("🔥 Run 1,000,000 Game Simulation")

if submitted:
    if sport == "MLB (Baseball)":
        sim_home = sim_negative_binomial(home_xr, dispersion, num_sims)
        sim_away = sim_negative_binomial(away_xr, dispersion, num_sims)
        sim_home_f5 = sim_negative_binomial(home_f5, dispersion * 0.8, num_sims)
        sim_away_f5 = sim_negative_binomial(away_f5, dispersion * 0.8, num_sims)

        st.info(
            f"⚾ **Scheduled Time:** {details['start_time_str']} | **Starters:** {details['home_sp_name']} ({details['home_sp_hand']}HP) vs {details['away_sp_name']} ({details['away_sp_hand']}HP)\n\n"
            f"🌤️ **Weather Forecast at First Pitch:** {weather_desc} (Multiplier = **{weather_multiplier:.3f}x**)\n\n"
            f"**Final Runs (xR):** {home_team} = **{home_xr:.2f}** | {away_team} = **{away_xr:.2f}**"
        )
    else:
        sim_home = np.random.normal(home_pts, nba_std, num_sims)
        sim_away = np.random.normal(away_pts, nba_std, num_sims)
        sim_home_1h = np.random.normal(home_1h, nba_std * 0.7, num_sims)
        sim_away_1h = np.random.normal(away_1h, nba_std * 0.7, num_sims)

        st.info(
            f"🏀 **NBA Game Environment:** Pace = **{game_pace:.1f} possessions** | Home Court = **+{home_court_adv} pts**\n\n"
            f"**Projected Full Game Points:** {home_team} = **{home_pts:.1f}** | {away_team} = **{away_pts:.1f}**"
        )

    st.subheader(f"1. Projected Scoreboard ({num_sims:,} Games Simulated)")
    col_s1, col_s2, col_s3 = st.columns(3)
    mean_h, mean_a = np.mean(sim_home), np.mean(sim_away)

    with col_s1:
        st.metric(f"{home_team}", f"{mean_h:.2f}")
    with col_s2:
        st.metric(f"{away_team}", f"{mean_a:.2f}")
    with col_s3:
        st.metric("Combined Total", f"{mean_h + mean_a:.2f}")

    st.markdown("---")

    tab_full, tab_split, tab_log = st.tabs(
        ["📊 Full Game Script", "⏱️ F5 / 1H Splits", "📝 Calibration Log"]
    )

    with tab_full:
        p_home_win = np.mean(sim_home > sim_away)
        diff = sim_home - sim_away
        st.write(f"**{home_team} Win Probability:** `{p_home_win*100:.2f}%`")
        st.write(
            f"**80% Total Range:** `{np.percentile(sim_home + sim_away, 10):.1f}` to `{np.percentile(sim_home + sim_away, 90):.1f}`"
        )
        if sport == "MLB (Baseball)":
            st.write(
                f"• **Win by 2+ Runs:** `{np.mean(diff >= 2)*100:.2f}%`"
            )
            st.write(
                f"• **1-Run Game Probability:** `{np.mean(np.abs(diff) == 1)*100:.2f}%`"
            )
        else:
            st.write(
                f"• **Clutch Finish (5 pts or less margin):** `{np.mean(np.abs(diff) <= 5)*100:.2f}%`"
            )
            st.write(
                f"• **Blowout Finish (12+ pts):** `{np.mean(np.abs(diff) >= 12)*100:.2f}%`"
            )

    with tab_split:
        if sport == "MLB (Baseball)":
            st.markdown("### First 5 Innings (F5) Projections")
            st.write(
                f"• **F5 Projected Score:** {home_team} `{np.mean(sim_home_f5):.2f}` – {away_team} `{np.mean(sim_away_f5):.2f}`"
            )
            st.write(
                f"• **F5 Home Lead Probability:** `{np.mean(sim_home_f5 > sim_away_f5)*100:.2f}%`"
            )
        else:
            st.markdown("### 1st Half (1H) Projections")
            st.write(
                f"• **1H Projected Score:** {home_team} `{np.mean(sim_home_1h):.2f}` – {away_team} `{np.mean(sim_away_1h):.2f}`"
            )
            st.write(
                f"• **1H Home Lead Probability:** `{np.mean(sim_home_1h > sim_away_1h)*100:.2f}%`"
            )

    with tab_log:
        st.markdown("### Model Calibration & Accuracy Logger")
        st.caption(
            "Log your prediction today, then enter the actual final score later to track your Mean Absolute Error (MAE)."
        )

        with st.form("log_form"):
            actual_home = st.number_input("Actual Home Score", value=0, step=1)
            actual_away = st.number_input("Actual Away Score", value=0, step=1)
            log_btn = st.form_submit_button("💾 Save to Log File")

            if log_btn:
                log_data = {
                    "Date": [str(datetime.date.today())],
                    "Sport": [sport],
                    "Matchup": [f"{home_team} vs {away_team}"],
                    "Proj_Home": [round(mean_h, 2)],
                    "Proj_Away": [round(mean_a, 2)],
                    "Actual_Home": [actual_home],
                    "Actual_Away": [actual_away],
                    "Error_Home": [round(abs(mean_h - actual_home), 2)],
                    "Error_Away": [round(abs(mean_a - actual_away), 2)],
                }
                df_new = pd.DataFrame(log_data)
                file_path = "model_calibration_log.csv"

                if os.path.exists(file_path):
                    df_new.to_csv(
                        file_path, mode="a", header=False, index=False
                    )
                else:
                    df_new.to_csv(file_path, index=False)
                st.success(
                    "Prediction logged successfully to model_calibration_log.csv!"
                )

        if os.path.exists("model_calibration_log.csv"):
            st.markdown("#### Past Logged Predictions")
            df_history = pd.read_csv("model_calibration_log.csv")
            st.dataframe(df_history)
            if len(df_history) > 0:
                mean_error = (
                    df_history["Error_Home"].mean()
                    + df_history["Error_Away"].mean()
                ) / 2
                st.metric(
                    "Overall Model Mean Absolute Error (MAE)",
                    f"{mean_error:.2f} pts/runs",
                )
