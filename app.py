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

# Add config directory to path
config_path = project_root / "config"
if config_path.exists():
    sys.path.insert(0, str(config_path))

def setup_environment():
    """Setup environment and handle compatibility issues."""
    try:
        # SQLite compatibility fix for Streamlit Cloud
        try:
            from src.utils.sqlite_fix import fix_sqlite
            fix_sqlite()
            print("✅ SQLite compatibility fix applied")
        except ImportError as e:
            print(f"⚠️  SQLite fix import warning: {e}")

        # ChromaDB telemetry fix - must be imported before any ChromaDB imports
        try:
            from src.utils.chroma_fix import fix_chroma_telemetry, disable_chroma_telemetry_completely
            fix_chroma_telemetry()
            disable_chroma_telemetry_completely()
            print("✅ ChromaDB telemetry fixes applied")
        except ImportError as e:
            print(f"⚠️  ChromaDB fix import warning: {e}")

        # Import and setup logging
        try:
            from src.utils import setup_logging
            setup_logging()
            print("✅ Logging setup completed")
        except ImportError as e:
            print(f"⚠️  Logging setup warning: {e}")

        return True
    except Exception as e:
        print(f"❌ Environment setup failed: {e}")
        return False

def run_app():
    """Run the Legal Research Assistant application."""
    try:
        # Setup environment first
        if not setup_environment():
            st.error("Failed to setup application environment")
            st.stop()
            return

        # Try to import the main app
        try:
            from src.ui.streamlit_app import main
            print("✅ Main application imported successfully")
        except ImportError as e:
            print(f"❌ Main app import error: {e}")
            st.error(f"Failed to import main application: {e}")
            st.stop()
            return

        # Run the Streamlit app
        main()
        
    except Exception as e:
        error_msg = f"Application failed to start: {e}"
        print(f"❌ {error_msg}")
        
        try:
            import streamlit as st
            st.error(error_msg)
            st.error("Please check the logs for more details.")
            st.stop()
        except:
            print("Critical error - cannot start Streamlit application")
            sys.exit(1)

if __name__ == "__main__":
    # Import streamlit here to avoid import issues
    try:
        import streamlit as st
        run_app()
    except ImportError as e:
        print(f"❌ Streamlit import failed: {e}")
        print("Please install Streamlit: pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Critical error: {e}")
        sys.exit(1)
