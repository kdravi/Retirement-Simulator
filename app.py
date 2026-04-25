# Add this section AFTER simulation to create a fan chart (clean visualization)
import matplotlib.pyplot as plt

# Modify simulation to store paths

def simulate_paths():
    paths = []
    for _ in range(simulations):
        corpus = initial_corpus
        withdrawal = monthly_expense * 12
        yearly_values = []
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
            corpus = corpus * (1 + portfolio_return) - withdrawal
            yearly_values.append(max(corpus, 0))

            if corpus <= 0:
                yearly_values += [0] * (years - year - 1)
                break

        paths.append(yearly_values)

    return np.array(paths)

# Plot fan chart
if st.button("Show Corpus Projection"):
    paths = simulate_paths()

    percentiles = np.percentile(paths, [5, 25, 50, 75, 95], axis=0)

    fig, ax = plt.subplots()
    ax.plot(percentiles[2], label="Median")
    ax.fill_between(range(years), percentiles[0], percentiles[4], alpha=0.2, label="Extreme range")
    ax.fill_between(range(years), percentiles[1], percentiles[3], alpha=0.3, label="Typical range")

    ax.set_title("Corpus Projection Over Time")
    ax.set_xlabel("Years")
    ax.set_ylabel("Corpus")
    ax.legend()

    st.pyplot(fig)

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

# Optional: Simple comparison tool
if st.checkbox("Test impact of reducing expenses by 10%"):
    reduced_expense = monthly_expense * 0.9
    alt_results = []

    for _ in range(1000):
        corpus = initial_corpus
        withdrawal = reduced_expense * 12
        regime = "normal"

        for year in range(years):
            if use_regime:
                regime = np.random.choice(regime_list, p=transition_matrix[regime])
                inflation = regimes[regime]["inflation"] + np.random.normal(0, stds["inflation"])
            else:
                inflation = np.random.normal(means["inflation"], stds["inflation"])

            portfolio_return = np.random.normal(0.1, 0.15)
            withdrawal *= (1 + inflation)
            corpus = corpus * (1 + portfolio_return) - withdrawal

            if corpus <= 0:
                alt_results.append(False)
                break
        else:
            alt_results.append(True)

    st.metric("Survival with 10% lower expense", f"{sum(alt_results)/len(alt_results)*100:.1f}%")
