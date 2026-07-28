import datetime
import numpy as np
import pandas as pd
import requests
from scipy.stats import nbinom
import streamlit as st

st.set_page_config(
    page_title="Pure Capper Simulation Engine", page_icon="🎯", layout="centered"
)

st.title("🎯 Pro Handicapper Simulation Engine")
st.caption("Game Script & Team Total Projections (No Sportsbook Odds)")

# 30 MLB Stadium Coordinates & Metadata
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

NBA_TEAMS = [
    "Atlanta Hawks",
    "Boston Celtics",
    "Brooklyn Nets",
    "Charlotte Hornets",
    "Chicago Bulls",
    "Cleveland Cavaliers",
    "Dallas Mavericks",
    "Denver Nuggets",
    "Detroit Pistons",
    "Golden State Warriors",
    "Houston Rockets",
    "Indiana Pacers",
    "LA Clippers",
    "Los Angeles Lakers",
    "Memphis Grizzlies",
    "Miami Heat",
    "Milwaukee Bucks",
    "Minnesota Timberwolves",
    "New Orleans Pelicans",
    "New York Knicks",
    "Oklahoma City Thunder",
    "Orlando Magic",
    "Philadelphia 76ers",
    "Phoenix Suns",
    "Portland Trail Blazers",
    "Sacramento Kings",
    "San Antonio Spurs",
    "Toronto Raptors",
    "Utah Jazz",
    "Washington Wizards",
]


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
            home_sp_xfip = st.number_input(
                f"{home_team} SP xFIP", value=3.20, step=0.05
            )
            home_bullpen_rating = st.slider(
                f"{home_team} Bullpen Fatigue/Quality",
                0.80,
                1.20,
                1.00,
                0.05,
                help="1.00 = Normal. >1.00 = Tired or poor bullpen. <1.00 = Elite or fresh bullpen.",
            )
            home_platoon_advantage = st.slider(
                f"{home_team} Platoon Split Advantage",
                -0.5,
                0.5,
                0.0,
                0.1,
                help="Add runs if Home lineup mashes against Away SP hand (LHP/RHP).",
            )

        with col2:
            away_team = st.selectbox("Away Team", team_names, index=18)  # Yankees
            away_sp_xfip = st.number_input(
                f"{away_team} SP xFIP", value=4.10, step=0.05
            )
            away_bullpen_rating = st.slider(
                f"{away_team} Bullpen Fatigue/Quality",
                0.80,
                1.20,
                1.00,
                0.05,
            )
            away_platoon_advantage = st.slider(
                f"{away_team} Platoon Split Advantage",
                -0.5,
                0.5,
                0.0,
                0.1,
            )

        st.markdown("### 🕒 Game Date & Start Time")
        dt_col1, dt_col2 = st.columns(2)
        with dt_col1:
            game_date = st.date_input("Game Date", datetime.date.today())
        with dt_col2:
            game_hour = st.selectbox(
                "Start Hour (24-Hr Local)",
                options=list(range(24)),
                index=19,
                format_func=lambda h: f"{h:02d}:00",
            )

        dispersion = st.slider(
            "Run Variance (Overdispersion)", 1.05, 1.80, 1.30, step=0.05
        )

        # Base Metrics & Weather Fetching
        stadium_info = MLB_TEAMS[home_team]
        park_factor = stadium_info["park_factor"]
        home_base_runs = stadium_info["base_runs"] + home_platoon_advantage
        away_base_runs = MLB_TEAMS[away_team]["base_runs"] + away_platoon_advantage

        LEAGUE_AVG_XFIP = 4.10
        # Starter (60%) + Bullpen (40%) pitching factor
        away_pitching_mult = (
            (0.60 * (away_sp_xfip / LEAGUE_AVG_XFIP))
            + (0.40 * away_bullpen_rating)
        )
        home_pitching_mult = (
            (0.60 * (home_sp_xfip / LEAGUE_AVG_XFIP))
            + (0.40 * home_bullpen_rating)
        )

        if stadium_info["dome"]:
            weather_desc = "Indoor Stadium / Dome (72°F, 0 mph)"
            weather_multiplier = 1.0
        else:
            w = fetch_game_time_weather(
                stadium_info["lat"], stadium_info["lon"], game_date, game_hour
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

    else:  # NBA
        with col1:
            home_team = st.selectbox("Home Team", NBA_TEAMS, index=1)
            home_off_rating = st.number_input(
                f"{home_team} Offense Rating", value=116.5, step=0.5
            )
            home_def_rating = st.number_input(
                f"{home_team} Defense Rating", value=112.0, step=0.5
            )
            home_rest = st.selectbox(
                f"{home_team} Rest Situation",
                ["Normal Rest", "Back-to-Back (-2.5 pts)", "3-in-4 Nights (-1.5 pts)"],
            )

        with col2:
            away_team = st.selectbox("Away Team", NBA_TEAMS, index=13)
            away_off_rating = st.number_input(
                f"{away_team} Offense Rating", value=114.0, step=0.5
            )
            away_def_rating = st.number_input(
                f"{away_team} Defense Rating", value=113.5, step=0.5
            )
            away_rest = st.selectbox(
                f"{away_team} Rest Situation",
                ["Normal Rest", "Back-to-Back (-2.5 pts)", "3-in-4 Nights (-1.5 pts)"],
            )

        st.markdown("### ⚙️ Game Environment & Pace")
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            game_pace = st.number_input(
                "Projected Game Pace (Possessions)", value=99.5, step=0.5
            )
        with c_p2:
            home_court_adv = st.number_input(
                "Home Court Advantage (Pts)", value=2.5, step=0.5
            )

        nba_std = st.slider("Game Variance (Std Dev)", 8.0, 15.0, 11.5, step=0.5)

        # Rest penalties
        rest_penalties = {
            "Normal Rest": 0.0,
            "Back-to-Back (-2.5 pts)": -2.5,
            "3-in-4 Nights (-1.5 pts)": -1.5,
        }

        # Calculate Expected Points per possession
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

    num_sims = st.select_slider(
        "Monte Carlo Iterations", [10000, 50000, 100000], value=100000
    )
    submitted = st.form_submit_button("🔥 Run Matchup Analysis")

if submitted:
    if sport == "MLB (Baseball)":
        sim_home = sim_negative_binomial(home_xr, dispersion, num_sims)
        sim_away = sim_negative_binomial(away_xr, dispersion, num_sims)
    else:
        sim_home = np.random.normal(home_pts, nba_std, num_sims)
        sim_away = np.random.normal(away_pts, nba_std, num_sims)

    # 1. Projected Final Scoreboard
    st.subheader("1. Projected Final Score")
    col_s1, col_s2, col_s3 = st.columns(3)

    mean_h = np.mean(sim_home)
    mean_a = np.mean(sim_away)
    proj_total = mean_h + mean_a

    with col_s1:
        st.metric(f"{home_team}", f"{mean_h:.2f} pts/runs")
    with col_s2:
        st.metric(f"{away_team}", f"{mean_a:.2f} pts/runs")
    with col_s3:
        st.metric("Projected Total", f"{proj_total:.2f}")

    st.markdown("---")

    # 2. Win & Margin Breakdown
    st.subheader("2. Game Script & Win Margins")
    p_home_win = np.mean(sim_home > sim_away)
    p_away_win = np.mean(sim_away > sim_home)
    diff = sim_home - sim_away

    tab_win, tab_script, tab_totals = st.tabs(
        ["🏆 Win Probabilities", "📜 Game Script / Margins", "📊 Team Totals"]
    )

    with tab_win:
        st.write(
            f"**{home_team} Win Probability:** `{p_home_win*100:.1f}%`"
        )
        st.write(
            f"**{away_team} Win Probability:** `{p_away_win*100:.1f}%`"
        )
        st.write(
            f"**Projected Differential:** `{home_team} by {mean_h - mean_a:+.2f}`"
        )

    with tab_script:
        if sport == "MLB (Baseball)":
            p_one_run = np.mean(np.abs(diff) == 1)
            p_home_cover_rl = np.mean(diff >= 2)
            p_blowout = np.mean(np.abs(diff) >= 4)

            st.write(f"• **1-Run Game Probability:** `{p_one_run*100:.1f}%`")
            st.write(
                f"• **{home_team} Cover Run Line (-1.5):** `{p_home_cover_rl*100:.1f}%`"
            )
            st.write(f"• **Blowout Game (4+ Run Margin):** `{p_blowout*100:.1f}%`")
        else:
            p_clutch = np.mean(np.abs(diff) <= 5)
            p_mod = np.mean((np.abs(diff) > 5) & (np.abs(diff) <= 11))
            p_blowout_nba = np.mean(np.abs(diff) >= 12)

            st.write(
                f"• **Clutch Finish ($\le 5$ pt margin):** `{p_clutch*100:.1f}%`"
            )
            st.write(
                f"• **Moderate Margin ($6\text{--}11$ pts):** `{p_mod*100:.1f}%`"
            )
            st.write(
                f"• **Blowout Finish ($12+$ pts):** `{p_blowout_nba*100:.1f}%`"
            )

    with tab_totals:
        st.write(
            f"**{home_team} Score Range (80% Confidence):** `{np.percentile(sim_home, 10):.1f}` to `{np.percentile(sim_home, 90):.1f}`"
        )
        st.write(
            f"**{away_team} Score Range (80% Confidence):** `{np.percentile(sim_away, 10):.1f}` to `{np.percentile(sim_away, 90):.1f}`"
        )
        st.write(
            f"**Game Combined Total Range (80% Confidence):** `{np.percentile(sim_home + sim_away, 10):.1f}` to `{np.percentile(sim_home + sim_away, 90):.1f}`"
        )
