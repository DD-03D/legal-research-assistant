"""
Fallback vector store implementation using FAISS.
This is used when ChromaDB has compatibility issues.
"""

import os
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

try:
    import numpy as np
    import faiss
    from sentence_transformers import SentenceTransformer
    from langchain.schema import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    FAISS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"FAISS dependencies not available: {e}")
    FAISS_AVAILABLE = False

class FallbackVectorStore:
    """
    Fallback vector store using FAISS when ChromaDB is not available.
    """
    
    def __init__(self, persist_directory: str = "data/faiss_db"):
        """Initialize the fallback vector store."""
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.persist_directory / "faiss_index.bin"
        self.metadata_file = self.persist_directory / "metadata.pkl"
        
        # Initialize FAISS index and metadata
        self.index = None
        self.metadata = []
        self.embeddings_model = None
        
        self._initialize_store()
    
    def _initialize_store(self):
        """Initialize the FAISS store."""
        try:
            # Load existing index if available
            if self.index_file.exists() and self.metadata_file.exists():
                self._load_existing_index()
            else:
                self._create_new_index()
                
            # Initialize embeddings model
            self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Fallback vector store initialized with FAISS")
            
        except Exception as e:
            logger.error(f"Failed to initialize fallback vector store: {e}")
            raise
    
    def _create_new_index(self):
        """Create a new FAISS index."""
        try:
            # Create a simple FAISS index for 384-dimensional vectors (all-MiniLM-L6-v2)
            dimension = 384
            self.index = faiss.IndexFlatL2(dimension)
            self.metadata = []
            logger.info("Created new FAISS index")
        except Exception as e:
            logger.error(f"Failed to create FAISS index: {e}")
            raise
    
    def _load_existing_index(self):
        """Load existing FAISS index and metadata."""
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(self.index_file))
            
            # Load metadata
            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
                
            logger.info(f"Loaded existing FAISS index with {len(self.metadata)} documents")
        except Exception as e:
            logger.warning(f"Failed to load existing index: {e}, creating new one")
            self._create_new_index()
    
    def _save_index(self):
        """Save the FAISS index and metadata."""
        try:
            if self.index is not None:
                faiss.write_index(self.index, str(self.index_file))
                
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
                
            logger.info("FAISS index saved successfully")
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the vector store."""
        try:
            if not documents:
                return []
            
            # Generate embeddings for documents
            texts = [doc.page_content for doc in documents]
            embeddings = self.embeddings_model.encode(texts)
            
            # Add to FAISS index
            if self.index is None:
                self._create_new_index()
            
            self.index.add(embeddings.astype('float32'))
            
            # Store metadata
            doc_ids = []
            for i, doc in enumerate(documents):
                doc_id = f"doc_{len(self.metadata) + i}"
                doc_ids.append(doc_id)
                
                self.metadata.append({
                    'id': doc_id,
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'index': len(self.metadata) + i
                })
            
            # Save the updated index
            self._save_index()
            
            logger.info(f"Added {len(documents)} documents to fallback vector store")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def search_similar_documents(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        try:
            if self.index is None or len(self.metadata) == 0:
                return []
            
            # Generate query embedding
            query_embedding = self.embeddings_model.encode([query])
            
            # Search in FAISS index
            distances, indices = self.index.search(
                query_embedding.astype('float32'), 
                min(n_results, len(self.metadata))
            )
            
            # Return results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.metadata):
                    metadata = self.metadata[idx].copy()
                    metadata['distance'] = float(distance)
                    metadata['rank'] = i + 1
                    results.append(metadata)
            
            logger.info(f"Found {len(results)} similar documents for query")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return []
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by its ID."""
        try:
            for doc in self.metadata:
                if doc['id'] == doc_id:
                    return doc
            return None
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the store."""
        try:
            # Find and remove the document
            for i, doc in enumerate(self.metadata):
                if doc['id'] == doc_id:
                    del self.metadata[i]
                    
                    # Rebuild the index without this document
                    self._rebuild_index()
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def _rebuild_index(self):
        """Rebuild the FAISS index from metadata."""
        try:
            if not self.metadata:
                self._create_new_index()
                return
            
            # Get all document contents
            texts = [doc['content'] for doc in self.metadata]
            embeddings = self.embeddings_model.encode(texts)
            
            # Create new index
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(embeddings.astype('float32'))
            
            # Update indices in metadata
            for i, doc in enumerate(self.metadata):
                doc['index'] = i
            
            # Save the rebuilt index
            self._save_index()
            
            logger.info("FAISS index rebuilt successfully")
        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        try:
            return {
                'total_documents': len(self.metadata),
                'index_size': self.index.ntotal if self.index else 0,
                'store_type': 'FAISS (Fallback)',
                'persist_directory': str(self.persist_directory)
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def clear_all(self):
        """Clear all documents from the store."""
        try:
            self._create_new_index()
            self._save_index()
            logger.info("Fallback vector store cleared")
        except Exception as e:
            logger.error(f"Failed to clear store: {e}")
