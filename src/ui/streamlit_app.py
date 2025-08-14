import streamlit as st
import sys
import os
from pathlib import Path
import json
import tempfile
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import our modules
try:
    from src.ingestion.vector_store import DocumentIngestionPipeline
    from src.generation.legal_rag import LegalResponseGenerator
    from src.evaluation.metrics import PerformanceEvaluator
    try:
        from config.settings import settings
    except ImportError:
        # Create minimal settings fallback
        class MockSettings:
            gemini_api_key = ""
            openai_api_key = ""
        settings = MockSettings()
    
    try:
        from src.utils import validate_file_type, format_file_size
    except ImportError:
        # Create utility fallbacks
        def validate_file_type(filename):
            return filename.endswith(('.pdf', '.docx', '.txt'))
        def format_file_size(size_bytes):
            return f"{size_bytes/1024:.1f} KB"
except ImportError as e:
    print(f"Import error: {e}")
    st.error(f"Failed to import required modules: {e}")
    # Create minimal fallbacks with basic functionality
    class DocumentIngestionPipeline:
        def __init__(self, vector_store_manager=None):
            self.vector_store = None
        def ingest_file(self, file_path):
            return {"status": "error", "message": "Service unavailable"}
        def get_collection_info(self):
            return {"documents": 0, "status": "unavailable"}
    
    class LegalResponseGenerator:
        def __init__(self, vector_store=None, api_provider=None):
            pass
        def generate_response(self, query, **kwargs):
            return {"response": "Service temporarily unavailable. Please try again later.", "sources": []}
    
    class PerformanceEvaluator:
        def __init__(self):
            self.performance_logs = []
        def measure_end_to_end_latency(self, query, response_generator):
            return {"latency": 0, "status": "unavailable"}
    
    def validate_file_type(filename):
        return filename.endswith(('.pdf', '.docx', '.txt'))
    def format_file_size(size_bytes):
        return f"{size_bytes/1024:.1f} KB"

# Get logger
try:
    from loguru import logger
except:
    logger = None

# Page config
st.set_page_config(
    page_title="Legal Research Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Minimal Material Design CSS
st.markdown("""
<style>
/* Import Google Inter font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Root variables */
:root {
    --primary-color: #1976d2;
    --primary-hover: #1565c0;
    --background: #fafafa;
    --surface: #ffffff;
    --text-primary: #212121;
    --text-secondary: #757575;
    --border-light: #e0e0e0;
    --success: #4caf50;
    --warning: #ff9800;
    --error: #f44336;
    --shadow: 0 2px 4px rgba(0,0,0,0.1);
    --shadow-hover: 0 4px 8px rgba(0,0,0,0.15);
}

/* Global styles */
.stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: var(--background);
}

/* Hide Streamlit default elements */
#MainMenu, .stDeployButton, footer, header {display: none !important;}

/* Minimal header */
.minimal-header {
    background: var(--surface);
    padding: 20px 24px;
    margin: -1rem -1rem 2rem -1rem;
    border-bottom: 1px solid var(--border-light);
    box-shadow: var(--shadow);
}

.minimal-header h1 {
    color: var(--text-primary);
    font-size: 24px;
    font-weight: 600;
    margin: 0;
    line-height: 1.2;
}

.minimal-header p {
    color: var(--text-secondary);
    margin: 4px 0 0 0;
    font-size: 14px;
}

/* Material cards */
.material-card {
    background: var(--surface);
    border-radius: 8px;
    padding: 24px;
    margin: 16px 0;
    border: 1px solid var(--border-light);
    box-shadow: var(--shadow);
    transition: box-shadow 0.2s ease;
}

.material-card:hover {
    box-shadow: var(--shadow-hover);
}

/* Section headers */
.section-header {
    color: var(--text-primary);
    font-size: 18px;
    font-weight: 600;
    margin: 0 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--primary-color);
}

/* Clean metrics */
.metric-minimal {
    background: var(--surface);
    border: 1px solid var(--border-light);
    border-radius: 6px;
    padding: 16px;
    text-align: center;
}

.metric-minimal h3 {
    color: var(--primary-color);
    font-size: 24px;
    font-weight: 700;
    margin: 0;
}

.metric-minimal p {
    color: var(--text-secondary);
    font-size: 12px;
    margin: 4px 0 0 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Status indicators */
.status-clean {
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    border-radius: 16px;
    font-size: 12px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.status-ready {
    background: rgba(76, 175, 80, 0.1);
    color: var(--success);
}

.status-empty {
    background: rgba(117, 117, 117, 0.1);
    color: var(--text-secondary);
}

/* Button overrides */
.stButton button {
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 24px;
    font-weight: 500;
    transition: all 0.2s ease;
}

.stButton button:hover {
    background: var(--primary-hover);
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
}

/* Form elements */
.stTextArea textarea, .stTextInput input {
    border: 1px solid var(--border-light) !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color 0.2s ease !important;
}

.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.1) !important;
}

/* File uploader */
.stFileUploader > div {
    border: 2px dashed var(--border-light);
    border-radius: 8px;
    padding: 24px;
    text-align: center;
    transition: border-color 0.2s ease;
}

.stFileUploader > div:hover {
    border-color: var(--primary-color);
}

/* Sidebar styling */
.css-1d391kg {
    background: var(--surface);
    border-right: 1px solid var(--border-light);
}

/* Response styling */
.response-container {
    background: var(--surface);
    border-left: 4px solid var(--primary-color);
    padding: 20px;
    border-radius: 0 8px 8px 0;
    margin: 16px 0;
}

/* Document grid */
.doc-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin: 16px 0;
}

.doc-item {
    background: var(--surface);
    border: 1px solid var(--border-light);
    border-radius: 8px;
    padding: 16px;
    transition: all 0.2s ease;
}

.doc-item:hover {
    border-color: var(--primary-color);
    box-shadow: var(--shadow);
}

/* Responsive design */
@media (max-width: 768px) {
    .minimal-header {
        padding: 16px;
        margin: -1rem -1rem 1rem -1rem;
    }
    
    .material-card {
        padding: 16px;
        margin: 12px 0;
    }
    
    .doc-grid {
        grid-template-columns: 1fr;
    }
}
</style>
""", unsafe_allow_html=True)

class LegalResearchUI:
    """Streamlit UI for Legal Research Assistant with minimal Material Design."""
    
    def __init__(self):
        self.init_session_state()
        self.ingestion_pipeline = None
        self.response_generator = None
        self.performance_evaluator = PerformanceEvaluator()
    
    def init_session_state(self):
        """Initialize session state variables."""
        if 'uploaded_documents' not in st.session_state:
            st.session_state.uploaded_documents = []
        if 'query_history' not in st.session_state:
            st.session_state.query_history = []
        if 'current_response' not in st.session_state:
            st.session_state.current_response = None
        if 'vector_store_status' not in st.session_state:
            st.session_state.vector_store_status = "Empty"
    
    def render_header(self):
        """Render the minimal header."""
        st.markdown("""
        <div class="minimal-header">
            <h1>⚖️ Legal Research Assistant</h1>
            <p>Upload legal documents and ask intelligent questions</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """Render the sidebar with document management."""
        with st.sidebar:
            st.markdown('<div class="section-header">📁 Document Library</div>', unsafe_allow_html=True)
            
            # Status indicator
            status_class = "status-ready" if st.session_state.uploaded_documents else "status-empty"
            status_text = "Ready" if st.session_state.uploaded_documents else "Empty"
            
            st.markdown(f"""
            <div class="status-clean {status_class}">
                {status_text} • {len(st.session_state.uploaded_documents)} docs
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # File upload
            uploaded_files = st.file_uploader(
                "Upload Documents",
                type=['pdf', 'docx', 'txt'],
                accept_multiple_files=True,
                help="Supported: PDF, DOCX, TXT"
            )
            
            if uploaded_files:
                if st.button("📤 Process Documents", use_container_width=True):
                    self.process_uploaded_files(uploaded_files)
            
            # Document list
            if st.session_state.uploaded_documents:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**Uploaded Documents:**")
                
                for i, doc in enumerate(st.session_state.uploaded_documents):
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.text(f"📄 {doc['filename']}")
                            st.caption(f"{doc['file_type']} • {format_file_size(doc['file_size'])}")
                        with col2:
                            if st.button("🗑️", key=f"remove_{i}", help="Remove document"):
                                self.remove_document(i)
                                st.rerun()
                
                if st.button("🗑️ Clear All", use_container_width=True, type="secondary"):
                    self.clear_all_documents()
    
    def render_query_interface(self):
        """Render the query interface."""
        st.markdown('<div class="material-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">🔍 Ask a Question</div>', unsafe_allow_html=True)
        
        if not st.session_state.uploaded_documents:
            st.info("👈 Please upload documents first to enable queries.")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        # Query input
        query = st.text_area(
            "Legal Question",
            placeholder="What are the key provisions regarding contract termination?",
            help="Ask specific legal questions about your uploaded documents"
        )
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Document filter
            doc_types = list(set(doc['file_type'] for doc in st.session_state.uploaded_documents))
            selected_types = st.multiselect(
                "Filter Documents",
                options=doc_types,
                default=doc_types,
                help="Select document types to include in search"
            )
        
        with col2:
            include_citations = st.checkbox("Include Citations", value=True)
        
        # Submit button
        if st.button("🔍 Analyze", use_container_width=True, disabled=not query.strip()):
            if query.strip():
                self.process_query(query.strip(), selected_types, include_citations)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_response_display(self):
        """Render the current response."""
        if st.session_state.current_response:
            response = st.session_state.current_response
            
            st.markdown('<div class="material-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-header">📋 Analysis Result</div>', unsafe_allow_html=True)
            
            # Response content
            st.markdown('<div class="response-container">', unsafe_allow_html=True)
            st.markdown(response.get('answer', 'No answer provided.'))
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Metadata
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown('<div class="metric-minimal">', unsafe_allow_html=True)
                st.markdown(f'<h3>{response.get("response_time_seconds", 0):.1f}s</h3>', unsafe_allow_html=True)
                st.markdown('<p>Response Time</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                sources_count = len(response.get('sources', []))
                st.markdown('<div class="metric-minimal">', unsafe_allow_html=True)
                st.markdown(f'<h3>{sources_count}</h3>', unsafe_allow_html=True)
                st.markdown('<p>Sources</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col3:
                conflicts = response.get('has_conflicts', False)
                conflict_text = "Yes" if conflicts else "No"
                st.markdown('<div class="metric-minimal">', unsafe_allow_html=True)
                st.markdown(f'<h3>{conflict_text}</h3>', unsafe_allow_html=True)
                st.markdown('<p>Conflicts</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Sources
            if response.get('sources'):
                with st.expander("📚 Sources", expanded=False):
                    for i, source in enumerate(response['sources'], 1):
                        st.markdown(f"**{i}.** {source.get('content', 'No content')}")
                        st.caption(f"Document: {source.get('document_id', 'Unknown')}")
            
            # Citations
            if response.get('citations'):
                with st.expander("📎 Citations", expanded=False):
                    for citation in response['citations']:
                        st.markdown(f"• {citation}")
            
            # Download option
            self.download_response(response)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    def render_query_history(self):
        """Render query history."""
        if st.session_state.query_history:
            st.markdown('<div class="material-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-header">📈 Query History</div>', unsafe_allow_html=True)
            
            for i, entry in enumerate(reversed(st.session_state.query_history[-5:]), 1):
                with st.expander(f"Query {len(st.session_state.query_history) - i + 1}: {entry['query'][:50]}..."):
                    st.markdown(f"**Question:** {entry['query']}")
                    st.markdown(f"**Answer:** {entry['response'].get('answer', 'No answer')[:200]}...")
                    st.caption(f"Time: {entry['timestamp']}")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files and add to vector store."""
        # Always check session state first to avoid recreating pipeline
        if 'ingestion_pipeline' in st.session_state and st.session_state.ingestion_pipeline is not None:
            self.ingestion_pipeline = st.session_state.ingestion_pipeline
            if logger:
                logger.info("Reusing existing ingestion pipeline from session state")
        
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
                # Persist pipeline for reuse across reruns IMMEDIATELY
                st.session_state.ingestion_pipeline = self.ingestion_pipeline
                if logger:
                    logger.info(f"Created new ingestion pipeline and stored in session state")
                    logger.info(f"Pipeline vector store ID: {id(self.ingestion_pipeline.vector_store)}")
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
                    
                    # Debug: Log the actual result
                    if logger:
                        logger.info(f"Document processing result for {uploaded_file.name}: {result}")
                    
                    # Check if result is a dictionary and has the expected structure
                    if isinstance(result, dict) and (result.get('success') or 'document_id' in result):
                        # Handle both success result format and direct document_id format
                        doc_id = result.get('document_id') if 'document_id' in result else result.get('filename', uploaded_file.name)
                        sections_count = result.get('sections_added', result.get('section_count', 0))
                        tokens_count = result.get('total_tokens', result.get('token_count', 0))
                        
                        doc_info = {
                            'filename': uploaded_file.name,
                            'file_type': Path(uploaded_file.name).suffix.upper()[1:],
                            'file_size': uploaded_file.size,
                            'document_id': doc_id,
                            'section_count': sections_count,
                            'token_count': tokens_count
                        }
                        
                        processed_docs.append(doc_info)
                        st.session_state.uploaded_documents.append(doc_info)
                        st.success(f"✅ Successfully processed {uploaded_file.name}")
                    else:
                        st.error(f"Failed to process {uploaded_file.name}: Invalid result format - {type(result)} - {result}")
                
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(tmp_file_path)
                    except:
                        pass
            
            except Exception as e:
                error_msg = str(e)
                # Don't show 'success' as an error
                if error_msg.lower() == 'success':
                    st.success(f"✅ Successfully processed {uploaded_file.name}")
                else:
                    st.error(f"Error processing {uploaded_file.name}: {error_msg}")
                    if logger:
                        logger.error(f"Document processing error for {uploaded_file.name}: {error_msg}")
        
        # Update status
        progress_bar.progress(1.0)
        status_text.text("Processing complete!")
        
        if processed_docs:
            st.success(f"Successfully processed {len(processed_docs)} documents!")
            st.session_state.vector_store_status = "Ready"
            # Ensure pipeline is persisted after successful processing
            st.session_state.ingestion_pipeline = self.ingestion_pipeline
        
        # Initialize response generator if not already done
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
                
                # Prefer retriever backed by the shared vector store
                if self.ingestion_pipeline and hasattr(self.ingestion_pipeline, 'vector_store'):
                    try:
                        from src.retrieval.retriever import LegalDocumentRetriever
                        retriever = LegalDocumentRetriever(self.ingestion_pipeline.vector_store)
                        self.response_generator = LegalResponseGenerator(retriever=retriever)
                        if logger:
                            logger.info("Response generator initialized with shared vector store after upload")
                    except ImportError:
                        self.response_generator = LegalResponseGenerator()
                        if logger:
                            logger.warning("Retriever not available, using response generator without shared vector store")
                else:
                    self.response_generator = LegalResponseGenerator()
                    if logger:
                        logger.warning("Response generator initialized without shared vector store after upload")
                # Persist generator for reuse
                st.session_state.response_generator = self.response_generator
            except Exception as e:
                st.error(f"❌ Failed to initialize response generator: {e}")
                if logger:
                    logger.error(f"Response generator initialization error: {e}")
                return
    
    def process_query(self, query: str, document_filter: List[str], include_citations: bool):
        """Process a user query and generate response."""
        # Always check session state first to avoid recreating components
        if 'ingestion_pipeline' in st.session_state and st.session_state.ingestion_pipeline is not None:
            self.ingestion_pipeline = st.session_state.ingestion_pipeline
            if logger:
                logger.info("Reusing ingestion pipeline from session state for query")
        
        if 'response_generator' in st.session_state and st.session_state.response_generator is not None:
            self.response_generator = st.session_state.response_generator
            if logger:
                logger.info("Reusing response generator from session state")
        
        # Debug: Log current state
        if logger:
            logger.info(f"=== Starting query processing for: {query[:50]}... ===")
            logger.info(f"Ingestion pipeline exists: {self.ingestion_pipeline is not None}")
            logger.info(f"Response generator exists: {self.response_generator is not None}")
            
            if self.ingestion_pipeline:
                try:
                    collection_info = self.ingestion_pipeline.get_collection_info()
                    logger.info(f"Vector store document count: {collection_info.get('document_count', 'unknown')}")
                    logger.info(f"Vector store type: {collection_info.get('vector_store_type', 'unknown')}")
                    logger.info(f"Pipeline vector store ID: {id(self.ingestion_pipeline.vector_store)}")
                except Exception as e:
                    logger.error(f"Failed to get collection info: {e}")
        
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
                    try:
                        from src.retrieval.retriever import LegalDocumentRetriever
                        retriever = LegalDocumentRetriever(self.ingestion_pipeline.vector_store)
                        self.response_generator = LegalResponseGenerator(retriever=retriever)
                        if logger:
                            logger.info("Response generator initialized with shared vector store")
                            logger.info(f"Shared vector store ID: {id(self.ingestion_pipeline.vector_store)}")
                    except ImportError:
                        self.response_generator = LegalResponseGenerator()
                        if logger:
                            logger.warning("Retriever not available, using response generator without shared vector store")
                else:
                    self.response_generator = LegalResponseGenerator()
                    if logger:
                        logger.warning("Response generator initialized with new vector store")
                # Persist generator for reuse across reruns IMMEDIATELY
                st.session_state.response_generator = self.response_generator
                if logger:
                    logger.info("Stored response generator in session state")
            except Exception as e:
                st.error(f"❌ Failed to initialize response generator: {e}")
                if logger:
                    logger.error(f"Response generator initialization error: {e}")
                return
        else:
            # Debug: Log existing generator info
            if logger:
                logger.info("Using existing response generator")
                if hasattr(self.response_generator, 'retriever') and hasattr(self.response_generator.retriever, 'vector_store'):
                    logger.info(f"Generator vector store ID: {id(self.response_generator.retriever.vector_store)}")
                    # Try to get document count from the retriever's vector store
                    try:
                        if hasattr(self.response_generator.retriever.vector_store, 'get_document_count'):
                            doc_count = self.response_generator.retriever.vector_store.get_document_count()
                            logger.info(f"Generator's vector store document count: {doc_count}")
                        else:
                            logger.info("Generator's vector store doesn't have get_document_count method")
                    except Exception as e:
                        logger.error(f"Failed to get document count from generator's vector store: {e}")
        
        try:
            # Show processing indicator
            with st.spinner("Analyzing legal documents..."):
                # Measure performance
                start_time = time.time()

                # Generate response with better error handling
                try:
                    response = self.response_generator.generate_response(
                        question=query,
                        document_filters={'document_type': document_filter} if document_filter else None
                    )
                    
                    # Debug: Log the response
                    if logger:
                        logger.info(f"Generated response: {response}")
                    
                    # Validate response structure
                    if not isinstance(response, dict):
                        st.error(f"Invalid response format: {type(response)}")
                        return
                    
                    if 'answer' not in response:
                        st.error(f"Response missing answer: {response}")
                        return
                    
                except Exception as gen_error:
                    st.error(f"Error generating response: {gen_error}")
                    if logger:
                        logger.error(f"Response generation error: {gen_error}")
                    return

                # Store response immediately so we always render something
                st.session_state.current_response = response

                # Measure latency (non-blocking for UI)
                try:
                    latency_data = self.performance_evaluator.measure_end_to_end_latency(
                        query, self.response_generator
                    )
                except Exception as m_err:
                    latency_data = {
                        'query': query,
                        'total_latency': None,
                        'retrieval_latency': None,
                        'generation_latency': None,
                        'timestamp': response.get('timestamp', ''),
                        'note': f'Latency measurement failed: {m_err}'
                    }

            # Store history
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
            if logger:
                logger.error(f"Query processing error: {e}")
    
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
    
    def run(self):
        """Main application entry point."""
        self.render_header()
        
        # Create layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self.render_query_interface()
            self.render_response_display()
            self.render_query_history()
        
        with col2:
            self.render_sidebar()


def main():
    """Main entry point for the Streamlit app."""
    try:
        app = LegalResearchUI()
        app.run()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.write(f"Debug info: {e}")
        print(f"Application error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
