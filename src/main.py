import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from kervielbot.agents import DataAgent, AnalysisAgent, TraderAgent, client
from kervielbot.stocks import STOCK_NAMES
from kervielbot.prompts import ANALYST_PROMPT, TRADER_PROMPT
from kervielbot.preprocessing import get_trading_dates

HISTORICAL_DATA_START = "2025-08-31"
TEST_DATE_START = "2025-09-01"
TEST_DATE_END = "2025-09-30"
STARTING_CAPITAL = 1_000_000.0


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
        
        # Analysis agent analyzes historical data
        analysis = analysis_agent.analyze(historical_data)
        
        # Trader agent allocates for forecast day
        portfolio_weights = trader_agent.allocation(portfolio_weights, forecast_date, analysis, list_of_stocks)
        
        # Update end-of-day capital based on new portfolio weights
        capital = update_capital(portfolio_weights, data_df, capital, forecast_date)
        
        print(f"Portfolio allocation for {forecast_date.date()}: {portfolio_weights.iloc[-1].to_dict()}")
        print(f"Portfolio net value for {forecast_date.date()}: {capital.iloc[-1]}")
    
    print(f"\n--- Final Portfolio ---")
    print(portfolio_weights)
    
    # Calculate performance metrics
    final_capital = capital.iloc[-1]
    total_return = (final_capital - STARTING_CAPITAL) / STARTING_CAPITAL
    print(f"\n--- Performance Summary ---")
    print(f"Initial Capital: ${STARTING_CAPITAL:,.2f}")
    print(f"Final Capital: ${final_capital:,.2f}")
    print(f"Total Return: {total_return:.4f} ({total_return*100:.2f}%)")
    
    # Fetch S&P 500 benchmark data
    print("\nFetching S&P 500 benchmark data...")
    benchmark = yf.Ticker("^GSPC")
    benchmark_data = benchmark.history(start=test_start, end=capital.index[-1])
    
    # Calculate benchmark capital values starting from test_start
    benchmark_returns = benchmark_data['Close'].pct_change()
    benchmark_capital_series = STARTING_CAPITAL * (1 + benchmark_returns).cumprod()
    
    # Prepend starting capital at test_start for benchmark
    benchmark_capital_series = pd.concat([
        pd.Series([STARTING_CAPITAL], index=[test_start]),
        benchmark_capital_series[benchmark_capital_series.index > test_start]
    ])
    
    # Get portfolio capital values starting from test_start only
    portfolio_capital_aligned = capital[capital.index >= test_start].copy()
    
    # Ensure first portfolio value is exactly the starting capital
    if len(portfolio_capital_aligned) > 0:
        first_idx = portfolio_capital_aligned.index[0]
        portfolio_capital_aligned.iloc[0] = STARTING_CAPITAL
    
    # Get benchmark values for the same dates as portfolio
    benchmark_aligned = benchmark_capital_series[benchmark_capital_series.index.isin(portfolio_capital_aligned.index)]
    
    # If there are gaps, forward fill only within the dates we have
    benchmark_aligned = benchmark_aligned.reindex(portfolio_capital_aligned.index, method='ffill')
    
    # Create visualization
    fig = go.Figure()
    
    # Portfolio line
    fig.add_trace(go.Scatter(
        x=portfolio_capital_aligned.index,
        y=portfolio_capital_aligned.values,
        mode='lines',
        name='Portfolio',
        line=dict(color='#1f77b4', width=2),
        hovertemplate='<b>Portfolio</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:,.2f}<extra></extra>'
    ))
    
    # Benchmark line
    fig.add_trace(go.Scatter(
        x=benchmark_aligned.index,
        y=benchmark_aligned.values,
        mode='lines',
        name='S&P 500',
        line=dict(color='#7f7f7f', width=2, dash='dash'),
        hovertemplate='<b>S&P 500</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:,.2f}<extra></extra>'
    ))
    
    # Calculate final benchmark return
    benchmark_final = benchmark_aligned.iloc[-1]
    benchmark_return = (benchmark_final - STARTING_CAPITAL) / STARTING_CAPITAL
    
    # Update layout with proper date formatting
    fig.update_layout(
        title=f'Portfolio Performance vs S&P 500<br><sub>Portfolio: {total_return*100:.2f}% | S&P 500: {benchmark_return*100:.2f}%</sub>',
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        hovermode='x unified',
        template='plotly_white',
        height=600,
        yaxis=dict(tickformat='$,.0f'),
        font=dict(size=11),
        xaxis=dict(
            tickformat='%Y-%m-%d',
            tickangle=-45,
            dtick='1D'  # Show every day
        )
    )
    
    # Add grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    # Save visualization
    output_file = "portfolio_performance.html"
    fig.write_html(output_file)
    print(f"\nVisualization saved to {output_file}")
    
    # Print benchmark comparison
    print(f"\n--- Benchmark Comparison ---")
    print(f"Portfolio Return: {total_return*100:.2f}%")
    print(f"S&P 500 Return: {benchmark_return*100:.2f}%")
    print(f"Outperformance: {(total_return - benchmark_return)*100:.2f}%")
    
    portfolio_weights.to_csv("portfolio_allocation.csv")

if __name__ == "__main__":
    main()