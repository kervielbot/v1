import yfinance as yf
from google.genai import Client, types
from tqdm import tqdm
import json
import pandas as pd

MODEL_ID = 'gemini-3.1-flash-lite-preview'

PROJECT_ID = 'rogue-trader-thursday'

LOCATION = 'global'

client = Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# Calculator tool for portfolio weight validation
def sum_weights(weights: dict) -> float:
    """Calculate the sum of portfolio weights to verify they total 1.0.
    
    Args:
        weights: Dictionary mapping asset names to their weight values
        
    Returns:
        The sum of all weight values
    """
    return sum(weights.values())

def calculate_period_return(data_df, weights_series, start_date, end_date):
    """Calculate portfolio return for a period.
    
    Args:
        data_df: Full price dataframe with {ticker}:Close columns
        weights_series: Series with asset allocations (including 'Cash')
        start_date: Period start date (pandas Timestamp)
        end_date: Period end date (pandas Timestamp)
        
    Returns:
        Float: Portfolio return for the period (e.g., 0.05 for 5% gain)
    """
    portfolio_return = 0.0
    
    for asset, weight in weights_series.items():
        if weight == 0:
            continue
            
        # Cash has 0% return
        if asset == 'Cash':
            continue
        
        # Get Close price column for this stock
        close_col = f"{asset}:Close"
        
        if close_col not in data_df.columns:
            print(f"Warning: No price data for {asset}, assuming 0% return")
            continue
        
        # Get prices at start and end
        try:
            start_price = data_df.loc[start_date, close_col]
            end_price = data_df.loc[end_date, close_col]
            
            # Ensure we have scalar values (handle potential Series returns)
            if isinstance(start_price, pd.Series):
                start_price = start_price.iloc[0] if len(start_price) > 0 else None
            if isinstance(end_price, pd.Series):
                end_price = end_price.iloc[0] if len(end_price) > 0 else None
            
            # Calculate return for this asset
            if start_price is not None and end_price is not None and pd.notna(start_price) and pd.notna(end_price) and start_price > 0:
                asset_return = (end_price - start_price) / start_price
                portfolio_return += weight * asset_return
            else:
                print(f"Warning: Invalid price data for {asset} between {start_date.date()} and {end_date.date()}")
        except KeyError:
            print(f"Warning: Missing date data for {asset}")
            continue
    
    return portfolio_return

# Tool declaration for Gemini function calling
SUM_WEIGHTS_TOOL = types.Tool(
    function_declarations=[{
        "name": "sum_weights",
        "description": "Calculate the sum of portfolio weights to verify they total 1.0. Use this to validate that your weight allocation is correct.",
        "parameters": {
            "type": "object",
            "properties": {
                "weights": {
                    "type": "object",
                    "description": "Dictionary mapping asset names (like 'Cash', 'AAPL', 'GOOGL') to their weight values (floats between 0 and 1)",
                    "additionalProperties": {
                        "type": "number"
                    }
                }
            },
            "required": ["weights"]
        }
    }]
)

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
    def fetch_data(self, ticker_list, period='1mo', interval='1d'):
        print(f"{self.name} is fetching data for {len(ticker_list)} stocks (Period: {period}, Interval: {interval}).")

        stocks = []
        for ticker in tqdm(sorted(ticker_list)):
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            df.columns = [ticker + ':' + c for c in df.columns]
            stocks.append(df)

        df = pd.concat(stocks, axis=1)
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
        
        IMPORTANT: Use the sum_weights tool to verify that your weights sum to 1.0 before finalizing your answer.
        
        After verifying with the tool, return ONLY a valid JSON object in the following format (no other text):
        {{"Cash": 0.2, "AAPL": 0.3, "GOOGL": 0.5}}
        
        Use ticker names for stocks and 'Cash' for free cash. Weights should be floats between 0 and 1 and must sum to exactly 1.0."""
        
        # Generate content with function calling enabled
        config = types.GenerateContentConfig(tools=[SUM_WEIGHTS_TOOL])
        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=prompt,
            config=config
        )
        
        # Handle function calls in a loop
        max_iterations = 5
        iteration = 0
        conversation = [types.Content(role="user", parts=[types.Part(text=prompt)])]
        final_response = None
        
        while iteration < max_iterations:
            # Check if the response contains a function call
            if (response.candidates and 
                response.candidates[0].content.parts and 
                hasattr(response.candidates[0].content.parts[0], 'function_call') and
                response.candidates[0].content.parts[0].function_call):
                
                function_call = response.candidates[0].content.parts[0].function_call
                print(f"[{self.name}] Function call detected: {function_call.name}")
                print(f"[{self.name}] Arguments: {dict(function_call.args)}")
                
                # Execute the sum_weights function
                if function_call.name == "sum_weights":
                    weights = dict(function_call.args.get("weights", {}))
                    result = sum_weights(weights)
                    print(f"[{self.name}] sum_weights result: {result}")
                    
                    # Add model's response to conversation
                    conversation.append(response.candidates[0].content)
                    
                    # Create function response and add to conversation
                    function_response = types.Part.from_function_response(
                        name=function_call.name,
                        response={"sum": result}
                    )
                    conversation.append(types.Content(role="user", parts=[function_response]))
                    
                    # Continue the conversation
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=conversation,
                        config=config
                    )
                    
                    iteration += 1
                else:
                    print(f"[{self.name}] Unknown function call: {function_call.name}")
                    break
            else:
                # No function call, we have the final response
                final_response = response.text
                break
        
        # If we exhausted iterations without getting text, try to extract from last response
        if final_response is None:
            final_response = response.text if response.text else ""
            if not final_response:
                print(f"[{self.name}] Warning: No text response after function calls")
        
        # Store response with latest_date
        self.allocation_history[latest_date] = final_response
        
        # Try to parse JSON and validate weights
        try:
            start_idx = final_response.find('{')
            end_idx = final_response.rfind('}') + 1
            if start_idx == -1 or end_idx <= start_idx:
                raise ValueError("No JSON object found in response")
            
            weights_dict = json.loads(final_response[start_idx:end_idx])
            
            # Exclude Portfolio_Value from columns when creating weights
            weight_columns = [col for col in portfolio.columns if col != 'Portfolio_Value']
            new_row = {col: weights_dict.get(col, 0.0) for col in weight_columns}
            
            # Validate weights sum to 1.0 (fallback validation)
            total_weight = sum(new_row.values())
            if not (0.99 <= total_weight <= 1.01):
                print(f"Weights sum to {total_weight}, not 1.0. Reweighting.")
                for key in new_row:
                    new_row[key] = new_row[key] / total_weight if total_weight > 0 else 0.0

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response: {final_response}")
            # Use previous weights, excluding Portfolio_Value
            prev_row = portfolio.iloc[-1].to_dict()
            new_row = {k: v for k, v in prev_row.items() if k != 'Portfolio_Value'}
        
        # Append new row with latest_date index
        new_df_row = pd.DataFrame([new_row], index=[latest_date])
        return pd.concat([portfolio, new_df_row])


