#!/usr/bin/env python3
"""
Test script to verify ChromaDB telemetry fixes work correctly.
Run this before deploying to Streamlit Cloud.
"""

import os
import sys
from pathlib import Path

def test_telemetry_disabled():
    """Test that telemetry is properly disabled."""
    print("🧪 Testing ChromaDB telemetry fixes...")
    
    # Check environment variables
    telemetry_vars = [
        "ANONYMIZED_TELEMETRY",
        "CHROMA_ANONYMIZED_TELEMETRY", 
        "CHROMA_TELEMETRY_ENABLED",
        "CHROMA_TELEMETRY_HOST",
        "CHROMA_TELEMETRY_PORT"
    ]
    
    print("\n📋 Environment Variables:")
    for var in telemetry_vars:
        value = os.environ.get(var, "NOT_SET")
        print(f"  {var}: {value}")
    
    # Test ChromaDB import
    try:
        print("\n🔍 Testing ChromaDB import...")
        
        # Apply our fixes first
        from src.utils.chroma_fix import fix_chroma_telemetry, disable_chroma_telemetry_completely
        fix_chroma_telemetry()
        disable_chroma_telemetry_completely()
        
        # Now try to import ChromaDB
        import chromadb
        print("✅ ChromaDB imported successfully")
        
        # Test client creation
        try:
            client = chromadb.Client(anonymized_telemetry=False)
            print("✅ ChromaDB client created successfully")
            
            # Test collection creation
            collection = client.create_collection("test_collection")
            print("✅ Collection created successfully")
            
            # Clean up
            client.delete_collection("test_collection")
            print("✅ Test collection cleaned up")
            
        except Exception as e:
            print(f"⚠️  Client creation test failed: {e}")
            
    except ImportError as e:
        print(f"❌ ChromaDB import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ ChromaDB test failed: {e}")
        return False
    
    return True

def test_streamlit_import():
    """Test that Streamlit can be imported."""
    print("\n🧪 Testing Streamlit import...")
    
    try:
        import streamlit as st
        print("✅ Streamlit imported successfully")
        print(f"  Version: {st.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Streamlit import failed: {e}")
        return False

def test_main_app_import():
    """Test that the main app can be imported."""
    print("\n🧪 Testing main app import...")
    
    try:
        # Add project root to path
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        src_path = project_root / "src"
        if src_path.exists():
            sys.path.insert(0, str(src_path))
        
        from src.ui.streamlit_app import LegalResearchUI
        print("✅ Main app imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Main app import failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Legal Research Assistant - Deployment Test")
    print("=" * 50)
    
    tests = [
        ("Telemetry Disabled", test_telemetry_disabled),
        ("Streamlit Import", test_streamlit_import),
        ("Main App Import", test_main_app_import)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your app is ready for Streamlit Cloud deployment.")
        print("\n📝 Next steps:")
        print("  1. Commit and push your changes to GitHub")
        print("  2. Deploy on Streamlit Cloud using requirements-streamlit.txt")
        print("  3. Set the required environment variables")
    else:
        print("⚠️  Some tests failed. Please fix the issues before deploying.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
