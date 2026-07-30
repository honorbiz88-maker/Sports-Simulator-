import streamlit as st
import numpy as np
import pandas as pd
import requests
from datetime import datetime

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & SETUP
# ---------------------------------------------------------
st.set_page_config(
    page_title="MLB Monte Carlo Capping Engine",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚾ MLB Monte Carlo Capping Engine")

# ---------------------------------------------------------
# 2. SECRETS & API KEY MANAGEMENT
# ---------------------------------------------------------
# Checks Streamlit Secrets first; falls back to manual entry if missing
if "ODDS_API_KEY" in st.secrets:
    api_key = st.secrets["ODDS_API_KEY"]
else:
    api_key = st.sidebar.text_input("The Odds API Key", type="password", help="Add ODDS_API_KEY to Streamlit Secrets to auto-load.")

# ---------------------------------------------------------
# 3. SIDEBAR CONFIGURATION
# ---------------------------------------------------------
st.sidebar.header("⚙️ Simulation Settings")

# Lineup Mode Toggle
sim_mode = st.sidebar.radio(
    "Lineup Mode",
    options=["Morning Mode (Projected Team Splits)", "Official Lineup Mode (1-9 Order)"],
    help="Morning Mode uses overall team platoon stats vs. starter hand before official 1-9 lineups lock in."
)

# Monte Carlo Parameters
iterations = st.sidebar.number_input("Monte Carlo Iterations", min_value=10000, max_value=1000000, value=1000000, step=90000)
variance_ratio = st.sidebar.slider("Run Variance Scale Factor", min_value=1.0, max_value=1.6, value=1.3, step=0.05)

# Environmental & Park Factor Modifiers
st.sidebar.subheader("🏟️ Game Environment")
park_factor = st.sidebar.slider("Park Factor (1.00 = Neutral)", min_value=0.85, max_value=1.20, value=1.00, step=0.01)
weather_mult = st.sidebar.slider("Weather/Temp Multiplier", min_value=0.90, max_value=1.15, value=1.00, step=0.01)

# ---------------------------------------------------------
# 4. HELPER FUNCTIONS & API INTEGRATION
# ---------------------------------------------------------
def get_live_odds(api_key):
    """Fetches upcoming MLB odds from The Odds API."""
    if not api_key:
        st.warning("⚠️ No API Key provided. Enter a key or save it in Streamlit Secrets.")
        return []
    
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={api_key}&regions=us&markets=h2h,totals&oddsFormat=american"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()
        else:
            st.error(f"API Error ({res.status_code}): {res.text}")
            return []
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return []

def american_to_implied(odds):
    """Converts American odds to implied probability percentage."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def run_monte_carlo(home_lambda, away_lambda, n_sims, var_ratio):
    """Runs Poisson-based Monte Carlo simulations for game score outcomes."""
    # Scale parameters by environmental modifiers
    home_exp = home_lambda * park_factor * weather_mult
    away_exp = away_lambda * park_factor * weather_mult
    
    # Generate simulated run distributions
    home_runs = np.random.poisson(home_exp * var_ratio, n_sims) / var_ratio
    away_runs = np.random.poisson(away_exp * var_ratio, n_sims) / var_ratio
    
    # Avoid ties in baseball: add tiebreaker extra-inning simulation
    ties = home_runs == away_runs
    home_runs[ties] += np.random.choice([1, 0], size=np.sum(ties), p=[0.54, 0.46]) # Home team slight extra-inning edge
    
    home_wins = np.sum(home_runs > away_runs)
    away_wins = np.sum(away_runs > home_runs)
    
    home_win_pct = home_wins / n_sims
    away_win_pct = away_wins / n_sims
    
    total_runs = home_runs + away_runs
    avg_total = np.mean(total_runs)
    
    return home_win_pct, away_win_pct, avg_total, np.mean(home_runs), np.mean(away_runs), total_runs

# Initialize Session State for Wager Tracker
if "wager_log" not in st.session_state:
    st.session_state.wager_log = []

# ---------------------------------------------------------
# 5. MAIN NAVIGATION TABS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Game Simulator", "🎯 Capping Report", "📝 Wager Log & CLV"])

# ---------------------------------------------------------
# TAB 1: GAME SIMULATOR
# ---------------------------------------------------------
with tab1:
    st.subheader("Matchup & Odds Input")
    
    col1, col2 = st.columns(2)
    with col1:
        away_team = st.text_input("Away Team", value="Chicago Cubs")
        away_starter = st.text_input("Away Starter & Hand", value="Javier Assad (RHP)")
    with col2:
        home_team = st.text_input("Home Team", value="St. Louis Cardinals")
        home_starter = st.text_input("Home Starter & Hand", value="Andre Pallante (RHP)")

    st.markdown("---")
    
    if sim_mode == "Morning Mode (Projected Team Splits)":
        st.info("⚡ **Morning Mode Active:** Inputs rely on team-wide platoon metrics (wRC+/OPS) vs. starter hand.")
        c1, c2 = st.columns(2)
        with c1:
            away_lambda = st.number_input(f"{away_team} Projected Baseline Runs", value=4.50, step=0.10)
        with c2:
            home_lambda = st.number_input(f"{home_team} Projected Baseline Runs", value=4.20, step=0.10)
    else:
        st.success("✅ **Official Lineup Mode Active:** Inputs rely on confirmed 1–9 PA-weighted stats.")
        c1, c2 = st.columns(2)
        with c1:
            away_lambda = st.number_input(f"{away_team} Confirmed Lineup Expected Runs", value=4.35, step=0.10)
        with c2:
            home_lambda = st.number_input(f"{home_team} Confirmed Lineup Expected Runs", value=4.15, step=0.10)

    # Market Lines Section
    st.subheader("Bookmaker Lines (Novig / FanDuel)")
    m1, m2, m3 = st.columns(3)
    with m1:
        away_ml_odds = st.number_input(f"{away_team} ML Odds", value=-110)
    with m2:
        home_ml_odds = st.number_input(f"{home_team} ML Odds", value=-110)
    with m3:
        market_total = st.number_input("Market Total Line", value=8.5, step=0.5)

    if st.button("🚀 Run 1,000,000 Simulation Iterations", use_container_width=True):
        hw_pct, aw_pct, sim_total, exp_home, exp_away, total_dist = run_monte_carlo(
            home_lambda, away_lambda, iterations, variance_ratio
        )
        
        # Save results into session state for Capping Report tab
        st.session_state.last_sim = {
            "date": datetime.now().strftime("%Y-%m-%d"),
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
            "total_dist": total_dist
        }
        st.success("Simulation complete! Head over to the **🎯 Capping Report** tab to view projections.")

# ---------------------------------------------------------
# TAB 2: CAPPING REPORT
# ---------------------------------------------------------
with tab2:
    if "last_sim" not in st.session_state:
        st.info("👈 Run a simulation in the **Game Simulator** tab first to generate a report.")
    else:
        sim = st.session_state.last_sim
        
        st.subheader("🎯 CAPPING REPORT (MLB)")
        st.caption(f"Date: {sim['date']} | Matchup: {sim['away_team']} @ {sim['home_team']}")
        st.markdown("---")
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Projected Score", f"{sim['away_team']} {sim['exp_away']:.2f} - {sim['exp_home']:.2f} {sim['home_team']}")
        with col_b:
            st.metric("Projected Total", f"{sim['sim_total']:.2f} Runs", delta=f"{sim['sim_total'] - sim['market_total']:.2f} vs line")
        with col_c:
            fav_team = sim['away_team'] if sim['aw_pct'] > sim['hw_pct'] else sim['home_team']
            fav_pct = max(sim['aw_pct'], sim['hw_pct']) * 100
            st.metric("Model Favorite", f"{fav_team}", f"{fav_pct:.1f}% Win Prob")

        st.markdown("---")
        
        # EV & Edge Calculations
        home_implied = american_to_implied(sim['home_ml_odds'])
        away_implied = american_to_implied(sim['away_ml_odds'])
        
        away_edge = (sim['aw_pct'] - away_implied) * 100
        home_edge = (sim['hw_pct'] - home_implied) * 100
        
        st.write("### Model Value & Edges")
        e1, e2 = st.columns(2)
        with e1:
            st.write(f"**{sim['away_team']} ML:** Model {sim['aw_pct']*100:.1f}% vs Implied {away_implied*100:.1f}%")
            if away_edge > 0:
                st.success(f"Edge: +{away_edge:.1f}% EV")
            else:
                st.write(f"Edge: {away_edge:.1f}% (No Value)")
                
        with e2:
            st.write(f"**{sim['home_team']} ML:** Model {sim['hw_pct']*100:.1f}% vs Implied {home_implied*100:.1f}%")
            if home_edge > 0:
                st.success(f"Edge: +{home_edge:.1f}% EV")
            else:
                st.write(f"Edge: {home_edge:.1f}% (No Value)")

        # Raw Text Export Box for Mobile Copy/Paste
        st.markdown("---")
        st.write("### Raw Text Summary")
        summary_text = (
            f"🎯 CAPPING REPORT (MLB)\n"
            f"Date: {sim['date']} | Matchup: {sim['away_team']} @ {sim['home_team']}\n"
            f"----------------------------------------\n"
            f"• Projected Final Score: {sim['away_team']} {sim['exp_away']:.2f} - {sim['home_team']} {sim['exp_home']:.2f}\n"
            f"• Projected Game Total: {sim['sim_total']:.2f} (Market Line: {sim['market_total']})\n"
            f"• {sim['away_team']} Win Prob: {sim['aw_pct']*100:.1f}%\n"
            f"• {sim['home_team']} Win Prob: {sim['hw_pct']*100:.1f}%\n"
            f"----------------------------------------\n"
            f"Simulated over {iterations:,} Monte Carlo iterations."
        )
        st.code(summary_text, language="text")

# ---------------------------------------------------------
# TAB 3: WAGER LOG & CLV TRACKER
# ---------------------------------------------------------
with tab3:
    st.subheader("📝 Wager Log & Closing Line Value (CLV) Tracker")
    
    with st.form("add_wager_form"):
        w_col1, w_col2, w_col3 = st.columns(3)
        with w_col1:
            w_date = st.date_input("Bet Date")
            w_matchup = st.text_input("Matchup", value="Cubs @ Cardinals")
        with w_col2:
            w_pick = st.text_input("Pick Taken", value="Cubs @ Cardinals UNDER 8.5")
            w_odds = st.number_input("Placed Odds (American)", value=-110)
        with w_col3:
            w_stake = st.number_input("Stake ($)", value=1.00, step=0.25)
            w_closing = st.number_input("Closing Odds (CLV)", value=-120)
            
        submitted = st.form_submit_button("Log Wager")
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

    st.markdown("---")
    st.write("### Logged Wagers")
    if st.session_state.wager_log:
        df_log = pd.DataFrame(st.session_state.wager_log)
        st.dataframe(df_log, use_container_width=True)
    else:
        st.info("No wagers logged yet. Use the form above to track your plays.")
