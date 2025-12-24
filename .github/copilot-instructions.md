# Copilot Instructions for Nifty 50 Option Chain Algo Trader

## Project Overview
This project is an algorithmic trading application for Nifty 50 options, utilizing the Groww API. It employs a "Confluence Strategy" combining Technical Analysis (Trend), Machine Learning (Random Forest), and Sentiment Analysis (Option Chain PCR).

## Tech Stack
- **Language**: Python
- **UI Framework**: Streamlit
- **Data Analysis**: Pandas, NumPy, Pandas-TA
- **Machine Learning**: Scikit-learn (Random Forest)
- **API**: Groww API (via `groww_client.py`)
- **Build Tool**: PyInstaller (for creating standalone executables)
- **CI/CD**: GitHub Actions

## Architecture & File Structure
- **`main.py`**: Entry point for the frozen executable. Handles `sys._MEIPASS` and sets `IS_FROZEN` env var.
- **`app.py`**: Main entry point for the Streamlit application logic. Hides UI elements if `IS_FROZEN` is set.
- **`strategy.py`**: Core trading logic, `StrategyEngine` class, feature engineering, and ML model training/prediction.
- **`groww_client.py`**: Wrapper for Groww API interactions (authentication, data fetching).
- **`ui/`**: Directory containing modular UI components.
  - `dashboard.py`: Main dashboard view.
  - `option_chain.py`: Option chain visualization.
  - `trades.py`: Trade logging and display.
  - `strategy_explanation.py`: Documentation of the strategy within the app.
- **`config.py`**: Configuration constants (Capital, Target Profit, etc.).
- **`logger.py`**: Centralized logging configuration.
- **`.github/workflows/ci-cd.yml`**: GitHub Actions workflow for linting, building, and releasing.

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
- **Confluence Strategy**: A trade is executed based on a voting system:
    1.  **Trend Filter**: 
        *   **Regime Detection**: Uses ADX to classify market as DEAD, CHOPPY, or TRENDING.
        *   **Momentum Override**: If Candle Body > ATR (High Momentum), it overrides "DEAD" regime to allow catching breakouts.
        *   **Indicators**: Uses SMA 50/20 for trending markets and Supertrend for volatile markets.
    2.  **ML Model**: Random Forest Classifier predicting Bullish/Bearish/Neutral based on last 200 candles.
    3.  **Sentiment**: PCR (Put-Call Ratio) from Option Chain (>1.2 Bullish, <0.8 Bearish).
- **Paper Trading**: The system currently simulates trades. Ensure any new execution logic maintains this separation unless explicitly moving to live trading.

## Deployment & Build
- **Executable**: The app is packaged as a standalone executable using PyInstaller.
- **Frozen State**: When running as an exe, `main.py` sets `os.environ["IS_FROZEN"] = "true"`. `app.py` uses this to hide Streamlit developer UI (Deploy button, Hamburger menu, Footer).
- **CI/CD**: 
    *   Commits to `master` trigger Lint and Build jobs on Windows, Linux, and macOS.
    *   Tags (e.g., `v1.0.0`) trigger a Release job that uploads the executables to GitHub Releases.

## Future Development
- When suggesting changes, prioritize maintaining the separation between the UI (`ui/`) and the logic (`strategy.py`, `groww_client.py`).
- Ensure `requirements.txt` is updated if new dependencies are introduced.
