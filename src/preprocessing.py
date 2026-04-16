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