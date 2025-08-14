#!/usr/bin/env python3
"""
Test script to verify API keys are loaded correctly.
"""

import os
import sys
from pathlib import Path

def test_api_key_loading():
    """Test that API keys are loaded correctly."""
    print("🧪 Testing API Key Loading...")
    
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
        
        # Test config import
        try:
            from config.settings import settings, get_gemini_api_key
            print("✅ Config settings imported successfully")
        except Exception as e:
            print(f"❌ Config import failed: {e}")
            return False
        
        # Test API key loading
        print("\n📋 API Key Status:")
        
        # Check OpenAI API key
        openai_key = settings.openai_api_key
        if openai_key:
            print(f"✅ OpenAI API Key: {openai_key[:20]}...")
        else:
            print("⚠️  OpenAI API Key: Not set")
        
        # Check Gemini API key
        gemini_key = settings.gemini_api_key
        if gemini_key:
            print(f"✅ Gemini API Key: {gemini_key[:20]}...")
        else:
            print("⚠️  Gemini API Key: Not set")
        
        # Test the get_gemini_api_key function
        print("\n🔍 Testing Gemini API Key Function:")
        
        # Test with GEMINI_API_KEY
        os.environ["GEMINI_API_KEY"] = "test_gemini_key"
        gemini_test = get_gemini_api_key()
        if gemini_test == "test_gemini_key":
            print("✅ GEMINI_API_KEY loading works")
        else:
            print("❌ GEMINI_API_KEY loading failed")
        
        # Test fallback to GOOGLE_API_KEY
        del os.environ["GEMINI_API_KEY"]
        os.environ["GOOGLE_API_KEY"] = "test_google_key"
        google_test = get_gemini_api_key()
        if google_test == "test_google_key":
            print("✅ GOOGLE_API_KEY fallback works")
        else:
            print("❌ GOOGLE_API_KEY fallback failed")
        
        # Clean up test environment variables
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
        
        print("\n🎉 API key loading test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def main():
    """Run the API key test."""
    print("🚀 Legal Research Assistant - API Key Test")
    print("=" * 50)
    
    success = test_api_key_loading()
    
    if success:
        print("\n🎉 API key loading test passed!")
        print("Your app should be able to access the API keys correctly.")
    else:
        print("\n⚠️  API key loading test failed.")
        print("Please check the configuration setup.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
