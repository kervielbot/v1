# KervielBot

bonjour le monde

A multi-agent LLM-powered portfolio management system using Google's Gemini API.

## Setup

After creating and activating your virtual environment, install the package:

```bash
pip install -e .
```

## Running the Application

### Normal execution:
```bash
python -m kervielbot.main
```

This runs the portfolio allocation strategy with agent reasoning hidden.

### Debug mode (with agent reasoning output):
```bash
python -m kervielbot.main debug
```

This displays the trader agent's raw responses, showing its reasoning and allocation decisions in detail.

## Architecture

The system uses three main agents:

- **DataAgent**: Fetches historical stock data from yfinance
- **AnalysisAgent**: Analyzes market data and generates insights using Gemini
- **TraderAgent**: Makes portfolio allocation decisions based on analysis, concentrating in high-conviction positions

## Configuration

Key parameters in `src/main.py`:
- `HISTORICAL_DATA_START`: Start date for historical data (default: "2025-03-01")
- `TEST_DATE_START`: Start of test period (default: "2025-09-01")
- `TEST_DATE_END`: End of test period (default: "2025-09-10")
- `STARTING_CAPITAL`: Initial portfolio value (default: $1,000,000)

## Output

The application generates:
- Daily portfolio allocations and net values
- Final portfolio composition
- Performance metrics (total return %)
- CSV file with allocation history (`portfolio_allocation.csv`)
- Performance visualization (`portfolio_performance.html`)
