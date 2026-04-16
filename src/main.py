import pandas as pd
from kervielbot.agents import DataAgent, AnalysisAgent, TraderAgent, client



TEST_DATE_START = "2025-01-01"
TEST_DATE_END = "2025-12-31"



def main():
    ticker = "AAPL"  # Example ticker for Apple Inc.
    # Create instances of the agents with specific roles.
    data_agent = DataAgent("DataAgent", "You fetch and provide historical stock data.", client)
    analysis_agent = AnalysisAgent("AnalysisAgent", "You analyze financial data and provide neutral insights.", client)
    trader_agent = TraderAgent("TraderAgent", "You provide portfolio weight recommendations.", client)

    # Step 1: Data Agent fetches historical data for a chosen stock.
    data_df = data_agent.fetch_data(ticker, period='12mo', interval='1d')

    # Portfolio weights at starting point (100% cash, 0% stocks)
    portfolio = pd.DataFrame({'Cash': 1, 'AAPL': 0}, index = [data_df.index[-1]])

    # Step 2: Analysis Agent analyzes the fetched data.
    analysis = analysis_agent.analyze(data_df)

    # Step 3: Trader Agent provides allocation recommendation based on the analysis and updates the portfolio.
    latest_date = data_df.index[-1] + pd.Timedelta(days=1)
    list_of_stocks = ['AAPL']

    portfolio_new = trader_agent.allocation(portfolio, latest_date, analysis, list_of_stocks)

    print(f"Updated Portfolio Allocation: {portfolio_new}")

    portfolio_new.to_csv("portfolio_allocation.csv")  # Save the new portfolio allocation to a CSV file

if __name__ == "__main__":
    main()