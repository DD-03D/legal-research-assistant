"""
ChromaDB compatibility fixes for deployment environments.
"""

import os
import warnings
import tempfile
from loguru import logger

# Force-disable telemetry as early as possible
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "0"
os.environ["CHROMA_SERVER_NOFILE"] = os.environ.get("CHROMA_SERVER_NOFILE", "1024")

def fix_chroma_telemetry():
    """Fix ChromaDB telemetry issues in deployment environments."""
    try:
        # Disable ChromaDB telemetry
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_TELEMETRY_ENABLED"] = "0"
        os.environ["CHROMA_SERVER_HTTP_PORT"] = "8000"

        # Suppress telemetry warnings
        warnings.filterwarnings("ignore", message=".*telemetry.*")
        warnings.filterwarnings("ignore", message=".*capture.*")

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
        
        # Try to import and configure ChromaDB
        import chromadb
        from chromadb.config import Settings
        
        # Configure ChromaDB settings for cloud deployment
        settings = Settings(
            anonymized_telemetry=False,
            allow_reset=True,
            is_persistent=True
        )
        
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
        chromadb.reset()
        logger.info("✅ ChromaDB client reset successfully")
        return True
    except Exception as e:
        logger.warning(f"Could not reset ChromaDB client: {e}")
        return False

# Apply fixes on import
fix_chroma_telemetry()
