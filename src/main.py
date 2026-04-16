import pandas as pd
from kervielbot.agents import DataAgent, AnalysisAgent, TraderAgent, client, calculate_period_return
from kervielbot.stocks import STOCK_NAMES
from kervielbot.prompts import ANALYST_PROMPT, TRADER_PROMPT
from kervielbot.preprocessing import get_trading_dates

HISTORICAL_DATA_START = "2025-08-31"
TEST_DATE_START = "2025-09-01"
TEST_DATE_END = "2025-09-05"
INITIAL_PORTFOLIO_VALUE = 100000.0  # Starting with $100,000




def main():
    # Create instances of the agents with specific roles.
    data_agent = DataAgent("DataAgent", "You fetch and provide historical stock data.", client)
    analysis_agent = AnalysisAgent("AnalysisAgent", ANALYST_PROMPT, client)
    trader_agent = TraderAgent("TraderAgent", TRADER_PROMPT, client)

    # Step 1: Data Agent fetches historical data for a chosen stock.
    # ticker = "AAPL"
    list_of_stocks = STOCK_NAMES
    data_df = data_agent.fetch_data(list_of_stocks, period='24mo', interval='1d')
    
    # Get actual dates from the dataframe
    hist_start, test_start, test_end = get_trading_dates(
        data_df, HISTORICAL_DATA_START, TEST_DATE_START, TEST_DATE_END
    )
    
    # Initialize portfolio with 100% cash at the start of test period
    init_weights = {t: 0.0 for t in list_of_stocks}
    init_weights['Cash'] = 1.0
    init_weights['Portfolio_Value'] = INITIAL_PORTFOLIO_VALUE
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
        
        # Calculate portfolio return and update value
        prev_date = portfolio_weights.index[-1]
        prev_weights = portfolio_weights.iloc[-1].drop('Portfolio_Value')  # Exclude Portfolio_Value from weights
        prev_value = portfolio_weights.iloc[-1]['Portfolio_Value']
        
        # Calculate period return from previous date to current forecast date
        period_return = calculate_period_return(data_df, prev_weights, prev_date, forecast_date)
        current_value = prev_value * (1 + period_return)
        
        print(f"Period return: {period_return:.4f} ({period_return*100:.2f}%)")
        print(f"Portfolio value: ${prev_value:,.2f} -> ${current_value:,.2f}")
        
        # Analysis agent analyzes historical data
        analysis = analysis_agent.analyze(historical_data)
        
        # Trader agent allocates for forecast day
        portfolio_weights = trader_agent.allocation(portfolio_weights, forecast_date, analysis, list_of_stocks)
        
        # Add Portfolio_Value to the new row
        portfolio_weights.loc[forecast_date, 'Portfolio_Value'] = current_value
        
        print(f"Portfolio allocation for {forecast_date.date()}: {portfolio_weights.iloc[-1].to_dict()}")
    
    print(f"\n--- Final Portfolio ---")
    print(portfolio_weights)
    
    # Calculate and display cumulative return
    final_value = portfolio_weights.iloc[-1]['Portfolio_Value']
    cumulative_return = (final_value - INITIAL_PORTFOLIO_VALUE) / INITIAL_PORTFOLIO_VALUE
    print(f"\n--- Performance Summary ---")
    print(f"Initial Value: ${INITIAL_PORTFOLIO_VALUE:,.2f}")
    print(f"Final Value: ${final_value:,.2f}")
    print(f"Cumulative Return: {cumulative_return:.4f} ({cumulative_return*100:.2f}%)")
    
    portfolio_weights.to_csv("portfolio_allocation.csv")

if __name__ == "__main__":
    main()