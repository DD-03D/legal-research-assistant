"""
Compatibility layer for document ingestion across different vector store implementations.
Provides a unified interface regardless of which vector store is available.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

try:
    from langchain.schema import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError as e:
    logger.error(f"Critical langchain dependencies missing: {e}")
    raise

from src.utils import DocumentUtils
from src.ingestion.document_processor import process_document, process_documents_batch
from src.api_providers import APIProviderFactory

# Try to determine which vector store implementation to use
VECTOR_STORE_TYPE = None
vector_store_class = None

try:
    from src.ingestion.vector_store import VectorStoreManager, CHROMA_AVAILABLE
    if CHROMA_AVAILABLE:
        VECTOR_STORE_TYPE = "ChromaDB"
        vector_store_class = VectorStoreManager
        logger.info("ChromaDB vector store available")
    else:
        raise ImportError("ChromaDB not available")
except ImportError as e:
    logger.warning(f"ChromaDB not available ({e}), trying fallback vector store")
    try:
        from src.ingestion.fallback_vector_store import FallbackVectorStore
        VECTOR_STORE_TYPE = "Fallback"
        vector_store_class = FallbackVectorStore
        logger.info("Using fallback vector store implementation")
    except ImportError as e:
        logger.error(f"No vector store implementation available: {e}")
        raise
except RuntimeError as e:
    # Handle SQLite compatibility errors
    if "sqlite3" in str(e).lower() or "3.35.0" in str(e):
        logger.warning(f"ChromaDB SQLite compatibility issue ({e}), using fallback vector store")
        try:
            from src.ingestion.fallback_vector_store import FallbackVectorStore
            VECTOR_STORE_TYPE = "Fallback"
            vector_store_class = FallbackVectorStore
            logger.info("Using fallback vector store due to SQLite compatibility issues")
        except ImportError as fallback_e:
            logger.error(f"Fallback vector store not available: {fallback_e}")
            raise
    else:
        logger.error(f"ChromaDB error: {e}")
        raise


class UnifiedDocumentIngestionPipeline:
    """
    Unified document ingestion pipeline that works with any available vector store.
    """
    
    def __init__(self, persist_directory: Optional[str] = None):
        """Initialize the ingestion pipeline."""
        self.persist_directory = persist_directory or "data/vector_db"
        self.vector_store = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize vector store based on available implementation
        self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """Initialize the appropriate vector store implementation."""
        try:
            if VECTOR_STORE_TYPE == "ChromaDB":
                self.vector_store = vector_store_class(self.persist_directory)
                logger.info("Initialized ChromaDB vector store")
            elif VECTOR_STORE_TYPE == "Fallback":
                self.vector_store = vector_store_class(self.persist_directory)
                logger.info("Initialized fallback vector store")
            else:
                raise RuntimeError("No vector store implementation available")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """
        Ingest a file - reads content and processes it.
        Maintains compatibility with existing code that only passes file_path.
        """
        try:
            # Use the existing document processor which handles file reading internally
            processed_doc = process_document(file_path)
            
            # Add to vector store based on which vector store implementation we're using
            try:
                logger.info(f"Vector store type: {type(self.vector_store)}")
                logger.info(f"Vector store methods: {[method for method in dir(self.vector_store) if not method.startswith('_')]}")
                
                # Check if it's the ChromaDB VectorStoreManager
                if hasattr(self.vector_store, 'add_document') and 'VectorStoreManager' in str(type(self.vector_store)):
                    logger.info("Using VectorStoreManager.add_document method with processed document data")
                    doc_ids = self.vector_store.add_document(processed_doc)
                
                # Check if it's the fallback vector store that expects Document objects
                elif hasattr(self.vector_store, 'add_documents'):
                    logger.info("Using add_documents method with Document objects")
                    # Create Document objects for fallback vector store
                    documents = []
                    for section in processed_doc.get('sections', []):
                        doc = Document(
                            page_content=section.get('content', ''),
                            metadata={
                                'filename': processed_doc.get('filename', ''),
                                'section_id': section.get('id', ''),
                                'section_type': section.get('type', ''),
                                'tokens': section.get('tokens', 0)
                            }
                        )
                        documents.append(doc)
                    
                    doc_ids = self.vector_store.add_documents(documents)
                else:
                    raise RuntimeError(f"Unknown vector store type: {type(self.vector_store)}")
                
                # Update the processed document with vector store IDs
                processed_doc['vector_store_ids'] = doc_ids
                processed_doc['vector_store_type'] = VECTOR_STORE_TYPE
                
                logger.info(f"Successfully ingested document: {processed_doc}")
                return processed_doc
                
            except Exception as e:
                logger.error(f"Failed to add document to vector store: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Failed to ingest file {file_path}: {e}")
            raise
    
    def ingest_documents_batch(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Ingest multiple documents in batch.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            List of processed document results
        """
        results = []
        
        for file_path in file_paths:
            try:
                result = self.ingest_file(file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to ingest {file_path}: {e}")
                # Continue with other files
                continue
        
        return results
    
    def search_documents(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents using the available vector store.
        
        Args:
            query: Search query string
            n_results: Number of results to return
            
        Returns:
            List of search results
        """
        try:
            if hasattr(self.vector_store, 'search_similar_documents'):
                return self.vector_store.search_similar_documents(query, n_results)
            elif hasattr(self.vector_store, 'search'):
                return self.vector_store.search(query, n_results)
            else:
                raise RuntimeError("Vector store does not support search operations")
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_vector_store_info(self) -> Dict[str, Any]:
        """Get information about the current vector store."""
        try:
            if hasattr(self.vector_store, 'get_collection_stats'):
                return self.vector_store.get_collection_stats()
            else:
                return {
                    'store_type': VECTOR_STORE_TYPE,
                    'persist_directory': self.persist_directory,
                    'methods': [method for method in dir(self.vector_store) if not method.startswith('_')]
                }
        except Exception as e:
            logger.error(f"Failed to get vector store info: {e}")
            return {'error': str(e)}

    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information for UI display."""
        try:
            if hasattr(self.vector_store, 'get_collection_stats'):
                stats = self.vector_store.get_collection_stats()
                return {
                    'vector_store_type': VECTOR_STORE_TYPE,
                    'status': 'Ready',
                    'document_count': stats.get('total_documents', 'Unknown'),
                    'store_type': stats.get('store_type', VECTOR_STORE_TYPE),
                    'persist_directory': self.persist_directory
                }
            elif hasattr(self.vector_store, 'get_document_count'):
                doc_count = self.vector_store.get_document_count()
                return {
                    'vector_store_type': VECTOR_STORE_TYPE,
                    'status': 'Ready',
                    'document_count': doc_count,
                    'store_type': VECTOR_STORE_TYPE,
                    'persist_directory': self.persist_directory
                }
            else:
                # Fallback information
                return {
                    'vector_store_type': VECTOR_STORE_TYPE,
                    'status': 'Ready',
                    'document_count': 'Unknown',
                    'store_type': VECTOR_STORE_TYPE,
                    'persist_directory': self.persist_directory
                }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {
                'vector_store_type': VECTOR_STORE_TYPE,
                'status': 'Error',
                'document_count': 'Unknown',
                'error': str(e),
                'persist_directory': self.persist_directory
            }


# Maintain backward compatibility
DocumentIngestionPipeline = UnifiedDocumentIngestionPipeline
