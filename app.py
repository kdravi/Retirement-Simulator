import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Retirement Survival Simulator", layout="wide")

# ---------------- UI ----------------
st.title("Retirement Corpus Survival Simulator")

st.markdown("Simulates whether your retirement savings will last under real-world market conditions.")

# User Inputs
st.header("Your Situation")
initial_corpus = st.number_input("Starting Corpus (₹)", value=50000000)
monthly_expense = st.number_input("Monthly Expense (₹)", value=100000)
years = st.slider("Years to simulate", 10, 50, 30)

st.header("Asset Allocation (%)")
eq = st.slider("Equity", 0, 100, 50)
debt = st.slider("Debt", 0, 100, 30)
liquid = st.slider("Liquid", 0, 100, 10)
gold = st.slider("Gold", 0, 100, 5)
silver = st.slider("Silver", 0, 100, 5)

alloc_total = eq + debt + liquid + gold + silver
if alloc_total != 100:
    st.warning("Allocation must sum to 100%")

st.header("Market Settings")
shock_level = st.selectbox("Market Shock Level", ["Low", "Medium", "High"])
use_regime = st.checkbox("Use Economic Regimes", value=True)

simulations = st.slider("Number of simulations", 1000, 20000, 5000)

# ---------------- Parameters ----------------
means = {
    "equity": 0.12,
    "debt": 0.07,
    "liquid": 0.05,
    "gold": 0.08,
    "silver": 0.10,
    "inflation": 0.06
}

stds = {
    "equity": 0.20,
    "debt": 0.04,
    "liquid": 0.015,
    "gold": 0.18,
    "silver": 0.30,
    "inflation": 0.02
}

# Shock level mapping
nu_map = {"Low": 10, "Medium": 5, "High": 3}
nu = nu_map[shock_level]

# Regime definitions
regimes = {
    "normal": {"inflation": 0.05},
    "high_inflation": {"inflation": 0.09},
    "low_growth": {"inflation": 0.03}
}

transition_matrix = {
    "normal": [0.7, 0.15, 0.15],
    "high_inflation": [0.4, 0.5, 0.1],
    "low_growth": [0.5, 0.1, 0.4]
}

regime_list = list(regimes.keys())

# ---------------- Simulation ----------------
def simulate_once():
    corpus = initial_corpus
    withdrawal = monthly_expense * 12
    regime = "normal"

    for year in range(years):
        if use_regime:
            probs = transition_matrix[regime]
            regime = np.random.choice(regime_list, p=probs)
            inflation = regimes[regime]["inflation"] + np.random.normal(0, stds["inflation"])
        else:
            inflation = np.random.normal(means["inflation"], stds["inflation"])

        # Student-t for equity
        equity_return = means["equity"] + stds["equity"] * np.random.standard_t(nu)

        # Other assets normal
        debt_return = np.random.normal(means["debt"], stds["debt"])
        liquid_return = np.random.normal(means["liquid"], stds["liquid"])
        gold_return = np.random.normal(means["gold"], stds["gold"])
        silver_return = np.random.normal(means["silver"], stds["silver"])

        portfolio_return = (
            eq/100 * equity_return +
            debt/100 * debt_return +
            liquid/100 * liquid_return +
            gold/100 * gold_return +
            silver/100 * silver_return
        )

        withdrawal *= (1 + inflation)
        corpus = corpus * (1 + portfolio_return) - withdrawal

        if corpus <= 0:
            return False, year

    return True, years

# ---------------- Run Simulation ----------------
if st.button("Run Simulation"):
    results = []
    failure_years = []

    for _ in range(simulations):
        success, yr = simulate_once()
        results.append(success)
        if not success:
            failure_years.append(yr)

    survival_prob = sum(results) / simulations

    st.header("Results")
    st.metric("Survival Probability", f"{survival_prob*100:.1f}%")

    if failure_years:
        st.subheader("Failure Year Distribution")
        df = pd.DataFrame(failure_years, columns=["Year"])
        st.bar_chart(df["Year"].value_counts().sort_index())

    st.success("Simulation complete")

