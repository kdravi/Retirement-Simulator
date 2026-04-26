import streamlit as st
import numpy as np
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import io

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
    help="""Enter your current monthly expense in today's value.

The model automatically increases this every year based on simulated inflation.

This means your future withdrawals are NOT constant—they grow over time to maintain purchasing power."""
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
    help="""Controls how extreme market ups and downs can be.

Low → Smooth markets
Medium → Occasional sharp movements
High → Frequent crashes and spikes

Technically: Uses Student-t distribution (fat tails) where extreme events are more likely than normal distribution."""
)

use_regime = st.checkbox(
    "Simulate changing economic conditions",
    value=True,
    help="""Simulates different economic environments over time.

Normal → Steady growth
High Inflation → Rising prices, stress on equity, stronger gold
Low Growth → Slower economy, weaker equity, stronger debt

Technically: Uses a regime-switching (Markov) model where the economy transitions between states."""
)

simulations = st.slider(
    "Number of simulations",
    1000,
    10000,
    3000,
    help="""Higher number of simulations increases accuracy but takes more time to compute."""
)

# Tax Inputs

st.header("Tax Settings")

tax_mode = st.radio("Filing Type", ["Single", "Couple"])

st.caption("Basic simplified Indian tax assumptions applied.")




# ---------------- Parameters ----------------
means = {"equity": 0.12, "debt": 0.07, "liquid": 0.05, "gold": 0.08, "silver": 0.10, "inflation": 0.06}
stds = {"equity": 0.20, "debt": 0.04, "liquid": 0.015, "gold": 0.18, "silver": 0.30, "inflation": 0.02}

nu_map = {"Low": 10, "Medium": 5, "High": 3}
nu = nu_map[shock_level]

regimes = {"normal": {"inflation": 0.05}, "high_inflation": {"inflation": 0.09}, "low_growth": {"inflation": 0.03}}
transition_matrix = {"normal": [0.7, 0.15, 0.15], "high_inflation": [0.4, 0.5, 0.1], "low_growth": [0.5, 0.1, 0.4]}
regime_list = list(regimes.keys())



# Simplified Tax function

def calculate_tax(income, mode):
    # basic slabs (simplified new regime style)
    if mode == "Single":
        exemption = 300000
    else:
        exemption = 600000  # assume split income benefit

    taxable = max(0, income - exemption)

    if taxable <= 300000:
        tax = taxable * 0.05
    elif taxable <= 600000:
        tax = 15000 + (taxable - 300000) * 0.10
    elif taxable <= 900000:
        tax = 45000 + (taxable - 600000) * 0.15
    else:
        tax = 90000 + (taxable - 900000) * 0.20

    return tax


# ---------------- Simulation ----------------
def simulate_once():
    corpus = initial_corpus
    withdrawal = monthly_expense * 12
    yearly_values = []
    yearly_expenses = []
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

        portfolio_return = (
            eq/100 * equity_return +
            debt/100 * debt_return +
            liquid/100 * liquid_return +
            gold/100 * gold_return +
            silver/100 * silver_return
        )

        withdrawal *= (1 + inflation)

        # Tax to include in expenses
        gross_withdrawal = withdrawal
        tax = calculate_tax(gross_withdrawal, tax_mode)
        net_withdrawal = gross_withdrawal + tax  # user needs extra to pay tax

        yearly_expenses.append(withdrawal)
        corpus = corpus * (1 + portfolio_return) - net_withdrawal
        yearly_values.append(max(corpus, 0))

        if corpus <= 0:
            remaining_years = years - year - 1

            yearly_values += [0] * (years - year - 1)

            last_expense = yearly_expenses[-1]
            yearly_expenses += [last_expense] * remaining_years
            return False, year, yearly_values, yearly_expenses

    return True, years, yearly_values, yearly_expenses


# ---------------- Run Simulation ----------------
if st.button("Run Simulation"):
    results = []
    failure_years = []
    progress = st.progress(0)
    paths = []
    expense_paths = []

    for i in range(simulations):
        success, yr, yearly_values, yearly_expenses = simulate_once()
        results.append(success)
        if not success:
            failure_years.append(yr)

        progress.progress((i + 1) / simulations)
        paths.append(yearly_values)
        expense_paths.append(yearly_expenses)


    survival_prob = sum(results) / simulations


    st.header("Results")
    st.metric("Probability your money lasts", f"{survival_prob*100:.1f}%")

    if survival_prob > 0.85:
        st.success("Your plan looks reasonably safe.")
    elif survival_prob > 0.70:
        st.warning("Your plan has moderate risk.")
    else:
        st.error("High risk of running out of money.")

    # Plot fan chart
    percentiles = np.percentile(paths, [5, 25, 50, 75, 95], axis=0)

    # Convert to Crores
    percentiles = percentiles / 1e7  # 1 Crore = 1e7

    st.write("Debug lengths:", set(len(x) for x in expense_paths))



    expense_array = np.array(expense_paths, dtype=float)
    expense_percentiles = np.percentile(expense_paths, [50], axis=0)  # median only
    expense_percentiles = expense_percentiles / 1e5  # convert to Lakhs


    # Plotting chart below
 

    fig, ax1 = plt.subplots(figsize=(8, 4.5))

    # Corpus (existing)
    ax1.plot(percentiles[2], linewidth=2, label="Median Corpus")
    ax1.fill_between(range(years), percentiles[0], percentiles[4], alpha=0.15)
    ax1.fill_between(range(years), percentiles[1], percentiles[3], alpha=0.25)

    ax1.set_ylabel("Corpus (₹ Crores)")
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f Cr'))

    # Expense axis (NEW)
    ax2 = ax1.twinx()
    ax2.plot(expense_percentiles[0], linestyle="--", label="Annual Expense", linewidth=2)
    ax2.set_ylabel("Annual Expense (₹ Lakhs)")

    # Common
    ax1.set_title("Corpus vs Inflation-Adjusted Expenses")
    ax1.set_xlabel("Years")

    ax1.axhline(y=0, linestyle="--", linewidth=1)

    ax1.grid(alpha=0.2)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2)

    plt.tight_layout()
    st.pyplot(fig)


    st.success("Simulation complete")


# ---------------- Risk Mitigation Section ----------------

st.header("Understanding Sequence of Returns Risk")

st.markdown("""
**Sequence risk** means that poor returns in the early years of retirement can significantly reduce your corpus, even if long-term averages are good.

### Practical ways to manage this risk:

**1. Maintain 5–7 years of expenses in safe assets (Liquid/Debt)**
- Avoid selling equity during market crashes
- Gives time for markets to recover

**2. Flexible withdrawals**
- Reduce expenses temporarily during market downturns
- Even a 10–15% reduction in early bad years can improve survival probability significantly

**3. Glide path allocation**
- Start with slightly higher allocation to safe assets
- Gradually increase equity later

### What this simulator shows
You can test:
- Higher liquid allocation → better downside protection
- Lower expenses → significantly higher survival probability

Try experimenting with:
- Increasing Liquid to 20–30%
- Reducing expenses by 10% in early years
""")


# Read the PDF file in binary mode
with open("retirement_simulation_methodology.pdf", "rb") as pdf_file:
    PDFbyte = pdf_file.read()

# Create the download button
st.download_button(
    label="Download Simulation Methodology Document",
    data=PDFbyte,
    file_name="retirement_simulation_methodology.pdf",
    mime="application/pdf"
)
