import yfinance as yf
from google.genai import Client
import json
import pandas as pd

MODEL_ID = 'gemini-3-flash-preview'
MODEL_ID = 'gemini-3.1-flash-lite-preview'
MODEL_ID = 'gemini-2.5-flash-lite'

PROJECT_ID = 'rogue-trader-wednesday'

LOCATION = 'global'

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
    def fetch_data(self, ticker, period='1mo', interval='1d'):
        print(f"{self.name} is fetching data for {ticker} (Period: {period}, Interval: {interval}).")
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
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
        
        Args:
            portfolio: DataFrame with datetime index and columns for each asset
            latest_date: Datetime for the new allocation row
            analysis: Analysis text to base allocation on
            list_of_stocks: List of stock tickers to consider
            
        Returns:
            Updated portfolio DataFrame with new allocation row appended
        """
        prompt = f"""You are given the following portfolio analysis: {analysis}. 
        Based on this analysis, suggest the ideal weights for the portfolio comprised of the following assets: 
        free cash and the following stocks {list_of_stocks}. 
        Ensure that the total weights sum to 1.0 (representing 100%).
        
        Return ONLY a valid JSON object in the following format (no other text):
        {{"Cash": 0.2, "AAPL": 0.3, "GOOGL": 0.5}}
        
        Use ticker names for stocks and 'Cash' for free cash. Weights should be floats between 0 and 1."""
        
        response = self.act(prompt)
        print(f"New allocation: {response}")
        
        # Store response with latest_date
        self.allocation_history[latest_date] = response
        
        # Try to parse JSON and validate weights
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx == -1 or end_idx <= start_idx:
                raise ValueError("No JSON object found in response")
            
            weights_dict = json.loads(response[start_idx:end_idx])
            new_row = {col: weights_dict.get(col, 0.0) for col in portfolio.columns}
            
            # Validate weights sum to 1.0
            total_weight = sum(new_row.values())
            if not (0.99 <= total_weight <= 1.01):
                print(f"Weights sum to {total_weight}, not 1.0. Using previous weights.")
                new_row = portfolio.iloc[-1].to_dict()
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response: {response}")
            new_row = portfolio.iloc[-1].to_dict()
        
        # Append new row with latest_date index
        new_df_row = pd.DataFrame([new_row], index=[latest_date])
        return pd.concat([portfolio, new_df_row])


