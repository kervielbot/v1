import pandas as pd
from kervielbot.agents import DataAgent, AnalysisAgent, TraderAgent, client
from kervielbot.stocks import STOCK_NAMES


HISTORICAL_DATA_START = "2025-08-31"
TEST_DATE_START = "2025-09-01"
TEST_DATE_END = "2025-09-05"
#TEST_DATE_END = "2025-12-31"


def get_actual_dates(data_df, hist_start, test_start, test_end):
    """Get actual dates from dataframe index, using next available date if exact match not found.
    
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


def main():
    # Create instances of the agents with specific roles.
    data_agent = DataAgent("DataAgent", "You fetch and provide historical stock data.", client)
    analysis_agent = AnalysisAgent("AnalysisAgent", "You analyze financial data and provide neutral insights.", client)
    trader_agent = TraderAgent("TraderAgent", "You provide portfolio weight recommendations.", client)

    # Step 1: Data Agent fetches historical data for a chosen stock.
    ticker = "AAPL"
    list_of_stocks = STOCK_NAMES
    data_df = data_agent.fetch_data(list_of_stocks, period='24mo', interval='1d')
    
    # Get actual dates from the dataframe
    hist_start, test_start, test_end = get_actual_dates(
        data_df, HISTORICAL_DATA_START, TEST_DATE_START, TEST_DATE_END
    )
    
    # Initialize portfolio with 100% cash at the start of test period
    init_weights = {t: 0.0 for t in list_of_stocks}
    init_weights['Cash'] = 1.0
    portfolio_weights = pd.DataFrame(init_weights, index=[hist_start])
    
    # Get all test dates from test_start to test_end
    test_dates = data_df[test_start:test_end].index
    
    # Get starting index position for the rolling window
    start_idx = data_df.index.get_loc(hist_start)
    
    # Loop over each forecast day
    for i, forecast_date in enumerate(test_dates):
        print(f"\n--- Processing forecast date: {forecast_date.date()} ---")
        
        # Rolling window: fixed-size window ending just before forecast_date
        end_idx = data_df.index.get_loc(forecast_date)
        historical_data = data_df.iloc[start_idx + i : end_idx]
        
        # Analysis agent analyzes historical data
        analysis = analysis_agent.analyze(historical_data)
        
        # Trader agent allocates for forecast day
        portfolio_weights = trader_agent.allocation(portfolio_weights, forecast_date, analysis, list_of_stocks)
        
        print(f"Portfolio allocation for {forecast_date.date()}: {portfolio_weights.iloc[-1].to_dict()}")
    
    print(f"\n--- Final Portfolio ---")
    print(portfolio_weights)
    
    portfolio_weights.to_csv("portfolio_allocation.csv")

if __name__ == "__main__":
    main()