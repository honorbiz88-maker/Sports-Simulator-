import streamlit as st
import numpy as np
import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# --- API KEY STORAGE SETUP ---
KEY_FILE = "weather_key.txt"

def load_api_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r") as f:
            return f.read().strip()
    return ""

def save_api_key(key):
    with open(KEY_FILE, "w") as f:
        f.write(key.strip())
# -----------------------------

# ---------------------------------------------------------
# 1. PAGE CONFIG & MOBILE-OPTIMIZED STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="Elite MLB Capping Engine",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .stButton>button {
        border-radius: 10px;
        font-weight: 700;
        height: 3rem;
        width: 100%;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 800;
    }
    .status-badge-green { background-color: #d1e7dd; color: #0f5132; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; display: inline-block; margin-bottom: 8px;}
    .status-badge-yellow { background-color: #fff3cd; color: #664d03; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; display: inline-block; margin-bottom: 8px;}
    .fatigue-box { padding: 12px; border-radius: 8px; border: 1px solid #555; background-color: transparent; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚾ Elite MLB Capping Engine")

# ---------------------------------------------------------
# 2. STRICT BASELINE DATABASES (GPS, HEADINGS, DOMES)
# ---------------------------------------------------------
MLB_VENUES = {
    "Arizona Diamondbacks": {"pf": 0.98, "lat": 33.4455, "lon": -112.0667, "heading": 0, "dome": True},
    "Atlanta Braves": {"pf": 1.03, "lat": 33.8908, "lon": -84.4678, "heading": 135, "dome": False},
    "Baltimore Orioles": {"pf": 1.05, "lat": 39.2840, "lon": -76.6215, "heading": 16, "dome": False},
    "Boston Red Sox": {"pf": 1.06, "lat": 42.3467, "lon": -71.0972, "heading": 58, "dome": False},
    "Chicago Cubs": {"pf": 1.02, "lat": 41.9484, "lon": -87.6553, "heading": 45, "dome": False},
    "Chicago White Sox": {"pf": 1.01, "lat": 41.8300, "lon": -87.6339, "heading": 135, "dome": False},
    "Cincinnati Reds": {"pf": 1.10, "lat": 39.0979, "lon": -84.5072, "heading": 135, "dome": False},
    "Cleveland Guardians": {"pf": 0.97, "lat": 41.4962, "lon": -81.6852, "heading": 0, "dome": False},
    "Colorado Rockies": {"pf": 1.25, "lat": 39.7559, "lon": -104.9942, "heading": 0, "dome": False},
    "Detroit Tigers": {"pf": 0.96, "lat": 42.3390, "lon": -83.0485, "heading": 135, "dome": False},
    "Houston Astros": {"pf": 0.99, "lat": 29.7570, "lon": -95.3555, "heading": 0, "dome": True},
    "Kansas City Royals": {"pf": 1.06, "lat": 39.0517, "lon": -94.4803, "heading": 45, "dome": False},
    "Los Angeles Angels": {"pf": 1.00, "lat": 33.8003, "lon": -117.8827, "heading": 45, "dome": False},
    "Los Angeles Dodgers": {"pf": 1.02, "lat": 34.0739, "lon": -118.2400, "heading": 16, "dome": False},
    "Miami Marlins": {"pf": 0.95, "lat": 25.7781, "lon": -80.2198, "heading": 90, "dome": True},
    "Milwaukee Brewers": {"pf": 1.02, "lat": 43.0280, "lon": -87.9712, "heading": 135, "dome": True},
    "Minnesota Twins": {"pf": 1.03, "lat": 44.9817, "lon": -93.2775, "heading": 45, "dome": False},
    "New York Mets": {"pf": 0.96, "lat": 40.7571, "lon": -73.8458, "heading": 45, "dome": False},
    "New York Yankees": {"pf": 1.03, "lat": 40.8296, "lon": -73.9262, "heading": 65, "dome": False},
    "Athletics": {"pf": 1.08, "lat": 38.5816, "lon": -121.4944, "heading": 0, "dome": False}, 
    "Philadelphia Phillies": {"pf": 1.07, "lat": 39.9061, "lon": -75.1665, "heading": 16, "dome": False},
    "Pittsburgh Pirates": {"pf": 0.96, "lat": 40.4469, "lon": -80.0057, "heading": 135, "dome": False},
    "San Diego Padres": {"pf": 0.94, "lat": 32.7076, "lon": -117.1570, "heading": 0, "dome": False},
    "San Francisco Giants": {"pf": 0.92, "lat": 37.7786, "lon": -122.3893, "heading": 90, "dome": False},
    "Seattle Mariners": {"pf": 0.88, "lat": 47.5914, "lon": -122.3325, "heading": 45, "dome": True},
    "St. Louis Cardinals": {"pf": 0.95, "lat": 38.6226, "lon": -90.1928, "heading": 90, "dome": False},
    "Tampa Bay Rays": {"pf": 0.94, "lat": 27.7682, "lon": -82.6534, "heading": 45, "dome": True},
    "Texas Rangers": {"pf": 1.01, "lat": 32.7511, "lon": -97.0825, "heading": 90, "dome": True},
    "Toronto Blue Jays": {"pf": 1.02, "lat": 43.6414, "lon": -79.3894, "heading": 0, "dome": True},
    "Washington Nationals": {"pf": 0.99, "lat": 38.8730, "lon": -77.0074, "heading": 45, "dome": False}
}

BULLPEN_ERA = {
    "Arizona Diamondbacks": 4.15, "Atlanta Braves": 3.80, "Baltimore Orioles": 3.85, "Boston Red Sox": 4.10, "Chicago Cubs": 4.00, 
    "Chicago White Sox": 4.80, "Cincinnati Reds": 4.30, "Cleveland Guardians": 3.50, "Colorado Rockies": 5.10, "Detroit Tigers": 3.90, 
    "Houston Astros": 3.75, "Kansas City Royals": 4.15, "Los Angeles Angels": 4.50, "Los Angeles Dodgers": 3.65, "Miami Marlins": 4.55,
    "Milwaukee Brewers": 3.60, "Minnesota Twins": 4.05, "New York Mets": 3.90, "New York Yankees": 3.70, "Athletics": 4.10, 
    "Philadelphia Phillies": 3.75, "Pittsburgh Pirates": 4.20, "San Diego Padres": 3.60, "San Francisco Giants": 4.00,
    "Seattle Mariners": 3.70, "St. Louis Cardinals": 4.10, "Tampa Bay Rays": 3.80, "Texas Rangers": 4.25, "Toronto Blue Jays": 4.15, 
    "Washington Nationals": 4.60
}

# ---------------------------------------------------------
# 3. HIGH-SPEED MLB & WEATHER API PIPELINES
# ---------------------------------------------------------
@st.cache_data(ttl=180)
def fetch_mlb_daily_schedule(game_date_str):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date_str}&hydrate=probablePitcher,lineups,officials"
    res = requests.get(url, timeout=6)
    res.raise_for_status()
    
    schedule = []
    data = res.json()
    dates = data.get("dates", [])
    if not dates:
        raise ValueError(f"MLB Stats API returned no games for date: {game_date_str}")
        
    for g in dates[0].get("games", []):
        away_name = g.get("teams", {}).get("away", {}).get("team", {}).get("name")
        home_name = g.get("teams", {}).get("home", {}).get("team", {}).get("name")
        away_id = g.get("teams", {}).get("away", {}).get("team", {}).get("id")
        home_id = g.get("teams", {}).get("home", {}).get("team", {}).get("id")
        
        a_p = g.get("teams", {}).get("away", {}).get("probablePitcher", {})
        a_hand = a_p.get("pitchHand", {}).get("code", "R") if a_p else "R"
        a_starter = f"{a_p.get('fullName', 'TBD')} ({a_hand}HP)" if a_p else "TBD Pitcher"
        
        h_p = g.get("teams", {}).get("home", {}).get("probablePitcher", {})
        h_hand = h_p.get("pitchHand", {}).get("code", "R") if h_p else "R"
        h_starter = f"{h_p.get('fullName', 'TBD')} ({h_hand}HP)" if h_p else "TBD Pitcher"
        
        lineups = g.get("lineups", {})
        is_official = len(lineups.get("homePlayers", [])) >= 9 and len(lineups.get("awayPlayers", [])) >= 9
        
        hp_umpire = "TBD / Unassigned"
        for official in g.get("officials", []):
            if official.get("officialType") == "Home Plate":
                hp_umpire = official.get("official", {}).get("fullName", "TBD")
                break
                
        schedule.append({
            "label": f"{away_name} @ {home_name}",
            "away_team": away_name, "home_team": home_name,
            "away_id": away_id, "home_id": home_id,
            "away_starter": a_starter, "home_starter": h_starter,
            "away_p_id": a_p.get("id") if a_p else None, "home_p_id": h_p.get("id") if h_p else None,
            "away_p_hand": a_hand, "home_p_hand": h_hand,
            "hp_umpire": hp_umpire,
            "game_time": g.get("gameDate"),
            "lineup_status": "🟢 Official Lineups Confirmed" if is_official else "⚡ Lineups Pending",
            "is_official": is_official
        })
    return schedule

@st.cache_data(ttl=900)
def fetch_live_weather(lat, lon, heading, is_dome, api_key):
    if is_dome or not api_key:
        return 72 if is_dome else 78, 0, "Calm / Cross / Dome"
        
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=imperial"
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            return 78, 0, "Calm / Cross / Dome"
            
        data = res.json()
        temp = data.get("main", {}).get("temp", 78)
        wind_speed = data.get("wind", {}).get("speed", 0)
        wind_deg = data.get("wind", {}).get("deg", 0)
        
        diff = (wind_deg - heading) % 360
        
        if diff > 315 or diff < 45:
            wind_dir = "Blowing In"
        elif 135 < diff < 225:
            wind_dir = "Blowing Out"
        else:
            wind_dir = "Calm / Cross / Dome"
            
        return int(temp), int(wind_speed), wind_dir
    except:
        return 78, 0, "Calm / Cross / Dome"

@st.cache_data(ttl=3600)
def fetch_live_stats(team_id, pitcher_id, opposing_pitcher_hand):
    team_ops, pitcher_fip = None, 4.10
    current_year = datetime.today().year
    
    l7_ops, l7_bullpen_era = None, None
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    if team_id:
        try:
            sit_code = 'vl' if opposing_pitcher_hand == 'L' else 'vr'
            split_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=statSplits&group=hitting&season={current_year}&sitCodes={sit_code}"
            res = requests.get(split_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if 'stats' in data and len(data['stats']) > 0 and len(data['stats'][0].get('splits', [])) > 0:
                    team_ops = float(data['stats'][0]['splits'][0]['stat']['ops'])
            
            l7_hit_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=byDateRange&group=hitting&startDate={start_date}&endDate={end_date}"
            res_l7 = requests.get(l7_hit_url, timeout=5)
            if res_l7.status_code == 200:
                 data_l7 = res_l7.json()
                 if 'stats' in data_l7 and len(data_l7['stats']) > 0 and len(data_l7['stats'][0].get('splits', [])) > 0:
                     l7_ops = float(data_l7['stats'][0]['splits'][0]['stat']['ops'])
                     
            l7_pitch_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=byDateRange&group=pitching&sitCodes=rp&startDate={start_date}&endDate={end_date}"
            res_bp = requests.get(l7_pitch_url, timeout=5)
            if res_bp.status_code == 200:
                 data_bp = res_bp.json()
                 if 'stats' in data_bp and len(data_bp['stats']) > 0 and len(data_bp['stats'][0].get('splits', [])) > 0:
                     l7_bullpen_era = float(data_bp['stats'][0]['splits'][0]['stat']['era'])
        except:
            pass
            
    if pitcher_id:
        try:
            res = requests.get(f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}?hydrate=stats(group=[pitching],type=[season,career],season={current_year})", timeout=5)
            if res.status_code == 200:
                data = res.json()
                stats_list = data.get('people', [{}])[0].get('stats', [])
                for stat_group in stats_list:
                    if stat_group.get('type', {}).get('displayName') in ['season', 'career'] and len(stat_group.get('splits', [])) > 0:
                        p_stats = stat_group['splits'][0]['stat']
                        hr = float(p_stats.get('homeRuns', 0))
                        bb = float(p_stats.get('baseOnBalls', 0))
                        hbp = float(p_stats.get('hitBatsmen', 0))
                        k = float(p_stats.get('strikeOuts', 0))
                        ip = float(p_stats.get('inningsPitched', 0.1))
                        if ip > 0:
                            pitcher_fip = ((13 * hr) + (3 * (bb + hbp)) - (2 * k)) / ip + 3.15
                        break
        except:
            pass
            
    return team_ops, l7_ops, round(pitcher_fip, 2) if pitcher_fip else None, l7_bullpen_era

@st.cache_data(ttl=3600)
def calculate_schedule_fatigue(team_id, game_date_str, today_is_home, today_game_time_str):
    game_date = datetime.strptime(game_date_str, "%Y-%m-%d")
    start_date = (game_date - timedelta(days=10)).strftime("%Y-%m-%d")
    yesterday_str = (game_date - timedelta(days=1)).strftime("%Y-%m-%d")
    
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId={team_id}&startDate={start_date}&endDate={yesterday_str}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            return 1.00, "Standard Routine"
            
        data = res.json()
        played_dates = []
        last_game_time_str = None
        last_game_was_home = None
        
        for d in data.get("dates", []):
            played_dates.append(d["date"])
            if d["date"] == yesterday_str:
                game = d["games"][0]
                last_game_time_str = game.get("gameDate")
                last_game_was_home = game["teams"]["home"]["team"]["id"] == team_id

        if yesterday_str not in played_dates:
            return 1.02, "Optimal (Rested)"
            
        consecutive_days = 0
        for i in range(1, 11):
            check_date = (game_date - timedelta(days=i)).strftime("%Y-%m-%d")
            if check_date in played_dates:
                consecutive_days += 1
            else:
                break
                
        is_exhausted = False
        if consecutive_days >= 10:
            is_exhausted = True
            
        if last_game_time_str and today_game_time_str:
            last_dt = datetime.strptime(last_game_time_str, "%Y-%m-%dT%H:%M:%SZ")
            today_dt = datetime.strptime(today_game_time_str, "%Y-%m-%dT%H:%M:%SZ")
            venue_changed = last_game_was_home != today_is_home
            if not last_game_was_home and not today_is_home: venue_changed = True 
            turnaround_hours = (today_dt - last_dt).total_seconds() / 3600
            
            if turnaround_hours < 18 and venue_changed:
                is_exhausted = True
                
        if is_exhausted:
            return 0.94, "Exhausted (Brutal Turnaround / 10+ Days)"
        elif consecutive_days >= 7:
            return 0.97, f"Tired ({consecutive_days} Days in a row)"
        else:
            return 1.00, f"Standard ({consecutive_days} Days playing)"
    except Exception:
        return 1.00, "Standard"

# ---------------------------------------------------------
# 4. OVERHAULED SABERMETRIC MATCHUP ENGINE (HEAVY STARTER ANCHOR)
# ---------------------------------------------------------
def calculate_true_matchup_lambda(team_ops_season, team_ops_l7, opp_starter_fip, opp_bullpen_era_season, opp_bullpen_era_l7, park_factor, temp_f, ump_factor, wind_speed, wind_dir, team_schedule_factor, is_f5):
    LEAGUE_R9 = 4.40
    LEAGUE_OPS = 0.715
    
    adj_team_ops = team_ops_season
    if team_ops_l7 and team_ops_season:
        adj_team_ops = (team_ops_season * 0.75) + (team_ops_l7 * 0.25)
        
    adj_bullpen_era = opp_bullpen_era_season
    if opp_bullpen_era_l7 and opp_bullpen_era_season:
        adj_bullpen_era = (opp_bullpen_era_season * 0.75) + (opp_bullpen_era_l7 * 0.25)
    
    team_r9 = (float(adj_team_ops) / LEAGUE_OPS) * LEAGUE_R9
    
    # 75% Starter / 25% Bullpen anchor so disaster pitchers heavily impact model
    starter_ra9 = float(opp_starter_fip) * 1.08
    bullpen_ra9 = float(adj_bullpen_era) * 1.08
    
    if is_f5:
        game_ra9 = starter_ra9
        raw_matchup_runs = ((team_r9 * game_ra9) / LEAGUE_R9) * (5.0 / 9.0)
    else:
        game_ra9 = (starter_ra9 * 0.75) + (bullpen_ra9 * 0.25)
        raw_matchup_runs = (team_r9 * game_ra9) / LEAGUE_R9

    temp_delta = float(temp_f) - 72.0
    temp_mult = 1.0 + (temp_delta * 0.004)
    
    wind_mult = 1.00
    if wind_dir == "Blowing Out":
        wind_mult = 1.00 + (float(wind_speed) * 0.005)
    elif wind_dir == "Blowing In":
        wind_mult = max(0.80, 1.00 - (float(wind_speed) * 0.005))
    
    final_lambda = raw_matchup_runs * float(park_factor) * temp_mult * float(ump_factor) * wind_mult * float(team_schedule_factor)
    return max(0.50, round(final_lambda, 2))

def run_monte_carlo(home_lambda, away_lambda, n_sims, is_f5):
    dispersion = 2.1
    home_shape = home_lambda / (dispersion - 1.0)
    home_scale = dispersion - 1.0
    away_shape = away_lambda / (dispersion - 1.0)
    away_scale = dispersion - 1.0
    
    home_lambdas_sim = np.random.gamma(shape=home_shape, scale=home_scale, size=n_sims)
    away_lambdas_sim = np.random.gamma(shape=away_shape, scale=away_scale, size=n_sims)
    
    home_runs = np.random.poisson(home_lambdas_sim)
    away_runs = np.random.poisson(away_lambdas_sim)
    
    home_wins = np.sum(home_runs > away_runs)
    away_wins = np.sum(away_runs > home_runs)
    ties = np.sum(home_runs == away_runs)
    
    if not is_f5: 
        home_wins += (ties * 0.525)
        away_wins += (ties * 0.475)
            
    return home_wins / n_sims, away_wins / n_sims, np.mean(home_runs + away_runs), np.mean(home_runs), np.mean(away_runs)

# ---------------------------------------------------------
# 5. UI LAYOUT & EXECUTION
# ---------------------------------------------------------
tab1, tab2 = st.tabs(["📊 Game Capping Engine", "🎯 Detailed Matchup Report"])

with tab1:
    with st.container(border=True):
        st.markdown("##### 🔑 API Integration")
        saved_key = load_api_key()
        openweather_api_key = st.text_input("OpenWeather API Key (Saved automatically)", value=saved_key, type="password")
        
        if openweather_api_key and openweather_api_key != saved_key:
            save_api_key(openweather_api_key)

    with st.container(border=True):
        st.markdown("##### 📅 Schedule & Scope Selection")
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            market_scope = st.radio("Capping Scope", options=["Full Game (9-Inn)", "First 5 Innings (F5)"], index=0, horizontal=True)
            is_f5_mode = "First 5" in market_scope
        with m_col2:
            date_str = st.date_input("Game Date", value=datetime.today()).strftime("%Y-%m-%d")
            
        try:
            daily_schedule = fetch_mlb_daily_schedule(date_str)
            selected_label = st.selectbox("🎯 Select Game from MLB Schedule", options=[g["label"] for g in daily_schedule])
            game_info = next((g for g in daily_schedule if g["label"] == selected_label), daily_schedule[0])
        except Exception as e:
            st.error(str(e))
            st.stop()

    def_away, def_home = game_info["away_team"], game_info["home_team"]
    def_away_p_hand, def_home_p_hand = game_info["away_p_hand"], game_info["home_p_hand"]
    
    with st.spinner("Compiling Platoon Splits and FIP..."):
        away_ops, away_l7_ops, away_starter_fip, away_l7_bp_era = fetch_live_stats(game_info["away_id"], game_info["away_p_id"], def_home_p_hand)
        home_ops, home_l7_ops, home_starter_fip, home_l7_bp_era = fetch_live_stats(game_info["home_id"], game_info["home_p_id"], def_away_p_hand)

    with st.spinner("Analyzing Logistics & Travel Schedules..."):
        away_schedule_factor, away_sch_status = calculate_schedule_fatigue(game_info["away_id"], date_str, False, game_info["game_time"])
        home_schedule_factor, home_sch_status = calculate_schedule_fatigue(game_info["home_id"], date_str, True, game_info["game_time"])

    venue_info = MLB_VENUES.get(def_home, {"pf": 1.00, "lat": 0, "lon": 0, "heading": 0, "dome": False})
    with st.spinner("Pulling Live Weather Vectors..."):
        live_temp, live_wind_speed, live_wind_dir = fetch_live_weather(
            venue_info["lat"], venue_info["lon"], venue_info["heading"], venue_info["dome"], openweather_api_key
        )

    away_ops_missing = away_ops is None
    home_ops_missing = home_ops is None

    if away_starter_fip is None: away_starter_fip = 4.10
    if home_starter_fip is None: home_starter_fip = 4.10
    away_bullpen_era_db = BULLPEN_ERA.get(def_away, 4.10)
    home_bullpen_era_db = BULLPEN_ERA.get(def_home, 4.10)

    dyn_key = f"{def_away}_{def_home}_{is_f5_mode}"

    if away_ops_missing or home_ops_missing:
        st.error("🚨 **Accuracy Alert:** The MLB API is missing Platoon Split data (OPS vs LHP/RHP) for one or both teams. Silent fallback is disabled to preserve model accuracy. Please enter the missing OPS manually to unlock the engine.")

    with st.container(border=True):
        st.markdown(f"##### 🏟️ Auto-Pulled Official MLB Stats")
        st.markdown(f'<div class="status-badge-{"green" if game_info.get("is_official") else "yellow"}">{game_info.get("lineup_status", "")}</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"**{def_away} (Away)**")
            away_ops_label = f"OPS (vs {def_home_p_hand}HP)"
            if away_l7_ops: away_ops_label += f" • {away_l7_ops:.3f} L7"
            away_bp_label = "Bullpen ERA"
            if away_l7_bp_era: away_bp_label += f" • {away_l7_bp_era:.2f} L7"
            
            away_ops_input = st.number_input(away_ops_label, value=float(away_ops) if not away_ops_missing else 0.000, format="%.3f", disabled=not away_ops_missing, key=f"a_ops_{dyn_key}")
            away_starter_fip_input = st.number_input("Starter FIP", value=float(away_starter_fip), format="%.2f", disabled=True, key=f"a_fip_{dyn_key}")
            away_bullpen_era = st.number_input(away_bp_label, value=float(away_bullpen_era_db), step=0.05, key=f"a_bp_{dyn_key}")
        with c2:
            st.caption(f"**{def_home} (Home)**")
            home_ops_label = f"OPS (vs {def_away_p_hand}HP)"
            if home_l7_ops: home_ops_label += f" • {home_l7_ops:.3f} L7"
            home_bp_label = "Bullpen ERA"
            if home_l7_bp_era: home_bp_label += f" • {home_l7_bp_era:.2f} L7"
            
            home_ops_input = st.number_input(home_ops_label, value=float(home_ops) if not home_ops_missing else 0.000, format="%.3f", disabled=not home_ops_missing, key=f"h_ops_{dyn_key}")
            home_starter_fip_input = st.number_input("Starter FIP", value=float(home_starter_fip), format="%.2f", disabled=True, key=f"h_fip_{dyn_key}")
            home_bullpen_era = st.number_input(home_bp_label, value=float(home_bullpen_era_db), step=0.05, key=f"h_bp_{dyn_key}")

    with st.container(border=True):
        st.markdown(f"##### ✈️ Auto-Calculated Travel Fatigue")
        sch1, sch2 = st.columns(2)
        with sch1:
            st.caption(f"**{def_away} (Away)**")
            st.markdown(f"<div class='fatigue-box'><b>{away_sch_status}</b><br>Multiplier: {away_schedule_factor}x</div>", unsafe_allow_html=True)
        with sch2:
            st.caption(f"**{def_home} (Home)**")
            st.markdown(f"<div class='fatigue-box'><b>{home_sch_status}</b><br>Multiplier: {home_schedule_factor}x</div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"##### 🌡️ Environment, Umpire & Wind ({def_home})")
        st.caption(f"**Home Plate Umpire:** {game_info['hp_umpire']}")
        
        env1, env2, env3 = st.columns(3)
        with env1: park_factor = st.slider("Park Factor", 0.85, 1.30, float(venue_info["pf"]), 0.01, key=f"pf_{dyn_key}")
        with env2: temp_f = st.slider("Temp (°F)", 40, 105, int(live_temp), 1, key=f"tmp_{dyn_key}")
        with env3: ump_factor = st.slider("Umpire Factor", 0.90, 1.10, 1.00, 0.01, key=f"ump_{dyn_key}", help=">1.00 = Hitter Friendly (Over)")
        
        w1, w2 = st.columns(2)
        dir_options = ["Calm / Cross / Dome", "Blowing Out", "Blowing In"]
        default_dir_idx = dir_options.index(live_wind_dir) if live_wind_dir in dir_options else 0
        with w1: wind_speed = st.slider("Wind Speed (mph)", 0, 30, int(live_wind_speed), 1, key=f"ws_{dyn_key}")
        with w2: wind_dir = st.selectbox("Wind Direction", dir_options, index=default_dir_idx, key=f"wd_{dyn_key}")

    calc_away_lambda = calculate_true_matchup_lambda(away_ops_input, away_l7_ops, away_starter_fip_input, home_bullpen_era, home_l7_bp_era, park_factor, temp_f, ump_factor, wind_speed, wind_dir, away_schedule_factor, is_f5_mode)
    calc_home_lambda = calculate_true_matchup_lambda(home_ops_input, home_l7_ops, home_starter_fip_input, away_bullpen_era, away_l7_bp_era, park_factor, temp_f, ump_factor, wind_speed, wind_dir, home_schedule_factor, is_f5_mode)

    with st.container(border=True):
        st.markdown(f"##### 🧮 Pure Matchup Projections")
        r1, r2, r3 = st.columns(3)
        with r1: st.metric(f"{def_away} Expected", f"{calc_away_lambda:.2f} Runs")
        with r2: st.metric(f"{def_home} Expected", f"{calc_home_lambda:.2f} Runs")
        with r3: st.metric("True Model Total", f"{calc_away_lambda + calc_home_lambda:.2f} Runs")

    st.markdown("<br>", unsafe_allow_html=True)
    
    if away_ops_input == 0.0 or home_ops_input == 0.0:
        st.warning("⚠️ **Engine Locked:** Please input the missing platoon OPS above to run the simulation.")
    else:
        if st.button("🚀 Run Complete Analytical Simulation", use_container_width=True, type="primary"):
            hw_pct, aw_pct, sim_total, exp_home, exp_away = run_monte_carlo(calc_home_lambda, calc_away_lambda, 500000, is_f5_mode)
            st.session_state.last_sim = {
                "date": date_str, "scope": market_scope, "away_team": def_away, "home_team": def_home,
                "away_starter": game_info["away_starter"], "home_starter": game_info["home_starter"],
                "lineup_status": game_info["lineup_status"],
                "hw_pct": hw_pct, "aw_pct": aw_pct, "sim_total": sim_total, "exp_home": exp_home, "exp_away": exp_away
            }
            st.success("Simulation complete! Check the **🎯 Detailed Matchup Report** tab.")

with tab2:
    if "last_sim" not in st.session_state:
        st.info("👈 Run a simulation from the **Game Capping Engine** tab first.")
    else:
        sim = st.session_state.last_sim
        with st.container(border=True):
            st.subheader("🎯 CAPPING REPORT")
            st.caption(f"📅 {sim['date']} | {sim['scope']} | {sim['away_team']} ({sim['away_starter']}) @ {sim['home_team']} ({sim['home_starter']})")
            st.caption(f"Lineup Status: {sim['lineup_status']}")

        with st.container(border=True):
            st.markdown("##### 📈 Projected Score & Totals")
            k1, k2, k3 = st.columns(3)
            with k1: st.metric("Proj Score", f"{sim['exp_away']:.2f} - {sim['exp_home']:.2f}")
            with k2: st.metric("Proj Total", f"{sim['sim_total']:.2f}")
            with k3: 
                fav = sim['away_team'] if sim['aw_pct'] > sim['hw_pct'] else sim['home_team']
                st.metric("Model Favorite", f"{fav}", f"{max(sim['aw_pct'], sim['hw_pct']) * 100:.1f}% Win Prob")

        with st.container(border=True):
            st.markdown("##### 📋 Mobile Copy Text")
            st.code(
                f"🎯 CAPPING REPORT ({sim['scope']})\n"
                f"Matchup: {sim['away_team']} @ {sim['home_team']}\n"
                f"----------------------------------------\n"
                f"• Proj Score: {sim['away_team']} {sim['exp_away']:.2f} - {sim['home_team']} {sim['exp_home']:.2f}\n"
                f"• Model Total: {sim['sim_total']:.2f}\n"
                f"• {sim['away_team']} Win Prob: {sim['aw_pct']*100:.1f}%\n"
                f"• {sim['home_team']} Win Prob: {sim['hw_pct']*100:.1f}%\n"
                f"----------------------------------------", language="text"
            )
