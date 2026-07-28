import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="NBA & MLB Simulator", page_icon="⚾", layout="centered"
)

st.title("⚾ NBA & MLB Monte Carlo Model")

# Sport Toggle
sport = st.radio(
    "Select Sport", ["NBA (Basketball)", "MLB (Baseball)"], horizontal=True
)


def get_ev(prob, odds):
    fair = 1 / prob if prob > 0 else 0
    ev = ((prob * (odds - 1)) - (1 - prob)) * 100
    return fair, ev


with st.form("simulation_form"):
    col1, col2 = st.columns(2)

    if sport == "NBA (Basketball)":
        with col1:
            home_team = st.text_input("Home Team", "Celtics")
            home_pts = st.number_input(
                "Home Projected Pts", value=114.5, step=0.5
            )
            sportsbook_home_ml = st.number_input(
                "Home Moneyline Odds", value=1.55
            )
            sportsbook_spread_odds = st.number_input(
                "Home Spread Odds", value=1.91
            )
            spread_line = st.number_input(
                "Home Spread Line (e.g. -5.5)", value=-5.5, step=0.5
            )

        with col2:
            away_team = st.text_input("Away Team", "Lakers")
            away_pts = st.number_input(
                "Away Projected Pts", value=108.0, step=0.5
            )
            sportsbook_away_ml = st.number_input(
                "Away Moneyline Odds", value=2.50
            )
            sportsbook_over_odds = st.number_input("Over Odds", value=1.91)
            total_line = st.number_input(
                "Over/Under Line", value=222.5, step=0.5
            )

        nba_std = st.slider(
            "Game Variance (Standard Deviation)", 8.0, 15.0, 11.5, step=0.5
        )

    else:  # MLB
        with col1:
            home_team = st.text_input("Home Team", "Dodgers")
            home_runs = st.number_input(
                "Home Expected Runs (xR)", value=4.8, step=0.1
            )
            sportsbook_home_ml = st.number_input(
                "Home Moneyline Odds", value=1.65
            )
            sportsbook_spread_odds = st.number_input(
                "Home Run Line (-1.5) Odds", value=2.20
            )
            spread_line = st.number_input(
                "Home Run Line", value=-1.5, step=0.5
            )

        with col2:
            away_team = st.text_input("Away Team", "Yankees")
            away_runs = st.number_input(
                "Away Expected Runs (xR)", value=3.9, step=0.1
            )
            sportsbook_away_ml = st.number_input(
                "Away Moneyline Odds", value=2.30
            )
            sportsbook_over_odds = st.number_input("Over Odds", value=1.91)
            total_line = st.number_input(
                "Over/Under Line", value=8.5, step=0.5
            )

    num_sims = st.select_slider(
        "Simulations", [10000, 50000, 100000], value=100000
    )
    submitted = st.form_submit_button("🔥 Run 100k Simulations")

if submitted:
    # Monte Carlo Engine
    if sport == "NBA (Basketball)":
        sim_home = np.random.normal(home_pts, nba_std, num_sims)
        sim_away = np.random.normal(away_pts, nba_std, num_sims)
    else:
        sim_home = np.random.poisson(home_runs, num_sims)
        sim_away = np.random.poisson(away_runs, num_sims)

    # Probabilities
    p_home_win = np.mean(sim_home > sim_away)
    p_away_win = np.mean(sim_away > sim_home)

    # Spread / Run Line Cover
    p_home_cover = np.mean((sim_home + spread_line) > sim_away)

    # Totals
    totals = sim_home + sim_away
    p_over = np.mean(totals > total_line)
    p_under = np.mean(totals < total_line)

    tab1, tab2, tab3 = st.tabs(
        ["💰 Moneyline", "📏 Spread / Run Line", "⚽ Totals (O/U)"]
    )

    with tab1:
        f_h, ev_h = get_ev(p_home_win, sportsbook_home_ml)
        f_a, ev_a = get_ev(p_away_win, sportsbook_away_ml)

        st.metric(
            f"{home_team} Win",
            f"{p_home_win*100:.1f}%",
            f"EV: {ev_h:+.1f}%",
            delta_color="normal" if ev_h > 0 else "inverse",
        )
        st.caption(
            f"Fair Odds: **{f_h:.2f}** | Bookie: **{sportsbook_home_ml:.2f}**"
        )

        st.metric(
            f"{away_team} Win",
            f"{p_away_win*100:.1f}%",
            f"EV: {ev_a:+.1f}%",
            delta_color="normal" if ev_a > 0 else "inverse",
        )
        st.caption(
            f"Fair Odds: **{f_a:.2f}** | Bookie: **{sportsbook_away_ml:.2f}**"
        )

    with tab2:
        f_cov, ev_cov = get_ev(p_home_cover, sportsbook_spread_odds)
        st.metric(
            f"{home_team} ({spread_line:+.1f}) Cover",
            f"{p_home_cover*100:.1f}%",
            f"EV: {ev_cov:+.1f}%",
            delta_color="normal" if ev_cov > 0 else "inverse",
        )
        st.caption(
            f"Fair Odds: **{f_cov:.2f}** | Bookie: **{sportsbook_spread_odds:.2f}**"
        )

    with tab3:
        f_o, ev_o = get_ev(p_over, sportsbook_over_odds)
        st.metric(
            f"Over {total_line}",
            f"{p_over*100:.1f}%",
            f"EV: {ev_o:+.1f}%",
            delta_color="normal" if ev_o > 0 else "inverse",
        )
        st.caption(
            f"Fair Odds: **{f_o:.2f}** | Bookie: **{sportsbook_over_odds:.2f}**"
        )

    
