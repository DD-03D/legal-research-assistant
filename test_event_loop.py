"""
Test script to verify API providers work correctly in different threading contexts.
"""

import asyncio
import threading
from src.api_providers import APIProviderFactory

def test_in_thread():
    """Test API provider initialization in a thread (similar to Streamlit)."""
    print("Testing in thread...")
    
    try:
        # Test embeddings
        embeddings = APIProviderFactory.get_embeddings()
        print(f"✅ Embeddings initialized: {type(embeddings).__name__}")
        
        # Test LLM
        llm = APIProviderFactory.get_llm()
        print(f"✅ LLM initialized: {type(llm).__name__}")
        
        return True
    except Exception as e:
        print(f"❌ Error in thread: {e}")
        return False

def main():
    print("🧪 Testing API Provider Event Loop Handling")
    print("=" * 50)
    
    # Test in main thread
    print("\n1. Testing in main thread:")
    success_main = test_in_thread()
    
    # Test in separate thread (like Streamlit ScriptRunner)
    print("\n2. Testing in separate thread (Streamlit-like):")
    result = [False]
    
    def thread_target():
        result[0] = test_in_thread()
    
    thread = threading.Thread(target=thread_target)
    thread.start()
    thread.join()
    
    success_thread = result[0]
    
    print(f"\n📊 Results:")
    print(f"   Main thread: {'✅ Success' if success_main else '❌ Failed'}")
    print(f"   Separate thread: {'✅ Success' if success_thread else '❌ Failed'}")
    
    if success_main and success_thread:
        print("\n🎉 All tests passed! API providers should work in Streamlit.")
    else:
        print("\n⚠️ Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()
