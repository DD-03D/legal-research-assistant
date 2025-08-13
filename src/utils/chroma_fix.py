"""
ChromaDB compatibility fixes for deployment environments.
"""

import os
import warnings
from loguru import logger

def fix_chroma_telemetry():
    """Fix ChromaDB telemetry issues in deployment environments."""
    try:
        # Disable ChromaDB telemetry
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_SERVER_NOFILE"] = "1"
        
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

# Apply fixes on import
fix_chroma_telemetry()
