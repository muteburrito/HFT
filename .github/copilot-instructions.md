# Copilot Instructions for Nifty 50 Option Chain Algo Trader

## Project Overview
This project is an algorithmic trading application for Nifty 50 options, utilizing the Groww API. It employs a "Confluence Strategy" combining Technical Analysis (Trend), Machine Learning (Random Forest), and Sentiment Analysis (Option Chain PCR).

## Tech Stack
- **Language**: Python
- **UI Framework**: Streamlit
- **Data Analysis**: Pandas, NumPy, Pandas-TA
- **Machine Learning**: Scikit-learn (Random Forest)
- **API**: Groww API (via `groww_client.py`)

## Architecture & File Structure
- **`app.py`**: Main entry point for the Streamlit application.
- **`strategy.py`**: Core trading logic, `StrategyEngine` class, feature engineering, and ML model training/prediction.
- **`groww_client.py`**: Wrapper for Groww API interactions (authentication, data fetching).
- **`ui/`**: Directory containing modular UI components.
  - `dashboard.py`: Main dashboard view.
  - `option_chain.py`: Option chain visualization.
  - `trades.py`: Trade logging and display.
- **`config.py`**: Configuration constants (Capital, Target Profit, etc.).
- **`logger.py`**: Centralized logging configuration.

## Coding Guidelines
1.  **Modular UI**: When adding new UI features, create a new module in the `ui/` directory and import it into `app.py` or the relevant parent component.
2.  **Strategy Logic**: All trading logic, indicator calculations, and ML operations belong in `strategy.py`. Avoid putting business logic in UI files.
3.  **Logging**: Use the `logger` module for all debug and info messages. Do not use `print()` statements.
    ```python
    from logger import setup_logger
    logger = setup_logger(__name__)
    logger.info("Message")
    ```
4.  **Configuration**: Use `config.py` for any hardcoded values or tunable parameters.
5.  **Type Hinting**: Use Python type hints where possible to improve code clarity.

## Key Concepts
- **Confluence Strategy**: A trade is only executed if:
    1.  Trend Filter (SMA Crossover) agrees.
    2.  ML Model predicts the same direction.
    3.  PCR (Put-Call Ratio) confirms the sentiment.
- **Paper Trading**: The system currently simulates trades. Ensure any new execution logic maintains this separation unless explicitly moving to live trading.

## Future Development
- When suggesting changes, prioritize maintaining the separation between the UI (`ui/`) and the logic (`strategy.py`, `groww_client.py`).
- Ensure `requirements.txt` is updated if new dependencies are introduced.
