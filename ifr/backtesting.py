# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: stock
#     language: python
#     name: python3
# ---

# %%
import numpy as np
import pandas as pd

# %%
test_prices = pd.DataFrame(
    {
        "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "AAPL": [1.0, 0.5, 2],
        "TSLA": [1.0, 2, 4],
    }
)
test_portfolio = pd.DataFrame(
    {
        "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "AAPL": [0.5, 0.5, 0.5],
        "TSLA": [0.5, 0.5, 0.5],
    }
)

# %%
test_prices

# %%
test_portfolio

# %% [markdown]
# Check that the portfolio is valid: stock weights add up to 1 at every point in time.

# %%
assert (
    test_portfolio[[col for col in test_portfolio.columns if col != "date"]].sum(axis=1)
    == np.repeat(1.0, test_portfolio.shape[0])
).all()


# %%
def backtest(stock_prices_df, portfolio):
    joined_df = stock_prices_df.merge(
        portfolio, on="date", suffixes=("_price", "_weight")
    ).sort_values("date", ascending=True)

    tickers = [col for col in stock_prices_df.columns if col != "date"]

    portfolio_value = list()
    for dt in stock_prices_df["date"].unique():
        value_at_date = 0
        for ticker in tickers:
            value_at_date += (
                joined_df.loc[joined_df["date"] == dt, ticker + "_price"].to_list()[0]
                * joined_df.loc[joined_df["date"] == dt, ticker + "_weight"].to_list()[
                    0
                ]
            )
        portfolio_value.append(value_at_date)

    return np.array(portfolio_value)


# %%
backtest(test_prices, test_portfolio)

