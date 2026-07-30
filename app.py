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
# 2. PARK FACTORS & BULLPEN BASELINE DATABASE
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
# 4. AUTO-PULLING API FUNCTIONS
# ---------------------------------------------------------
@st.cache_data(ttl=180)
def fetch_mlb_daily_schedule(game_date_str):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date_str}&hydrate=probablePitcher,lineups"
    schedule = []
    try:
        res = requests.get(url, timeout=6).json()
        dates = res.get("dates", [])
        if dates:
            for g in dates[0].get("games", []):
                away_name = g.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
                home_name = g.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
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
    except Exception:
        pass
    return schedule

@st.cache_data(ttl=3600)
def fetch_live_stats(team_id, pitcher_id):
    team_ops, pitcher_era = 0.715, 4.10
    if team_id:
        try:
            res = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=season&group=hitting", timeout=4).json()
            if 'stats' in res and len(res['stats']) > 0:
                team_ops = float(res['stats'][0]['splits'][0]['stat']['ops'])
        except: pass
    if pitcher_id:
        try:
            res = requests.get(f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}?hydrate=stats(group=[pitching],type=[season])", timeout=4).json()
            pitcher_era = float(res['people'][0]['stats'][0]['splits'][0]['stat']['era'])
        except: pass
    
    # Wide limits to allow elite Aces (e.g. 1.80) to dramatically drop the projection
    return min(max(team_ops, 0.500), 0.900), min(max(pitcher_era, 1.00), 8.00)

def get_team_kw(name):
    parts = name.strip().split()
    return f"{parts[-2]} {parts[-1]}".lower() if len(parts) >= 2 and parts[-2].lower() in ["red", "white"] else parts[-1].lower()

def american_to_implied(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

@st.cache_data(ttl=60)
def fetch_live_odds_for_game(key, target_book_key, away_team, home_team, default_total=8.5):
    if not key: return -110, -110, default_total, "⚠️ No API Key Saved"
    try:
        res = requests.get(f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={key}&regions=us,us2,us_ex&markets=h2h,totals&oddsFormat=american", timeout=8).json()
        a_kw, h_kw = get_team_kw(away_team), get_team_kw(home_team)
        for game in res:
            if {a_kw, h_kw} == {get_team_kw(game.get("away_team", "")), get_team_kw(game.get("home_team", ""))}:
                bookmakers = game.get("bookmakers", [])
                if not bookmakers: break
                all_totals = [float(out["point"]) for bm in bookmakers for m in bm.get("markets", []) if m.get("key") == "totals" for out in m.get("outcomes", []) if "point" in out]
                consensus_total = max(set(all_totals), key=all_totals.count) if all_totals else default_total
                selected_bm = next((bm for bm in bookmakers if bm.get("key") == target_book_key), bookmakers[0])
                
                away_ml, home_ml = -110, -110
                for m in selected_bm.get("markets", []):
                    if m.get("key") == "h2h":
                        for out in m.get("outcomes", []):
                            if get_team_kw(out.get("name", "")) == a_kw: away_ml = out.get("price", -110)
                            elif get_team_kw(out.get("name", "")) == h_kw: home_ml = out.get("price", -110)
                return away_ml, home_ml, consensus_total, f"🟢 Live Odds via {selected_bm.get('title', target_book_key)}"
        return -110, -110, default_total, "⚠️ Game Not Found in Odds Feed"
    except Exception as e: return -110, -110, default_total, f"⚠️ Connection Error"

# ---------------------------------------------------------
# 5. BILL JAMES EXPECTED RUNS ALGORITHM
# ---------------------------------------------------------
def calculate_bill_james_lambda(team_ops, opp_starter_era, opp_bullpen_era, park_factor, temp_f, wind_mph, is_f5):
    """
    Applies the Bill James Matchup Formula:
    (Offense Runs Created * Pitching Runs Allowed) / League Average
    This perfectly isolates elite pitching to drop totals into the 6.0 range.
    """
    LEAGUE_AVG_RUNS = 2.30 if is_f5 else 4.35
    LEAGUE_AVG_OPS = 0.715
    
    # 1. Calculate Team Runs Created based on OPS deviation
    team_rc = LEAGUE_AVG_RUNS * (float(team_ops) / LEAGUE_AVG_OPS)
    
    # 2. Calculate Pitcher Runs Allowed based on projected innings
    if is_f5:
        opp_ra = float(opp_starter_era) * (5.0 / 9.0)
    else:
        # Starter covers ~62% of innings, Bullpen covers ~38%
        opp_ra = (float(opp_starter_era) * 0.62) + (float(opp_bullpen_era) * 0.38)

    # 3. Bill James Matchup Formula
    matchup_expected_runs = (team_rc * opp_ra) / LEAGUE_AVG_RUNS

    # 4. Weather & Park Constraints
    # Temperatures are heavily dampened so 95 degrees doesn't blindly add an extra run
    temp_adj = 1.0 + ((float(temp_f) - 75.0) * 0.002) 
    wind_adj = 1.0 + (float(wind_mph) * 0.002)
    env_mult = float(park_factor) * temp_adj * wind_adj
    
    return max(0.50, round(matchup_expected_runs * env_mult, 2))

def run_monte_carlo(home_lambda, away_lambda, n_sims, var_ratio, is_f5):
    home_runs = np.random.poisson(home_lambda * var_ratio, n_sims) / var_ratio
    away_runs = np.random.poisson(away_lambda * var_ratio, n_sims) / var_ratio
    
    if not is_f5: 
        ties = home_runs == away_runs
        n_ties = np.sum(ties)
        if n_ties > 0:
            winner_is_home = np.random.choice([True, False], size=n_ties, p=[0.53, 0.47])
            home_runs[ties] += np.where(winner_is_home, 1, 0) + np.random.poisson(0.5, n_ties)
            away_runs[ties] += np.where(~winner_is_home, 1, 0) + np.random.poisson(0.5, n_ties)
            still_tied = home_runs[ties] == away_runs[ties]
            home_runs[ties] = np.where(still_tied, home_runs[ties] + 1, home_runs[ties])
            
    return np.sum(home_runs > away_runs) / n_sims, np.sum(away_runs > home_runs) / n_sims, np.mean(home_runs + away_runs), np.mean(home_runs), np.mean(away_runs)

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
            
        daily_schedule = fetch_mlb_daily_schedule(date_str)
        if daily_schedule:
            selected_label = st.selectbox("🎯 Select Game from MLB Schedule", options=[g["label"] for g in daily_schedule])
            game_info = next((g for g in daily_schedule if g["label"] == selected_label), daily_schedule[0])
        else:
            game_info = None
            st.warning("⚠️ Fetching MLB Schedule...")

    if game_info:
        def_away, def_home = game_info["away_team"], game_info["home_team"]
        away_ops, away_starter_era = fetch_live_stats(game_info["away_id"], game_info["away_p_id"])
        home_ops, home_starter_era = fetch_live_stats(game_info["home_id"], game_info["home_p_id"])
    else:
        def_away, def_home, away_ops, away_starter_era, home_ops, home_starter_era = "Chicago Cubs", "St. Louis Cardinals", 0.715, 4.10, 0.715, 4.10
        game_info = {"is_official": False, "lineup_status": "⚡ Pending"}

    home_venue_defaults = MLB_PARK_FACTORS.get(def_home, {"pf": 1.00, "temp": 78, "wind": 0})
    live_away_ml, live_home_ml, live_total, odds_status_msg = fetch_live_odds_for_game(api_key, target_book_key, def_away, def_home, 4.5 if is_f5_mode else 8.5)

    with st.container(border=True):
        st.markdown(f"##### 🏟️ Auto-Pulled Official MLB Stats")
        st.markdown(f'<div class="status-badge-{"green" if game_info["is_official"] else "yellow"}">{game_info["lineup_status"]}</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"**{def_away} (Away)**")
            away_wrc = st.number_input("Season OPS", value=away_ops, format="%.3f", disabled=True, key="a_ops")
            away_starter_era_input = st.number_input("Starter ERA (Edit to update)", value=away_starter_era, format="%.2f", key="a_era")
            away_bullpen_era = st.number_input("Bullpen ERA", value=BULLPEN_ERA.get(def_away, 4.10), step=0.05, key="a_bp")
        with c2:
            st.caption(f"**{def_home} (Home)**")
            home_wrc = st.number_input("Season OPS", value=home_ops, format="%.3f", disabled=True, key="h_ops")
            home_starter_era_input = st.number_input("Starter ERA (Edit to update)", value=home_starter_era, format="%.2f", key="h_era")
            home_bullpen_era = st.number_input("Bullpen ERA", value=BULLPEN_ERA.get(def_home, 4.10), step=0.05, key="h_bp")

    with st.container(border=True):
        st.markdown(f"##### 🌡️ Environmental Conditions ({def_home})")
        env1, env2, env3 = st.columns(3)
        with env1: park_factor = st.slider("Park Factor", 0.85, 1.30, float(home_venue_defaults["pf"]), 0.01)
        with env2: temp_f = st.slider("Temperature (°F)", 40, 105, int(home_venue_defaults["temp"]), 1)
        with env3: wind_out = st.slider("Wind Out (mph)", -15, 25, int(home_venue_defaults["wind"]), 1)

    # EXECUTE BILL JAMES ALGORITHM
    calc_away_lambda = calculate_bill_james_lambda(away_wrc, home_starter_era_input, home_bullpen_era, park_factor, temp_f, wind_out, is_f5_mode)
    calc_home_lambda = calculate_bill_james_lambda(home_wrc, away_starter_era_input, away_bullpen_era, park_factor, temp_f, wind_out, is_f5_mode)

    with st.container(border=True):
        st.markdown(f"##### 🧮 Expected Runs: Bill James Algorithm")
        r1, r2, r3 = st.columns(3)
        with r1: st.metric(f"{def_away} λ", f"{calc_away_lambda:.2f} Runs")
        with r2: st.metric(f"{def_home} λ", f"{calc_home_lambda:.2f} Runs")
        with r3: st.metric("True Model Total", f"{calc_away_lambda + calc_home_lambda:.2f} Runs")

    with st.container(border=True):
        st.markdown("##### 💰 Consensus Market Lines")
        st.markdown(f'<div class="status-badge-blue">{odds_status_msg}</div>', unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        with m1: away_ml_odds = st.number_input(f"{def_away} ML", value=int(live_away_ml))
        with m2: home_ml_odds = st.number_input(f"{def_home} ML", value=int(live_home_ml))
        with m3: market_total = st.number_input("Market Total Line", value=float(live_total), step=0.5)

    with st.expander("⚙️ Advanced Monte Carlo Tuning"):
        iterations = st.number_input("Iterations", 10000, 1000000, 1000000, 90000)
        variance_ratio = st.slider("Run Variance Scale Factor", 1.0, 1.6, 1.3, 0.05)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Run Monte Carlo Simulation", use_container_width=True, type="primary") and game_info:
        hw_pct, aw_pct, sim_total, exp_home, exp_away = run_monte_carlo(calc_home_lambda, calc_away_lambda, iterations, variance_ratio, is_f5_mode)
        st.session_state.last_sim = {
            "date": date_str, "scope": market_scope, "away_team": def_away, "home_team": def_home,
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
            st.caption(f"📅 {sim['date']} | {sim['scope']} | {sim['away_team']} @ {sim['home_team']}")

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
