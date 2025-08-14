"""
Context-aware retrieval system for legal documents.
Handles semantic search and context preparation for RAG.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    logger = None

from config.settings import settings
# Try to import vector store, use alternative if needed
try:
    from src.ingestion.vector_store import VectorStoreManager
    VECTOR_STORE_AVAILABLE = True
except ImportError as e:
    print(f"Primary vector store not available: {e}")
    VECTOR_STORE_AVAILABLE = False
    try:
        from src.ingestion.alternative_vector_store import create_alternative_vector_store
    except ImportError as alt_e:
        print(f"Alternative vector store also not available: {alt_e}")
        raise ImportError("No vector store implementation available")

from src.utils import ConflictDetector, CitationFormatter


class LegalDocumentRetriever:
    """Advanced retriever for legal documents with context awareness."""
    
    def __init__(self, vector_store_manager: Optional[VectorStoreManager] = None):
        """Initialize the retriever."""
        self.vector_store = vector_store_manager or VectorStoreManager()
        self.conflict_detector = ConflictDetector()
        self.citation_formatter = CitationFormatter()
    
    def retrieve_relevant_documents(self, 
                                   query: str, 
                                   k: int = None,
                                   document_types: Optional[List[str]] = None,
                                   date_range: Optional[Tuple[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query with optional filters.
        
        Args:
            query: User query
            k: Number of documents to retrieve
            document_types: Filter by document types (PDF, DOCX, etc.)
            date_range: Filter by date range (start_date, end_date)
            
        Returns:
            List of relevant documents with enhanced metadata
        """
        try:
            k = k or settings.top_k_retrievals
            
            # Debug: Log vector store status
            if logger:
                logger.info(f"=== Retrieval Debug Info ===")
                logger.info(f"Vector store instance ID: {id(self.vector_store)}")
                logger.info(f"Query: {query}")
                logger.info(f"Requested k: {k}")
                
                # Try to get document count
                try:
                    if hasattr(self.vector_store, 'get_document_count'):
                        doc_count = self.vector_store.get_document_count()
                        logger.info(f"Vector store document count: {doc_count}")
                    else:
                        logger.warning("Vector store doesn't have get_document_count method")
                        
                    # Try to get collection info if available
                    if hasattr(self.vector_store, 'get_collection_info'):
                        collection_info = self.vector_store.get_collection_info()
                        logger.info(f"Collection info: {collection_info}")
                except Exception as e:
                    logger.error(f"Failed to get vector store info: {e}")
            
            # Build filter dictionary
            filter_dict = self._build_filter_dict(document_types, date_range)
            
            # Enhance query for better legal document retrieval
            enhanced_query = self._enhance_legal_query(query)
            
            if logger:
                logger.info(f"Enhanced query: {enhanced_query}")
                logger.info(f"Filter dict: {filter_dict}")
            
            # Retrieve documents
            results = self.vector_store.search_similar_documents(
                query=enhanced_query,
                k=k * 2,  # Get more results for better filtering
                filter_dict=filter_dict
            )
            
            if logger:
                logger.info(f"Vector store returned {len(results)} raw results for query: {query[:50]}...")
                if results:
                    logger.info(f"First result similarity score: {results[0].get('similarity_score', 'N/A')}")
                    logger.info(f"First result content preview: {results[0].get('content', '')[:100]}...")
                else:
                    logger.warning("No results returned from vector store - this may indicate no documents are indexed")
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in results 
                if result['similarity_score'] <= settings.similarity_threshold
            ]
            
            if logger:
                logger.info(f"After similarity filtering ({settings.similarity_threshold}): {len(filtered_results)} results")
            
            # Take top k results
            top_results = filtered_results[:k]
            
            # Enhance results with additional metadata
            enhanced_results = self._enhance_results(top_results, query)
            
            if logger:
                logger.info(f"Retrieved {len(enhanced_results)} relevant documents for query")
            
            return enhanced_results
            
        except Exception as e:
            if logger:
                logger.error(f"Error retrieving documents: {e}")
            return []
    
    def retrieve_with_conflict_detection(self, query: str, k: int = None) -> Dict[str, Any]:
        """
        Retrieve documents and detect potential conflicts.
        
        Args:
            query: User query
            k: Number of documents to retrieve
            
        Returns:
            Dictionary containing results and conflict analysis
        """
        try:
            # Retrieve relevant documents
            results = self.retrieve_relevant_documents(query, k)
            
            # Detect conflicts between results
            conflicts = self.conflict_detector.detect_conflicts(results)
            
            # Group results by document source
            grouped_results = self._group_by_source(results)
            
            return {
                'query': query,
                'results': results,
                'grouped_results': grouped_results,
                'conflicts': conflicts,
                'has_conflicts': len(conflicts) > 0,
                'total_results': len(results),
                'retrieval_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            if logger:
                logger.error(f"Error in conflict detection retrieval: {e}")
            return {
                'query': query,
                'results': [],
                'conflicts': [],
                'has_conflicts': False,
                'error': str(e)
            }
    
    def retrieve_by_section(self, 
                           document_name: str, 
                           section_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific section from a document.
        
        Args:
            document_name: Name of the document
            section_number: Section number to retrieve
            
        Returns:
            Section content if found, None otherwise
        """
        try:
            filter_dict = {
                'document_name': document_name,
                'section_number': section_number
            }
            
            results = self.vector_store.search_similar_documents(
                query=f"section {section_number}",
                k=1,
                filter_dict=filter_dict
            )
            
            if results:
                return results[0]
            
            return None
            
        except Exception as e:
            if logger:
                logger.error(f"Error retrieving section {section_number} from {document_name}: {e}")
            return None
    
    def search_by_citation(self, citation: str) -> List[Dict[str, Any]]:
        """
        Search for documents by legal citation.
        
        Args:
            citation: Legal citation to search for
            
        Returns:
            List of matching documents
        """
        try:
            # Extract citation components
            citation_query = self._parse_citation(citation)
            
            # Search using enhanced citation query
            results = self.vector_store.search_similar_documents(
                query=citation_query,
                k=settings.top_k_retrievals
            )
            
            return results
            
        except Exception as e:
            if logger:
                logger.error(f"Error searching by citation {citation}: {e}")
            return []
    
    def get_document_context(self, 
                           document_name: str, 
                           section_number: str,
                           context_sections: int = 2) -> Dict[str, Any]:
        """
        Get document context around a specific section.
        
        Args:
            document_name: Name of the document
            section_number: Target section number
            context_sections: Number of sections before/after to include
            
        Returns:
            Dictionary with target section and surrounding context
        """
        try:
            # Get target section
            target_section = self.retrieve_by_section(document_name, section_number)
            
            if not target_section:
                return {'error': f'Section {section_number} not found in {document_name}'}
            
            # Get surrounding sections
            context = {
                'target_section': target_section,
                'preceding_sections': [],
                'following_sections': [],
                'document_name': document_name,
                'section_number': section_number
            }
            
            # Try to get preceding and following sections
            # This is a simplified implementation - could be enhanced with better section ordering
            section_num = float(section_number) if '.' in section_number else int(section_number)
            
            for i in range(1, context_sections + 1):
                # Preceding sections
                prev_section_num = str(section_num - i)
                prev_section = self.retrieve_by_section(document_name, prev_section_num)
                if prev_section:
                    context['preceding_sections'].insert(0, prev_section)
                
                # Following sections
                next_section_num = str(section_num + i)
                next_section = self.retrieve_by_section(document_name, next_section_num)
                if next_section:
                    context['following_sections'].append(next_section)
            
            return context
            
        except Exception as e:
            if logger:
                logger.error(f"Error getting document context: {e}")
            return {'error': str(e)}
    
    def _build_filter_dict(self, 
                          document_types: Optional[List[str]], 
                          date_range: Optional[Tuple[str, str]]) -> Optional[Dict]:
        """Build filter dictionary for vector store queries."""
        filter_dict = {}
        
        if document_types:
            filter_dict['document_type'] = {'$in': document_types}
        
        if date_range:
            start_date, end_date = date_range
            filter_dict['creation_date'] = {
                '$gte': start_date,
                '$lte': end_date
            }
        
        return filter_dict if filter_dict else None
    
    def _enhance_legal_query(self, query: str) -> str:
        """Enhance query for better legal document retrieval."""
        # Add legal context keywords
        legal_keywords = [
            'contract', 'agreement', 'clause', 'section', 'provision',
            'statute', 'regulation', 'law', 'legal', 'rights', 'obligations',
            'liability', 'damages', 'breach', 'performance', 'termination'
        ]
        
        query_lower = query.lower()
        relevant_keywords = [kw for kw in legal_keywords if kw in query_lower]
        
        if relevant_keywords:
            enhanced_query = f"{query} {' '.join(relevant_keywords)}"
        else:
            enhanced_query = query
        
        return enhanced_query
    
    def _enhance_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Enhance retrieval results with additional metadata."""
        enhanced_results = []
        
        for result in results:
            # Add formatted citation
            citation = self.citation_formatter.format_citation(
                document_name=result['document_name'],
                section_number=result['section_number']
            )
            
            # Calculate relevance score (inverse of similarity score)
            relevance_score = 1.0 - result['similarity_score']
            
            # Add query-specific highlights
            highlights = self._extract_highlights(result['content'], query)
            
            enhanced_result = {
                **result,
                'citation': citation,
                'relevance_score': relevance_score,
                'highlights': highlights,
                'content_length': len(result['content']),
                'source': result['document_name']
            }
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def _group_by_source(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group results by document source."""
        grouped = {}
        
        for result in results:
            source = result['document_name']
            if source not in grouped:
                grouped[source] = []
            grouped[source].append(result)
        
        return grouped
    
    def _parse_citation(self, citation: str) -> str:
        """Parse legal citation and convert to search query."""
        # Simple citation parsing - could be enhanced
        citation = citation.strip()
        
        # Remove common citation punctuation
        citation = re.sub(r'[,\.]', ' ', citation)
        
        # Extract key components
        words = citation.split()
        
        # Build search query from citation components
        search_terms = []
        for word in words:
            if word.isdigit() or '.' in word:
                search_terms.append(f"section {word}")
            else:
                search_terms.append(word)
        
        return ' '.join(search_terms)
    
    def _extract_highlights(self, content: str, query: str, max_highlights: int = 3) -> List[str]:
        """Extract relevant highlights from content based on query."""
        query_words = query.lower().split()
        content_lower = content.lower()
        
        highlights = []
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences[:max_highlights * 2]:  # Check more sentences than needed
            sentence_lower = sentence.lower()
            
            # Count query word matches
            matches = sum(1 for word in query_words if word in sentence_lower)
            
            if matches > 0:
                # Clean and truncate sentence
                clean_sentence = sentence.strip()
                if len(clean_sentence) > 150:
                    clean_sentence = clean_sentence[:150] + "..."
                
                highlights.append(clean_sentence)
                
                if len(highlights) >= max_highlights:
                    break
        
        return highlights


class ContextBuilder:
    """Builds context for RAG generation from retrieved documents."""
    
    def __init__(self):
        """Initialize context builder."""
        self.citation_formatter = CitationFormatter()
    
    def build_context(self, 
                     retrieval_results: Dict[str, Any],
                     max_context_length: int = 4000) -> Dict[str, Any]:
        """
        Build context for RAG generation from retrieval results.
        
        Args:
            retrieval_results: Results from retrieval
            max_context_length: Maximum context length in characters
            
        Returns:
            Formatted context for generation
        """
        try:
            results = retrieval_results.get('results', [])
            conflicts = retrieval_results.get('conflicts', [])
            
            if not results:
                return {
                    'context': '',
                    'sources': [],
                    'citations': [],
                    'has_conflicts': False,
                    'conflicts': []
                }
            
            # Sort results by relevance score
            sorted_results = sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Build context pieces
            context_pieces = []
            sources = set()
            citations = []
            current_length = 0
            
            for i, result in enumerate(sorted_results):
                # Format citation
                citation = result.get('citation', f"Source {i+1}")
                citations.append(citation)
                sources.add(result['document_name'])
                
                # Format context piece
                content = result['content']
                context_piece = f"[{citation}]\n{content}\n"
                
                # Check if adding this piece would exceed limit
                if current_length + len(context_piece) > max_context_length:
                    # Try to truncate the content
                    remaining_space = max_context_length - current_length - len(f"[{citation}]\n...\n")
                    if remaining_space > 100:  # Only add if meaningful content can fit
                        truncated_content = content[:remaining_space] + "..."
                        context_piece = f"[{citation}]\n{truncated_content}\n"
                        context_pieces.append(context_piece)
                    break
                
                context_pieces.append(context_piece)
                current_length += len(context_piece)
            
            # Join context pieces
            context = "\n".join(context_pieces)
            
            return {
                'context': context,
                'sources': list(sources),
                'citations': citations,
                'has_conflicts': len(conflicts) > 0,
                'conflicts': conflicts,
                'total_sources': len(sources),
                'context_length': len(context)
            }
            
        except Exception as e:
            if logger:
                logger.error(f"Error building context: {e}")
            return {
                'context': '',
                'sources': [],
                'citations': [],
                'has_conflicts': False,
                'conflicts': [],
                'error': str(e)
            }
