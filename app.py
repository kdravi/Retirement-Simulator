import streamlit as st
import numpy as np
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Retirement Survival Simulator", layout="wide")

# ---------------- UI ----------------
st.title("Retirement Corpus Survival Simulator")

st.info("""
This tool estimates the probability that your retirement savings will last.
It simulates thousands of possible future market scenarios.
Results are not predictions, but probabilities.
""")

# ---------------- Inputs ----------------
st.header("Your Situation")
initial_corpus = st.number_input("Starting Corpus (₹)", value=50000000)
monthly_expense = st.number_input(
    "Monthly Expense (₹)",
    value=100000,
    help='Enter your current monthly expense in today\'s value. The model automatically increases this every year based on simulated inflation. This 
means your future withdrawals are NOT constant—they grow over time to maintain purchasing power.'
)
st.caption("Note: Expenses are adjusted for inflation each year. They are not constant over the full duration.")
years = st.slider("Years to simulate", 10, 50, 30)

st.header("Investment Mix")
col1, col2, col3 = st.columns(3)

if col1.button("Conservative"):
    st.session_state.alloc = [20, 50, 20, 5, 5]
if col2.button("Balanced"):
    st.session_state.alloc = [50, 30, 10, 5, 5]
if col3.button("Aggressive"):
    st.session_state.alloc = [70, 20, 5, 3, 2]

if "alloc" not in st.session_state:
    st.session_state.alloc = [50, 30, 10, 5, 5]

eq = st.slider("Equity (%)", 0, 100, st.session_state.alloc[0])
debt = st.slider("Debt (%)", 0, 100, st.session_state.alloc[1])
liquid = st.slider("Liquid (%)", 0, 100, st.session_state.alloc[2])
gold = st.slider("Gold (%)", 0, 100, st.session_state.alloc[3])
silver = st.slider("Silver (%)", 0, 100, st.session_state.alloc[4])

total = eq + debt + liquid + gold + silver
if total != 100:
    eq = eq * 100 / total
    debt = debt * 100 / total
    liquid = liquid * 100 / total
    gold = gold * 100 / total
    silver = silver * 100 / total

st.caption(f"Adjusted Allocation → Equity: {eq:.1f}%, Debt: {debt:.1f}%, Liquid: {liquid:.1f}%, Gold: {gold:.1f}%, Silver: {silver:.1f}%")

st.header("Market Behaviour")
shock_level = st.selectbox(
    "Market Shock Level",
    ["Low", "Medium", "High"],
    help="Controls how extreme market ups and downs can be.\n\nLow → Smooth markets\nMedium → Occasional sharp movements\nHigh → Frequent 
crashes/spikes\n\nTechnically: Uses Student-t distribution (fat tails)."
)

use_regime = st.checkbox(
    "Simulate changing economic conditions",
    value=True,
    help="Simulates different economic environments like normal growth, high inflation, and low growth using a regime-switching model."
)

simulations = st.slider("Number of simulations", 1000, 10000, 3000,
                        help="Higher = more accurate but slower")

# ---------------- Parameters ----------------
means = {"equity": 0.12, "debt": 0.07, "liquid": 0.05, "gold": 0.08, "silver": 0.10, "inflation": 0.06}
stds = {"equity": 0.20, "debt": 0.04, "liquid": 0.015, "gold": 0.18, "silver": 0.30, "inflation": 0.02}

nu_map = {"Low": 10, "Medium": 5, "High": 3}
nu = nu_map[shock_level]

regimes = {"normal": {"inflation": 0.05}, "high_inflation": {"inflation": 0.09}, "low_growth": {"inflation": 0.03}}
transition_matrix = {"normal": [0.7, 0.15, 0.15], "high_inflation": [0.4, 0.5, 0.1], "low_growth": [0.5, 0.1, 0.4]}
regime_list = list(regimes.keys())

# ---------------- Simulation ----------------
def simulate_once():
    corpus = initial_corpus
    withdrawal = monthly_expense * 12
    regime = "normal"

    for year in range(years):
        if use_regime:
            regime = np.random.choice(regime_list, p=transition_matrix[regime])
            inflation = regimes[regime]["inflation"] + np.random.normal(0, stds["inflation"])
        else:
            inflation = np.random.normal(means["inflation"], stds["inflation"])

        equity_return = means["equity"] + stds["equity"] * np.random.standard_t(nu)
        debt_return = np.random.normal(means["debt"], stds["debt"])
        liquid_return = np.random.normal(means["liquid"], stds["liquid"])
        gold_return = np.random.normal(means["gold"], stds["gold"])
        silver_return = np.random.normal(means["silver"], stds["silver"])

        portfolio_return = (eq/100 * equity_return + debt/100 * debt_return + liquid/100 * liquid_return + gold/100 * gold_return + silver/100 * 
silver_return)

        withdrawal *= (1 + inflation)
        corpus = corpus * (1 + portfolio_return) - withdrawal

        if corpus <= 0:
            return False, year

    return True, years

# ---------------- PDF Generator ----------------
def generate_pdf():
    doc = SimpleDocTemplate("retirement_report.pdf")
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("Retirement Simulation – Methodology & Assumptions", styles['Title']))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Approach:", styles['Heading2']))
    content.append(Paragraph("This tool uses Monte Carlo simulation to model thousands of possible future scenarios. Each simulation randomly generates 
yearly returns for different asset classes and inflation, then evaluates whether the retirement corpus survives.", styles['BodyText']))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Key Concepts:", styles['Heading2']))
    content.append(Paragraph("1. Sequence of returns risk – early losses hurt more.<br/>2. Inflation-adjusted withdrawals.<br/>3. Diversified asset 
allocation.<br/>4. Probability-based outcomes instead of single estimates.", styles['BodyText']))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Market Modeling:", styles['Heading2']))
    content.append(Paragraph("Equity returns use a Student-t distribution to capture extreme events (fat tails). Other assets use normal distributions. 
Economic regimes simulate changing macro conditions.", styles['BodyText']))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Assumptions (Typical India context):", styles['Heading2']))
    content.append(Paragraph("Equity ~12%, Debt ~7%, Gold ~8%, Inflation ~6% with respective volatilities.", styles['BodyText']))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Disclaimer:", styles['Heading2']))
    content.append(Paragraph("This is a probabilistic model for educational purposes. Actual market outcomes may vary significantly.", 
styles['BodyText']))

    doc.build(content)
    return "retirement_report.pdf"

# ---------------- Run Simulation ----------------
if st.button("Run Simulation"):
    results = []
    failure_years = []
    progress = st.progress(0)

    for i in range(simulations):
        success, yr = simulate_once()
        results.append(success)
        if not success:
            failure_years.append(yr)
        progress.progress((i + 1) / simulations)

    survival_prob = sum(results) / simulations

    st.header("Results")
    st.metric("Probability your money lasts", f"{survival_prob*100:.1f}%")

    if survival_prob > 0.85:
        st.success("Your plan looks reasonably safe.")
    elif survival_prob > 0.70:
        st.warning("Your plan has moderate risk.")
    else:
        st.error("High risk of running out of money.")

    if failure_years:
        df = pd.DataFrame(failure_years, columns=["Year"])
        st.bar_chart(df["Year"].value_counts().sort_index())

    # PDF Download
    pdf_file = generate_pdf()
    with open(pdf_file, "rb") as f:
        st.download_button("Download Methodology PDF", f, file_name="retirement_simulation.pdf")

    st.success("Simulation complete")

