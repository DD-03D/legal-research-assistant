"""
Main entry point for the Legal Research Assistant.
This script initializes and runs the Streamlit application.
"""

import sys
import os
from pathlib import Path

# Force disable telemetry before any other imports
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "0"
os.environ["CHROMA_TELEMETRY_HOST"] = ""
os.environ["CHROMA_TELEMETRY_PORT"] = ""

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Also add src directory to path for Streamlit Cloud
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

# SQLite compatibility fix for Streamlit Cloud
try:
    from src.utils.sqlite_fix import fix_sqlite
    fix_sqlite()
except ImportError as e:
    print(f"SQLite fix import warning: {e}")

# ChromaDB telemetry fix - must be imported before any ChromaDB imports
try:
    from src.utils.chroma_fix import fix_chroma_telemetry, disable_chroma_telemetry_completely
    fix_chroma_telemetry()
    disable_chroma_telemetry_completely()
except ImportError as e:
    print(f"ChromaDB fix import warning: {e}")

# Import and setup with error handling
try:
    from src.utils import setup_logging
    setup_logging()
except ImportError as e:
    print(f"Logging setup warning: {e}")

try:
    from src.ui.streamlit_app import main
except ImportError as e:
    print(f"Main app import error: {e}")
    # Try alternative import
    try:
        import streamlit as st
        st.error(f"Failed to import main application: {e}")
        st.stop()
    except:
        print("Critical import failure - cannot start application")
        sys.exit(1)

def run_app():
    """Run the Legal Research Assistant application."""
    try:
        # Run the Streamlit app
        main()
    except Exception as e:
        print(f"Application error: {e}")
        import streamlit as st
        st.error(f"Application failed to start: {e}")
        st.stop()

if __name__ == "__main__":
    run_app()
