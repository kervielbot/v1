import pandas as pd
import numpy as np


def calculate_returns(data_df):
    """
    Calculate daily percentage returns from price data.
    
    Called once on full data_df before the main loop. No leakage since 
    returns at time t only use prices at t and t-1.
    
    Args:
        data_df: DataFrame with columns named as "TICKER:Close", "TICKER:Open", etc.
                 (concatenated yfinance data per ticker)
    
    Returns:
        DataFrame of daily percentage returns for each ticker (columns = ticker symbols)
    """
    # Extract close price columns
    close_cols = [col for col in data_df.columns if col.endswith(':Close')]
    
    # Create DataFrame with just close prices, renamed to ticker symbols
    close_prices = data_df[close_cols].copy()
    close_prices.columns = [col.replace(':Close', '') for col in close_cols]
    
    # Calculate daily returns: (P_t - P_{t-1}) / P_{t-1}
    daily_returns = close_prices.pct_change()
    
    return daily_returns


def calculate_return_correlations(historical_returns):
    """
    Calculate correlation matrix of returns over the entire historical period.
    
    Called each pass with historical_returns ending before forecast_date.
    Computes a single correlation matrix using all available historical data.
    
    Args:
        historical_returns: DataFrame of daily returns (columns = ticker symbols),
                            pre-computed and sliced to the historical window
    
    Returns:
        DataFrame: correlation matrix (ticker x ticker) computed over entire period
    """
    # Drop NaN rows (first row will be NaN from pct_change)
    returns_clean = historical_returns.dropna()
    
    # Correlation matrix over full historical period
    correlation_matrix = returns_clean.corr()
    
    return correlation_matrix


def calculate_rolling_volatility(historical_returns, windows=None):
    """
    Calculate annualized volatility as of the last day in historical_returns.
    
    Called each pass with historical_returns ending before forecast_date.
    Returns the most recent volatility values using available data.
    
    Windows are automatically capped to available data length to ensure
    robustness across varying historical window sizes.
    
    Args:
        historical_returns: DataFrame of daily returns (columns = ticker symbols),
                            pre-computed and sliced to the historical window
        windows: List of rolling window sizes in days. Defaults to [20, 60].
    
    Returns:
        dict with pd.Series of annualized volatility for each ticker:
            - 'volatility_20d': Series of 20-day volatility per ticker
            - 'volatility_60d': Series of 60-day volatility per ticker
    """
    if windows is None:
        windows = [20, 60]
    
    # Drop NaN rows (first row will be NaN from pct_change)
    returns_clean = historical_returns.dropna()
    available_length = len(returns_clean)
    
    # Annualization factor (assuming ~252 trading days per year)
    annualization_factor = np.sqrt(252)
    
    volatility_data = {}
    
    for window in windows:
        # Cap window to available data length
        effective_window = min(window, available_length)
        
        if effective_window < 2:
            # Not enough data to compute volatility
            volatility_data[f'volatility_{window}d'] = pd.Series(
                index=returns_clean.columns, 
                data=np.nan
            )
        else:
            # Compute std of the last N days, annualized
            recent_returns = returns_clean.tail(effective_window)
            vol = recent_returns.std() * annualization_factor
            volatility_data[f'volatility_{window}d'] = vol
    
    return volatility_data
