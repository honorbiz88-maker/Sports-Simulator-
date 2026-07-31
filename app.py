import streamlit as st
import numpy as np
import pandas as pd
import requests
from datetime import datetime

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
    </style>
""", unsafe_allow_html=True)

st.title("⚾ Elite MLB Capping Engine")

# ---------------------------------------------------------
# 2. STRICT BASELINE DATABASES (PARK FACTORS & BULLPENS)
# ---------------------------------------------------------
MLB_PARK_FACTORS = {
    "Arizona Diamondbacks": {"pf": 0.98, "temp": 78}, "Atlanta Braves": {"pf": 1.03, "temp": 82},
    "Baltimore Orioles": {"pf": 1.05, "temp": 78}, "Boston Red Sox": {"pf": 1.06, "temp": 75},
    "Chicago Cubs": {"pf": 1.02, "temp": 76}, "Chicago White Sox": {"pf": 1.01, "temp": 76},
    "Cincinnati Reds": {"pf": 1.10, "temp": 78}, "Cleveland Guardians": {"pf": 0.97, "temp": 75},
    "Colorado Rockies": {"pf": 1.25, "temp": 78}, "Detroit Tigers": {"pf": 0.96, "temp": 75},
    "Houston Astros": {"pf": 0.99, "temp": 74}, "Kansas City Royals": {"pf": 1.06, "temp": 80},
    "Los Angeles Angels": {"pf": 1.00, "temp": 78}, "Los Angeles Dodgers": {"pf": 1.02, "temp": 78},
    "Miami Marlins": {"pf": 0.95, "temp": 74}, "Milwaukee Brewers": {"pf": 1.02, "temp": 74},
    "Minnesota Twins": {"pf": 1.03, "temp": 76}, "New York Mets": {"pf": 0.96, "temp": 78},
    "New York Yankees": {"pf": 1.03, "temp": 78}, "Athletics": {"pf": 1.08, "temp": 80},
    "Philadelphia Phillies": {"pf": 1.07, "temp": 78}, "Pittsburgh Pirates": {"pf": 0.96, "temp": 76},
    "San Diego Padres": {"pf": 0.94, "temp": 74}, "San Francisco Giants": {"pf": 0.92, "temp": 65},
    "Seattle Mariners": {"pf": 0.88, "temp": 68}, "St. Louis Cardinals": {"pf": 0.95, "temp": 80},
    "Tampa Bay Rays": {"pf": 0.94, "temp": 72}, "Texas Rangers": {"pf": 1.01, "temp": 74},
    "Toronto Blue Jays": {"pf": 1.02, "temp": 72}, "Washington Nationals": {"pf": 0.99, "temp": 80}
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
# 3. HIGH-SPEED MLB API PIPELINE (WITH NULL SAFETY)
# ---------------------------------------------------------
@st.cache_data(ttl=180)
def fetch_mlb_daily_schedule(game_date_str):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date_str}&hydrate=probablePitcher,lineups"
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
        a_starter = f"{a_p.get('fullName', 'TBD')} ({a_p.get('pitchHand', {}).get('code', 'R')}HP)" if a_p else "TBD Pitcher"
        
        h_p = g.get("teams", {}).get("home", {}).get("probablePitcher", {})
        h_starter = f"{h_p.get('fullName', 'TBD')} ({h_p.get('pitchHand', {}).get('code', 'R')}HP)" if h_p else "TBD Pitcher"
        
        lineups = g.get("lineups", {})
        is_official = len(lineups.get("homePlayers", [])) >= 9 and len(lineups.get("awayPlayers", [])) >= 9
        
        schedule.append({
            "label": f"{away_name} @ {home_name}",
            "away_team": away_name, "home_team": home_name,
            "away_id": away_id, "home_id": home_id,
            "away_starter": a_starter, "home_starter": h_starter,
            "away_p_id": a_p.get("id") if a_p else None, "home_p_id": h_p.get("id") if h_p else None,
            "lineup_status": "🟢 Official Lineups Confirmed" if is_official else "⚡ Lineups Pending",
            "is_official": is_official
        })
    return schedule

@st.cache_data(ttl=3600)
def fetch_live_stats(team_id, pitcher_id):
    team_ops, pitcher_era = 0.715, 4.10
    current_year = datetime.today().year
    
    if team_id:
        try:
            res = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=season&group=hitting&season={current_year}", timeout=5)
            if res.status_code == 200:
                data = res.json()
                if 'stats' in data and len(data['stats']) > 0 and len(data['stats'][0].get('splits', [])) > 0:
                    team_ops = float(data['stats'][0]['splits'][0]['stat']['ops'])
        except:
            pass
            
    if pitcher_id:
        try:
            res = requests.get(f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}?hydrate=stats(group=[pitching],type=[season,career],season={current_year})", timeout=5)
            if res.status_code == 200:
                data = res.json()
                stats_list = data.get('people', [{}])[0].get('stats', [])
                for stat_group in stats_list:
                    if stat_group.get('type', {}).get('displayName') == 'season' and len(stat_group.get('splits', [])) > 0:
                        pitcher_era = float(stat_group['splits'][0]['stat']['era'])
                        break
                    elif stat_group.get('type', {}).get('displayName') == 'career' and len(stat_group.get('splits', [])) > 0:
                        pitcher_era = float(stat_group['splits'][0]['stat']['era'])
                        break
        except:
            pass
            
    return team_ops, pitcher_era

# ---------------------------------------------------------
# 4. PURE SABERMETRIC MATCHUP ENGINE
# ---------------------------------------------------------
def calculate_true_matchup_lambda(team_ops, opp_starter_era, opp_bullpen_era, park_factor, temp_f, is_f5):
    LEAGUE_R9 = 4.40
    LEAGUE_OPS = 0.715
    
    team_r9 = (float(team_ops) / LEAGUE_OPS) * LEAGUE_R9
    starter_ra9 = float(opp_starter_era) * 1.08
    bullpen_ra9 = float(opp_bullpen_era) * 1.08
    
    if is_f5:
        raw_matchup_runs = ((team_r9 * starter_ra9) / LEAGUE_R9) * (5.0 / 9.0)
    else:
        game_ra9 = (starter_ra9 * 0.62) + (bullpen_ra9 * 0.38)
        raw_matchup_runs = (team_r9 * game_ra9) / LEAGUE_R9

    temp_delta = float(temp_f) - 72.0
    temp_mult = 1.0 + (temp_delta * 0.004)
    
    return max(0.50, round(raw_matchup_runs * float(park_factor) * temp_mult, 2))

def run_monte_carlo(home_lambda, away_lambda, n_sims, is_f5):
    home_runs = np.random.poisson(home_lambda, n_sims)
    away_runs = np.random.poisson(away_lambda, n_sims)
    
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
    
    away_ops, away_starter_era = fetch_live_stats(game_info["away_id"], game_info["away_p_id"])
    home_ops, home_starter_era = fetch_live_stats(game_info["home_id"], game_info["home_p_id"])

    # Null safety fallbacks
    if away_ops is None: away_ops = 0.715
    if home_ops is None: home_ops = 0.715
    if away_starter_era is None: away_starter_era = 4.10
    if home_starter_era is None: home_starter_era = 4.10

    home_venue_defaults = MLB_PARK_FACTORS.get(def_home, {"pf": 1.00, "temp": 78})
    away_bullpen_era_db = BULLPEN_ERA.get(def_away, 4.10)
    home_bullpen_era_db = BULLPEN_ERA.get(def_home, 4.10)

    dyn_key = f"{def_away}_{def_home}_{is_f5_mode}"

    with st.container(border=True):
        st.markdown(f"##### 🏟️ Auto-Pulled Official MLB Stats")
        st.markdown(f'<div class="status-badge-{"green" if game_info.get("is_official") else "yellow"}">{game_info.get("lineup_status", "")}</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"**{def_away} (Away)**")
            away_ops_input = st.number_input("Season OPS", value=float(away_ops), format="%.3f", disabled=True, key=f"a_ops_{dyn_key}")
            away_starter_era_input = st.number_input("Starter ERA", value=float(away_starter_era), format="%.2f", disabled=True, key=f"a_era_{dyn_key}")
            away_bullpen_era = st.number_input("Bullpen ERA", value=float(away_bullpen_era_db), step=0.05, key=f"a_bp_{dyn_key}")
        with c2:
            st.caption(f"**{def_home} (Home)**")
            home_ops_input = st.number_input("Season OPS", value=float(home_ops), format="%.3f", disabled=True, key=f"h_ops_{dyn_key}")
            home_starter_era_input = st.number_input("Starter ERA", value=float(home_starter_era), format="%.2f", disabled=True, key=f"h_era_{dyn_key}")
            home_bullpen_era = st.number_input("Bullpen ERA", value=float(home_bullpen_era_db), step=0.05, key=f"h_bp_{dyn_key}")

    with st.container(border=True):
        st.markdown(f"##### 🌡️ Environmental Conditions ({def_home})")
        env1, env2 = st.columns(2)
        with env1: park_factor = st.slider("Park Factor", 0.85, 1.30, float(home_venue_defaults["pf"]), 0.01, key=f"pf_{dyn_key}")
        with env2: temp_f = st.slider("Temperature (°F)", 40, 105, int(home_venue_defaults["temp"]), 1, key=f"tmp_{dyn_key}")

    calc_away_lambda = calculate_true_matchup_lambda(away_ops_input, home_starter_era_input, home_bullpen_era, park_factor, temp_f, is_f5_mode)
    calc_home_lambda = calculate_true_matchup_lambda(home_ops_input, away_starter_era_input, away_bullpen_era, park_factor, temp_f, is_f5_mode)

    with st.container(border=True):
        st.markdown(f"##### 🧮 Pure Matchup Projections")
        r1, r2, r3 = st.columns(3)
        with r1: st.metric(f"{def_away} Expected", f"{calc_away_lambda:.2f} Runs")
        with r2: st.metric(f"{def_home} Expected", f"{calc_home_lambda:.2f} Runs")
        with r3: st.metric("True Model Total", f"{calc_away_lambda + calc_home_lambda:.2f} Runs")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Run Pure Simulation Core", use_container_width=True, type="primary"):
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
