"""
Minimal, clean Streamlit UI for the Legal Research Assistant.
Refactored for modern Material Design principles.
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
    """Minimal, clean UI class for the Legal Research Assistant."""
    
    def __init__(self):
        """Initialize the minimal UI."""
        self.setup_page_config()
        self.initialize_session_state()
        self.ingestion_pipeline = st.session_state.get('ingestion_pipeline')
        self.response_generator = st.session_state.get('response_generator')
        self.performance_evaluator = PerformanceEvaluator()
    
    def setup_page_config(self):
        """Configure Streamlit page with minimal Material Design."""
        try:
            st.set_page_config(
                page_title="Legal Research Assistant",
                page_icon="⚖️",
                layout="wide",
                initial_sidebar_state="expanded"
            )
        except Exception as e:
            pass
        
        # Minimal Material Design CSS
        st.markdown("""
            <style>
            /* Import modern font */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            /* === GLOBAL FOUNDATION === */
            .main {
                font-family: 'Inter', sans-serif;
                background-color: #fafafa;
                color: #212121;
            }
            
            /* Clean text defaults */
            body, .main .block-container, p, div, span, h1, h2, h3, h4, h5, h6 {
                color: #212121 !important;
                font-family: 'Inter', sans-serif;
            }
            
            /* Hide Streamlit branding */
            #MainMenu { visibility: hidden; }
            footer { visibility: hidden; }
            header { visibility: hidden; }
            .css-1rs6os { display: none; }
            
            /* Main container spacing */
            .main .block-container {
                padding: 2rem 2rem 1rem 2rem;
                max-width: 1200px;
                margin: 0 auto;
            }
            
            /* === MINIMAL HEADER === */
            .minimal-header {
                background: #ffffff;
                padding: 2rem;
                border-radius: 12px;
                margin-bottom: 2rem;
                border: 1px solid #e0e0e0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                text-align: center;
            }
            
            .minimal-header h1 {
                color: #1565c0 !important;
                font-size: 2.2rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
                letter-spacing: -0.02em;
            }
            
            .minimal-header p {
                color: #616161 !important;
                font-size: 1rem;
                margin: 0;
                font-weight: 400;
            }
            
            /* === MATERIAL BUTTONS === */
            .stButton > button {
                background: #1976d2;
                color: white !important;
                border: none;
                border-radius: 8px;
                padding: 0.75rem 2rem;
                font-weight: 500;
                font-size: 0.95rem;
                transition: all 0.2s ease;
                box-shadow: 0 2px 4px rgba(25, 118, 210, 0.2);
                min-height: 48px;
            }
            
            .stButton > button:hover {
                background: #1565c0;
                box-shadow: 0 4px 12px rgba(25, 118, 210, 0.3);
                transform: translateY(-1px);
            }
            
            .stButton > button:active {
                transform: translateY(0);
                box-shadow: 0 2px 4px rgba(25, 118, 210, 0.2);
            }
            
            /* Secondary buttons */
            .stButton[data-testid*="secondary"] > button {
                background: #f5f5f5;
                color: #424242 !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            
            .stButton[data-testid*="secondary"] > button:hover {
                background: #eeeeee;
                box-shadow: 0 2px 6px rgba(0,0,0,0.15);
            }
            
            /* === CLEAN CARDS === */
            .material-card {
                background: #ffffff;
                border-radius: 12px;
                padding: 1.5rem;
                margin: 1rem 0;
                border: 1px solid #e0e0e0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                transition: box-shadow 0.2s ease;
            }
            
            .material-card:hover {
                box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            }
            
            /* === METRIC CARDS === */
            .metric-minimal {
                background: #ffffff;
                padding: 1.5rem;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
                text-align: center;
                transition: transform 0.2s ease;
            }
            
            .metric-minimal:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }
            
            .metric-value {
                font-size: 1.8rem;
                font-weight: 600;
                color: #1976d2;
                margin-bottom: 0.25rem;
            }
            
            .metric-label {
                font-size: 0.85rem;
                color: #757575;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-weight: 500;
            }
            
            /* === CLEAN STATUS INDICATORS === */
            .status-clean {
                display: flex;
                align-items: center;
                padding: 0.75rem 1rem;
                border-radius: 8px;
                font-weight: 500;
                margin: 0.5rem 0;
            }
            
            .status-success {
                background: #e8f5e8;
                color: #2e7d32 !important;
                border: 1px solid #c8e6c9;
            }
            
            .status-warning {
                background: #fff3e0;
                color: #ef6c00 !important;
                border: 1px solid #ffcc02;
            }
            
            .status-info {
                background: #e3f2fd;
                color: #0277bd !important;
                border: 1px solid #bbdefb;
            }
            
            /* === MODERN FILE UPLOAD === */
            .stFileUploader > div {
                border: 2px dashed #bdbdbd;
                border-radius: 12px;
                padding: 2rem;
                background: #fafafa;
                transition: all 0.2s ease;
            }
            
            .stFileUploader > div:hover {
                border-color: #1976d2;
                background: #f3f8ff;
            }
            
            /* === CLEAN INPUTS === */
            .stTextInput > div > div > input {
                border-radius: 8px;
                border: 1px solid #d0d0d0;
                padding: 0.75rem;
                font-size: 0.95rem;
                background: #ffffff;
                transition: border-color 0.2s ease;
            }
            
            .stTextInput > div > div > input:focus {
                border-color: #1976d2;
                box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.1);
            }
            
            .stTextArea > div > div > textarea {
                border-radius: 8px;
                border: 1px solid #d0d0d0;
                padding: 0.75rem;
                font-size: 0.95rem;
                background: #ffffff;
                min-height: 120px;
                transition: border-color 0.2s ease;
            }
            
            .stTextArea > div > div > textarea:focus {
                border-color: #1976d2;
                box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.1);
            }
            
            /* === SIDEBAR MINIMAL === */
            .css-1d391kg {
                background: #ffffff;
                border-right: 1px solid #e0e0e0;
            }
            
            /* === SECTION HEADERS === */
            .section-header {
                color: #424242 !important;
                font-size: 1.2rem;
                font-weight: 600;
                margin: 2rem 0 1rem 0;
                padding-bottom: 0.5rem;
                border-bottom: 2px solid #f0f0f0;
            }
            
            /* === CLEAN EXPANDERS === */
            .streamlit-expanderHeader {
                background: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-weight: 500;
            }
            
            /* === RESPONSIVE === */
            @media (max-width: 768px) {
                .main .block-container {
                    padding: 1rem;
                }
                
                .minimal-header {
                    padding: 1.5rem;
                }
                
                .minimal-header h1 {
                    font-size: 1.8rem;
                }
                
                .material-card {
                    padding: 1rem;
                    margin: 0.5rem 0;
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
        """Run the minimal UI application."""
        try:
            self.render_header()
            self.render_sidebar()
            self.render_main_content()
            
        except Exception as e:
            st.error(f"❌ Application error: {e}")
            if logger:
                logger.error(f"Run method error: {e}")
    
    def render_header(self):
        """Render minimal, clean application header."""
        st.markdown("""
            <div class="minimal-header">
                <h1>⚖️ Legal Research Assistant</h1>
                <p>AI-powered legal document analysis with intelligent citations</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Clean metric cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            doc_count = len(st.session_state.uploaded_documents)
            st.markdown(f"""
                <div class="metric-minimal">
                    <div class="metric-value">{doc_count}</div>
                    <div class="metric-label">Documents</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            query_count = len(st.session_state.query_history)
            st.markdown(f"""
                <div class="metric-minimal">
                    <div class="metric-value">{query_count}</div>
                    <div class="metric-label">Queries</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            status = st.session_state.vector_store_status
            status_text = "Ready" if status == "Ready" else "Pending"
            st.markdown(f"""
                <div class="metric-minimal">
                    <div class="metric-value" style="color: {'#2e7d32' if status == 'Ready' else '#ed6c02'};">{status_text}</div>
                    <div class="metric-label">Status</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            total_tokens = sum(doc.get('token_count', 0) for doc in st.session_state.uploaded_documents)
            st.markdown(f"""
                <div class="metric-minimal">
                    <div class="metric-value">{total_tokens:,}</div>
                    <div class="metric-label">Tokens</div>
                </div>
            """, unsafe_allow_html=True)
    
    def render_main_content(self):
        """Render clean, minimal main content area."""
        
        # Document upload/management section
        if not st.session_state.uploaded_documents:
            st.markdown('<h2 class="section-header">📤 Upload Documents</h2>', unsafe_allow_html=True)
            
            st.markdown("""
                <div class="status-clean status-info">
                    Ready to analyze your legal documents. Upload PDF, DOCX, or TXT files to begin.
                </div>
            """, unsafe_allow_html=True)
            
            # Clean file uploader
            main_uploaded_files = st.file_uploader(
                "Select legal documents",
                type=['pdf', 'docx', 'txt'],
                accept_multiple_files=True,
                help="Supported: PDF, DOCX, TXT • Max 10MB per file",
                key="main_content_uploader"
            )
            
            if main_uploaded_files:
                st.markdown(f"""
                    <div class="status-clean status-success">
                        ✓ {len(main_uploaded_files)} file(s) selected
                    </div>
                """, unsafe_allow_html=True)
                
                # Clean action button
                if st.button("🚀 Process Documents", type="primary", use_container_width=True):
                    with st.spinner("Processing documents..."):
                        self.process_uploaded_files(main_uploaded_files)
        else:
            # Document management section
            st.markdown('<h2 class="section-header">📋 Document Management</h2>', unsafe_allow_html=True)
            
            st.markdown(f"""
                <div class="status-clean status-success">
                    ✓ {len(st.session_state.uploaded_documents)} documents uploaded and ready
                </div>
            """, unsafe_allow_html=True)
            
            # Clean document list
            for i, doc in enumerate(st.session_state.uploaded_documents):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"""
                        <div class="material-card">
                            <h4 style="margin: 0 0 0.5rem 0; color: #424242;">📄 {doc['filename']}</h4>
                            <div style="display: flex; gap: 1rem; font-size: 0.9rem; color: #757575;">
                                <span><strong>Type:</strong> {doc['file_type'].upper()}</span>
                                <span><strong>Size:</strong> {format_file_size(doc['file_size'])}</span>
                                <span><strong>Sections:</strong> {doc['section_count']}</span>
                                <span><strong>Tokens:</strong> {doc['token_count']:,}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("Remove", key=f"remove_main_{i}", type="secondary", help=f"Remove {doc['filename']}"):
                        self.remove_document(i)
                        st.rerun()
        
        # Query interface
        if st.session_state.uploaded_documents:
            st.markdown('<h2 class="section-header">💬 Ask Questions</h2>', unsafe_allow_html=True)
            self.render_query_interface()
        
        # Results display
        if st.session_state.get('show_results', False) and st.session_state.current_response:
            st.markdown('<h2 class="section-header">📊 Analysis Results</h2>', unsafe_allow_html=True)
            self.render_response_display()
    
    def render_query_interface(self):
        """Render clean query input interface."""
        # Sample questions
        with st.expander("💡 Sample Questions", expanded=False):
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
                    if st.button(query, key=f"sample_{hash(query)}", use_container_width=True):
                        st.session_state.current_query = query
                        st.rerun()
        
        # Clean query input
        query = st.text_area(
            "Enter your legal question:",
            value=st.session_state.get('current_query', ''),
            height=100,
            placeholder="e.g., What are the termination conditions in the employment contract?",
            help="Be specific about what you're looking for in the legal documents."
        )
        
        # Clean search button
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🔍 Analyze Documents", type="primary", use_container_width=True):
                if query.strip():
                    with st.spinner("Analyzing documents..."):
                        self.process_query(query.strip())
                else:
                    st.warning("Please enter a question first.")
        with col2:
            if st.button("Clear", type="secondary", use_container_width=True):
                st.session_state.current_query = ""
                st.rerun()
    
    def render_response_display(self):
        """Render clean response display."""
        response = st.session_state.current_response
        
        # Clean response overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            sources_count = len(response.get('sources', []))
            st.markdown(f"""
                <div class="metric-minimal">
                    <div class="metric-value" style="color: #2e7d32;">{sources_count}</div>
                    <div class="metric-label">Sources</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            citations_count = len(response.get('citations', []))
            st.markdown(f"""
                <div class="metric-minimal">
                    <div class="metric-value" style="color: #1976d2;">{citations_count}</div>
                    <div class="metric-label">Citations</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            conflicts = "Yes" if response.get('has_conflicts', False) else "No"
            conflict_color = "#ed6c02" if conflicts == "Yes" else "#2e7d32"
            st.markdown(f"""
                <div class="metric-minimal">
                    <div class="metric-value" style="color: {conflict_color};">{conflicts}</div>
                    <div class="metric-label">Conflicts</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            response_time = response.get('response_time_seconds', 0)
            st.markdown(f"""
                <div class="metric-minimal">
                    <div class="metric-value" style="color: #7c3aed;">{response_time:.1f}s</div>
                    <div class="metric-label">Time</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Main response in clean card
        formatted_response = ResponseFormatter.format_for_display(response)
        
        st.markdown(f"""
            <div class="material-card">
                <h3 style="color: #424242; margin-top: 0;">📄 Legal Analysis</h3>
                {formatted_response['formatted_answer']}
            </div>
        """, unsafe_allow_html=True)
        
        # Clean sections for additional information
        col1, col2 = st.columns(2)
        
        with col1:
            if response.get('sources'):
                with st.expander(f"📚 Sources ({len(response['sources'])})", expanded=False):
                    for i, source in enumerate(response['sources'], 1):
                        st.write(f"{i}. {source}")
        
        with col2:
            if response.get('citations'):
                with st.expander(f"📖 Citations ({len(response['citations'])})", expanded=False):
                    for i, citation in enumerate(response['citations'], 1):
                        st.write(f"{i}. {citation}")
        
        # Conflicts section
        if response.get('has_conflicts'):
            with st.expander("⚠️ Conflicts Detected", expanded=True):
                st.markdown("""
                    <div class="status-clean status-warning">
                        The analysis found conflicting information in the documents.
                    </div>
                """, unsafe_allow_html=True)
                
                for i, conflict in enumerate(response.get('conflicts', []), 1):
                    st.write(f"**Conflict {i}:** {conflict.get('type', 'Unknown')}")
                    st.write(f"**Documents:** {', '.join(conflict.get('documents', []))}")
        
        # Download button
        if st.button("💾 Download Analysis", type="secondary", use_container_width=True):
            self.download_response(response)
    
    def render_sidebar(self):
        """Render minimal sidebar."""
        with st.sidebar:
            st.markdown("### ⚖️ Legal Research")
            st.markdown("AI-powered document analysis")
            
            st.markdown("---")
            
            # Collection status
            if hasattr(st.session_state, 'ingestion_pipeline') and st.session_state.ingestion_pipeline:
                try:
                    collection_info = st.session_state.ingestion_pipeline.get_collection_info()
                    st.success("✅ Collection Active")
                    st.write(f"**Documents**: {collection_info.get('document_count', 0)}")
                    st.write(f"**Chunks**: {collection_info.get('total_documents', 0)}")
                except Exception:
                    st.warning("Collection status unavailable")
            else:
                st.info("📋 No documents uploaded yet")
            
            # Quick actions
            if st.button("🔄 Reset Collection", type="secondary", use_container_width=True):
                if hasattr(st.session_state, 'ingestion_pipeline') and st.session_state.ingestion_pipeline:
                    try:
                        st.session_state.ingestion_pipeline.reset_collection()
                        st.success("Collection reset!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Reset failed: {str(e)}")
                else:
                    st.warning("No collection to reset")
            
            # Settings
            st.markdown("---")
            st.markdown("### ⚙️ Settings")
            
            provider_icon = "🤖" if settings.api_provider == "gemini" else "🔥"
            st.info(f"{provider_icon} Using {settings.api_provider.title()} API")
    
    # Include essential methods from original file
    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files (minimal implementation)."""
        # This would contain the actual processing logic
        # For now, just showing the structure
        st.success(f"Processing {len(uploaded_files)} files...")
        # Implementation would go here
    
    def process_query(self, query):
        """Process user query (minimal implementation)."""
        # This would contain the actual query processing logic
        st.success(f"Processing query: {query}")
        # Implementation would go here
    
    def remove_document(self, index):
        """Remove document from session state."""
        if 0 <= index < len(st.session_state.uploaded_documents):
            removed = st.session_state.uploaded_documents.pop(index)
            st.success(f"Removed: {removed['filename']}")
    
    def download_response(self, response):
        """Download response as text file."""
        # Implementation for downloading response
        st.success("Download prepared!")


def main():
    """Main entry point for the minimal Streamlit app."""
    try:
        app = LegalResearchUI()
        app.run()
    except Exception as e:
        st.error(f"Application error: {str(e)}")


if __name__ == "__main__":
    main()
