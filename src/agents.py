import yfinance as yf
from google.genai import Client

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
        prompt = f"Analyze the following financial data summary and provide neutral insights:\n{summary}"
        return self.act(prompt)
    

# Decision Agent: Provides a trading recommendation based on the analysis.
class DecisionAgent(BaseAgent):
    def recommend(self, analysis):
        prompt = f"Based on the following analysis, provide a simple trading recommendation (Buy, Hold, or Sell) with reasoning:\n{analysis}"
        return self.act(prompt)