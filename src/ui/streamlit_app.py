"""
Streamlit UI for the Legal Research Assistant.
Provides an intuitive interface for document upload, querying, and result display.
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import streamlit as st
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from loguru import logger
except ImportError as e:
    print(f"Import warning: {e}")
    # Re-raise the error instead of setting st = None
    raise ImportError(f"Required packages not installed: {e}")

from config.settings import settings
from src.ingestion.document_processor import DocumentProcessorFactory, process_document

# Use unified pipeline that handles all vector store implementations
try:
    from src.ingestion.unified_pipeline import UnifiedDocumentIngestionPipeline as DocumentIngestionPipeline
    VECTOR_STORE_TYPE = "Unified"
    logger.info("Using unified document ingestion pipeline")
except ImportError as e:
    logger.error(f"Failed to import unified pipeline: {e}")
    # Fallback to direct import attempts
    try:
        from src.ingestion.vector_store import DocumentIngestionPipeline
        VECTOR_STORE_TYPE = "ChromaDB"
    except (ImportError, RuntimeError) as e:
        logger.warning(f"ChromaDB not available ({e}), using alternative vector store")
        from src.ingestion.alternative_vector_store import create_alternative_vector_store
        VECTOR_STORE_TYPE = "Alternative"
    
from src.generation.legal_rag import LegalResponseGenerator, ResponseFormatter
from src.evaluation.metrics import PerformanceEvaluator
from src.utils import validate_file_type, format_file_size


class LegalResearchUI:
    """Main UI class for the Legal Research Assistant."""
    
    def __init__(self):
        """Initialize the UI."""
        self.setup_page_config()
        self.initialize_session_state()
        self.ingestion_pipeline = None
        self.response_generator = None
        self.performance_evaluator = PerformanceEvaluator()
    
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="Legal Research Assistant",
            page_icon="⚖️",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Add CSS to help with browser extension conflicts
        st.markdown("""
            <style>
            /* Hide elements that might conflict with browser extensions */
            iframe[src*="extension"] { display: none !important; }
            
            /* Improve file uploader styling */
            .uploadedFile { 
                border: 2px dashed #cccccc;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                margin: 10px 0;
            }
            
            /* Custom styling for better UX */
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            
            /* Hide Streamlit menu and footer for cleaner look */
            #MainMenu { visibility: hidden; }
            footer { visibility: hidden; }
            header { visibility: hidden; }
            </style>
        """, unsafe_allow_html=True)
    
    def initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        if 'initialized' not in st.session_state:
            st.session_state.initialized = True
            st.session_state.uploaded_documents = []
            st.session_state.query_history = []
            st.session_state.current_response = None
            st.session_state.vector_store_status = "Not initialized"
            st.session_state.processing_status = ""
    
    def run(self):
        """Run the main UI application."""
        self.render_header()
        self.render_sidebar()
        self.render_main_content()
        self.render_footer()
    
    def render_header(self):
        """Render the application header."""
        st.title("⚖️ Legal Research Assistant")
        st.markdown("""
        **Advanced RAG System for Legal Document Analysis**
        
        Upload legal documents (PDF, DOCX, TXT) and ask questions to get contextual answers 
        with proper citations and conflict detection.
        """)
        
        # Status indicators
        col1, col2, col3 = st.columns(3)
        
        with col1:
            doc_count = len(st.session_state.uploaded_documents)
            st.metric("Documents Uploaded", doc_count)
        
        with col2:
            query_count = len(st.session_state.query_history)
            st.metric("Queries Processed", query_count)
        
        with col3:
            status = st.session_state.vector_store_status
            st.metric("Vector Store", status)
    
    def render_sidebar(self):
        """Render the sidebar with controls and settings."""
        with st.sidebar:
            st.header("📁 Document Management")
            
            # File upload section
            self.render_file_upload()
            
            # Document list
            self.render_document_list()
            
            # Settings section
            st.header("⚙️ Settings")
            self.render_settings()
            
            # System status
            st.header("📊 System Status")
            self.render_system_status()
    
    def render_file_upload(self):
        """Render file upload interface."""
        st.subheader("Upload Legal Documents")
        
        uploaded_files = st.file_uploader(
            "Choose files",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help="Upload PDF, DOCX, or TXT files containing legal documents"
        )
        
        if uploaded_files:
            if st.button("Process Documents", type="primary"):
                self.process_uploaded_files(uploaded_files)
        
        # Clear documents button
        if st.session_state.uploaded_documents:
            if st.button("Clear All Documents", type="secondary"):
                self.clear_all_documents()
    
    def render_document_list(self):
        """Render list of uploaded documents."""
        if st.session_state.uploaded_documents:
            st.subheader("Uploaded Documents")
            
            for i, doc in enumerate(st.session_state.uploaded_documents):
                with st.expander(f"📄 {doc['filename']}"):
                    st.write(f"**Type:** {doc['file_type']}")
                    st.write(f"**Size:** {format_file_size(doc['file_size'])}")
                    st.write(f"**Sections:** {doc['section_count']}")
                    st.write(f"**Tokens:** {doc['token_count']:,}")
                    
                    if st.button(f"Remove {doc['filename']}", key=f"remove_{i}"):
                        self.remove_document(i)
                        st.rerun()
    
    def render_settings(self):
        """Render application settings."""
        # API Provider info
        st.subheader("API Provider")
        provider_icon = "🤖" if settings.api_provider == "gemini" else "🔥"
        st.info(f"{provider_icon} Using {settings.api_provider.title()} API")
        
        if settings.api_provider == "gemini" and not settings.gemini_api_key:
            st.error("⚠️ Gemini API key not configured!")
            st.text("Please add your Gemini API key to the .env file")
        elif settings.api_provider == "openai" and not settings.openai_api_key:
            st.error("⚠️ OpenAI API key not configured!")
            st.text("Please add your OpenAI API key to the .env file")
        
        # Retrieval settings
        st.subheader("Retrieval Settings")
        
        top_k = st.slider(
            "Number of documents to retrieve",
            min_value=1, max_value=20, 
            value=settings.top_k_retrievals,
            help="Number of relevant documents to retrieve for each query"
        )
        
        similarity_threshold = st.slider(
            "Similarity threshold",
            min_value=0.0, max_value=1.0, 
            value=settings.similarity_threshold,
            step=0.1,
            help="Minimum similarity score for document retrieval"
        )
        
        # Generation settings
        st.subheader("Generation Settings")
        
        temperature = st.slider(
            "Response creativity",
            min_value=0.0, max_value=1.0,
            value=settings.temperature,
            step=0.1,
            help="Higher values make responses more creative but less focused"
        )
        
        max_tokens = st.slider(
            "Maximum response length",
            min_value=500, max_value=4000,
            value=settings.max_output_tokens,
            step=100,
            help="Maximum number of tokens in the response"
        )
        
        # Update settings (in a real app, you'd save these)
        if st.button("Update Settings"):
            st.success("Settings updated!")
    
    def render_system_status(self):
        """Render system status information."""
        # Vector store status
        if hasattr(self, 'ingestion_pipeline') and self.ingestion_pipeline:
            try:
                # Get collection info from unified pipeline
                collection_info = self.ingestion_pipeline.get_collection_info()
                st.write(f"**Vector Store:** {collection_info.get('vector_store_type', 'Unknown')}")
                st.write(f"**Status:** {collection_info.get('status', 'Unknown')}")
                
                doc_count = collection_info.get('document_count', 'Unknown')
                if doc_count != 'Unknown':
                    st.write(f"**Documents in DB:** {doc_count}")
                else:
                    st.write(f"**Documents in DB:** Unable to retrieve count")
                    
                if 'error' in collection_info:
                    st.error(f"Error: {collection_info['error']}")
                    
            except Exception as e:
                st.write(f"**Status:** Error retrieving status: {e}")
        else:
            st.write("**Status:** Not initialized")
        
        # Processing status
        if st.session_state.processing_status:
            st.info(st.session_state.processing_status)
    
    def render_main_content(self):
        """Render the main content area."""
        # Query interface
        self.render_query_interface()
        
        # Results display
        if st.session_state.current_response:
            self.render_response_display()
        
        # Query history
        if st.session_state.query_history:
            self.render_query_history()
    
    def render_query_interface(self):
        """Render the query input interface."""
        st.header("🔍 Ask a Legal Question")
        
        # Sample queries
        with st.expander("💡 Sample Questions"):
            sample_queries = [
                "What are the termination clauses in the contract?",
                "What are the liability limitations?",
                "What are the intellectual property rights mentioned?",
                "What are the payment terms and conditions?",
                "Are there any conflict resolution mechanisms?",
                "What are the confidentiality obligations?"
            ]
            
            for query in sample_queries:
                if st.button(f"📝 {query}", key=f"sample_{hash(query)}"):
                    st.session_state.current_query = query
        
        # Query input
        query = st.text_area(
            "Enter your legal question:",
            value=st.session_state.get('current_query', ''),
            height=100,
            placeholder="e.g., What are the termination conditions in the employment contract?"
        )
        
        # Advanced options
        with st.expander("⚙️ Advanced Options"):
            col1, col2 = st.columns(2)
            
            with col1:
                document_filter = st.multiselect(
                    "Filter by document type",
                    options=['PDF', 'DOCX', 'TXT'],
                    help="Only search in documents of selected types"
                )
            
            with col2:
                include_citations = st.checkbox(
                    "Include detailed citations",
                    value=True,
                    help="Include detailed section references in the response"
                )
        
        # Search button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("🔍 Search Legal Documents", type="primary", use_container_width=True):
                if query.strip():
                    if st.session_state.uploaded_documents:
                        self.process_query(query, document_filter, include_citations)
                    else:
                        st.warning("Please upload legal documents first!")
                else:
                    st.warning("Please enter a question!")
    
    def render_response_display(self):
        """Render the response display area."""
        response = st.session_state.current_response
        
        st.header("📋 Analysis Results")
        
        # Response overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Sources Found", len(response.get('sources', [])))
        
        with col2:
            st.metric("Citations", len(response.get('citations', [])))
        
        with col3:
            conflicts = "Yes" if response.get('has_conflicts', False) else "No"
            st.metric("Conflicts Detected", conflicts)
        
        with col4:
            response_time = response.get('response_time_seconds', 0)
            st.metric("Response Time", f"{response_time:.2f}s")
        
        # Main response
        st.subheader("📄 Legal Analysis")
        
        # Format response for display
        formatted_response = ResponseFormatter.format_for_display(response)
        st.markdown(formatted_response['formatted_answer'])
        
        # Sources and citations
        if response.get('sources'):
            with st.expander("📚 Sources"):
                for source in response['sources']:
                    st.write(f"• {source}")
        
        if response.get('citations'):
            with st.expander("📖 Citations"):
                for i, citation in enumerate(response['citations'], 1):
                    st.write(f"{i}. {citation}")
        
        # Conflicts section
        if response.get('has_conflicts'):
            with st.expander("⚠️ Conflicts Detected", expanded=True):
                st.warning("The analysis found conflicting information in the documents.")
                
                for conflict in response.get('conflicts', []):
                    st.write(f"**Conflict Type:** {conflict.get('type', 'Unknown')}")
                    st.write(f"**Between Documents:** {', '.join(conflict.get('documents', []))}")
                    if conflict.get('keywords'):
                        st.write(f"**Key Terms:** {', '.join(conflict.get('keywords', []))}")
                    st.write("---")
        
        # Download response
        if st.button("💾 Download Analysis"):
            self.download_response(response)
    
    def render_query_history(self):
        """Render query history section."""
        with st.expander("📜 Query History"):
            st.subheader("Previous Queries")
            
            for i, entry in enumerate(reversed(st.session_state.query_history[-10:])):
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Q:** {entry['query']}")
                        st.write(f"**Time:** {entry['timestamp']}")
                    
                    with col2:
                        if st.button(f"View Response", key=f"history_{i}"):
                            st.session_state.current_response = entry['response']
                            st.rerun()
                    
                    st.divider()
    
    def render_footer(self):
        """Render application footer."""
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: #666;'>
                Legal Research Assistant v1.0.0 | Built with Streamlit, LangChain & OpenAI
            </div>
            """,
            unsafe_allow_html=True
        )
    
    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files and add to vector store."""
        # Initialize ingestion pipeline with error handling
        if not self.ingestion_pipeline:
            try:
                # Ensure event loop for Streamlit thread
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    # No event loop in current thread, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                self.ingestion_pipeline = DocumentIngestionPipeline()
                st.success("✅ Document processing pipeline initialized")
            except Exception as e:
                st.error(f"❌ Failed to initialize document processing pipeline: {e}")
                if logger:
                    logger.error(f"Pipeline initialization error: {e}")
                return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_docs = []
        total_files = len(uploaded_files)
        
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                # Update progress
                progress = (i + 1) / total_files
                progress_bar.progress(progress)
                status_text.text(f"Processing {uploaded_file.name}...")
                
                # Validate file type
                if not validate_file_type(uploaded_file.name):
                    st.error(f"Unsupported file type: {uploaded_file.name}")
                    continue
                
                # Check file size
                if uploaded_file.size > settings.max_file_size_mb * 1024 * 1024:
                    st.error(f"File too large: {uploaded_file.name} ({format_file_size(uploaded_file.size)})")
                    continue
                
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                try:
                    # Process document
                    result = self.ingestion_pipeline.ingest_file(tmp_file_path)
                    
                    if result['success']:
                        doc_info = {
                            'filename': uploaded_file.name,
                            'file_type': Path(uploaded_file.name).suffix.upper()[1:],
                            'file_size': uploaded_file.size,
                            'document_id': result['document_id'],
                            'section_count': result['sections_added'],
                            'token_count': result['total_tokens']
                        }
                        
                        processed_docs.append(doc_info)
                        st.session_state.uploaded_documents.append(doc_info)
                    else:
                        st.error(f"Failed to process {uploaded_file.name}: {result.get('error', 'Unknown error')}")
                
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(tmp_file_path)
                    except:
                        pass
            
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        
        # Update status
        progress_bar.progress(1.0)
        status_text.text("Processing complete!")
        
        if processed_docs:
            st.success(f"Successfully processed {len(processed_docs)} documents!")
            st.session_state.vector_store_status = "Ready"
        
        # Initialize response generator if not already done
        # Initialize response generator with event loop handling
        if not self.response_generator:
            try:
                # Ensure event loop for Streamlit thread
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    # No event loop in current thread, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                self.response_generator = LegalResponseGenerator()
            except Exception as e:
                st.error(f"❌ Failed to initialize response generator: {e}")
                if logger:
                    logger.error(f"Response generator initialization error: {e}")
                return
    
    def process_query(self, query: str, document_filter: List[str], include_citations: bool):
        """Process a user query and generate response."""
        # Initialize response generator with event loop handling
        if not self.response_generator:
            try:
                # Ensure event loop for Streamlit thread
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    # No event loop in current thread, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Use the same vector store from ingestion pipeline
                if self.ingestion_pipeline and hasattr(self.ingestion_pipeline, 'vector_store'):
                    from src.retrieval.retriever import LegalDocumentRetriever
                    retriever = LegalDocumentRetriever(self.ingestion_pipeline.vector_store)
                    self.response_generator = LegalResponseGenerator(retriever=retriever)
                    if logger:
                        logger.info("Response generator initialized with shared vector store")
                else:
                    self.response_generator = LegalResponseGenerator()
                    if logger:
                        logger.warning("Response generator initialized with new vector store")
            except Exception as e:
                st.error(f"❌ Failed to initialize response generator: {e}")
                if logger:
                    logger.error(f"Response generator initialization error: {e}")
                return
        
        try:
            # Show processing indicator
            with st.spinner("Analyzing legal documents..."):
                # Measure performance
                start_time = time.time()
                
                # Generate response
                response = self.response_generator.generate_response(
                    question=query,
                    document_filters={'document_type': document_filter} if document_filter else None
                )
                
                # Measure latency
                latency_data = self.performance_evaluator.measure_end_to_end_latency(
                    query, self.response_generator
                )
            
            # Store response and history
            st.session_state.current_response = response
            
            query_entry = {
                'query': query,
                'response': response,
                'timestamp': response.get('timestamp', ''),
                'latency': latency_data
            }
            
            st.session_state.query_history.append(query_entry)
            
            # Clear current query
            if 'current_query' in st.session_state:
                del st.session_state.current_query
            
            st.rerun()
        
        except Exception as e:
            st.error(f"Error processing query: {str(e)}")
    
    def clear_all_documents(self):
        """Clear all uploaded documents."""
        if self.ingestion_pipeline and hasattr(self.ingestion_pipeline.vector_store, 'clear_collection'):
            self.ingestion_pipeline.vector_store.clear_collection()
        
        st.session_state.uploaded_documents = []
        st.session_state.vector_store_status = "Cleared"
        st.success("All documents cleared!")
        st.rerun()
    
    def remove_document(self, index: int):
        """Remove a specific document."""
        if 0 <= index < len(st.session_state.uploaded_documents):
            doc = st.session_state.uploaded_documents[index]
            st.session_state.uploaded_documents.pop(index)
            st.success(f"Removed {doc['filename']}")
    
    def download_response(self, response: Dict[str, Any]):
        """Provide download functionality for response."""
        # Create downloadable content
        download_content = {
            'query': response['question'],
            'answer': response['answer'],
            'sources': response.get('sources', []),
            'citations': response.get('citations', []),
            'conflicts': response.get('conflicts', []),
            'timestamp': response.get('timestamp', ''),
            'metadata': {
                'response_time': response.get('response_time_seconds', 0),
                'model_used': response.get('model_used', ''),
                'has_conflicts': response.get('has_conflicts', False)
            }
        }
        
        json_content = json.dumps(download_content, indent=2)
        
        st.download_button(
            label="📥 Download as JSON",
            data=json_content,
            file_name=f"legal_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )


def main():
    """Main entry point for the Streamlit app."""
    try:
        app = LegalResearchUI()
        app.run()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        print(f"Application error: {str(e)}")


if __name__ == "__main__":
    main()
