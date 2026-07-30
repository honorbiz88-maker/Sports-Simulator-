import streamlit as st
import numpy as np
import pandas as pd
import requests
from datetime import datetime

# ---------------------------------------------------------
# 1. PAGE CONFIG & MOBILE STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="MLB Monte Carlo Capping Engine",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for polished mobile visual cards and badges
st.markdown("""
    <style>
    .stButton>button {
        border-radius: 10px;
        font-weight: 700;
        height: 3rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 800;
    }
    .status-badge-green {
        background-color: #d1e7dd;
        color: #0f5132;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 8px;
    }
    .status-badge-yellow {
        background-color: #fff3cd;
        color: #664d03;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 8px;
    }
    .status-badge-blue {
        background-color: #cff4fc;
        color: #055160;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 8px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚾ MLB Capping Engine")

MLB_TEAMS = [
    "Arizona Diamondbacks", "Atlanta Braves", "Baltimore Orioles", "Boston Red Sox",
    "Chicago Cubs", "Chicago White Sox", "Cincinnati Reds", "Cleveland Guardians",
    "Colorado Rockies", "Detroit Tigers", "Houston Astros", "Kansas City Royals",
    "Los Angeles Angels", "Los Angeles Dodgers", "Miami Marlins", "Milwaukee Brewers",
    "Minnesota Twins", "New York Mets", "New York Yankees", "Athletics",
    "Philadelphia Phillies", "Pittsburgh Pirates", "San Diego Padres", "San Francisco Giants",
    "Seattle Mariners", "St. Louis Cardinals", "Tampa Bay Rays", "Texas Rangers",
    "Toronto Blue Jays", "Washington Nationals"
]

BOOKMAKER_MAP = {
    "Novig (Exchange)": "novig",
    "FanDuel": "fanduel",
    "DraftKings": "draftkings",
    "BetMGM": "betmgm",
    "Bovada": "bovada",
    "Pinnacle": "pinnacle"
}

# ---------------------------------------------------------
# 2. PARK FACTORS & TEAM BASELINE DATABASE
# ---------------------------------------------------------
MLB_PARK_FACTORS = {
    "Arizona Diamondbacks": {"pf": 0.98, "temp": 72, "wind": 0},
    "Atlanta Braves": {"pf": 1.03, "temp": 82, "wind": 2},
    "Baltimore Orioles": {"pf": 1.05, "temp": 78, "wind": 3},
    "Boston Red Sox": {"pf": 1.06, "temp": 70, "wind": 4},
    "Chicago Cubs": {"pf": 1.02, "temp": 72, "wind": 5},
    "Chicago White Sox": {"pf": 1.01, "temp": 72, "wind": 3},
    "Cincinnati Reds": {"pf": 1.10, "temp": 76, "wind": 3},
    "Cleveland Guardians": {"pf": 0.97, "temp": 68, "wind": 4},
    "Colorado Rockies": {"pf": 1.25, "temp": 75, "wind": 2},
    "Detroit Tigers": {"pf": 0.96, "temp": 70, "wind": 3},
    "Houston Astros": {"pf": 0.99, "temp": 72, "wind": 0},
    "Kansas City Royals": {"pf": 1.06, "temp": 78, "wind": 4},
    "Los Angeles Angels": {"pf": 1.00, "temp": 74, "wind": 2},
    "Los Angeles Dodgers": {"pf": 1.02, "temp": 75, "wind": 2},
    "Miami Marlins": {"pf": 0.95, "temp": 72, "wind": 0},
    "Milwaukee Brewers": {"pf": 1.02, "temp": 72, "wind": 0},
    "Minnesota Twins": {"pf": 1.03, "temp": 70, "wind": 4},
    "New York Mets": {"pf": 0.96, "temp": 74, "wind": 3},
    "New York Yankees": {"pf": 1.03, "temp": 74, "wind": 3},
    "Athletics": {"pf": 1.08, "temp": 85, "wind": 5},
    "Philadelphia Phillies": {"pf": 1.07, "temp": 76, "wind": 3},
    "Pittsburgh Pirates": {"pf": 0.96, "temp": 72, "wind": 2},
    "San Diego Padres": {"pf": 0.94, "temp": 70, "wind": 3},
    "San Francisco Giants": {"pf": 0.92, "temp": 62, "wind": 6},
    "Seattle Mariners": {"pf": 0.88, "temp": 68, "wind": 0},
    "St. Louis Cardinals": {"pf": 0.95, "temp": 78, "wind": 2},
    "Tampa Bay Rays": {"pf": 0.94, "temp": 72, "wind": 0},
    "Texas Rangers": {"pf": 1.01, "temp": 72, "wind": 0},
    "Toronto Blue Jays": {"pf": 1.02, "temp": 72, "wind": 0},
    "Washington Nationals": {"pf": 0.99, "temp": 78, "wind": 2}
}

MLB_TEAM_PROFILES = {
    "Arizona Diamondbacks": {"wrc": 104, "sp_xfip": 4.10, "bp_xfip": 4.15},
    "Atlanta Braves": {"wrc": 110, "sp_xfip": 3.70, "bp_xfip": 3.80},
    "Baltimore Orioles": {"wrc": 112, "sp_xfip": 3.80, "bp_xfip": 3.85},
    "Boston Red Sox": {"wrc": 105, "sp_xfip": 4.05, "bp_xfip": 4.10},
    "Chicago Cubs": {"wrc": 106, "sp_xfip": 3.90, "bp_xfip": 4.00},
    "Chicago White Sox": {"wrc": 82, "sp_xfip": 4.65, "bp_xfip": 4.80},
    "Cincinnati Reds": {"wrc": 96, "sp_xfip": 4.25, "bp_xfip": 4.30},
    "Cleveland Guardians": {"wrc": 102, "sp_xfip": 3.85, "bp_xfip": 3.50},
    "Colorado Rockies": {"wrc": 85, "sp_xfip": 4.90, "bp_xfip": 5.10},
    "Detroit Tigers": {"wrc": 99, "sp_xfip": 3.75, "bp_xfip": 3.90},
    "Houston Astros": {"wrc": 111, "sp_xfip": 3.80, "bp_xfip": 3.75},
    "Kansas City Royals": {"wrc": 101, "sp_xfip": 3.85, "bp_xfip": 4.15},
    "Los Angeles Angels": {"wrc": 94, "sp_xfip": 4.35, "bp_xfip": 4.50},
    "Los Angeles Dodgers": {"wrc": 118, "sp_xfip": 3.55, "bp_xfip": 3.65},
    "Miami Marlins": {"wrc": 88, "sp_xfip": 4.40, "bp_xfip": 4.55},
    "Milwaukee Brewers": {"wrc": 103, "sp_xfip": 3.80, "bp_xfip": 3.60},
    "Minnesota Twins": {"wrc": 107, "sp_xfip": 3.95, "bp_xfip": 4.05},
    "New York Mets": {"wrc": 109, "sp_xfip": 3.85, "bp_xfip": 3.90},
    "New York Yankees": {"wrc": 116, "sp_xfip": 3.65, "bp_xfip": 3.70},
    "Athletics": {"wrc": 97, "sp_xfip": 4.20, "bp_xfip": 4.10},
    "Philadelphia Phillies": {"wrc": 112, "sp_xfip": 3.60, "bp_xfip": 3.75},
    "Pittsburgh Pirates": {"wrc": 90, "sp_xfip": 4.05, "bp_xfip": 4.20},
    "San Diego Padres": {"wrc": 108, "sp_xfip": 3.75, "bp_xfip": 3.60},
    "San Francisco Giants": {"wrc": 98, "sp_xfip": 3.80, "bp_xfip": 4.00},
    "Seattle Mariners": {"wrc": 95, "sp_xfip": 3.45, "bp_xfip": 3.70},
    "St. Louis Cardinals": {"wrc": 98, "sp_xfip": 4.15, "bp_xfip": 4.10},
    "Tampa Bay Rays": {"wrc": 100, "sp_xfip": 3.75, "bp_xfip": 3.80},
    "Texas Rangers": {"wrc": 104, "sp_xfip": 4.00, "bp_xfip": 4.25},
    "Toronto Blue Jays": {"wrc": 101, "sp_xfip": 4.00, "bp_xfip": 4.15},
    "Washington Nationals": {"wrc": 92, "sp_xfip": 4.45, "bp_xfip": 4.60}
}

# ---------------------------------------------------------
# 3. SECRETS & API KEY MANAGEMENT
# ---------------------------------------------------------
if "ODDS_API_KEY" in st.secrets:
    api_key = st.secrets["ODDS_API_KEY"]
else:
    api_key = st.sidebar.text_input("The Odds API Key", type="password")

# ---------------------------------------------------------
# 4. INDEPENDENT LAMBDA & MATHEMATICAL MODEL ENGINE
# ---------------------------------------------------------
def calculate_independent_lambda(
    team_wrc_plus,       # Offensive wRC+ vs starter hand (100 = MLB Avg)
    opp_starter_xfip,    # Opposing starter xFIP (4.10 = MLB Avg)
    opp_bullpen_xfip,    # Opposing bullpen xFIP (4.10 = MLB Avg)
    park_factor=1.00,    # Park factor (1.00 = Neutral)
    temp_fahrenheit=72,  # Game temp (°F)
    wind_out_mph=0       # Wind blowing out (mph)
):
    """
    Calculates team expected runs (Lambda) strictly from fundamental matchups:
    Lambda = League_Avg * Offensive_Factor * Pitching_Suppression * Environmental_Factor
    """
    LEAGUE_AVG_RUNS = 4.50
    LEAGUE_AVG_ERA = 4.10
    
    # 1. Hitting Production Factor vs Starter Hand
    O = float(team_wrc_plus) / 100.0
    
    # 2. Pitching Suppression Factor (60% Starter Weight / 40% Bullpen Weight)
    S = float(opp_starter_xfip) / LEAGUE_AVG_ERA
    B = float(opp_bullpen_xfip) / LEAGUE_AVG_ERA
    P = (0.60 * S) + (0.40 * B)
    
    # 3. Environmental Modifiers
    temp_adj = 1.0 + (((float(temp_fahrenheit) - 70.0) / 10.0) * 0.015)
    wind_adj = 1.0 + (float(wind_out_mph) * 0.008)
    weather_mult = temp_adj * wind_adj
    E = float(park_factor) * weather_mult
    
    # Final Independent Expected Runs
    expected_runs = LEAGUE_AVG_RUNS * O * P * E
    return round(expected_runs, 2)

def get_team_keyword(name):
    parts = name.strip().split()
    if len(parts) >= 2 and parts[-2].lower() in ["red", "white"]:
        return f"{parts[-2]} {parts[-1]}".lower()
    return parts[-1].lower()

def american_to_implied(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

@st.cache_data(ttl=180)
def fetch_mlb_daily_schedule(game_date_str):
    """Fetches daily schedule, starter info, and lineup status from official MLB Stats API."""
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date_str}&hydrate=probablePitcher,lineups"
    schedule = []
    
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            data = res.json()
            dates = data.get("dates", [])
            if dates:
                games = dates[0].get("games", [])
                for g in games:
                    teams_data = g.get("teams", {})
                    a_info = teams_data.get("away", {})
                    h_info = teams_data.get("home", {})
                    
                    away_name = a_info.get("team", {}).get("name", "")
                    home_name = h_info.get("team", {}).get("name", "")
                    
                    a_p = a_info.get("probablePitcher", {})
                    a_starter = f"{a_p.get('fullName', 'TBD')} ({a_p.get('pitchHand', {}).get('code', 'R')}HP)" if a_p else "TBD Pitcher"
                    
                    h_p = h_info.get("probablePitcher", {})
                    h_starter = f"{h_p.get('fullName', 'TBD')} ({h_p.get('pitchHand', {}).get('code', 'R')}HP)" if h_p else "TBD Pitcher"
                    
                    lineups = g.get("lineups", {})
                    has_home = len(lineups.get("homePlayers", [])) >= 9
                    has_away = len(lineups.get("awayPlayers", [])) >= 9
                    is_official = has_home and has_away
                    lineup_status = "🟢 Official 1-9 Lineups Confirmed" if is_official else "⚡ Lineups Pending — Using Morning Splits"
                    
                    schedule.append({
                        "label": f"{away_name} @ {home_name}",
                        "away_team": away_name,
                        "home_team": home_name,
                        "away_starter": a_starter,
                        "home_starter": h_starter,
                        "lineup_status": lineup_status,
                        "is_official": is_official
                    })
    except Exception:
        pass

    return schedule

@st.cache_data(ttl=120)
def fetch_live_odds_for_game(key, target_book_key, away_team, home_team):
    """Fetches bookmaker lines strictly for market comparison in Capping Report."""
    if not key:
        return -110, -110, 8.5, "⚠️ No API Key Saved"
    
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={key}&regions=us,us2,us_ex&markets=h2h,totals&oddsFormat=american"
    
    try:
        res = requests.get(url, timeout=8)
        if res.status_code != 200:
            return -110, -110, 8.5, f"⚠️ API Error {res.status_code}"
            
        games_data = res.json()
        if not games_data:
            return -110, -110, 8.5, "⚠️ No Odds Returned"
            
        away_kw = get_team_keyword(away_team)
        home_kw = get_team_keyword(home_team)

        for game in games_data:
            g_away = game.get("away_team", "")
            g_home = game.get("home_team", "")
            
            if away_kw == get_team_keyword(g_away) and home_kw == get_team_keyword(g_home):
                bookmakers = game.get("bookmakers", [])
                if not bookmakers:
                    return -110, -110, 8.5, "⚠️ No Bookmaker Lines Posted Yet"

                selected_bm = next((bm for bm in bookmakers if bm.get("key") == target_book_key), None)
                used_fallback = False
                
                if not selected_bm:
                    selected_bm = bookmakers[0]
                    used_fallback = True

                away_ml, home_ml, total_line = -110, -110, 8.5
                for market in selected_bm.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            if get_team_keyword(outcome.get("name", "")) == away_kw:
                                away_ml = outcome.get("price", -110)
                            elif get_team_keyword(outcome.get("name", "")) == home_kw:
                                home_ml = outcome.get("price", -110)
                    elif market.get("key") == "totals":
                        outcomes = market.get("outcomes", [])
                        if outcomes:
                            total_line = outcomes[0].get("point", 8.5)

                bm_title = selected_bm.get("title", target_book_key)
                if used_fallback:
                    return away_ml, home_ml, total_line, f"⚡ {target_book_key.upper()} N/A — Using {bm_title}"
                return away_ml, home_ml, total_line, f"🟢 Live Odds via {bm_title}"

        return -110, -110, 8.5, "⚠️ Game Not Found in Odds Feed"
    except Exception as e:
        return -110, -110, 8.5, f"⚠️ Connection Error: {str(e)}"

def run_monte_carlo(home_lambda, away_lambda, n_sims, var_ratio):
    """Runs Poisson Monte Carlo simulations to project win probabilities and run distributions."""
    home_runs = np.random.poisson(home_lambda * var_ratio, n_sims) / var_ratio
    away_runs = np.random.poisson(away_lambda * var_ratio, n_sims) / var_ratio
    
    ties = home_runs == away_runs
    home_runs[ties] += np.random.choice([1, 0], size=np.sum(ties), p=[0.54, 0.46])
    
    home_wins = np.sum(home_runs > away_runs)
    away_wins = np.sum(away_runs > home_runs)
    
    return home_wins / n_sims, away_wins / n_sims, np.mean(home_runs + away_runs), np.mean(home_runs), np.mean(away_runs)

if "wager_log" not in st.session_state:
    st.session_state.wager_log = []

# ---------------------------------------------------------
# 5. NAVIGATION TABS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Game Simulator", "🎯 Capping Report", "📝 Wager Log & CLV"])

# ---------------------------------------------------------
# TAB 1: GAME SIMULATOR
# ---------------------------------------------------------
with tab1:
    # --- CARD 1: MASTER SCHEDULE & BOOKMAKER SELECTION ---
    with st.container(border=True):
        st.markdown("##### 📅 Schedule & Odds Comparison Source")
        
        b_col, d_col = st.columns(2)
        with b_col:
            selected_book_label = st.selectbox("Preferred Bookmaker", options=list(BOOKMAKER_MAP.keys()), index=0)
            target_book_key = BOOKMAKER_MAP[selected_book_label]
            
        with d_col:
            selected_date = st.date_input("Game Date", value=datetime.today())
            
        date_str = selected_date.strftime("%Y-%m-%d")
        daily_schedule = fetch_mlb_daily_schedule(date_str)
        
        selected_game_info = None
        if daily_schedule:
            game_labels = [g["label"] for g in daily_schedule]
            selected_label = st.selectbox("🎯 Select Game from MLB Schedule", options=game_labels)
            selected_game_info = next((g for g in daily_schedule if g["label"] == selected_label), daily_schedule[0])
        else:
            st.warning("⚠️ Fetching MLB Schedule...")

    # Set Matchup Defaults from MLB Stats API
    if selected_game_info:
        def_away = selected_game_info["away_team"]
        def_home = selected_game_info["home_team"]
        def_away_starter = selected_game_info["away_starter"]
        def_home_starter = selected_game_info["home_starter"]
        lineup_status_msg = selected_game_info["lineup_status"]
        lineups_are_official = selected_game_info["is_official"]
    else:
        def_away, def_home = "Chicago Cubs", "St. Louis Cardinals"
        def_away_starter, def_home_starter = "Javier Assad (RHP)", "Andre Pallante (RHP)"
        lineup_status_msg, lineups_are_official = "⚡ Lineups Pending", False

    # Dynamic Venue Environmental Lookup for Home Team
    home_venue_defaults = MLB_PARK_FACTORS.get(def_home, {"pf": 1.00, "temp": 75, "wind": 0})
    
    # Dynamic Team Performance Stats Lookup
    default_away_profile = MLB_TEAM_PROFILES.get(def_away, {"wrc": 100, "sp_xfip": 4.10, "bp_xfip": 4.10})
    default_home_profile = MLB_TEAM_PROFILES.get(def_home, {"wrc": 100, "sp_xfip": 4.10, "bp_xfip": 4.10})

    # Fetch Bookmaker lines (strictly for market comparison)
    live_away_ml, live_home_ml, live_total, odds_status_msg = fetch_live_odds_for_game(
        api_key, target_book_key, def_away, def_home
    )

    # --- CARD 2: INDEPENDENT MODEL ENGINE (LAMBDA BUILDER) ---
    with st.container(border=True):
        st.markdown("##### 🏟️ Independent Model Inputs (Matchup & Pitching)")
        
        if lineups_are_official:
            st.markdown(f'<div class="status-badge-green">{lineup_status_msg}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-badge-yellow">{lineup_status_msg}</div>', unsafe_allow_html=True)

        # 1. Define team selectboxes & starter inputs FIRST
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            away_idx = MLB_TEAMS.index(def_away) if def_away in MLB_TEAMS else 0
            away_team = st.selectbox("Away Team", options=MLB_TEAMS, index=away_idx)
            away_starter = st.text_input("Away Starter", value=def_away_starter)
        with t_col2:
            home_idx = MLB_TEAMS.index(def_home) if def_home in MLB_TEAMS else 0
            home_team = st.selectbox("Home Team", options=MLB_TEAMS, index=home_idx)
            home_starter = st.text_input("Home Starter", value=def_home_starter)

        st.markdown("---")

        # 2. Re-query profile for newly selected team dropdowns
        curr_away_profile = MLB_TEAM_PROFILES.get(away_team, default_away_profile)
        curr_home_profile = MLB_TEAM_PROFILES.get(home_team, default_home_profile)

        c1, c2 = st.columns(2)
        with c1:
            away_wrc = st.number_input(f"{away_team} wRC+ vs Starter Hand", value=int(curr_away_profile["wrc"]), step=1)
            home_starter_xfip = st.number_input(f"{home_team} Starter xFIP", value=float(curr_home_profile["sp_xfip"]), step=0.05)
            home_bullpen_xfip = st.number_input(f"{home_team} Bullpen xFIP", value=float(curr_home_profile["bp_xfip"]), step=0.05)
            
        with c2:
            home_wrc = st.number_input(f"{home_team} wRC+ vs Starter Hand", value=int(curr_home_profile["wrc"]), step=1)
            away_starter_xfip = st.number_input(f"{away_team} Starter xFIP", value=float(curr_away_profile["sp_xfip"]), step=0.05)
            away_bullpen_xfip = st.number_input(f"{away_team} Bullpen xFIP", value=float(curr_away_profile["bp_xfip"]), step=0.05)

    # --- CARD 3: DYNAMIC ENVIRONMENT & PARK CONDITIONS ---
    with st.container(border=True):
        st.markdown(f"##### 🌡️ Environmental & Park Conditions ({home_team} Home Park)")
        env1, env2, env3 = st.columns(3)
        with env1:
            park_factor = st.slider("Park Factor (1.00 = Neutral)", min_value=0.85, max_value=1.30, value=float(home_venue_defaults["pf"]), step=0.01)
        with env2:
            temp_f = st.slider("Temperature (°F)", min_value=40, max_value=105, value=int(home_venue_defaults["temp"]), step=1)
        with env3:
            wind_out = st.slider("Wind Out (mph)", min_value=-15, max_value=25, value=int(home_venue_defaults["wind"]), step=1)

    # DYNAMIC CALCULATED EXPECTED RUNS (INDEPENDENT LAMBDA FORMULA)
    calculated_away_lambda = calculate_independent_lambda(
        team_wrc_plus=away_wrc,
        opp_starter_xfip=home_starter_xfip,
        opp_bullpen_xfip=home_bullpen_xfip,
        park_factor=park_factor,
        temp_fahrenheit=temp_f,
        wind_out_mph=wind_out
    )
    
    calculated_home_lambda = calculate_independent_lambda(
        team_wrc_plus=home_wrc,
        opp_starter_xfip=away_starter_xfip,
        opp_bullpen_xfip=away_bullpen_xfip,
        park_factor=park_factor,
        temp_fahrenheit=temp_f,
        wind_out_mph=wind_out
    )

    # Display Independent Runs Summary Card
    with st.container(border=True):
        st.markdown("##### 🧮 Calculated Independent Expected Runs (λ)")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.metric(f"{away_team} λ", f"{calculated_away_lambda:.2f} Runs")
        with r2:
            st.metric(f"{home_team} λ", f"{calculated_home_lambda:.2f} Runs")
        with r3:
            st.metric("Model Baseline Total", f"{calculated_away_lambda + calculated_home_lambda:.2f} Runs")

    # --- CARD 4: BOOKMAKER COMPARISON LINES ---
    with st.container(border=True):
        st.markdown("##### 💰 Bookmaker Lines (For Market Comparison)")
        st.markdown(f'<div class="status-badge-blue">{odds_status_msg}</div>', unsafe_allow_html=True)
        
        m1, m2, m3 = st.columns(3)
        with m1:
            away_ml_odds = st.number_input(f"{away_team} ML", value=int(live_away_ml))
        with m2:
            home_ml_odds = st.number_input(f"{home_team} ML", value=int(live_home_ml))
        with m3:
            market_total = st.number_input("Market Total Line", value=float(live_total), step=0.5)

    # --- ADVANCED MODEL TUNING EXPANDER ---
    with st.expander("⚙️ Advanced Monte Carlo Simulation Settings"):
        e1, e2 = st.columns(2)
        with e1:
            iterations = st.number_input("Iterations", min_value=10000, max_value=1000000, value=1000000, step=90000)
        with e2:
            variance_ratio = st.slider("Run Variance Scale Factor", min_value=1.0, max_value=1.6, value=1.3, step=0.05)

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 Run Monte Carlo Simulation", use_container_width=True, type="primary"):
        hw_pct, aw_pct, sim_total, exp_home, exp_away = run_monte_carlo(
            calculated_home_lambda, calculated_away_lambda, iterations, variance_ratio
        )
        
        st.session_state.last_sim = {
            "date": date_str,
            "away_team": away_team,
            "home_team": home_team,
            "away_starter": away_starter,
            "home_starter": home_starter,
            "hw_pct": hw_pct,
            "aw_pct": aw_pct,
            "sim_total": sim_total,
            "exp_home": exp_home,
            "exp_away": exp_away,
            "away_ml_odds": away_ml_odds,
            "home_ml_odds": home_ml_odds,
            "market_total": market_total,
            "lineup_status": lineup_status_msg,
            "odds_status": odds_status_msg,
            "iterations": iterations
        }
        st.success("Simulation complete! Check the **🎯 Capping Report** tab.")

# ---------------------------------------------------------
# TAB 2: CAPPING REPORT
# ---------------------------------------------------------
with tab2:
    if "last_sim" not in st.session_state:
        st.info("👈 Run a simulation in the **Game Simulator** tab first.")
    else:
        sim = st.session_state.last_sim
        
        # Matchup Header Card
        with st.container(border=True):
            st.subheader("🎯 CAPPING REPORT")
            st.caption(f"📅 {sim['date']} | {sim['away_team']} ({sim['away_starter']}) @ {sim['home_team']} ({sim['home_starter']})")
            st.caption(f"Status: {sim['lineup_status']} | Market Source: {sim['odds_status']}")

        # Primary Projections KPI Card
        with st.container(border=True):
            st.markdown("##### 📈 Projected Game Outcomes")
            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Projected Score", f"{sim['exp_away']:.2f} - {sim['exp_home']:.2f}")
            with k2:
                st.metric("Projected Total", f"{sim['sim_total']:.2f}", delta=f"{sim['sim_total'] - sim['market_total']:+.2f} vs Line ({sim['market_total']})")
            with k3:
                fav_team = sim['away_team'] if sim['aw_pct'] > sim['hw_pct'] else sim['home_team']
                fav_pct = max(sim['aw_pct'], sim['hw_pct']) * 100
                st.metric("Model Favorite", f"{fav_team}", f"{fav_pct:.1f}%")

        # Direct Model Picks Card
        with st.container(border=True):
            st.markdown("##### 🎯 Direct Model Picks")
            p1, p2, p3 = st.columns(3)
            with p1:
                ml_pick = sim['away_team'] if sim['aw_pct'] > 0.50 else sim['home_team']
                st.success(f"**Moneyline:** {ml_pick}")
            with p2:
                tot_pick = "OVER" if sim['sim_total'] > sim['market_total'] else "UNDER"
                st.success(f"**Game Total:** {tot_pick} {sim['market_total']}")
            with p3:
                away_tt_pick = "OVER" if sim['exp_away'] > (sim['market_total'] / 2) else "UNDER"
                st.info(f"**{sim['away_team']} Team Total:** {away_tt_pick} {sim['market_total']/2:.1f}")

        # Market Edges Card
        with st.container(border=True):
            st.markdown("##### 🔥 Market Edges vs Bookmaker")
            home_implied = american_to_implied(sim['home_ml_odds'])
            away_implied = american_to_implied(sim['away_ml_odds'])
            
            away_edge = (sim['aw_pct'] - away_implied) * 100
            home_edge = (sim['hw_pct'] - home_implied) * 100
            
            e1, e2 = st.columns(2)
            with e1:
                st.write(f"**{sim['away_team']} ML ({sim['away_ml_odds']:+d}):**")
                st.write(f"Model: **{sim['aw_pct']*100:.1f}%** | Implied: **{away_implied*100:.1f}%**")
                if away_edge > 0:
                    st.success(f"🔥 Edge: +{away_edge:.1f}% EV")
                else:
                    st.caption(f"No Edge ({away_edge:.1f}%)")
                    
            with e2:
                st.write(f"**{sim['home_team']} ML ({sim['home_ml_odds']:+d}):**")
                st.write(f"Model: **{sim['hw_pct']*100:.1f}%** | Implied: **{home_implied*100:.1f}%**")
                if home_edge > 0:
                    st.success(f"🔥 Edge: +{home_edge:.1f}% EV")
                else:
                    st.caption(f"No Edge ({home_edge:.1f}%)")

        # Copyable Raw Text Summary Card
        with st.container(border=True):
            st.markdown("##### 📋 Raw Text Summary (Mobile Copy)")
            summary_text = (
                f"🎯 CAPPING REPORT (MLB)\n"
                f"Date: {sim['date']} | Matchup: {sim['away_team']} ({sim['away_starter']}) @ {sim['home_team']} ({sim['home_starter']})\n"
                f"Lineup: {sim['lineup_status']}\n"
                f"----------------------------------------\n"
                f"• Projected Score: {sim['away_team']} {sim['exp_away']:.2f} - {sim['home_team']} {sim['exp_home']:.2f}\n"
                f"• Projected Total: {sim['sim_total']:.2f} (Market Line: {sim['market_total']})\n"
                f"• {sim['away_team']} Win Prob: {sim['aw_pct']*100:.1f}%\n"
                f"• {sim['home_team']} Win Prob: {sim['hw_pct']*100:.1f}%\n"
                f"----------------------------------------\n"
                f"Simulated over {sim['iterations']:,} Monte Carlo iterations."
            )
            st.code(summary_text, language="text")

# ---------------------------------------------------------
# TAB 3: WAGER LOG & CLV TRACKER
# ---------------------------------------------------------
with tab3:
    with st.container(border=True):
        st.markdown("##### 📝 Log New Wager")
        with st.form("add_wager_form"):
            w_col1, w_col2, w_col3 = st.columns(3)
            with w_col1:
                w_date = st.date_input("Bet Date", value=selected_date)
                w_matchup = st.text_input("Matchup", value=f"{def_away} @ {def_home}")
            with w_col2:
                w_pick = st.text_input("Pick Taken", value=f"{def_away} ML")
                w_odds = st.number_input("Placed Odds", value=-110)
            with w_col3:
                w_stake = st.number_input("Stake ($)", value=1.00, step=0.25)
                w_closing = st.number_input("Closing Odds (CLV)", value=-120)
                
            submitted = st.form_submit_button("Log Wager", use_container_width=True)
            if submitted:
                st.session_state.wager_log.append({
                    "Date": w_date.strftime("%Y-%m-%d"),
                    "Matchup": w_matchup,
                    "Pick": w_pick,
                    "Placed Odds": w_odds,
                    "Stake": f"${w_stake:.2f}",
                    "Closing Odds": w_closing,
                    "CLV Edge": f"{(american_to_implied(w_closing) - american_to_implied(w_odds))*100:+.2f}%"
                })
                st.success("Wager logged successfully!")

    with st.container(border=True):
        st.markdown("##### 📊 Active Wager Log")
        if st.session_state.wager_log:
            st.dataframe(pd.DataFrame(st.session_state.wager_log), use_container_width=True)
        else:
            st.info("No wagers logged yet.")
