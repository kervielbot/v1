import yfinance as yf
from google.genai import Client
from tqdm import tqdm
import json
import pandas as pd
import hashlib
from pathlib import Path

MODEL_ID = 'gemini-3.1-flash-lite-preview'

PROJECT_ID = 'rogue-trader-friday'

LOCATION = 'global'

# Debug flag for agent reasoning output
DEBUG_AGENT_REASONING = False

client = Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# Define a base agent class that uses the OpenAI API if an API key is set; otherwise, it returns a simulated response.
class BaseAgent:
    def __init__(self, name, role, client):
        self.name = name
        self.role = role  # This describes the agent's responsibility
        self.client = client

    def act(self, prompt):
        response = client.models.generate_content(
            model=MODEL_ID, contents=prompt, 
        )
        return response.text

# Data Agent: Fetches financial data using yfinance.
class DataAgent(BaseAgent):
    def __init__(self, name, role, client):
        super().__init__(name, role, client)
        self.cache_dir = Path(".data_cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_filename(self, ticker_list, period, interval):
        """Generate a deterministic cache filename from parameters."""
        # Create a hash of the parameters
        params_str = f"{'_'.join(sorted(ticker_list))}_{period}_{interval}"
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        return self.cache_dir / f"data_{params_hash}.pkl"
    
    def fetch_data(self, ticker_list, period='1mo', interval='1d'):
        cache_file = self._get_cache_filename(ticker_list, period, interval)
        
        # Check if cache exists
        if cache_file.exists():
            print(f"{self.name} is loading cached data for {len(ticker_list)} stocks from {cache_file.name}")
            df = pd.read_pickle(cache_file)
            return df
        
        print(f"{self.name} is fetching data for {len(ticker_list)} stocks (Period: {period}, Interval: {interval}).")

        stocks = []
        for ticker in tqdm(sorted(ticker_list)):
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            df.columns = [ticker + ':' + c for c in df.columns]
            stocks.append(df)

        df = pd.concat(stocks, axis=1)
        
        # Save to cache
        df.to_pickle(cache_file)
        print(f"{self.name} cached data to {cache_file.name}")
        
        return df
    
# Analysis Agent: Analyzes the data by computing summary statistics and generating insights.
class AnalysisAgent(BaseAgent):
    def analyze(self, data_df):
        # Compute summary statistics from the DataFrame.
        summary = data_df.describe().to_string()
        prompt = f"Analyze the following financial data summary and provide neutral insights:\n{summary}."
        return self.act(prompt)
    

# Decision Agent: Provides a trading recommendation based on the analysis.
class DecisionAgent(BaseAgent):
    def recommend(self, analysis):
        prompt = f"Based on the following analysis, provide a simple trading recommendation (Buy, Hold, or Sell) with reasoning:\n{analysis}"
        return self.act(prompt)
    
class TraderAgent(BaseAgent):
    def __init__(self, name, role, client):
        super().__init__(name, role, client)
        self.allocation_history = {}
    
    def allocation(self, portfolio, latest_date, analysis, list_of_stocks):
        """Generate allocation weights and update portfolio dataframe.
        
        Validates that weights sum to within ±5% of 1.0. If not, retries up to 3 times
        with feedback about the previous sum.
        
        Args:
            portfolio: DataFrame with datetime index and columns for each asset
            latest_date: Datetime for the new allocation row
            analysis: Analysis text to base allocation on
            list_of_stocks: List of stock tickers to consider
            
        Returns:
            Updated portfolio DataFrame with new allocation row appended
        """
        base_prompt = f"""You are given the following portfolio analysis: {analysis}.
        Based on this analysis, suggest the ideal weights for the portfolio comprised of the following assets:
        free cash and the following stocks {list_of_stocks}.
        
        IMPORTANT: Concentrate the portfolio in high-conviction positions. Allocate meaningful weights (>2%) to your top 5-10 conviction ideas, not equal weights across all 73 stocks. Use 0% for stocks you don't have strong conviction on.
        
        First, provide your reasoning for the allocation in 2-3 sentences. Then return a valid JSON object in this exact format:
        {{"Cash": 0.2, "AAPL": 0.3, "GOOGL": 0.5}}
        
        Use ticker names for stocks and 'Cash' for free cash. Weights must be floats between 0 and 1 and sum to 1.0."""
        
        max_retries = 3
        best_weights = None
        last_total = None
        
        for attempt in range(max_retries + 1):  # 0, 1, 2, 3 = 4 total attempts
            # Build prompt with feedback if retry
            if attempt == 0:
                prompt = base_prompt
            else:
                prompt = f"{base_prompt}\n\nYour previous allocation summed to {last_total:.4f} instead of 1.0. Please return weights that sum to exactly 1.0."
            
            try:
                response = client.models.generate_content(model=MODEL_ID, contents=prompt)
                
                if DEBUG_AGENT_REASONING:
                    print(f"\n[DEBUG] Trader Agent Raw Response:\n{response.text}\n")
                
                # Parse JSON
                start_idx = response.text.find('{')
                end_idx = response.text.rfind('}') + 1
                weights_dict = json.loads(response.text[start_idx:end_idx])
                weights = {col: round(weights_dict.get(col, 0.0), 2) for col in portfolio.columns}
                
                # Calculate total
                total = sum(weights.values())
                last_total = total
                
                # Track best attempt (closest to 1.0)
                if best_weights is None or abs(total - 1.0) < abs(sum(best_weights.values()) - 1.0):
                    best_weights = weights
                
                # Check if within bounds (0.95 to 1.05)
                if 0.95 <= total <= 1.05:
                    # Within bounds, normalize and round to 2 decimals
                    new_row = {k: round(v / total, 2) for k, v in weights.items()}
                    new_df_row = pd.DataFrame([new_row], index=[latest_date])
                    return pd.concat([portfolio, new_df_row])
                # Otherwise continue loop to retry
                
            except:
                # Parse error, continue to next attempt
                continue
        
        # All retries exhausted, use best attempt or fallback
        if best_weights is None:
            # No valid parse, use previous allocation
            new_row = portfolio.iloc[-1].to_dict()
        else:
            # Use best attempt even though it's out of bounds
            new_row = best_weights
        
        # If weights sum to zero, fall back to previous allocation
        total = sum(new_row.values())
        if total <= 0:
            new_row = portfolio.iloc[-1].to_dict()
            total = sum(new_row.values())
        
        # Normalize weights to 1.0 and round to 2 decimals
        if total > 0:
            new_row = {k: round(v / total, 2) for k, v in new_row.items()}
        
        # Append new row with latest_date index
        new_df_row = pd.DataFrame([new_row], index=[latest_date])
        return pd.concat([portfolio, new_df_row])


