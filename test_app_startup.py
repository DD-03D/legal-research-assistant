#!/usr/bin/env python3
"""
Test script to verify the app can start without import errors.
"""

import os
import sys
from pathlib import Path

def test_app_startup():
    """Test that the app can start without import errors."""
    print("🧪 Testing App Startup...")
    
    try:
        # Add project root to path
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        src_path = project_root / "src"
        if src_path.exists():
            sys.path.insert(0, str(src_path))
        
        config_path = project_root / "config"
        if config_path.exists():
            sys.path.insert(0, str(config_path))
        
        # Test basic imports
        print("📦 Testing basic imports...")
        
        # Test config import
        try:
            from config.settings import settings
            print("✅ Config settings imported successfully")
        except Exception as e:
            print(f"❌ Config import failed: {e}")
            return False
        
        # Test utils import
        try:
            from src.utils import setup_logging
            print("✅ Utils imported successfully")
        except Exception as e:
            print(f"❌ Utils import failed: {e}")
            return False
        
        # Test document processor import
        try:
            from src.ingestion.document_processor import process_document
            print("✅ Document processor imported successfully")
        except Exception as e:
            print(f"❌ Document processor import failed: {e}")
            return False
        
        # Test unified pipeline import
        try:
            from src.ingestion.unified_pipeline import UnifiedDocumentIngestionPipeline
            print("✅ Unified pipeline imported successfully")
        except Exception as e:
            print(f"❌ Unified pipeline import failed: {e}")
            return False
        
        # Test fallback vector store import
        try:
            from src.ingestion.fallback_vector_store import FallbackVectorStore
            print("✅ Fallback vector store imported successfully")
        except Exception as e:
            print(f"❌ Fallback vector store import failed: {e}")
            return False
        
        # Test legal RAG import
        try:
            from src.generation.legal_rag import LegalResponseGenerator
            print("✅ Legal RAG imported successfully")
        except Exception as e:
            print(f"❌ Legal RAG import failed: {e}")
            return False
        
        # Test main app import (this is the critical one)
        try:
            from src.ui.streamlit_app import main
            print("✅ Main app imported successfully")
        except Exception as e:
            print(f"❌ Main app import failed: {e}")
            return False
        
        print("🎉 All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def main():
    """Run the startup test."""
    print("🚀 Legal Research Assistant - Startup Test")
    print("=" * 50)
    
    success = test_app_startup()
    
    if success:
        print("\n🎉 All tests passed! Your app should start successfully.")
        print("Ready for Streamlit Cloud deployment!")
    else:
        print("\n⚠️  Some tests failed. Please fix the import issues before deploying.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
