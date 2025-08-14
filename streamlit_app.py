# Streamlit Cloud Entry Point
# This file serves as the main entry point for Streamlit Cloud deployment

import sys
from pathlib import Path

# Add the source directory to the Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import and run the main UI application
if __name__ == "__main__":
    from src.ui.streamlit_app import main
    main()
