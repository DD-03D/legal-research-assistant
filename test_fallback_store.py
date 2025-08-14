#!/usr/bin/env python3
"""
Test script to verify the fallback vector store works correctly.
"""

import os
import sys
from pathlib import Path

def test_fallback_vector_store():
    """Test the fallback vector store implementation."""
    print("🧪 Testing Fallback Vector Store...")
    
    try:
        # Add project root to path
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        src_path = project_root / "src"
        if src_path.exists():
            sys.path.insert(0, str(src_path))
        
        # Test fallback vector store import
        from src.ingestion.fallback_vector_store import FallbackVectorStore
        print("✅ Fallback vector store imported successfully")
        
        # Test initialization
        store = FallbackVectorStore("test_faiss_db")
        print("✅ Fallback vector store initialized successfully")
        
        # Test adding documents
        from langchain.schema import Document
        
        test_docs = [
            Document(
                page_content="This is a test legal document about contracts.",
                metadata={"filename": "test1.txt", "type": "contract"}
            ),
            Document(
                page_content="This is another test document about employment law.",
                metadata={"filename": "test2.txt", "type": "employment"}
            )
        ]
        
        doc_ids = store.add_documents(test_docs)
        print(f"✅ Added {len(doc_ids)} documents: {doc_ids}")
        
        # Test search
        results = store.search_similar_documents("contracts", n_results=2)
        print(f"✅ Search returned {len(results)} results")
        
        # Test stats
        stats = store.get_collection_stats()
        print(f"✅ Store stats: {stats}")
        
        # Clean up
        import shutil
        if Path("test_faiss_db").exists():
            shutil.rmtree("test_faiss_db")
            print("✅ Test database cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback vector store test failed: {e}")
        return False

def main():
    """Run the fallback vector store test."""
    print("🚀 Fallback Vector Store Test")
    print("=" * 40)
    
    success = test_fallback_vector_store()
    
    if success:
        print("\n🎉 Fallback vector store test passed!")
        print("This means your app will work even if ChromaDB has SQLite issues.")
    else:
        print("\n⚠️  Fallback vector store test failed.")
        print("You may need to install additional dependencies.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
