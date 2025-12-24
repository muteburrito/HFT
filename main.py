import sys
import os

# Set environment variables BEFORE importing streamlit to ensure they are picked up
# This prevents the "Welcome to Streamlit" email prompt on first run
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

from streamlit.web import cli as stcli

def main():
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
