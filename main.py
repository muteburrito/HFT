import sys
import os
from logger import setup_logger

# Set environment variables BEFORE importing streamlit to ensure they are picked up
# This prevents the "Welcome to Streamlit" email prompt on first run
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

from streamlit.web import cli as stcli

logger = setup_logger("main")

def main():
    # Self-test mode to verify imports (used in CI/CD)
    if "--check-imports" in sys.argv:
        try:
            logger.info("Running import self-check...")
            import pandas  # noqa: F401
            import numpy  # noqa: F401
            import sklearn  # noqa: F401
            import sklearn.ensemble  # noqa: F401
            import pandas_ta  # noqa: F401
            import growwapi  # noqa: F401
            import matplotlib  # noqa: F401
            import plotly  # noqa: F401
            import pyotp  # noqa: F401
            
            # In frozen mode, ensure we can import local modules
            if getattr(sys, 'frozen', False):
                sys.path.append(sys._MEIPASS)
                
            import strategy  # noqa: F401
            import groww_client  # noqa: F401
            import database  # noqa: F401
            import config  # noqa: F401
            
            logger.info("Success: All modules imported correctly.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error: Import check failed - {e}")
            sys.exit(1)

    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app 
        # path into variable _MEIPASS'.
        application_path = sys._MEIPASS
        os.environ["IS_FROZEN"] = "true"
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(application_path, "app.py")

    sys.argv = [
        "streamlit", 
        "run", 
        app_path, 
        "--global.developmentMode=false",
        "--client.showErrorDetails=false",
        "--client.toolbarMode=viewer",
        "--browser.gatherUsageStats=false"
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
