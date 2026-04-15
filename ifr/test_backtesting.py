import backtesting
import pandas as pd
import numpy as np

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

def test_backtest():
    np.testing.assert_array_equal(
        backtesting.backtest(test_prices, test_portfolio),
        np.array([1.0, 1.25, 3.0]),
    )