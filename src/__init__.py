# Legal Research Assistant - Main Package
# Fix for Streamlit Cloud deployment

import os
import sys
from pathlib import Path

# Add project root to path if not already there
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Fix SQLite issue for Streamlit Cloud
try:
    import pysqlite3
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

# Set environment variables for better compatibility
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Import and setup
try:
    from src.utils.sqlite_fix import fix_sqlite
    fix_sqlite()
except ImportError:
    pass
