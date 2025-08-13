"""
Main entry point for the Legal Research Assistant.
This script initializes and runs the Streamlit application.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and setup
from src.utils import setup_logging
from src.ui.streamlit_app import main

def run_app():
    """Run the Legal Research Assistant application."""
    # Setup logging
    setup_logging()
    
    # Run the Streamlit app
    main()

if __name__ == "__main__":
    run_app()
