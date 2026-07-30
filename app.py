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
    initial_sidebar_state="collapsed"  # Collapsed by default for clean phone view
)

# Custom CSS for mobile polish
st.markdown("""
    <style>
    .stButton>button {
        border-radius: 10px;
        font-weight: 700;
        height: 3rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem;
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
        margin-bottom: 10px;
    }
    .status-badge-yellow {
        background-color: #fff3cd;
        color: #664d03;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚾ MLB Capping Engine")

# 30-Team Standard List for Dropdowns
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

# ---------------------------------------------------------
# 2. SECRETS & API KEY MANAGEMENT
# ---------------------------------------------------------
if "ODDS_API_KEY" in st.secrets:
    api_key = st.secrets["ODDS_API_KEY"]
else:
    api_key = st.sidebar.text_input("The Odds API Key", type="password")

# ---------------------------------------------------------
# 3. HELPER & API FUNCTIONS
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_live_games(key):
    """Fetches upcoming MLB odds and parses them for auto-fill dropdowns."""
    if not key:
        return []
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={key}&regions=us&markets=h2h,totals&oddsFormat=american"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            games_data = res.json()
            parsed_games = []
            for game in games_data:
                home = game.get("home_team")
                away = game.get("away_team")
                
                away_ml, home_ml, total_line = -110, -110, 8.5
                
                bookmakers = game.get("bookmakers", [])
                if bookmakers:
                    target_book = bookmakers[0]
                    for bm in bookmakers:
                        if bm.get("key") in ["novig", "fanduel"]:
                            target_book = bm
                            break
                    
                    for market in target_book.get("markets", []):
                        if market.get("key") == "h2h":
                            for outcome in market.get("outcomes", []):
                                if outcome.get("name") == away:
                                    away_ml = outcome.get("price", -110)
                                elif outcome.get("name") == home:
                                    home_ml = outcome.get("price", -110)
                        elif market.get("key") == "totals":
                            outcomes = market.get("outcomes", [])
                            if outcomes:
                                total_line = outcomes[0].get("point", 8.5)

                parsed_games.append({
                    "label": f"{away} @ {home}",
                    "away_team": away,
                    "home_team": home,
                    "away_ml": away_ml,
                    "home_ml": home_ml,
                    "total_line": total_line
                })
            return parsed_games
        return []
    except Exception:
        return []

@st.cache_data(ttl=180)
def check_official_mlb_lineups(game_date_str, away_team, home_team):
    """Queries MLB Stats API to check if 1-9 lineup cards are officially posted."""
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date_str}&hydrate=lineups"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            dates = data.get("dates", [])
            if dates:
                games = dates[0].get("games", [])
                for g in games:
                    h_name = g.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
                    a_name = g.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
                    
                    if (away_team in a_name or a_name in away_team) and (home_team in h_name or h_name in home_team):
                        lineups = g.get("lineups", {})
                        has_home = len(lineups.get("homePlayers", [])) >= 9
                        has_away = len(lineups.get("awayPlayers", [])) >= 9
                        if has_home and has_away:
                            return True, "🟢 Official 1-9 Lineups Confirmed"
        return False, "⚡ Lineups Pending — Using Morning Splits"
    except Exception:
        return False, "⚡ Lineups Pending — Using Morning Splits"

def american_to_implied(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def run_monte_carlo(home_lambda, away_lambda, n_sims, var_ratio, park_factor, weather_mult):
    home_exp = home_lambda * park_factor * weather_mult
    away_exp = away_lambda * park_factor * weather_mult
    
    home_runs = np.random.poisson(home_exp * var_ratio, n_sims) / var_ratio
    away_runs = np.random.poisson(away_exp * var_ratio, n_sims) / var_ratio
    
    ties = home_runs == away_runs
    home_runs[ties] += np.random.choice([1, 0], size=np.sum(ties), p=[0.54, 0.46])
    
    home_wins = np.sum(home_runs > away_runs)
    away_wins = np.sum(away_runs > home_runs)
    
    return home_wins / n_sims, away_wins / n_sims, np.mean(home_runs + away_runs), np.mean(home_runs), np.mean(away_runs)

if "wager_log" not in st.session_state:
    st.session_state.wager_log = []

# ---------------------------------------------------------
# 4. NAVIGATION TABS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Game Simulator", "🎯 Capping Report", "📝 Wager Log & CLV"])

# ---------------------------------------------------------
# TAB 1: GAME SIMULATOR
# ---------------------------------------------------------
with tab1:
    # --- CARD 1: MATCHUP & LIVE AUTO-FILL ---
    with st.container(border=True):
        st.markdown("##### 📅 Schedule & Matchup Auto-Fill")
        
        date_col, game_col = st.columns([1, 2])
        with date_col:
            selected_date = st.date_input("Game Date", value=datetime.today())
        
        live_games = fetch_live_games(api_key)
        def_away, def_home = "Chicago Cubs", "St. Louis Cardinals"
        def_away_ml, def_home_ml, def_total = -110, -110, 8.5
        
        with game_col:
            if live_games:
                game_options = ["Select Game from Live Schedule..."] + [g["label"] for g in live_games]
                selected_game_label = st.selectbox("🎯 Live Schedule", options=game_options, label_visibility="collapsed")
                
                if selected_game_label != "Select Game from Live Schedule...":
                    game_match = next((g for g in live_games if g["label"] == selected_game_label), None)
                    if game_match:
                        def_away = game_match["away_team"]
                        def_home = game_match["home_team"]
                        def_away_ml = game_match["away_ml"]
                        def_home_ml = game_match["home_ml"]
                        def_total = game_match["total_line"]
            else:
                st.caption("💡 Key saved in Secrets for auto-fill.")

    # --- CARD 2: TEAM SELECTION & LINEUP STATUS ---
    with st.container(border=True):
        st.markdown("##### 🏟️ Matchup & Automated Lineup Status")
        
        # Automated Lineup Detection Badge
        date_str = selected_date.strftime("%Y-%m-%d")
        lineups_are_official, lineup_status_msg = check_official_mlb_lineups(date_str, def_away, def_home)
        
        if lineups_are_official:
            st.markdown(f'<div class="status-badge-green">{lineup_status_msg}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-badge-yellow">{lineup_status_msg}</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            away_idx = MLB_TEAMS.index(def_away) if def_away in MLB_TEAMS else 0
            away_team = st.selectbox("Away Team", options=MLB_TEAMS, index=away_idx)
            away_starter = st.text_input("Away Starter", value="Javier Assad (RHP)")
            away_lambda = st.number_input(f"{away_team} Exp Runs", value=4.35, step=0.10)
            
        with col2:
            home_idx = MLB_TEAMS.index(def_home) if def_home in MLB_TEAMS else 0
            home_team = st.selectbox("Home Team", options=MLB_TEAMS, index=home_idx)
            home_starter = st.text_input("Home Starter", value="Andre Pallante (RHP)")
            home_lambda = st.number_input(f"{home_team} Exp Runs", value=4.15, step=0.10)

    # --- CARD 3: MARKET ODDS ---
    with st.container(border=True):
        st.markdown("##### 💰 Live Bookmaker Odds (Novig / FanDuel)")
        m1, m2, m3 = st.columns(3)
        with m1:
            away_ml_odds = st.number_input(f"{away_team} ML", value=int(def_away_ml))
        with m2:
            home_ml_odds = st.number_input(f"{home_team} ML", value=int(def_home_ml))
        with m3:
            market_total = st.number_input("Market Total", value=float(def_total), step=0.5)

    # --- PROGRESSIVE DISCLOSURE: ADVANCED TUNING EXPANDER ---
    with st.expander("⚙️ Advanced Model & Environment Tuning"):
        st.caption("Adjust Monte Carlo parameters and environmental multipliers if needed.")
        e1, e2 = st.columns(2)
        with e1:
            iterations = st.number_input("Iterations", min_value=10000, max_value=1000000, value=1000000, step=90000)
            variance_ratio = st.slider("Run Variance Scale Factor", min_value=1.0, max_value=1.6, value=1.3, step=0.05)
        with e2:
            park_factor = st.slider("Park Factor (1.00 = Neutral)", min_value=0.85, max_value=1.20, value=1.00, step=0.01)
            weather_mult = st.slider("Weather/Temp Multiplier", min_value=0.90, max_value=1.15, value=1.00, step=0.01)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Large Action Button
    if st.button("🚀 Run Monte Carlo Simulation", use_container_width=True, type="primary"):
        hw_pct, aw_pct, sim_total, exp_home, exp_away = run_monte_carlo(
            home_lambda, away_lambda, iterations, variance_ratio, park_factor, weather_mult
        )
        
        st.session_state.last_sim = {
            "date": date_str,
            "away_team": away_team,
            "home_team": home_team,
            "hw_pct": hw_pct,
            "aw_pct": aw_pct,
            "sim_total": sim_total,
            "exp_home": exp_home,
            "exp_away": exp_away,
            "away_ml_odds": away_ml_odds,
            "home_ml_odds": home_ml_odds,
            "market_total": market_total,
            "lineup_status": lineup_status_msg,
            "iterations": iterations
        }
        st.success("Simulation complete! Head over to the **🎯 Capping Report** tab.")

# ---------------------------------------------------------
# TAB 2: CAPPING REPORT
# ---------------------------------------------------------
with tab2:
    if "last_sim" not in st.session_state:
        st.info("👈 Run a simulation in the **Game Simulator** tab first.")
    else:
        sim = st.session_state.last_sim
        
        # Header Card
        with st.container(border=True):
            st.subheader("🎯 CAPPING REPORT")
            st.caption(f"📅 {sim['date']} | {sim['away_team']} @ {sim['home_team']}")
            st.caption(f"Status: {sim['lineup_status']}")

        # Primary Projections KPI Card
        with st.container(border=True):
            st.markdown("##### 📈 Projected Game Outcomes")
            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Projected Score", f"{sim['exp_away']:.2f} - {sim['exp_home']:.2f}")
            with k2:
                st.metric("Projected Total", f"{sim['sim_total']:.2f}", delta=f"{sim['sim_total'] - sim['market_total']:+.2f} vs Line")
            with k3:
                fav_team = sim['away_team'] if sim['aw_pct'] > sim['hw_pct'] else sim['home_team']
                fav_pct = max(sim['aw_pct'], sim['hw_pct']) * 100
                st.metric("Model Favorite", f"{fav_team}", f"{fav_pct:.1f}%")

        # EV & Value Card
        with st.container(border=True):
            st.markdown("##### 🔥 Market Edges & Expected Value")
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

        # Copyable Raw Text Card
        with st.container(border=True):
            st.markdown("##### 📋 Raw Text Output (Mobile Copy)")
            summary_text = (
                f"🎯 CAPPING REPORT (MLB)\n"
                f"Date: {sim['date']} | Matchup: {sim['away_team']} @ {sim['home_team']}\n"
                f"Status: {sim['lineup_status']}\n"
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
