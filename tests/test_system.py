"""
Test script to validate the Legal Research Assistant system.
This script tests the complete pipeline from document ingestion to response generation.
"""

import sys
import os
from pathlib import Path
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.ingestion.document_processor import process_document
    from src.ingestion.vector_store import DocumentIngestionPipeline
    from src.generation.legal_rag import LegalResponseGenerator
    from src.evaluation.metrics import RetrievalEvaluator, ResponseEvaluator, PerformanceEvaluator
    from config.settings import settings
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

def test_document_processing():
    """Test document processing functionality."""
    print("\n📄 Testing Document Processing...")
    
    sample_docs_dir = project_root / "data" / "sample_documents"
    
    if not sample_docs_dir.exists():
        print(f"❌ Sample documents directory not found: {sample_docs_dir}")
        return False
    
    try:
        # Test processing each sample document
        for doc_file in sample_docs_dir.glob("*.txt"):
            print(f"  Processing: {doc_file.name}")
            
            result = process_document(str(doc_file))
            
            print(f"    ✅ Sections: {result['section_count']}")
            print(f"    ✅ Tokens: {result['token_count']}")
            print(f"    ✅ Document ID: {result['document_id'][:16]}...")
        
        print("✅ Document processing test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Document processing test failed: {e}")
        return False

def test_vector_store():
    """Test vector store ingestion."""
    print("\n🔍 Testing Vector Store Ingestion...")
    
    try:
        # Initialize ingestion pipeline
        pipeline = DocumentIngestionPipeline()
        
        # Test with sample documents
        sample_docs_dir = project_root / "data" / "sample_documents"
        sample_files = list(sample_docs_dir.glob("*.txt"))
        
        if not sample_files:
            print("❌ No sample documents found for testing")
            return False
        
        # Ingest first document
        test_file = sample_files[0]
        print(f"  Ingesting: {test_file.name}")
        
        result = pipeline.ingest_file(str(test_file))
        
        if result['success']:
            print(f"    ✅ Sections added: {result['sections_added']}")
            print(f"    ✅ Total tokens: {result['total_tokens']}")
        else:
            print(f"    ❌ Ingestion failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Test retrieval
        status = pipeline.get_status()
        print(f"  Vector store status: {status['total_documents']} documents")
        
        print("✅ Vector store test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Vector store test failed: {e}")
        return False

def test_response_generation():
    """Test response generation."""
    print("\n🤖 Testing Response Generation...")
    
    try:
        # Initialize response generator
        generator = LegalResponseGenerator()
        
        # Test queries
        test_queries = [
            "What are the termination conditions?",
            "What are the liability limitations?",
            "What are the payment terms?"
        ]
        
        for query in test_queries:
            print(f"  Testing query: {query}")
            
            start_time = time.time()
            response = generator.generate_response(query)
            response_time = time.time() - start_time
            
            if response.get('answer'):
                print(f"    ✅ Response generated ({response_time:.2f}s)")
                print(f"    ✅ Sources: {len(response.get('sources', []))}")
                print(f"    ✅ Citations: {len(response.get('citations', []))}")
                
                # Check for conflicts
                if response.get('has_conflicts'):
                    print(f"    ⚠️  Conflicts detected: {len(response.get('conflicts', []))}")
                
            else:
                print(f"    ❌ No response generated")
                return False
        
        print("✅ Response generation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Response generation test failed: {e}")
        return False

def test_evaluation_metrics():
    """Test evaluation metrics."""
    print("\n📊 Testing Evaluation Metrics...")
    
    try:
        # Test retrieval evaluator
        retrieval_eval = RetrievalEvaluator()
        
        # Mock data for testing
        retrieved_docs = [
            {'document_name': 'employment_agreement.txt', 'similarity_score': 0.9},
            {'document_name': 'service_agreement.txt', 'similarity_score': 0.7},
        ]
        relevant_docs = ['employment_agreement.txt']
        
        precision_scores = retrieval_eval.evaluate_precision_at_k(
            "test query", retrieved_docs, relevant_docs
        )
        
        print(f"  ✅ Precision@1: {precision_scores.get('precision@1', 0):.2f}")
        print(f"  ✅ Precision@3: {precision_scores.get('precision@3', 0):.2f}")
        
        # Test response evaluator
        response_eval = ResponseEvaluator()
        
        test_response = "According to [Employment Agreement, Section 7], termination requires 30 days notice."
        metrics = response_eval.evaluate_response_quality(test_response)
        
        print(f"  ✅ Citations found: {metrics.get('total_legal_references', 0)}")
        print(f"  ✅ Legal term density: {metrics.get('legal_term_density', 0):.3f}")
        
        print("✅ Evaluation metrics test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Evaluation metrics test failed: {e}")
        return False

def test_end_to_end():
    """Test complete end-to-end workflow."""
    print("\n🔄 Testing End-to-End Workflow...")
    
    try:
        # 1. Process and ingest documents
        pipeline = DocumentIngestionPipeline()
        sample_docs_dir = project_root / "data" / "sample_documents"
        
        file_paths = [str(f) for f in sample_docs_dir.glob("*.txt")]
        batch_result = pipeline.ingest_files_batch(file_paths)
        
        print(f"  ✅ Batch ingestion: {batch_result['successful_files']}/{batch_result['total_files']} files")
        
        # 2. Generate response
        generator = LegalResponseGenerator()
        query = "What are the termination clauses and notice requirements across all documents?"
        
        response = generator.generate_response(query)
        
        print(f"  ✅ End-to-end response generated")
        print(f"  ✅ Response length: {len(response.get('answer', ''))} characters")
        print(f"  ✅ Sources used: {len(response.get('sources', []))}")
        
        # 3. Performance measurement
        perf_eval = PerformanceEvaluator()
        latency_data = perf_eval.measure_end_to_end_latency(query, generator)
        
        print(f"  ✅ Total latency: {latency_data['total_latency']:.2f}s")
        
        print("✅ End-to-end test passed!")
        return True
        
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Legal Research Assistant - System Validation")
    print("=" * 50)
    
    # Check environment setup
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY environment variable not set!")
        print("Please set your OpenAI API key in the .env file")
        return
    
    print(f"✅ OpenAI API key configured")
    print(f"✅ Project root: {project_root}")
    
    # Run tests
    tests = [
        ("Document Processing", test_document_processing),
        ("Vector Store", test_vector_store),
        ("Response Generation", test_response_generation),
        ("Evaluation Metrics", test_evaluation_metrics),
        ("End-to-End Workflow", test_end_to_end)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        try:
            if test_func():
                passed_tests += 1
            else:
                print(f"❌ {test_name} test failed!")
        except Exception as e:
            print(f"❌ {test_name} test encountered an error: {e}")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"📊 Test Summary: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The system is ready for use.")
        print("\nTo start the application, run:")
        print("streamlit run app.py")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        print("Make sure all dependencies are installed and the environment is properly configured.")

if __name__ == "__main__":
    main()
