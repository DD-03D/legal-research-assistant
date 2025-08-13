"""
Test document processing with Gemini API to verify everything works.
"""

import tempfile
from pathlib import Path
from src.ingestion.vector_store import DocumentIngestionPipeline

def test_document_processing():
    """Test document processing with a simple text document."""
    print("🧪 Testing Document Processing with Gemini API")
    print("=" * 50)
    
    # Create a test legal document
    test_content = """
    LEGAL SERVICES AGREEMENT
    
    Section 1. Scope of Services
    The Attorney agrees to provide legal services as outlined in this agreement.
    
    Section 2. Payment Terms
    Client agrees to pay attorney fees as specified in Schedule A.
    
    Section 3. Confidentiality
    All communications between Attorney and Client shall remain confidential.
    
    Article 4. Termination
    Either party may terminate this agreement with 30 days written notice.
    """
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        temp_file = f.name
    
    try:
        print(f"📄 Created test document: {Path(temp_file).name}")
        
        # Initialize ingestion pipeline
        print("🔧 Initializing ingestion pipeline...")
        pipeline = DocumentIngestionPipeline()
        print("✅ Pipeline initialized successfully")
        
        # Process document
        print("📥 Processing document...")
        result = pipeline.ingest_file(temp_file)
        
        if result['success']:
            print("✅ Document processed successfully!")
            print(f"   📊 Document ID: {result['document_id']}")
            print(f"   📄 Sections added: {result['sections_added']}")
            print(f"   🔤 Total tokens: {result['total_tokens']}")
            return True
        else:
            print(f"❌ Document processing failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return False
    finally:
        # Clean up
        Path(temp_file).unlink(missing_ok=True)

if __name__ == "__main__":
    success = test_document_processing()
    
    if success:
        print("\n🎉 All tests passed! Your Legal Research Assistant is ready to use!")
        print("📱 Open http://localhost:8501 to start using the application.")
    else:
        print("\n⚠️ Some issues were found. Check the error messages above.")
