
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go


def calculate_tiered_interest_capital(capital):
    """
    Calculate capital growth with tiered monthly interest rates.
    
    Tiered annual interest rates:
    - Up to $10,000: 1.25% annually
    - $10,000 to $1,000,000: 1.00% annually
    - Above $1,000,000: 0.00%
    
    Args:
        capital: pd.Series with date index and capital values
        
    Returns:
        pd.Series with updated capital values based on tiered interest rates
    """
    # Create a copy to avoid modifying the original
    interest_capital = capital.copy()
    
    # Get the starting capital (first value)
    starting_value = interest_capital.iloc[0]
    current_value = starting_value
    
    # Get the first date
    start_date = interest_capital.index[0]
    
    # Iterate through each subsequent date
    for i in range(1, len(interest_capital)):
        current_date = interest_capital.index[i]
        
        # Calculate months elapsed from start
        months_elapsed = (current_date.year - start_date.year) * 12 + (current_date.month - start_date.month)
        
        # Calculate interest for the current capital value
        # Apply tiered monthly interest for the number of months elapsed
        value = starting_value
        for month in range(months_elapsed):
            # Calculate interest based on current value tiers
            monthly_interest = 0.0
            
            if value <= 10000:
                # First tier: 1.25% annual = 1.25/12 % monthly
                monthly_interest = value * (0.0125 / 12)
            elif value <= 1000000:
                # First $10,000 at 1.25%, remainder at 1.00%
                monthly_interest = 10000 * (0.0125 / 12) + (value - 10000) * (0.01 / 12)
            else:
                # First $10,000 at 1.25%, next $990,000 at 1.00%, rest at 0%
                monthly_interest = 10000 * (0.0125 / 12) + 990000 * (0.01 / 12)
            
            value += monthly_interest
        
        interest_capital.iloc[i] = value
    
    return interest_capital


def generate_benchmark_plot(capital, test_start, starting_capital): 
    # Calculate total return for portfolio
    final_capital = capital.iloc[-1]
    total_return = (final_capital - starting_capital) / starting_capital
    
    # Fetch S&P 500 benchmark data
    print("\nFetching S&P 500 benchmark data...")
    benchmark = yf.Ticker("^GSPC")
    benchmark_data = benchmark.history(start=test_start, end=capital.index[-1])
    
    # Calculate benchmark capital values starting from test_start
    benchmark_returns = benchmark_data['Close'].pct_change()
    benchmark_capital_series = starting_capital * (1 + benchmark_returns).cumprod()
    
    # Prepend starting capital at test_start for benchmark
    benchmark_capital_series = pd.concat([
        pd.Series([starting_capital], index=[test_start]),
        benchmark_capital_series[benchmark_capital_series.index > test_start]
    ])
    
    # Get portfolio capital values starting from test_start only
    portfolio_capital_aligned = capital[capital.index >= test_start].copy()
    
    # Ensure first portfolio value is exactly the starting capital
    if len(portfolio_capital_aligned) > 0:
        first_idx = portfolio_capital_aligned.index[0]
        portfolio_capital_aligned.iloc[0] = starting_capital
    
    # Calculate ING Savings series with tiered interest
    ing_savings = calculate_tiered_interest_capital(portfolio_capital_aligned)
    
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
    
    # ING Savings line
    fig.add_trace(go.Scatter(
        x=ing_savings.index,
        y=ing_savings.values,
        mode='lines',
        name='ING Savings Acc.',
        line=dict(color='#ff7f0e', width=2, dash='dot'),
        hovertemplate='<b>ING Savings Acc.</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:,.2f}<extra></extra>'
    ))
    
    # Calculate final benchmark return
    benchmark_final = benchmark_aligned.iloc[-1]
    benchmark_return = (benchmark_final - starting_capital) / starting_capital
    
    # Calculate final ING Savings return
    ing_final = ing_savings.iloc[-1]
    ing_return = (ing_final - starting_capital) / starting_capital
    
    # Update layout with proper date formatting
    fig.update_layout(
        title=f'Portfolio Performance vs Benchmarks<br><sub>Portfolio: {total_return*100:.2f}% | S&P 500: {benchmark_return*100:.2f}% | ING Savings: {ing_return*100:.2f}%</sub>',
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
    print(f"ING Savings Return: {ing_return*100:.2f}%")
    print(f"Outperformance vs S&P 500: {(total_return - benchmark_return)*100:.2f}%")
    print(f"Outperformance vs ING Savings: {(total_return - ing_return)*100:.2f}%")
