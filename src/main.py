import pandas as pd
import sys
from kervielbot import agents
from kervielbot.agents import DataAgent, AnalysisAgent, TraderAgent, client
from kervielbot.stocks import STOCK_NAMES
from kervielbot.prompts import ANALYST_PROMPT, TRADER_PROMPT
from kervielbot.preprocessing import get_trading_dates, update_capital
from kervielbot.visuals import generate_benchmark_plot
from kervielbot.stats import calculate_returns, calculate_return_correlations, calculate_rolling_volatility, calculate_return_covariance

HISTORICAL_DATA_START = "2025-01-01"
TEST_DATE_START = "2025-09-01"
TEST_DATE_END = "2025-10-01"
STARTING_CAPITAL = 1_000_000.0

# Enable agent reasoning debug output if passed as command line arg
if len(sys.argv) > 1 and sys.argv[1].lower() == 'debug':
    agents.DEBUG_AGENT_REASONING = True



def main():
    # Create instances of the agents with specific roles.
    data_agent = DataAgent("DataAgent", "You fetch and provide historical stock data.", client)
    analysis_agent = AnalysisAgent("AnalysisAgent", ANALYST_PROMPT, client)
    trader_agent = TraderAgent("TraderAgent", TRADER_PROMPT, client)

    # Step 1: Data Agent fetches historical data for a chosen stock.
    # ticker = "AAPL"
    list_of_stocks = STOCK_NAMES
    data_df = data_agent.fetch_data(list_of_stocks, period='24mo', interval='1d')
    
    # Compute daily returns for all data (no leakage - only uses t and t-1 prices)
    daily_returns = calculate_returns(data_df)
    
    # Get actual dates from the dataframe
    hist_start, test_start, test_end = get_trading_dates(
        data_df, HISTORICAL_DATA_START, TEST_DATE_START, TEST_DATE_END
    )
    
    # Initialize portfolio with 100% cash at the start of test period
    init_weights = {t: 0.0 for t in list_of_stocks}
    init_weights['Cash'] = 1.0
    portfolio_weights = pd.DataFrame(init_weights, index=[hist_start])
    
    # Get all test dates from test_start to test_end
    test_dates = data_df[test_start:test_end].index
    
    # Initialize capital on the trading day before test_start
    # Find the previous trading day before test_start
    test_start_idx = data_df.index.get_loc(test_start)
    if test_start_idx > 0:
        prev_trading_day = data_df.index[test_start_idx - 1]
    else:
        prev_trading_day = test_start
    capital = pd.Series([STARTING_CAPITAL], index=[prev_trading_day])
    
    # Get starting index position for the rolling window
    start_idx = data_df.index.get_loc(hist_start)
    
    # Loop over each forecast day
    for i, forecast_date in enumerate(test_dates):
        print(f"\n--- Processing forecast date: {forecast_date.date()} ---")
        
        # Rolling window: fixed-size window ending just before forecast_date
        end_idx = data_df.index.get_loc(forecast_date)
        historical_data = data_df.iloc[start_idx + i : end_idx]
        
        # Truncate daily returns to same historical window
        historical_returns = daily_returns.iloc[start_idx + i : end_idx]
        
        # Compute volatilities and correlation matrix from historical returns
        volatility_dict = calculate_rolling_volatility(historical_returns)
        correlation_matrix = calculate_return_correlations(historical_returns)
        covariance_matrix = calculate_return_covariance(historical_returns)
        
        # Analysis agent analyzes historical data with volatility and correlation insights
        analysis = analysis_agent.analyze(historical_data, volatility_dict, correlation_matrix, covariance_matrix)
        
        # Trader agent allocates for forecast day
        portfolio_weights = trader_agent.allocation(portfolio_weights, forecast_date, analysis, list_of_stocks)

        # Update end-of-day capital based on new portfolio weights
        capital = update_capital(portfolio_weights, data_df, capital, forecast_date)
        
        # Print only non-zero allocations for this date
        current_alloc = portfolio_weights.iloc[-1]
        non_zero_alloc = current_alloc[current_alloc > 0.001]
        print(f"Portfolio allocation for {forecast_date.date()}: {non_zero_alloc.to_dict()}")
        print(f"Portfolio net value for {forecast_date.date()}: ${capital.iloc[-1]:,.2f}")
    
    print(f"\n--- Final Portfolio ---")
    # Only show columns with at least one non-zero value
    portfolio_with_holdings = portfolio_weights.loc[:, (portfolio_weights != 0).any()]
    print(portfolio_with_holdings)
    
    # Calculate performance metrics
    final_capital = capital.iloc[-1]
    total_return = (final_capital - STARTING_CAPITAL) / STARTING_CAPITAL
    print(f"\n--- Performance Summary ---")
    print(f"Initial Capital: ${STARTING_CAPITAL:,.2f}")
    print(f"Final Capital: ${final_capital:,.2f}")
    print(f"Total Return: {total_return:.4f} ({total_return*100:.2f}%)")
    
    generate_benchmark_plot(capital, test_start, STARTING_CAPITAL)
    
    portfolio_weights.to_csv("portfolio_allocation.csv")

if __name__ == "__main__":
    main()