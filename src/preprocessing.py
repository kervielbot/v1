import pandas as pd

def get_trading_dates(data_df, hist_start, test_start, test_end):
    """Get closest trading dates from dataframe index, using next available date if exact match not found.
    
    Args:
        data_df: DataFrame with datetime index
        hist_start: Historical data start date string
        test_start: Test period start date string  
        test_end: Test period end date string
        
    Returns:
        tuple: (actual_hist_start, actual_test_start, actual_test_end) as Timestamps
    """
    def get_next_available(date_str):
        target = pd.to_datetime(date_str).tz_localize(data_df.index.tz)
        if target in data_df.index:
            return target
        # Find next available date after target
        future_dates = data_df.index[data_df.index >= target]
        if len(future_dates) == 0:
            raise ValueError(f"No dates found on or after {date_str}")
        return future_dates[0]
    
    def get_prev_available(date_str):
        target = pd.to_datetime(date_str).tz_localize(data_df.index.tz)
        if target in data_df.index:
            return target
        # Find previous available date before target
        past_dates = data_df.index[data_df.index <= target]
        if len(past_dates) == 0:
            raise ValueError(f"No dates found on or before {date_str}")
        return past_dates[-1]
    
    return (
        get_next_available(hist_start),
        get_next_available(test_start),
        get_prev_available(test_end)
    )


def update_capital(portfolio_weights, data_df, capital, forecast_date):
    """
    Update capital series with new end-of-day capital based on portfolio weights and stock returns.
    
    Args:
        portfolio_weights: DataFrame with datetime index and columns for each asset (stocks + Cash)
        data_df: DataFrame with datetime index and columns like "TICKER:Close"
        capital: pd.Series with date as index, containing capital values
        forecast_date: The date for which to calculate new capital
        
    Returns:
        Updated capital series with new row appended
    """
    # Get the current capital (last value in the series)
    current_capital = capital.iloc[-1]
    
    # Get the forecast date index position - handle potential duplicates
    forecast_idx = data_df.index.get_loc(forecast_date)
    if isinstance(forecast_idx, slice):
        forecast_idx = forecast_idx.start
    elif hasattr(forecast_idx, '__iter__'):
        # It's a boolean array or similar - find first True
        forecast_idx = int(forecast_idx.argmax())
    prev_idx = forecast_idx - 1
    
    # Get the weights for the forecast date (or use the latest weights)
    # Use the most recent weights available
    weights = portfolio_weights.iloc[-1]
    
    # Calculate returns for each asset
    total_return = 0.0
    
    for asset in weights.index:
        weight = weights[asset]
        
        if asset == 'Cash':
            # Cash has a return of 1.0 (no change)
            asset_return = 1.0
        else:
            # Get close prices for the stock
            close_col = f"{asset}:Close"
            if close_col not in data_df.columns:
                # Skip assets not in data_df (could be duplicates removed)
                continue
            
            # Get previous day's close and current day's close using positional indexing
            prev_close = data_df.iloc[prev_idx][close_col]
            curr_close = data_df.iloc[forecast_idx][close_col]
            
            # Handle case where column returns a Series (duplicates)
            if isinstance(prev_close, pd.Series):
                prev_close = prev_close.iloc[0]
            if isinstance(curr_close, pd.Series):
                curr_close = curr_close.iloc[0]
            
            # Calculate return
            asset_return = curr_close / prev_close
        
        # Add to total weighted return
        total_return += weight * asset_return
    
    # Calculate new capital
    new_capital = current_capital * total_return
    
    # Append new row to capital series
    new_row = pd.Series([new_capital], index=[forecast_date])
    capital = pd.concat([capital, new_row], verify_integrity=False)
    
    return capital