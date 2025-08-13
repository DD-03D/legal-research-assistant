"""
Alternative vector store implementation for environments with SQLite compatibility issues.
This module provides a fallback FAISS-based vector store when ChromaDB is not available.
"""

import os
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
from loguru import logger

# Vector Store Dependencies
try:
    from langchain_community.vectorstores import FAISS
    FAISS_AVAILABLE = True
except ImportError:
    try:
        # Try alternative import path
        from langchain.vectorstores import FAISS
        FAISS_AVAILABLE = True
    except ImportError:
        FAISS_AVAILABLE = False
        logger.warning("FAISS not available, using in-memory vector store")

try:
    from langchain.schema import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError as e:
    logger.error(f"Critical langchain imports failed: {e}")
    raise

from src.api_providers import APIProviderFactory


class AlternativeVectorStore:
    """
    Alternative vector store implementation using FAISS or in-memory storage.
    Used as fallback when ChromaDB has SQLite compatibility issues.
    """
    
    def __init__(self, persist_directory: str = "data/faiss_db"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.embeddings = APIProviderFactory.get_embeddings()
        self.vectorstore = None
        self.documents = []
        
        # Try to load existing vector store
        self._load_vectorstore()
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the vector store."""
        try:
            if FAISS_AVAILABLE:
                if self.vectorstore is None:
                    # Create new FAISS vector store
                    self.vectorstore = FAISS.from_documents(documents, self.embeddings)
                else:
                    # Add to existing vector store
                    self.vectorstore.add_documents(documents)
                
                # Save the vector store
                self._save_vectorstore()
                
            else:
                # Fallback to in-memory storage
                self.documents.extend(documents)
                self._save_documents()
            
            return [f"doc_{i}" for i in range(len(documents))]
            
        except Exception as e:
            logger.error(f"Error adding documents to alternative vector store: {e}")
            raise
    
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Search for similar documents."""
        try:
            if FAISS_AVAILABLE and self.vectorstore is not None:
                return self.vectorstore.similarity_search(query, k=k)
            else:
                # Fallback: simple text matching
                return self._simple_text_search(query, k=k)
                
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    def _simple_text_search(self, query: str, k: int = 4) -> List[Document]:
        """Simple text-based search fallback."""
        query_lower = query.lower()
        scored_docs = []
        
        for doc in self.documents:
            content_lower = doc.page_content.lower()
            score = 0
            
            # Simple scoring based on keyword matches
            query_words = query_lower.split()
            for word in query_words:
                score += content_lower.count(word)
            
            if score > 0:
                scored_docs.append((score, doc))
        
        # Sort by score and return top k
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs[:k]]
    
    def _save_vectorstore(self):
        """Save FAISS vector store to disk."""
        if FAISS_AVAILABLE and self.vectorstore is not None:
            try:
                self.vectorstore.save_local(str(self.persist_directory))
                logger.info("Vector store saved successfully")
            except Exception as e:
                logger.error(f"Error saving vector store: {e}")
    
    def _load_vectorstore(self):
        """Load FAISS vector store from disk."""
        if FAISS_AVAILABLE:
            try:
                index_path = self.persist_directory / "index.faiss"
                if index_path.exists():
                    self.vectorstore = FAISS.load_local(
                        str(self.persist_directory), 
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                    logger.info("Vector store loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load existing vector store: {e}")
    
    def _save_documents(self):
        """Save documents to pickle file as fallback."""
        try:
            docs_path = self.persist_directory / "documents.pkl"
            with open(docs_path, 'wb') as f:
                pickle.dump(self.documents, f)
        except Exception as e:
            logger.error(f"Error saving documents: {e}")
    
    def _load_documents(self):
        """Load documents from pickle file."""
        try:
            docs_path = self.persist_directory / "documents.pkl"
            if docs_path.exists():
                with open(docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
                logger.info(f"Loaded {len(self.documents)} documents from fallback storage")
        except Exception as e:
            logger.warning(f"Could not load documents from fallback storage: {e}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the vector store collection."""
        if FAISS_AVAILABLE and self.vectorstore is not None:
            return {
                'type': 'FAISS',
                'document_count': len(self.documents),
                'index_size': self.vectorstore.index.ntotal if hasattr(self.vectorstore.index, 'ntotal') else 'Unknown'
            }
        else:
            return {
                'type': 'In-Memory',
                'document_count': len(self.documents),
                'index_size': 'N/A'
            }


def create_alternative_vector_store(persist_directory: str = "data/faiss_db") -> AlternativeVectorStore:
    """Create and return an alternative vector store instance."""
    return AlternativeVectorStore(persist_directory)
