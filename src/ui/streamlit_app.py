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
        # Reuse persisted instances to avoid creating new vector stores on rerun
        self.ingestion_pipeline = st.session_state.get('ingestion_pipeline')
        self.response_generator = st.session_state.get('response_generator')
        self.performance_evaluator = PerformanceEvaluator()
    
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        try:
            st.set_page_config(
                page_title="Legal Research Assistant",
                page_icon="⚖️",
                layout="wide",
                initial_sidebar_state="expanded"
            )
        except Exception as e:
            # Page config might already be set, ignore the error
            pass
        
        # Enhanced CSS for professional UI
        st.markdown("""
            <style>
            /* Import Google Fonts */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            /* Global Styles */
            .main {
                font-family: 'Inter', sans-serif;
                color: #1e293b !important;
            }
            
            /* Ensure all text is dark by default */
            body, .main .block-container, p, div, span, h1, h2, h3, h4, h5, h6 {
                color: #1e293b !important;
            }
            
            /* Override any Streamlit default white text */
            .stMarkdown, .stText, .element-container {
                color: #1e293b !important;
            }
            
            /* Hide Streamlit elements */
            #MainMenu { visibility: hidden; }
            footer { visibility: hidden; }
            header { visibility: hidden; }
            .css-1rs6os { display: none; }
            .css-17ziqus { display: none; }
            
            /* Main container */
            .main .block-container {
                padding-top: 1rem;
                padding-bottom: 1rem;
                max-width: 1200px;
            }
            
            /* Header styling */
            .main-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 2rem;
                border-radius: 15px;
                margin-bottom: 2rem;
                color: white !important;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .main-header h1 {
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                color: white !important;
            }
            
            .main-header p {
                font-size: 1.2rem;
                opacity: 0.9;
                margin-bottom: 0;
                color: white !important;
            }
            
            .main-header * {
                color: white !important;
            }
            
            /* Metrics cards */
            .metric-card {
                background: white;
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                border: 1px solid #f0f2f6;
                text-align: center;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            
            .metric-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.12);
            }
            
            .metric-value {
                font-size: 2rem;
                font-weight: 700;
                color: #667eea;
                margin-bottom: 0.5rem;
            }
            
            .metric-label {
                font-size: 0.9rem;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            /* Upload section */
            .upload-section {
                background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                padding: 2rem;
                border-radius: 15px;
                border: 2px dashed #cbd5e1;
                margin: 1rem 0;
                text-align: center;
                transition: all 0.3s ease;
            }
            
            .upload-section:hover {
                border-color: #667eea;
                background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
            }
            
            /* File uploader styling */
            .stFileUploader > div {
                background: white;
                border-radius: 10px;
                border: 2px dashed #cbd5e1;
                padding: 2rem;
                transition: all 0.3s ease;
            }
            
            .stFileUploader > div:hover {
                border-color: #667eea;
                background: #f8fafc;
            }
            
            /* Buttons */
            .stButton > button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white !important;
                border: none;
                border-radius: 8px;
                padding: 0.6rem 2rem;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }
            
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
                color: white !important;
            }
            
            /* Secondary button */
            .stButton[data-baseweb="button"]:nth-child(2) > button {
                background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
                box-shadow: 0 4px 15px rgba(248, 113, 113, 0.3);
                color: white !important;
            }
            
            /* Sidebar enhancements */
            .sidebar-header {
                padding: 1rem;
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                border-radius: 12px;
                margin-bottom: 1rem;
                border: 1px solid #e2e8f0;
            }
            
            .document-stats {
                background: #f8fafc;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
                border: 1px solid #e2e8f0;
            }
            
            .stat-row {
                display: flex;
                align-items: center;
                margin: 0.5rem 0;
                font-size: 0.9rem;
            }
            
            .stat-icon {
                width: 20px;
                margin-right: 8px;
            }
            
            .stat-label {
                flex: 1;
                color: #64748b;
                font-weight: 500;
            }
            
            .stat-value {
                color: #1e293b;
                font-weight: 600;
            }
            
            .collection-metrics {
                background: #f0f9ff;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
                border: 1px solid #bae6fd;
            }
            
            .metric-row {
                display: flex;
                align-items: center;
                margin: 0.5rem 0;
                font-size: 0.9rem;
            }
            
            .metric-icon {
                width: 20px;
                margin-right: 8px;
            }
            
            .metric-text {
                color: #0369a1;
            }
            
            /* Query section */
            .query-section {
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                border: 1px solid #f0f2f6;
                margin: 2rem 0;
            }
            
            /* Response section */
            .response-section {
                background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
                padding: 2rem;
                border-radius: 15px;
                border-left: 4px solid #667eea;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                margin: 2rem 0;
            }
            
            /* Sample questions */
            .sample-questions {
                background: #f8fafc;
                padding: 1.5rem;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
                margin: 1rem 0;
            }
            
            /* Document cards */
            .document-card {
                background: white;
                padding: 1.5rem;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
                margin: 1rem 0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
                transition: all 0.3s ease;
            }
            
            .document-card:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
            
            /* Status indicators */
            .status-success {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white !important;
                padding: 0.8rem 1.5rem;
                border-radius: 8px;
                font-weight: 600;
            }
            
            .status-success * {
                color: white !important;
            }
            
            .status-warning {
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                color: white !important;
                padding: 0.8rem 1.5rem;
                border-radius: 8px;
                font-weight: 600;
            }
            
            .status-warning * {
                color: white !important;
            }
            
            .status-info {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white !important;
                padding: 0.8rem 1.5rem;
                border-radius: 8px;
                font-weight: 600;
            }
            
            .status-info * {
                color: white !important;
            }
            
            /* Sidebar styling */
            .css-1d391kg {
                background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .css-1d391kg .sidebar-content {
                color: white;
            }
            
            /* Text area styling */
            .stTextArea > div > div > textarea {
                border-radius: 8px;
                border: 2px solid #e2e8f0;
                padding: 1rem;
                font-size: 1rem;
                transition: border-color 0.3s ease;
            }
            
            .stTextArea > div > div > textarea:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            /* Expander styling */
            .streamlit-expanderHeader {
                background: #f8fafc;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
                padding: 1rem;
                font-weight: 600;
            }
            
            /* Progress bar */
            .stProgress > div > div > div {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            
            /* Custom icons */
            .icon {
                font-size: 1.2rem;
                margin-right: 0.5rem;
            }
            
            /* Animations */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .fade-in {
                animation: fadeIn 0.6s ease-out;
            }
            
            /* Responsive design */
            @media (max-width: 768px) {
                .main-header h1 {
                    font-size: 2rem;
                }
                
                .main-header p {
                    font-size: 1rem;
                }
                
                .metric-card {
                    margin-bottom: 1rem;
                }
            }
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
        try:
            self.render_header()
            
            # Clean sidebar implementation
            self.render_sidebar()
            
            # Main content with fallback upload for reliability
            self.render_main_content()
            
            self.render_footer()
            
        except Exception as e:
            st.error(f"❌ Error in run method: {e}")
            if logger:
                logger.error(f"Run method error: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def render_header(self):
        """Render the application header with enhanced styling."""
        st.markdown("""
            <div class="main-header fade-in">
                <h1>⚖️ Legal Research Assistant</h1>
                <p>Advanced RAG System for Legal Document Analysis</p>
                <p style="font-size: 1rem; margin-top: 1rem; opacity: 0.8;">
                    Upload legal documents and get intelligent answers with proper citations and conflict detection
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Enhanced status indicators with better styling
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            doc_count = len(st.session_state.uploaded_documents)
            st.markdown(f"""
                <div class="metric-card fade-in">
                    <div class="metric-value">📄 {doc_count}</div>
                    <div class="metric-label">Documents</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            query_count = len(st.session_state.query_history)
            st.markdown(f"""
                <div class="metric-card fade-in">
                    <div class="metric-value">🔍 {query_count}</div>
                    <div class="metric-label">Queries</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            status = st.session_state.vector_store_status
            status_color = "🟢" if status == "Ready" else "🟡" if status == "Cleared" else "🔴"
            st.markdown(f"""
                <div class="metric-card fade-in">
                    <div class="metric-value">{status_color}</div>
                    <div class="metric-label">Vector Store</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            # Calculate total tokens if available
            total_tokens = sum(doc.get('token_count', 0) for doc in st.session_state.uploaded_documents)
            st.markdown(f"""
                <div class="metric-card fade-in">
                    <div class="metric-value">🧮 {total_tokens:,}</div>
                    <div class="metric-label">Tokens</div>
                </div>
            """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """Render the enhanced sidebar with beautiful styling."""
        with st.sidebar:
            # Beautiful header
            st.markdown("""
                <div class="sidebar-header fade-in">
                    <h2 style="color: #1e293b; margin: 0; display: flex; align-items: center;">
                        <span class="icon" style="margin-right: 10px;">⚖️</span>Legal Research Hub
                    </h2>
                    <p style="color: #64748b; margin: 0.5rem 0 0 0; font-size: 0.9rem;">
                        AI-Powered Document Analysis
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            # Beautiful divider
            st.markdown("""
                <div style="height: 3px; background: linear-gradient(90deg, #667eea, #764ba2); margin: 1rem 0; border-radius: 2px;"></div>
            """, unsafe_allow_html=True)
            
            # Enhanced document management section
            st.markdown("""
                <h3 style="color: #374151; margin-bottom: 1rem; display: flex; align-items: center;">
                    <span class="icon" style="margin-right: 8px;">📁</span>Document Management
                </h3>
            """, unsafe_allow_html=True)
            
            # File upload section
            self.render_file_upload()
            
            # Document list
            self.render_document_list()
            
            # Settings section
            st.markdown("""
                <div style="height: 1px; background: linear-gradient(90deg, transparent, #e2e8f0, transparent); margin: 1.5rem 0;"></div>
                <h3 style="color: #374151; margin-bottom: 1rem; display: flex; align-items: center;">
                    <span class="icon" style="margin-right: 8px;">⚙️</span>Settings
                </h3>
            """, unsafe_allow_html=True)
            self.render_settings()
            
            # System status section
            st.markdown("""
                <div style="height: 1px; background: linear-gradient(90deg, transparent, #e2e8f0, transparent); margin: 1.5rem 0;"></div>
                <h3 style="color: #374151; margin-bottom: 1rem; display: flex; align-items: center;">
                    <span class="icon" style="margin-right: 8px;">📊</span>System Status
                </h3>
            """, unsafe_allow_html=True)
            self.render_system_status()
            
            # Beautiful footer
            st.markdown("""
                <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;">
                    <p style="color: #9ca3af; font-size: 0.8rem; text-align: center; margin: 0;">
                        Powered by AI • Built with Streamlit
                    </p>
                    <p style="color: #9ca3af; font-size: 0.75rem; text-align: center; margin: 0.25rem 0 0 0;">
                        © 2024 Legal Research Assistant
                    </p>
                </div>
            """, unsafe_allow_html=True)
    
    def render_file_upload(self):
        """Render enhanced file upload interface."""
        st.markdown("""
            <div class="upload-section fade-in">
                <h4 style="color: #374151; margin-bottom: 1rem; display: flex; align-items: center;">
                    <span class="icon" style="margin-right: 8px;">📤</span>Upload Legal Documents
                </h4>
            </div>
        """, unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "Choose files",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help="Upload PDF, DOCX, or TXT files containing legal documents",
            label_visibility="collapsed"
        )
        
        if uploaded_files:
            st.markdown(f"""
                <div class="status-success fade-in">
                    <span class="icon">✅</span>
                    {len(uploaded_files)} file(s) selected
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 Process Documents", type="primary", use_container_width=True):
                self.process_uploaded_files(uploaded_files)
        else:
            st.markdown("""
                <div class="status-info fade-in">
                    <span class="icon">👆</span>
                    Please select files to upload
                </div>
            """, unsafe_allow_html=True)
        
        # Clear documents button with enhanced styling
        if st.session_state.uploaded_documents:
            if st.button("🗑️ Clear All Documents", type="secondary", use_container_width=True):
                self.clear_all_documents()
    
    def render_document_list(self):
        """Render enhanced list of uploaded documents."""
        if st.session_state.uploaded_documents:
            st.markdown("""
                <h4 style="color: #374151; margin: 1.5rem 0 1rem 0; display: flex; align-items: center;">
                    <span class="icon" style="margin-right: 8px;">📄</span>Uploaded Documents
                </h4>
            """, unsafe_allow_html=True)
            
            for i, doc in enumerate(st.session_state.uploaded_documents):
                with st.expander(f"📄 {doc['filename']}", expanded=False):
                    # Enhanced document info display
                    st.markdown(f"""
                        <div class="document-stats">
                            <div class="stat-row">
                                <span class="stat-icon">📋</span>
                                <span class="stat-label">Type:</span>
                                <span class="stat-value">{doc['file_type'].upper()}</span>
                            </div>
                            <div class="stat-row">
                                <span class="stat-icon">📏</span>
                                <span class="stat-label">Size:</span>
                                <span class="stat-value">{format_file_size(doc['file_size'])}</span>
                            </div>
                            <div class="stat-row">
                                <span class="stat-icon">🧩</span>
                                <span class="stat-label">Sections:</span>
                                <span class="stat-value">{doc['section_count']}</span>
                            </div>
                            <div class="stat-row">
                                <span class="stat-icon">🧮</span>
                                <span class="stat-label">Tokens:</span>
                                <span class="stat-value">{doc['token_count']:,}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Enhanced remove button
                    if st.button(f"🗑️ Remove", key=f"remove_{i}", type="secondary", use_container_width=True):
                        self.remove_document(i)
                        st.rerun()
    
    def render_settings(self):
        """Render enhanced application settings."""
        # Enhanced API Provider info
        st.markdown("""
            <h4 style="color: #374151; margin-bottom: 1rem; display: flex; align-items: center;">
                <span class="icon" style="margin-right: 8px;">🔗</span>API Provider
            </h4>
        """, unsafe_allow_html=True)
        
        provider_icon = "🤖" if settings.api_provider == "gemini" else "🔥"
        
        st.markdown(f"""
            <div class="status-info fade-in">
                <span class="icon">{provider_icon}</span>
                Using {settings.api_provider.title()} API
            </div>
        """, unsafe_allow_html=True)
        
        if settings.api_provider == "gemini" and not settings.gemini_api_key:
            st.markdown("""
                <div class="status-warning fade-in">
                    <span class="icon">⚠️</span>
                    Gemini API key not configured!
                </div>
            """, unsafe_allow_html=True)
        elif settings.api_provider == "openai" and not settings.openai_api_key:
            st.markdown("""
                <div class="status-warning fade-in">
                    <span class="icon">⚠️</span>
                    OpenAI API key not configured!
                </div>
            """, unsafe_allow_html=True)
        
        # Enhanced Retrieval settings
        st.markdown("""
            <h4 style="color: #374151; margin: 1.5rem 0 1rem 0; display: flex; align-items: center;">
                <span class="icon" style="margin-right: 8px;">🔍</span>Retrieval Settings
            </h4>
        """, unsafe_allow_html=True)
        
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
        
        # Enhanced Generation settings
        st.markdown("""
            <h4 style="color: #374151; margin: 1.5rem 0 1rem 0; display: flex; align-items: center;">
                <span class="icon" style="margin-right: 8px;">⚡</span>Generation Settings
            </h4>
        """, unsafe_allow_html=True)
        
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
        
        # Enhanced update button
        if st.button("💾 Update Settings", type="secondary", use_container_width=True):
            st.markdown("""
                <div class="status-success fade-in">
                    <span class="icon">✅</span>
                    Settings updated successfully!
                </div>
            """, unsafe_allow_html=True)
    
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
        """Render the main content area with enhanced styling."""
        # Enhanced document upload section
        st.markdown("""
            <div class="upload-section fade-in">
                <h2 style="color: #1e293b; margin-bottom: 1rem;">
                    <span class="icon">📄</span>Document Upload Center
                </h2>
            </div>
        """, unsafe_allow_html=True)
        
        # Check if we have any uploaded documents in session state
        if not st.session_state.uploaded_documents:
            st.markdown("""
                <div class="status-info fade-in">
                    <span class="icon">ℹ️</span>Ready to process your legal documents. 
                    Upload PDF, DOCX, or TXT files to get started with intelligent legal analysis.
                </div>
            """, unsafe_allow_html=True)
            
            # Main content file uploader with enhanced styling
            st.markdown("### 📤 Upload Your Documents")
            main_uploaded_files = st.file_uploader(
                "Choose your legal documents",
                type=['pdf', 'docx', 'txt'],
                accept_multiple_files=True,
                help="📋 Supported formats: PDF, DOCX, TXT • Maximum size: 10MB per file",
                key="main_content_uploader"
            )
            
            if main_uploaded_files:
                # Enhanced file selection display
                st.markdown(f"""
                    <div class="status-success fade-in">
                        <span class="icon">✅</span>
                        {len(main_uploaded_files)} file(s) selected • 
                        Total size: {sum(f.size for f in main_uploaded_files):,} bytes
                    </div>
                """, unsafe_allow_html=True)
                
                # Enhanced button layout
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    if st.button("� Process Documents", type="primary", use_container_width=True):
                        with st.spinner("🔄 Processing your documents..."):
                            self.process_uploaded_files(main_uploaded_files)
                with col2:
                    st.markdown(f"**Files:** {len(main_uploaded_files)}")
                with col3:
                    file_types = list(set(f.name.split('.')[-1].upper() for f in main_uploaded_files))
                    st.markdown(f"**Types:** {', '.join(file_types)}")
        else:
            # Enhanced uploaded documents display
            st.markdown(f"""
                <div class="status-success fade-in">
                    <span class="icon">✅</span>
                    Successfully uploaded {len(st.session_state.uploaded_documents)} documents
                </div>
            """, unsafe_allow_html=True)
            
            # Enhanced document cards
            with st.expander("📋 Manage Uploaded Documents", expanded=True):
                for i, doc in enumerate(st.session_state.uploaded_documents):
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                        with col1:
                            st.markdown(f"""
                                <div class="document-card">
                                    <strong>📄 {doc['filename']}</strong>
                                    <br><small style="color: #64748b;">{doc['file_type']} Document</small>
                                </div>
                            """, unsafe_allow_html=True)
                        with col2:
                            st.metric("Sections", doc['section_count'])
                        with col3:
                            st.metric("Tokens", f"{doc['token_count']:,}")
                        with col4:
                            st.metric("Size", format_file_size(doc['file_size']))
                        with col5:
                            if st.button("🗑️", key=f"remove_main_{i}", help=f"Remove {doc['filename']}", type="secondary"):
                                self.remove_document(i)
                                st.rerun()
                        st.divider()
            
            # Enhanced clear all button
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("🗑️ Clear All Documents", type="secondary", use_container_width=True):
                    self.clear_all_documents()
        
        # Enhanced query interface
        st.markdown("""
            <div class="query-section fade-in">
                <h2 style="color: #1e293b; margin-bottom: 1.5rem;">
                    <span class="icon">🔍</span>Legal Question Analysis
                </h2>
            </div>
        """, unsafe_allow_html=True)
        
        self.render_query_interface()
        
        # Results display with enhanced styling
        if st.session_state.current_response:
            st.markdown("""
                <div class="response-section fade-in">
                    <h2 style="color: #1e293b; margin-bottom: 1.5rem;">
                        <span class="icon">📋</span>Analysis Results
                    </h2>
                </div>
            """, unsafe_allow_html=True)
            self.render_response_display()
        
        # Query history with enhanced styling
        if st.session_state.query_history:
            st.markdown("""
                <div class="query-section fade-in">
                    <h2 style="color: #1e293b; margin-bottom: 1.5rem;">
                        <span class="icon">📜</span>Query History
                    </h2>
                </div>
            """, unsafe_allow_html=True)
            self.render_query_history()
    
    def render_query_interface(self):
        """Render the enhanced query input interface."""
        # Sample queries with better styling
        with st.expander("� Sample Legal Questions", expanded=False):
            st.markdown("""
                <div class="sample-questions">
                    <p style="margin-bottom: 1rem; color: #64748b; font-size: 0.9rem;">
                        Click any question below to use it as a starting point:
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            sample_queries = [
                "What are the termination clauses in the contract?",
                "What are the liability limitations?",
                "What are the intellectual property rights mentioned?",
                "What are the payment terms and conditions?",
                "Are there any conflict resolution mechanisms?",
                "What are the confidentiality obligations?"
            ]
            
            cols = st.columns(2)
            for i, query in enumerate(sample_queries):
                with cols[i % 2]:
                    if st.button(f"📝 {query}", key=f"sample_{hash(query)}", use_container_width=True):
                        st.session_state.current_query = query
                        st.rerun()
        
        # Enhanced query input
        st.markdown("### ✏️ Your Legal Question")
        query = st.text_area(
            "Enter your legal question:",
            value=st.session_state.get('current_query', ''),
            height=120,
            placeholder="e.g., What are the termination conditions in the employment contract?",
            help="💡 Tip: Be specific about what you're looking for. You can ask about clauses, terms, obligations, rights, or any other legal concepts."
        )
        
        # Advanced options with better styling
        with st.expander("⚙️ Advanced Search Options"):
            col1, col2 = st.columns(2)
            
            with col1:
                document_filter = st.multiselect(
                    "📄 Filter by document type",
                    options=['PDF', 'DOCX', 'TXT'],
                    help="Only search in documents of selected types"
                )
            
            with col2:
                include_citations = st.checkbox(
                    "📚 Include detailed citations",
                    value=True,
                    help="Include detailed section references in the response"
                )
        
        # Enhanced search button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            search_disabled = not query.strip() or not st.session_state.uploaded_documents
            button_text = "🔍 Analyze Legal Documents" if not search_disabled else "⚠️ Upload documents first"
            
            if st.button(button_text, type="primary", use_container_width=True, disabled=search_disabled):
                if query.strip():
                    if st.session_state.uploaded_documents:
                        with st.spinner("🔄 Analyzing legal documents..."):
                            self.process_query(query, document_filter, include_citations)
                    else:
                        st.warning("📄 Please upload legal documents first!")
                else:
                    st.warning("✏️ Please enter a question!")
        
        # Help text
        if not st.session_state.uploaded_documents:
            st.markdown("""
                <div class="status-warning fade-in">
                    <span class="icon">⚠️</span>
                    Upload legal documents above before asking questions
                </div>
            """, unsafe_allow_html=True)
    
    def render_response_display(self):
        """Render the enhanced response display area."""
        response = st.session_state.current_response
        
        # Enhanced response overview with beautiful metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            sources_count = len(response.get('sources', []))
            st.markdown(f"""
                <div class="metric-card fade-in">
                    <div class="metric-value" style="color: #059669;">📚 {sources_count}</div>
                    <div class="metric-label">Sources Found</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            citations_count = len(response.get('citations', []))
            st.markdown(f"""
                <div class="metric-card fade-in">
                    <div class="metric-value" style="color: #0284c7;">📖 {citations_count}</div>
                    <div class="metric-label">Citations</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            conflicts = "Yes" if response.get('has_conflicts', False) else "No"
            conflict_color = "#dc2626" if conflicts == "Yes" else "#059669"
            conflict_icon = "⚠️" if conflicts == "Yes" else "✅"
            st.markdown(f"""
                <div class="metric-card fade-in">
                    <div class="metric-value" style="color: {conflict_color};">{conflict_icon} {conflicts}</div>
                    <div class="metric-label">Conflicts</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            response_time = response.get('response_time_seconds', 0)
            st.markdown(f"""
                <div class="metric-card fade-in">
                    <div class="metric-value" style="color: #7c3aed;">⚡ {response_time:.1f}s</div>
                    <div class="metric-label">Response Time</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Enhanced main response
        st.markdown("""
            <h3 style="color: #1e293b; border-bottom: 2px solid #667eea; padding-bottom: 0.5rem;">
                <span class="icon">📄</span>Legal Analysis
            </h3>
        """, unsafe_allow_html=True)
        
        # Format response for display with enhanced styling
        formatted_response = ResponseFormatter.format_for_display(response)
        
        # Display answer in a beautiful container
        st.markdown(f"""
            <div class="response-section fade-in" style="background: white; border-left: 4px solid #10b981;">
                {formatted_response['formatted_answer']}
            </div>
        """, unsafe_allow_html=True)
        
        # Enhanced sections for additional information
        col1, col2 = st.columns(2)
        
        with col1:
            # Sources section with enhanced styling
            if response.get('sources'):
                with st.expander(f"📚 Sources ({len(response['sources'])})", expanded=False):
                    for i, source in enumerate(response['sources'], 1):
                        st.markdown(f"""
                            <div class="document-card">
                                <strong>{i}.</strong> {source}
                            </div>
                        """, unsafe_allow_html=True)
        
        with col2:
            # Citations section with enhanced styling
            if response.get('citations'):
                with st.expander(f"📖 Citations ({len(response['citations'])})", expanded=False):
                    for i, citation in enumerate(response['citations'], 1):
                        st.markdown(f"""
                            <div class="document-card">
                                <strong>{i}.</strong> {citation}
                            </div>
                        """, unsafe_allow_html=True)
        
        # Conflicts section with enhanced warning styling
        if response.get('has_conflicts'):
            with st.expander("⚠️ Conflicts Detected", expanded=True):
                st.markdown("""
                    <div class="status-warning fade-in">
                        <span class="icon">⚠️</span>
                        The analysis found conflicting information in the documents.
                    </div>
                """, unsafe_allow_html=True)
                
                for i, conflict in enumerate(response.get('conflicts', []), 1):
                    st.markdown(f"""
                        <div class="document-card" style="border-left: 4px solid #f59e0b;">
                            <strong>Conflict {i}:</strong><br>
                            <strong>Type:</strong> {conflict.get('type', 'Unknown')}<br>
                            <strong>Between Documents:</strong> {', '.join(conflict.get('documents', []))}<br>
                            {f"<strong>Key Terms:</strong> {', '.join(conflict.get('keywords', []))}" if conflict.get('keywords') else ""}
                        </div>
                    """, unsafe_allow_html=True)
        
        # Enhanced download section
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("💾 Download Analysis", type="secondary", use_container_width=True):
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
                    if isinstance(result, dict) and 'document_id' in result:
                        doc_info = {
                            'filename': uploaded_file.name,
                            'file_type': Path(uploaded_file.name).suffix.upper()[1:],
                            'file_size': uploaded_file.size,
                            'document_id': result.get('document_id', 'unknown'),
                            'section_count': result.get('section_count', 0),
                            'token_count': result.get('token_count', 0)
                        }
                        
                        processed_docs.append(doc_info)
                        st.session_state.uploaded_documents.append(doc_info)
                        st.success(f"✅ Successfully processed {uploaded_file.name}")
                    else:
                        st.error(f"Failed to process {uploaded_file.name}: Invalid result format - {type(result)}")
                
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
                
                # Prefer retriever backed by the shared vector store
                if self.ingestion_pipeline and hasattr(self.ingestion_pipeline, 'vector_store'):
                    from src.retrieval.retriever import LegalDocumentRetriever
                    retriever = LegalDocumentRetriever(self.ingestion_pipeline.vector_store)
                    self.response_generator = LegalResponseGenerator(retriever=retriever)
                    if logger:
                        logger.info("Response generator initialized with shared vector store after upload")
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
                    from src.retrieval.retriever import LegalDocumentRetriever
                    retriever = LegalDocumentRetriever(self.ingestion_pipeline.vector_store)
                    self.response_generator = LegalResponseGenerator(retriever=retriever)
                    if logger:
                        logger.info("Response generator initialized with shared vector store")
                        logger.info(f"Shared vector store ID: {id(self.ingestion_pipeline.vector_store)}")
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
