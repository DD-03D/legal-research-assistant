#!/usr/bin/env python3
"""
Test script to verify vector store sharing between ingestion and retrieval.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.ingestion.unified_pipeline import UnifiedDocumentIngestionPipeline
    from src.retrieval.retriever import LegalDocumentRetriever
    from src.generation.legal_rag import LegalResponseGenerator
    import tempfile
    
    print("=== Testing Vector Store Sharing ===")
    
    # Create pipeline
    pipeline = UnifiedDocumentIngestionPipeline()
    print(f"Pipeline vector store ID: {id(pipeline.vector_store)}")
    
    # Create a simple test document
    test_content = """
    CONTRACT AGREEMENT
    
    This Agreement is made between Party A and Party B.
    
    Section 1: Payment Terms
    Party B shall pay $10,000 within 30 days.
    
    Section 2: Termination
    Either party may terminate with 14 days notice.
    """
    
    # Save test content to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        temp_file = f.name
    
    try:
        # Ingest document
        print("\n=== Ingesting Document ===")
        result = pipeline.ingest_file(temp_file)
        print(f"Ingestion result: {result}")
        
        # Get collection info
        collection_info = pipeline.get_collection_info()
        print(f"Collection info: {collection_info}")
        
        # Create retriever with SAME vector store
        print(f"\n=== Creating Retriever ===")
        retriever = LegalDocumentRetriever(pipeline.vector_store)
        print(f"Retriever vector store ID: {id(retriever.vector_store)}")
        
        # Verify they match
        if id(pipeline.vector_store) == id(retriever.vector_store):
            print("✅ Vector stores match!")
        else:
            print("❌ Vector stores DON'T match!")
        
        # Test retrieval directly
        print(f"\n=== Testing Direct Retrieval ===")
        results = retriever.retrieve_relevant_documents("payment terms", k=5)
        print(f"Retrieval results: {len(results)} documents found")
        
        if results:
            print(f"First result: {results[0]}")
        else:
            print("No results found - investigating...")
            
            # Check vector store document count
            try:
                doc_count = pipeline.vector_store.get_document_count()
                print(f"Vector store document count: {doc_count}")
            except Exception as e:
                print(f"Failed to get document count: {e}")
        
        # Test with response generator
        print(f"\n=== Testing Response Generator ===")
        response_gen = LegalResponseGenerator(retriever=retriever)
        response = response_gen.generate_response("What are the payment terms?")
        print(f"Response: {response.get('answer', 'No answer')}")
        
    finally:
        # Clean up
        import os
        try:
            os.unlink(temp_file)
        except:
            pass
    
except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
