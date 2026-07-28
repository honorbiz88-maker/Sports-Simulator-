import numpy as np
import pandas as pd
from scipy.stats import poisson
import streamlit as st

st.set_page_config(
    page_title="Pro Monte Carlo Simulator", page_icon="⚡", layout="centered"
)

st.title("⚡ Pro Sports Monte Carlo Model")

# 1. Inputs inside a Form to prevent lag
with st.form("model_inputs"):
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.text_input("Home Team", "Arsenal")
        home_xg = st.number_input("Home xG", value=1.75, step=0.05)
        sportsbook_home = st.number_input("Bookie Home Odds", value=2.10)
    with col2:
        away_team = st.text_input("Away Team", "Chelsea")
        away_xg = st.number_input("Away xG", value=1.15, step=0.05)
        sportsbook_away = st.number_input("Bookie Away Odds", value=3.60)

    st.markdown("---")
    c3, c4 = st.columns(2)
    with c3:
        sportsbook_draw = st.number_input("Bookie Draw Odds", value=3.40)
        total_line = st.number_input("O/U Line", value=2.5, step=0.5)
    with c4:
        sportsbook_over = st.number_input("Bookie Over Odds", value=1.90)
        sportsbook_under = st.number_input("Bookie Under Odds", value=1.90)

    num_sims = st.select_slider("Simulations", [10000, 50000, 100000], value=100000)
    run_btn = st.form_submit_button("🚀 Run Simulation")


# 2. Cached Heavy Math Functions
@st.cache_data
def run_simulation(h_xg, a_xg, sims, t_line):
    sim_h = np.random.poisson(h_xg, sims)
    sim_a = np.random.poisson(a_xg, sims)

    p_h = np.mean(sim_h > sim_a)
    p_d = np.mean(sim_h == sim_a)
    p_a = np.mean(sim_h < sim_a)

    p_o = np.mean((sim_h + sim_a) > t_line)
    p_u = np.mean((sim_h + sim_a) < t_line)

    return p_h, p_d, p_a, p_o, p_u


def get_ev(prob, odds):
    fair = 1 / prob if prob > 0 else 0
    ev = ((prob * (odds - 1)) - (1 - prob)) * 100
    return fair, ev


# 3. Output Tabs for Mobile Viewing
if run_btn:
    p_h, p_d, p_a, p_o, p_u = run_simulation(
        home_xg, away_xg, num_sims, total_line
    )

    tab1, tab2, tab3 = st.tabs(
        ["📊 Match Outcomes", "⚽ Totals", "🎯 Exact Scores"]
    )

    with tab1:
        for name, p, odds in [
            (home_team, p_h, sportsbook_home),
            ("Draw", p_d, sportsbook_draw),
            (away_team, p_a, sportsbook_away),
        ]:
            fair, ev = get_ev(p, odds)
            st.metric(
                label=f"{name} ({p*100:.1f}%)",
                value=f"Fair: {fair:.2f}",
                delta=f"EV: {ev:+.1f}%",
            )

    with tab2:
        for name, p, odds in [
            (f"Over {total_line}", p_o, sportsbook_over),
            (f"Under {total_line}", p_u, sportsbook_under),
        ]:
            fair, ev = get_ev(p, odds)
            st.metric(
                label=f"{name} ({p*100:.1f}%)",
                value=f"Fair: {fair:.2f}",
                delta=f"EV: {ev:+.1f}%",
            )

    with tab3:
        h_p = poisson.pmf(np.arange(6), home_xg)
        a_p = poisson.pmf(np.arange(6), away_xg)
        grid = pd.DataFrame(
            np.outer(h_p, a_p) * 100,
            index=[f"{home_team} {i}" for i in range(6)],
            columns=[f"{away_team} {j}" for j in range(6)],
        )
        st.dataframe(grid.style.highlight_max(axis=None, color="#1e4620"))
