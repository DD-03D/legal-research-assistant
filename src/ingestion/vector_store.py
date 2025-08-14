"""
Vector database ingestion and management.
Handles document embedding and storage in Chroma vector database.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import threading

# SQLite compatibility check before importing chromadb
try:
    # Apply SQLite fix if available
    try:
        from src.utils.sqlite_fix import fix_sqlite
        fix_sqlite()
    except ImportError:
        pass
    
    # Apply ChromaDB telemetry fix
    try:
        from src.utils.chroma_fix import fix_chroma_telemetry, reset_chroma_client
        fix_chroma_telemetry()
        reset_chroma_client()
    except ImportError:
        pass
    
    import chromadb
    from chromadb.config import Settings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_chroma import Chroma
    from langchain.schema import Document
    from loguru import logger
    CHROMA_AVAILABLE = True
except ImportError as e:
    logger = None
    print(f"ChromaDB import warning: {e}")
    CHROMA_AVAILABLE = False
    # Import fallback components
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.schema import Document
        from loguru import logger
    except ImportError as fallback_e:
        print(f"Critical import error: {fallback_e}")
        raise

from config.settings import settings
from src.utils import DocumentUtils
from src.ingestion.document_processor import process_document, process_documents_batch
from src.api_providers import APIProviderFactory


class VectorStoreManager:
    """Manages vector database operations for legal documents."""
    
    _lock = threading.Lock()
    _instance = None
    
    def __init__(self, persist_directory: Optional[str] = None):
        """Initialize vector store manager."""
        if not CHROMA_AVAILABLE:
            raise ImportError(
                "ChromaDB is not available. Please install required dependencies or use alternative vector store."
            )
            
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        self.collection_name = "legal_documents"
        self._vectorstore = None
        self._embeddings = None
        
        # Ensure persist directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
    
    @property
    def embeddings(self):
        """Get embeddings with thread-safe initialization."""
        if self._embeddings is None:
            with self._lock:
                if self._embeddings is None:  # Double-check pattern
                    try:
                        self._embeddings = APIProviderFactory.get_embeddings()
                    except Exception as e:
                        if logger:
                            logger.error(f"Failed to initialize embeddings: {e}")
                        raise
        return self._embeddings
    
    @property
    def vectorstore(self) -> Chroma:
        """Get or create vector store instance."""
        if self._vectorstore is None:
            try:
                # Try to reset any existing ChromaDB instance
                try:
                    import chromadb
                    chromadb.reset()
                except:
                    pass
                
                # Create ChromaDB settings optimized for client mode
                client_settings = Settings(
                    anonymized_telemetry=False,
                    is_persistent=True,
                    allow_reset=True,
                    # Don't set server-specific options in client mode
                )
                
                self._vectorstore = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=self.persist_directory,
                    client_settings=client_settings
                )
            except Exception as e:
                if "already exists" in str(e).lower():
                    # Handle existing instance by using a unique directory
                    if logger:
                        logger.warning(f"ChromaDB instance conflict, using unique directory: {e}")
                    
                    try:
                        from src.utils.chroma_fix import get_unique_persist_directory
                        unique_dir = get_unique_persist_directory()
                        self.persist_directory = unique_dir
                        
                        self._vectorstore = Chroma(
                            collection_name=self.collection_name,
                            embedding_function=self.embeddings,
                            persist_directory=unique_dir,
                            client_settings=client_settings
                        )
                        if logger:
                            logger.info(f"Created ChromaDB with unique directory: {unique_dir}")
                    except Exception as fallback_e:
                        if logger:
                            logger.error(f"Failed to create ChromaDB with unique directory: {fallback_e}")
                        raise
                else:
                    if logger:
                        logger.error(f"Failed to create ChromaDB instance: {e}")
                    raise
        return self._vectorstore
    
    def add_document(self, document_data: Dict[str, Any]) -> List[str]:
        """
        Add a processed document to the vector store.
        
        Args:
            document_data: Processed document data from document_processor
            
        Returns:
            List of document IDs added to the vector store
        """
        try:
            documents = self._create_langchain_documents(document_data)
            
            if not documents:
                if logger:
                    logger.warning(f"No documents created for {document_data.get('filename')}")
                return []
            
            # Add documents to vector store
            doc_ids = self.vectorstore.add_documents(documents)
            
            if logger:
                logger.info(f"Added {len(documents)} chunks from document "
                           f"{document_data['filename']} to vector store")
            
            return doc_ids
            
        except Exception as e:
            if logger:
                logger.error(f"Error adding document to vector store: {e}")
            raise
    
    def add_documents_batch(self, documents_data: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple processed documents to the vector store.
        
        Args:
            documents_data: List of processed document data
            
        Returns:
            List of all document IDs added
        """
        all_doc_ids = []
        
        for doc_data in documents_data:
            try:
                doc_ids = self.add_document(doc_data)
                all_doc_ids.extend(doc_ids)
            except Exception as e:
                if logger:
                    logger.error(f"Failed to add document {doc_data.get('filename')}: {e}")
                continue
        
        return all_doc_ids
    
    def search_similar_documents(self, 
                                query: str, 
                                k: int = None, 
                                filter_dict: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents using semantic similarity.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_dict: Optional metadata filters
            
        Returns:
            List of similar documents with metadata
        """
        try:
            k = k or settings.top_k_retrievals
            
            # Perform similarity search
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_dict
            )
            
            # Format results
            formatted_results = []
            for doc, score in results:
                result = {
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'similarity_score': score,
                    'document_name': doc.metadata.get('document_name', 'Unknown'),
                    'section_number': doc.metadata.get('section_number', 'Unknown'),
                    'document_type': doc.metadata.get('document_type', 'Unknown')
                }
                formatted_results.append(result)
            
            if logger:
                logger.info(f"Found {len(formatted_results)} similar documents for query: {query[:50]}...")
            
            return formatted_results
            
        except Exception as e:
            if logger:
                logger.error(f"Error searching documents: {e}")
            raise
    
    def get_document_count(self) -> int:
        """Get total number of documents in the vector store."""
        try:
            collection = self.vectorstore._collection
            return collection.count()
        except Exception as e:
            if logger:
                logger.error(f"Error getting document count: {e}")
            return 0
    
    def delete_documents(self, document_ids: List[str]) -> bool:
        """
        Delete documents from vector store.
        
        Args:
            document_ids: List of document IDs to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.vectorstore.delete(ids=document_ids)
            if logger:
                logger.info(f"Deleted {len(document_ids)} documents from vector store")
            return True
        except Exception as e:
            if logger:
                logger.error(f"Error deleting documents: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """Clear all documents from the collection."""
        try:
            # Get all document IDs
            collection = self.vectorstore._collection
            results = collection.get()
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                if logger:
                    logger.info(f"Cleared {len(results['ids'])} documents from collection")
            
            return True
        except Exception as e:
            if logger:
                logger.error(f"Error clearing collection: {e}")
            return False
    
    def _create_langchain_documents(self, document_data: Dict[str, Any]) -> List[Document]:
        """
        Create LangChain Document objects from processed document data.
        
        Args:
            document_data: Processed document data
            
        Returns:
            List of LangChain Document objects
        """
        documents = []
        
        try:
            # Create documents for each section
            for section in document_data['sections']:
                # Create metadata
                metadata = {
                    'document_id': document_data['document_id'],
                    'document_name': document_data['filename'],
                    'document_type': document_data['metadata'].get('file_type', 'Unknown'),
                    'section_number': section['section_number'],
                    'section_type': section['type'],
                    'file_path': document_data['filepath'],
                    'title': document_data['metadata'].get('title', ''),
                    'author': document_data['metadata'].get('author', ''),
                    'creation_date': document_data['metadata'].get('creation_date', ''),
                    'total_sections': document_data['section_count'],
                    'token_count': DocumentUtils.count_tokens(section['content'])
                }
                
                # Create LangChain Document
                doc = Document(
                    page_content=section['content'],
                    metadata=metadata
                )
                
                # Further chunk if section is too large
                if DocumentUtils.count_tokens(section['content']) > settings.max_tokens_per_chunk:
                    chunked_docs = self._chunk_large_section(doc)
                    documents.extend(chunked_docs)
                else:
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            if logger:
                logger.error(f"Error creating LangChain documents: {e}")
            return []
    
    def _chunk_large_section(self, document: Document) -> List[Document]:
        """Chunk large sections into smaller pieces."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_text(document.page_content)
        
        chunked_docs = []
        for i, chunk in enumerate(chunks):
            # Copy metadata and add chunk information
            chunk_metadata = document.metadata.copy()
            chunk_metadata['chunk_number'] = i + 1
            chunk_metadata['total_chunks'] = len(chunks)
            chunk_metadata['token_count'] = DocumentUtils.count_tokens(chunk)
            
            chunked_doc = Document(
                page_content=chunk,
                metadata=chunk_metadata
            )
            chunked_docs.append(chunked_doc)
        
        return chunked_docs


class DocumentIngestionPipeline:
    """Complete pipeline for document ingestion into vector store."""
    
    def __init__(self, vector_store_manager: Optional[VectorStoreManager] = None):
        """Initialize ingestion pipeline."""
        self.vector_store = vector_store_manager or VectorStoreManager()
    
    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """
        Ingest a single file into the vector store.
        
        Args:
            file_path: Path to the file to ingest
            
        Returns:
            Ingestion result summary
        """
        try:
            # Process document
            if logger:
                logger.info(f"Processing document: {file_path}")
            
            document_data = process_document(file_path)
            
            # Add to vector store
            if logger:
                logger.info(f"Adding document to vector store: {document_data['filename']}")
            
            doc_ids = self.vector_store.add_document(document_data)
            
            result = {
                'success': True,
                'filename': document_data['filename'],
                'document_id': document_data['document_id'],
                'sections_added': len(doc_ids),
                'total_tokens': document_data['token_count'],
                'vector_store_ids': doc_ids
            }
            
            if logger:
                logger.info(f"Successfully ingested document: {result}")
            
            return result
            
        except Exception as e:
            error_result = {
                'success': False,
                'filename': Path(file_path).name,
                'error': str(e)
            }
            
            if logger:
                logger.error(f"Failed to ingest document {file_path}: {e}")
            
            return error_result
    
    def ingest_files_batch(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Ingest multiple files into the vector store.
        
        Args:
            file_paths: List of file paths to ingest
            
        Returns:
            Batch ingestion result summary
        """
        results = []
        total_sections = 0
        total_tokens = 0
        successful_files = 0
        
        for file_path in file_paths:
            result = self.ingest_file(file_path)
            results.append(result)
            
            if result['success']:
                successful_files += 1
                total_sections += result['sections_added']
                total_tokens += result['total_tokens']
        
        summary = {
            'total_files': len(file_paths),
            'successful_files': successful_files,
            'failed_files': len(file_paths) - successful_files,
            'total_sections_added': total_sections,
            'total_tokens': total_tokens,
            'results': results
        }
        
        if logger:
            logger.info(f"Batch ingestion completed: {summary}")
        
        return summary
    
    def get_status(self) -> Dict[str, Any]:
        """Get current vector store status."""
        return {
            'total_documents': self.vector_store.get_document_count(),
            'collection_name': self.vector_store.collection_name,
            'persist_directory': self.vector_store.persist_directory
        }
