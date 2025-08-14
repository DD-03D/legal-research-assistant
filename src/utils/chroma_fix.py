"""
ChromaDB compatibility fixes for deployment environments.
"""

import os
import warnings
import tempfile
import sqlite3
from loguru import logger

# Force-disable telemetry as early as possible
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "0"
os.environ["CHROMA_TELEMETRY_HOST"] = ""
os.environ["CHROMA_TELEMETRY_PORT"] = ""

# Force ChromaDB into client mode to avoid server configuration warnings
os.environ["CHROMA_SERVER_MODE"] = "false"
os.environ["CHROMA_CLIENT_MODE"] = "true"

# Fix CHROMA_SERVER_NOFILE issue - only set if not already set and in server mode
if "CHROMA_SERVER_NOFILE" not in os.environ:
    # Only set this for server mode, not client mode
    if os.environ.get("CHROMA_SERVER_MODE", "").lower() == "true":
        os.environ["CHROMA_SERVER_NOFILE"] = "1048576"  # Use a higher value
    else:
        # For client mode, don't set this variable to avoid warnings
        pass

def check_sqlite_version():
    """Check SQLite version and provide compatibility info."""
    try:
        version = sqlite3.sqlite_version
        version_tuple = tuple(map(int, version.split('.')))
        logger.info(f"System SQLite version: {version}")
        
        if version_tuple < (3, 35, 0):
            logger.warning(f"⚠️  System SQLite version {version} may be incompatible")
            logger.warning("   Consider installing pysqlite3-binary for better compatibility")
            return False
        else:
            logger.info(f"✅ System SQLite version {version} is compatible")
            return True
    except Exception as e:
        logger.warning(f"Could not determine SQLite version: {e}")
        return False

def fix_sqlite_compatibility():
    """Fix SQLite compatibility issues for ChromaDB."""
    try:
        # Try to import pysqlite3 and replace the system sqlite3
        import pysqlite3
        import sys
        
        # Replace the system sqlite3 with pysqlite3
        sys.modules["sqlite3"] = pysqlite3
        logger.info("✅ Successfully replaced system sqlite3 with pysqlite3")
        return True
        
    except ImportError:
        logger.warning("⚠️  pysqlite3 not available, using system sqlite3")
        return False

def fix_chroma_telemetry():
    """Fix ChromaDB telemetry issues in deployment environments."""
    try:
        # Disable ChromaDB telemetry
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_TELEMETRY_ENABLED"] = "0"
        os.environ["CHROMA_TELEMETRY_HOST"] = ""
        os.environ["CHROMA_TELEMETRY_PORT"] = ""

        # Suppress telemetry warnings
        warnings.filterwarnings("ignore", message=".*telemetry.*")
        warnings.filterwarnings("ignore", message=".*capture.*")
        warnings.filterwarnings("ignore", message=".*ClientStartEvent.*")
        warnings.filterwarnings("ignore", message=".*ClientCreateCollectionEvent.*")
        warnings.filterwarnings("ignore", message=".*CollectionQueryEvent.*")
        warnings.filterwarnings("ignore", message=".*chroma_server_nofile.*")

        # Check SQLite compatibility first
        sqlite_ok = check_sqlite_version()
        if not sqlite_ok:
            fix_sqlite_compatibility()

        # Monkey patch the telemetry capture method if it exists
        try:
            import chromadb
            if hasattr(chromadb, 'telemetry'):
                # Disable telemetry completely
                chromadb.telemetry = None
                logger.info("✅ ChromaDB telemetry module disabled")
        except Exception:
            pass

        logger.info("✅ ChromaDB telemetry disabled")
        return True

    except Exception as e:
        logger.warning(f"Could not disable ChromaDB telemetry: {e}")
        return False

def fix_chroma_import():
    """Fix ChromaDB import issues."""
    try:
        # Set environment variables before importing ChromaDB
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_TELEMETRY_ENABLED"] = "0"
        
        # Fix SQLite compatibility first
        fix_sqlite_compatibility()
        
        # Try to import and configure ChromaDB
        import chromadb
        from chromadb.config import Settings
        
        # Configure ChromaDB settings for cloud deployment
        settings = Settings(
            anonymized_telemetry=False,
            allow_reset=True,
            is_persistent=True
        )
        
        # Disable telemetry at the client level
        if hasattr(chromadb, 'Client'):
            # Monkey patch the Client class to disable telemetry
            original_init = chromadb.Client.__init__
            def patched_init(self, *args, **kwargs):
                kwargs['anonymized_telemetry'] = False
                return original_init(self, *args, **kwargs)
            chromadb.Client.__init__ = patched_init
        
        logger.info("✅ ChromaDB configured successfully")
        return True
        
    except Exception as e:
        logger.error(f"ChromaDB configuration failed: {e}")
        return False

def get_unique_persist_directory():
    """Get a unique persist directory to avoid conflicts."""
    try:
        # For cloud deployment, use a unique directory in temp
        if os.path.exists('/mount/src'):  # Streamlit Cloud indicator
            base_dir = "/tmp"
        else:
            base_dir = "./data"
            
        # Create unique directory name
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        persist_dir = os.path.join(base_dir, f"chroma_db_{unique_id}")
        
        os.makedirs(persist_dir, exist_ok=True)
        logger.info(f"Created unique ChromaDB directory: {persist_dir}")
        return persist_dir
        
    except Exception as e:
        logger.error(f"Failed to create unique directory: {e}")
        return "./data/chroma_db"

def reset_chroma_client():
    """Reset ChromaDB client to avoid instance conflicts."""
    try:
        import chromadb
        # Try to reset any existing client
        if hasattr(chromadb, 'reset'):
            chromadb.reset()
            logger.info("✅ ChromaDB client reset successfully")
        else:
            logger.warning("ChromaDB reset method not available")
        return True
    except Exception as e:
        logger.warning(f"Could not reset ChromaDB client: {e}")
        return False

def disable_chroma_telemetry_completely():
    """Completely disable ChromaDB telemetry by patching the capture method."""
    try:
        # Fix SQLite compatibility first
        fix_sqlite_compatibility()
        
        import chromadb
        if hasattr(chromadb, 'telemetry') and chromadb.telemetry:
            # Create a dummy capture method that does nothing
            def dummy_capture(*args, **kwargs):
                pass
            
            # Replace the capture method
            if hasattr(chromadb.telemetry, 'capture'):
                chromadb.telemetry.capture = dummy_capture
                logger.info("✅ ChromaDB telemetry capture method patched")
            
            # Disable the entire telemetry module
            chromadb.telemetry = None
            logger.info("✅ ChromaDB telemetry module completely disabled")
            
    except Exception as e:
        logger.warning(f"Could not patch ChromaDB telemetry: {e}")

# Apply fixes on import
fix_chroma_telemetry()
disable_chroma_telemetry_completely()
