import streamlit as st
import numpy as np
import pandas as pd
import requests
from datetime import datetime

# ---------------------------------------------------------
# 1. PAGE CONFIG & STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="MLB Monte Carlo Capping Engine",
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
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 800;
    }
    .status-badge-green { background-color: #d1e7dd; color: #0f5132; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; display: inline-block; margin-bottom: 8px;}
    .status-badge-yellow { background-color: #fff3cd; color: #664d03; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; display: inline-block; margin-bottom: 8px;}
    .status-badge-blue { background-color: #cff4fc; color: #055160; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; display: inline-block; margin-bottom: 8px;}
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

BOOKMAKER_MAP = {"Novig (Exchange)": "novig", "FanDuel": "fanduel", "DraftKings": "draftkings", "BetMGM": "betmgm", "Pinnacle": "pinnacle"}

# ---------------------------------------------------------
# 2. STRICT BASELINE DATABASES
# ---------------------------------------------------------
MLB_PARK_FACTORS = {
    "Arizona Diamondbacks": {"pf": 0.98, "temp": 78, "wind": 0}, "Atlanta Braves": {"pf": 1.03, "temp": 82, "wind": 2},
    "Baltimore Orioles": {"pf": 1.05, "temp": 78, "wind": 3}, "Boston Red Sox": {"pf": 1.06, "temp": 75, "wind": 4},
    "Chicago Cubs": {"pf": 1.02, "temp": 76, "wind": 5}, "Chicago White Sox": {"pf": 1.01, "temp": 76, "wind": 3},
    "Cincinnati Reds": {"pf": 1.10, "temp": 78, "wind": 3}, "Cleveland Guardians": {"pf": 0.97, "temp": 75, "wind": 4},
    "Colorado Rockies": {"pf": 1.25, "temp": 78, "wind": 2}, "Detroit Tigers": {"pf": 0.96, "temp": 75, "wind": 3},
    "Houston Astros": {"pf": 0.99, "temp": 74, "wind": 0}, "Kansas City Royals": {"pf": 1.06, "temp": 80, "wind": 4},
    "Los Angeles Angels": {"pf": 1.00, "temp": 78, "wind": 2}, "Los Angeles Dodgers": {"pf": 1.02, "temp": 78, "wind": 2},
    "Miami Marlins": {"pf": 0.95, "temp": 74, "wind": 0}, "Milwaukee Brewers": {"pf": 1.02, "temp": 74, "wind": 0},
    "Minnesota Twins": {"pf": 1.03, "temp": 76, "wind": 4}, "New York Mets": {"pf": 0.96, "temp": 78, "wind": 3},
    "New York Yankees": {"pf": 1.03, "temp": 78, "wind": 3}, "Athletics": {"pf": 1.08, "temp": 80, "wind": 5},
    "Philadelphia Phillies": {"pf": 1.07, "temp": 78, "wind": 3}, "Pittsburgh Pirates": {"pf": 0.96, "temp": 76, "wind": 2},
    "San Diego Padres": {"pf": 0.94, "temp": 74, "wind": 3}, "San Francisco Giants": {"pf": 0.92, "temp": 65, "wind": 6},
    "Seattle Mariners": {"pf": 0.88, "temp": 68, "wind": 0}, "St. Louis Cardinals": {"pf": 0.95, "temp": 80, "wind": 2},
    "Tampa Bay Rays": {"pf": 0.94, "temp": 72, "wind": 0}, "Texas Rangers": {"pf": 1.01, "temp": 74, "wind": 0},
    "Toronto Blue Jays": {"pf": 1.02, "temp": 72, "wind": 0}, "Washington Nationals": {"pf": 0.99, "temp": 80, "wind": 2}
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
# 3. SECRETS & API KEY MANAGEMENT
# ---------------------------------------------------------
if "ODDS_API_KEY" in st.secrets:
    api_key = st.secrets["ODDS_API_KEY"]
else:
    api_key = st.sidebar.text_input("The Odds API Key", type="password")

# ---------------------------------------------------------
# 4. STRICT EXCEPTION-RAISING API FUNCTIONS
# ---------------------------------------------------------
@st.cache_data(ttl=180)
def fetch_mlb_daily_schedule(game_date_str):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date_str}&hydrate=probablePitcher,lineups"
    res = requests.get(url, timeout=8)
    res.raise_for_status() # Fails loud if MLB API drops
    
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
    team_ops, pitcher_era = None, None
    current_year = datetime.today().year
    
    if team_id:
        res = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=season&group=hitting&season={current_year}", timeout=6)
        res.raise_for_status()
        data = res.json()
        if 'stats' in data and len(data['stats']) > 0 and len(data['stats'][0].get('splits', [])) > 0:
            team_ops = float(data['stats'][0]['splits'][0]['stat']['ops'])
        else:
            raise ValueError(f"🚨 API Error: No Team OPS returned for Team ID {team_id}.")
            
    if pitcher_id:
        res = requests.get(f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}?hydrate=stats(group=[pitching],type=[season,career],season={current_year})", timeout=6)
        res.raise_for_status()
        data = res.json()
        
        stats_list = data['people'][0].get('stats', [])
        for stat_group in stats_list:
            if stat_group['type']['displayName'] == 'season' and len(stat_group.get('splits', [])) > 0:
                pitcher_era = float(stat_group['splits'][0]['stat']['era'])
                break
            elif stat_group['type']['displayName'] == 'career' and len(stat_group.get('splits', [])) > 0:
                pitcher_era = float(stat_group['splits'][0]['stat']['era'])
                break
                
        if pitcher_era is None:
            raise ValueError(f"🚨 API Error: No ERA data exists for Pitcher ID {pitcher_id}.")
            
    return team_ops, pitcher_era

def get_team_kw(name):
    parts = name.strip().split()
    return f"{parts[-2]} {parts[-1]}".lower() if len(parts) >= 2 and parts[-2].lower() in ["red", "white"] else parts[-1].lower()

def american_to_implied(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

@st.cache_data(ttl=60)
def fetch_live_odds_for_game(key, target_book_key, away_team, home_team):
    if not key: raise ValueError("🚨 API Key for The Odds API is missing!")
    
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={key}&regions=us,us2,us_ex&markets=h2h,totals&oddsFormat=american"
    res = requests.get(url, timeout=8)
    res.raise_for_status()
    
    games_data = res.json()
    if not games_data:
        raise ValueError("🚨 Odds API Error: The bookmaker data payload was completely empty.")
        
    a_kw, h_kw = get_team_kw(away_team), get_team_kw(home_team)
    
    for game in games_data:
        if {a_kw, h_kw} == {get_team_kw(game.get("away_team", "")), get_team_kw(game.get("home_team", ""))}:
            bookmakers = game.get("bookmakers", [])
            if not bookmakers: 
                raise ValueError(f"🚨 Odds Error: Game {away_team} vs {home_team} found, but no bookmaker lines are currently posted.")
            
            # Scrape all totals to find consensus
            all_totals = [float(out["point"]) for bm in bookmakers for m in bm.get("markets", []) if m.get("key") == "totals" for out in m.get("outcomes", []) if "point" in out]
            if not all_totals:
                raise ValueError(f"🚨 Odds Error: No Totals market lines posted across ANY bookmaker for {away_team} vs {home_team}.")
            consensus_total = max(set(all_totals), key=all_totals.count)
            
            selected_bm = next((bm for bm in bookmakers if bm.get("key") == target_book_key), None)
            if not selected_bm:
                raise ValueError(f"🚨 Odds Error: Your target bookmaker '{target_book_key}' is not offering lines for this game yet.")
            
            away_ml, home_ml = None, None
            for m in selected_bm.get("markets", []):
                if m.get("key") == "h2h":
                    for out in m.get("outcomes", []):
                        if get_team_kw(out.get("name", "")) == a_kw: away_ml = out.get("price")
                        elif get_team_kw(out.get("name", "")) == h_kw: home_ml = out.get("price")
            
            if away_ml is None or home_ml is None:
                raise ValueError(f"🚨 Odds Error: The selected bookmaker '{target_book_key}' does not have a Moneyline posted for this game yet.")
                
            return away_ml, home_ml, consensus_total, f"🟢 Live Odds via {selected_bm.get('title', target_book_key)}"
            
    raise ValueError(f"🚨 Odds Error: {away_team} vs {home_team} was not found on the Odds API feed.")

# ---------------------------------------------------------
# 5. REFINED ELASTIC EXPECTED RUNS ALGORITHM
# ---------------------------------------------------------
def calculate_elastic_lambda(team_ops, opp_starter_era, opp_bullpen_era, park_factor, temp_f, wind_mph, is_f5):
    # Hitting Multiplier (1.00 = League Average)
    off_mult = float(team_ops) / 0.715
    
    # Direct inning-level ERA conversion (No baselines clamping the math)
    if is_f5:
        base_runs = float(opp_starter_era) * (5.0 / 9.0)
    else:
        sp_runs = float(opp_starter_era) * (6.0 / 9.0)
        bp_runs = float(opp_bullpen_era) * (3.0 / 9.0)
        base_runs = sp_runs + bp_runs

    matchup_runs = base_runs * off_mult

    # Weather multipliers heavily compressed so they don't break extreme ERAs
    pf_adj = 1.0 + ((float(park_factor) - 1.0) * 0.6) 
    temp_adj = 1.0 + ((float(temp_f) - 75.0) * 0.0015) 
    wind_adj = 1.0 + (float(wind_mph) * 0.0015)
    
    return max(0.50, round(matchup_runs * (pf_adj * temp_adj * wind_adj), 2))

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

if "wager_log" not in st.session_state: st.session_state.wager_log = []

# ---------------------------------------------------------
# 6. UI TABS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Game Simulator", "🎯 Capping Report", "📝 Wager Log & CLV"])

with tab1:
    with st.container(border=True):
        st.markdown("##### 📅 Schedule & Market Selection")
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            market_scope = st.radio("Market Scope", options=["Full Game (9-Inn)", "First 5 Innings (F5)"], index=0, horizontal=True)
            is_f5_mode = "First 5" in market_scope
        with m_col2:
            target_book_key = BOOKMAKER_MAP[st.selectbox("Preferred Bookmaker", options=list(BOOKMAKER_MAP.keys()), index=0)]
        with m_col3:
            date_str = st.date_input("Game Date", value=datetime.today()).strftime("%Y-%m-%d")
            
        try:
            daily_schedule = fetch_mlb_daily_schedule(date_str)
            selected_label = st.selectbox("🎯 Select Game from MLB Schedule", options=[g["label"] for g in daily_schedule])
            game_info = next((g for g in daily_schedule if g["label"] == selected_label), daily_schedule[0])
        except Exception as e:
            st.error(str(e))
            st.stop()

    def_away, def_home = game_info["away_team"], game_info["home_team"]
    
    try:
        away_ops, away_starter_era = fetch_live_stats(game_info["away_id"], game_info["away_p_id"])
        home_ops, home_starter_era = fetch_live_stats(game_info["home_id"], game_info["home_p_id"])
    except Exception as e:
        st.error(str(e))
        st.stop()

    try:
        home_venue_defaults = MLB_PARK_FACTORS[def_home] # Fails loud if team not in database
        away_bullpen_era_db = BULLPEN_ERA[def_away]
        home_bullpen_era_db = BULLPEN_ERA[def_home]
    except KeyError as e:
        st.error(f"🚨 Database Error: Team {str(e)} is missing from internal dictionary.")
        st.stop()

    try:
        live_away_ml, live_home_ml, live_total, odds_status_msg = fetch_live_odds_for_game(api_key, target_book_key, def_away, def_home)
    except Exception as e:
        st.error(str(e))
        st.stop()

    dyn_key = f"{def_away}_{def_home}_{is_f5_mode}"

    with st.container(border=True):
        st.markdown(f"##### 🏟️ Auto-Pulled Official MLB Stats")
        st.markdown(f'<div class="status-badge-{"green" if game_info.get("is_official") else "yellow"}">{game_info.get("lineup_status", "")}</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"**{def_away} (Away)**")
            away_ops_input = st.number_input("Season OPS", value=float(away_ops), format="%.3f", disabled=True, key=f"a_ops_{dyn_key}")
            away_starter_era_input = st.number_input("Starter ERA (Edit to override)", value=float(away_starter_era), format="%.2f", key=f"a_era_{dyn_key}")
            away_bullpen_era = st.number_input("Bullpen ERA", value=float(away_bullpen_era_db), step=0.05, key=f"a_bp_{dyn_key}")
        with c2:
            st.caption(f"**{def_home} (Home)**")
            home_ops_input = st.number_input("Season OPS", value=float(home_ops), format="%.3f", disabled=True, key=f"h_ops_{dyn_key}")
            home_starter_era_input = st.number_input("Starter ERA (Edit to override)", value=float(home_starter_era), format="%.2f", key=f"h_era_{dyn_key}")
            home_bullpen_era = st.number_input("Bullpen ERA", value=float(home_bullpen_era_db), step=0.05, key=f"h_bp_{dyn_key}")

    with st.container(border=True):
        st.markdown(f"##### 🌡️ Environmental Conditions ({def_home})")
        env1, env2, env3 = st.columns(3)
        with env1: park_factor = st.slider("Park Factor", 0.85, 1.30, float(home_venue_defaults["pf"]), 0.01, key=f"pf_{dyn_key}")
        with env2: temp_f = st.slider("Temperature (°F)", 40, 105, int(home_venue_defaults["temp"]), 1, key=f"tmp_{dyn_key}")
        with env3: wind_out = st.slider("Wind Out (mph)", -15, 25, int(home_venue_defaults["wind"]), 1, key=f"wnd_{dyn_key}")

    calc_away_lambda = calculate_elastic_lambda(away_ops_input, home_starter_era_input, home_bullpen_era, park_factor, temp_f, wind_out, is_f5_mode)
    calc_home_lambda = calculate_elastic_lambda(home_ops_input, away_starter_era_input, away_bullpen_era, park_factor, temp_f, wind_out, is_f5_mode)

    with st.container(border=True):
        st.markdown(f"##### 🧮 Expected Runs: Elastic Math Engine")
        r1, r2, r3 = st.columns(3)
        with r1: st.metric(f"{def_away} λ", f"{calc_away_lambda:.2f} Runs")
        with r2: st.metric(f"{def_home} λ", f"{calc_home_lambda:.2f} Runs")
        with r3: st.metric("True Model Total", f"{calc_away_lambda + calc_home_lambda:.2f} Runs")

    with st.container(border=True):
        st.markdown("##### 💰 Consensus Market Lines")
        st.markdown(f'<div class="status-badge-blue">{odds_status_msg}</div>', unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        with m1: away_ml_odds = st.number_input(f"{def_away} ML", value=int(live_away_ml), key=f"a_ml_{dyn_key}")
        with m2: home_ml_odds = st.number_input(f"{def_home} ML", value=int(live_home_ml), key=f"h_ml_{dyn_key}")
        with m3: market_total = st.number_input("Market Total Line", value=float(live_total), step=0.5, key=f"mtot_{dyn_key}")

    with st.expander("⚙️ Advanced Monte Carlo Tuning"):
        iterations = st.number_input("Iterations", 10000, 1000000, 1000000, 90000)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Run Monte Carlo Simulation", use_container_width=True, type="primary"):
        hw_pct, aw_pct, sim_total, exp_home, exp_away = run_monte_carlo(calc_home_lambda, calc_away_lambda, iterations, is_f5_mode)
        st.session_state.last_sim = {
            "date": date_str, "scope": market_scope, "away_team": def_away, "home_team": def_home,
            "away_starter": game_info["away_starter"], "home_starter": game_info["home_starter"],
            "lineup_status": game_info["lineup_status"], "odds_status": odds_status_msg,
            "hw_pct": hw_pct, "aw_pct": aw_pct, "sim_total": sim_total, "exp_home": exp_home, "exp_away": exp_away,
            "away_ml_odds": away_ml_odds, "home_ml_odds": home_ml_odds, "market_total": market_total,
            "iterations": iterations
        }
        st.success("Simulation complete! Check the **🎯 Capping Report** tab.")

with tab2:
    if "last_sim" not in st.session_state: st.info("👈 Run a simulation first.")
    else:
        sim = st.session_state.last_sim
        with st.container(border=True):
            st.subheader("🎯 CAPPING REPORT")
            st.caption(f"📅 {sim['date']} | {sim['scope']} | {sim['away_team']} ({sim['away_starter']}) @ {sim['home_team']} ({sim['home_starter']})")
            st.caption(f"Status: {sim['lineup_status']} | Market Source: {sim['odds_status']}")

        with st.container(border=True):
            st.markdown("##### 📈 Projected Outcomes")
            k1, k2, k3 = st.columns(3)
            with k1: st.metric("Proj Score", f"{sim['exp_away']:.2f} - {sim['exp_home']:.2f}")
            with k2: st.metric("Proj Total", f"{sim['sim_total']:.2f}", delta=f"{sim['sim_total'] - sim['market_total']:+.2f} vs Line")
            with k3: st.metric("Model Fav", f"{sim['away_team'] if sim['aw_pct'] > sim['hw_pct'] else sim['home_team']}", f"{max(sim['aw_pct'], sim['hw_pct']) * 100:.1f}%")

        with st.container(border=True):
            st.markdown("##### 🎯 Model Picks")
            p1, p2, p3 = st.columns(3)
            with p1: st.success(f"**Winner:** {sim['away_team'] if sim['aw_pct'] > sim['hw_pct'] else sim['home_team']}")
            with p2: st.success(f"**Total ({sim['market_total']}):** {'OVER' if sim['sim_total'] > sim['market_total'] else 'UNDER'}")
            with p3: st.info(f"**{sim['away_team']} TT:** {'OVER' if sim['exp_away'] > (sim['market_total']/2) else 'UNDER'} {sim['market_total']/2:.1f}")

        with st.container(border=True):
            st.markdown("##### 🔥 Market Edges")
            h_imp, a_imp = american_to_implied(sim['home_ml_odds']), american_to_implied(sim['away_ml_odds'])
            e1, e2 = st.columns(2)
            with e1:
                st.write(f"**{sim['away_team']} ML:** Model **{sim['aw_pct']*100:.1f}%** | Implied **{a_imp*100:.1f}%**")
                if (sim['aw_pct'] - a_imp)*100 > 0: st.success(f"🔥 Edge: +{(sim['aw_pct'] - a_imp)*100:.1f}%")
                else: st.caption("No Edge")
            with e2:
                st.write(f"**{sim['home_team']} ML:** Model **{sim['hw_pct']*100:.1f}%** | Implied **{h_imp*100:.1f}%**")
                if (sim['hw_pct'] - h_imp)*100 > 0: st.success(f"🔥 Edge: +{(sim['hw_pct'] - h_imp)*100:.1f}%")
                else: st.caption("No Edge")

with tab3:
    with st.container(border=True):
        st.markdown("##### 📝 Log New Wager")
        with st.form("add_wager"):
            w_col1, w_col2, w_col3 = st.columns(3)
            with w_col1:
                w_date = st.date_input("Bet Date", value=datetime.today())
                w_matchup = st.text_input("Matchup", value="Away @ Home")
            with w_col2:
                w_pick = st.text_input("Pick Taken", value="ML")
                w_odds = st.number_input("Placed Odds", value=-110)
            with w_col3:
                w_stake = st.number_input("Stake ($)", value=1.00, step=0.25)
                w_closing = st.number_input("Closing Odds", value=-120)
                
            if st.form_submit_button("Log Wager", use_container_width=True):
                st.session_state.wager_log.append({
                    "Date": w_date.strftime("%Y-%m-%d"), "Matchup": w_matchup, "Pick": w_pick,
                    "Odds": w_odds, "Stake": f"${w_stake:.2f}", "CLV Edge": f"{(american_to_implied(w_closing) - american_to_implied(w_odds))*100:+.2f}%"
                })
                st.success("Wager logged!")
    with st.container(border=True):
        st.markdown("##### 📊 Active Wager Log")
        if st.session_state.wager_log: st.dataframe(pd.DataFrame(st.session_state.wager_log), use_container_width=True)
        else: st.info("No wagers logged yet.")
