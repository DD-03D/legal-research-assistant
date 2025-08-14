"""
Legal-specific RAG generation system.
Handles prompt engineering and response generation for legal queries.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json

try:
    from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
    from langchain.schema import AIMessage, HumanMessage, SystemMessage
    from loguru import logger
except ImportError as e:
    logger = None
    print(f"Import warning: {e}")

from config.settings import settings
from src.retrieval.retriever import LegalDocumentRetriever, ContextBuilder
from src.api_providers import APIProviderFactory


class LegalPromptTemplates:
    """Templates for legal document analysis prompts."""
    
    SYSTEM_PROMPT = """You are an expert legal research assistant with deep knowledge of contract law, statutory interpretation, and legal document analysis. Your role is to provide accurate, well-cited legal analysis based on the provided documents.

INSTRUCTIONS:
1. Analyze the provided legal documents carefully
2. Provide accurate answers with proper legal citations
3. When information conflicts between sources, present both views clearly
4. Use proper legal terminology and formatting
5. Always cite specific sections and document names
6. If you're uncertain about something, state it clearly
7. Focus on the legal implications and practical applications

CITATION FORMAT:
- Use format: [Document Name, Section X.X]
- For conflicts: "Document A states X, while Document B states Y"
- Always include section numbers when available

RESPONSE STRUCTURE:
1. Direct answer to the question
2. Supporting legal analysis
3. Relevant citations
4. Any conflicts or limitations
5. Practical implications if applicable"""

    QUERY_PROMPT = """Based on the following legal documents and context, please answer the user's question:

CONTEXT:
{context}

USER QUESTION: {question}

{conflict_instructions}

Please provide a comprehensive legal analysis with proper citations."""

    CONFLICT_RESOLUTION_PROMPT = """
IMPORTANT: The documents contain conflicting information. Please:
1. Identify and explain each conflicting position
2. Cite the specific sources for each position
3. If possible, suggest how these conflicts might be resolved
4. Note any hierarchy or precedence between sources
"""

    SECTION_ANALYSIS_PROMPT = """You are analyzing a specific section of a legal document. Please provide:

1. Summary of the section's main provisions
2. Legal implications and obligations
3. Key terms and definitions
4. Relationship to other sections (if context provided)
5. Potential areas of concern or ambiguity

SECTION TO ANALYZE:
{section_content}

DOCUMENT: {document_name}
SECTION: {section_number}

{additional_context}"""


class LegalResponseGenerator:
    """Generates legal responses using RAG with legal-specific prompts."""
    
    def __init__(self, 
                 retriever: Optional[LegalDocumentRetriever] = None,
                 context_builder: Optional[ContextBuilder] = None):
        """Initialize the response generator."""
        try:
            if logger:
                logger.info("Initializing LegalResponseGenerator")
            
            self.retriever = retriever or LegalDocumentRetriever()
            self.context_builder = context_builder or ContextBuilder()
            
            if logger:
                logger.info("Initializing language model using API provider factory")
            
            # Initialize language model using API provider factory
            self.llm = APIProviderFactory.get_llm()
            
            if logger:
                logger.info(f"LLM initialized successfully: {type(self.llm)}")
                logger.info(f"LLM model: {getattr(self.llm, 'model_name', 'Unknown')}")
            
            # Initialize prompt templates
            self.templates = LegalPromptTemplates()
            
            if logger:
                logger.info("LegalResponseGenerator initialization completed successfully")
                
        except Exception as e:
            if logger:
                logger.error(f"Failed to initialize LegalResponseGenerator: {e}")
            raise
    
    def generate_response(self, 
                         question: str,
                         document_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive legal response to a question.
        
        Args:
            question: User's legal question
            document_filters: Optional filters for document retrieval
            
        Returns:
            Dictionary containing response and metadata
        """
        try:
            start_time = datetime.now()
            
            # Debug: Log the question and settings
            if logger:
                logger.info(f"Starting response generation for question: {question[:100]}...")
                logger.info(f"Using API provider: {settings.api_provider}")
                logger.info(f"LLM model: {settings.llm_model}")
            
            # Retrieve relevant documents with conflict detection
            if logger:
                logger.info(f"Retrieving documents for question: {question[:100]}...")
            
            try:
                retrieval_results = self.retriever.retrieve_with_conflict_detection(
                    query=question,
                    k=settings.top_k_retrievals
                )
                if logger:
                    logger.info(f"Retrieved {len(retrieval_results)} documents")
            except Exception as retrieval_error:
                if logger:
                    logger.error(f"Document retrieval failed: {retrieval_error}")
                return self._generate_error_response(question, f"Document retrieval failed: {retrieval_error}")
            
            # Build context for generation
            try:
                context_data = self.context_builder.build_context(retrieval_results)
                if logger:
                    logger.info(f"Context built successfully, length: {context_data.get('context_length', 0)}")
            except Exception as context_error:
                if logger:
                    logger.error(f"Context building failed: {context_error}")
                return self._generate_error_response(question, f"Context building failed: {context_error}")
            
            if not context_data['context']:
                if logger:
                    logger.warning("No context available, generating no-context response")
                return self._generate_no_context_response(question)
            
            # Generate response based on whether conflicts exist
            try:
                if context_data['has_conflicts']:
                    if logger:
                        logger.info("Generating conflict-aware response")
                    response = self._generate_conflict_aware_response(question, context_data)
                else:
                    if logger:
                        logger.info("Generating standard response")
                    response = self._generate_standard_response(question, context_data)
                
                if logger:
                    logger.info(f"Response generated successfully: {response[:200]}...")
                    
            except Exception as gen_error:
                if logger:
                    logger.error(f"Response generation failed: {gen_error}")
                return self._generate_error_response(question, f"Response generation failed: {gen_error}")
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Format final response
            final_response = {
                'question': question,
                'answer': response,
                'sources': context_data['sources'],
                'citations': context_data['citations'],
                'has_conflicts': context_data['has_conflicts'],
                'conflicts': context_data.get('conflicts', []),
                'context_length': context_data['context_length'],
                'response_time_seconds': response_time,
                'timestamp': datetime.now().isoformat(),
                'model_used': settings.llm_model
            }
            
            if logger:
                logger.info(f"Generated response in {response_time:.2f} seconds")
            
            return final_response
            
        except Exception as e:
            if logger:
                logger.error(f"Error generating response: {e}")
            return self._generate_error_response(question, str(e))
    
    def analyze_document_section(self, 
                                document_name: str, 
                                section_number: str,
                                include_context: bool = True) -> Dict[str, Any]:
        """
        Analyze a specific document section.
        
        Args:
            document_name: Name of the document
            section_number: Section number to analyze
            include_context: Whether to include surrounding context
            
        Returns:
            Dictionary containing section analysis
        """
        try:
            if include_context:
                # Get section with context
                context_data = self.retriever.get_document_context(
                    document_name=document_name,
                    section_number=section_number,
                    context_sections=2
                )
                
                if 'error' in context_data:
                    return {'error': context_data['error']}
                
                target_section = context_data['target_section']['content']
                additional_context = self._format_section_context(context_data)
            else:
                # Get just the target section
                section_data = self.retriever.retrieve_by_section(document_name, section_number)
                if not section_data:
                    return {'error': f'Section {section_number} not found in {document_name}'}
                
                target_section = section_data['content']
                additional_context = ""
            
            # Create analysis prompt
            prompt = self.templates.SECTION_ANALYSIS_PROMPT.format(
                section_content=target_section,
                document_name=document_name,
                section_number=section_number,
                additional_context=additional_context
            )
            
            # Generate analysis
            messages = [
                SystemMessage(content=self.templates.SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm(messages)
            
            return {
                'document_name': document_name,
                'section_number': section_number,
                'analysis': response.content,
                'section_content': target_section,
                'has_context': include_context,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            if logger:
                logger.error(f"Error analyzing section: {e}")
            return {'error': str(e)}
    
    def compare_documents(self, 
                         question: str,
                         document_names: List[str]) -> Dict[str, Any]:
        """
        Compare specific documents in relation to a question.
        
        Args:
            question: Question to analyze across documents
            document_names: List of document names to compare
            
        Returns:
            Dictionary containing comparison analysis
        """
        try:
            comparisons = []
            
            for doc_name in document_names:
                # Filter retrieval to specific document
                filter_dict = {'document_name': doc_name}
                
                results = self.retriever.vector_store.search_similar_documents(
                    query=question,
                    k=3,
                    filter_dict=filter_dict
                )
                
                if results:
                    # Build context for this document
                    doc_context = self._build_document_specific_context(results)
                    
                    # Generate document-specific response
                    doc_response = self._generate_document_comparison_response(
                        question, doc_name, doc_context
                    )
                    
                    comparisons.append({
                        'document_name': doc_name,
                        'response': doc_response,
                        'relevant_sections': len(results)
                    })
            
            # Generate overall comparison
            overall_comparison = self._generate_overall_comparison(question, comparisons)
            
            return {
                'question': question,
                'documents_compared': document_names,
                'individual_analyses': comparisons,
                'overall_comparison': overall_comparison,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            if logger:
                logger.error(f"Error comparing documents: {e}")
            return {'error': str(e)}
    
    def _generate_standard_response(self, question: str, context_data: Dict[str, Any]) -> str:
        """Generate standard response without conflicts."""
        try:
            if logger:
                logger.info("Building prompt for standard response")
            
            prompt = self.templates.QUERY_PROMPT.format(
                context=context_data['context'],
                question=question,
                conflict_instructions=""
            )
            
            if logger:
                logger.info(f"Prompt built successfully, length: {len(prompt)}")
                logger.info(f"Using LLM: {type(self.llm)}")
            
            messages = [
                SystemMessage(content=self.templates.SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            if logger:
                logger.info("Calling LLM with messages")
            
            response = self.llm(messages)
            
            if logger:
                logger.info(f"LLM response received: {response.content[:200]}...")
            
            return response.content
            
        except Exception as e:
            if logger:
                logger.error(f"Error in standard response generation: {e}")
            raise
    
    def _generate_conflict_aware_response(self, question: str, context_data: Dict[str, Any]) -> str:
        """Generate response that addresses conflicts."""
        try:
            if logger:
                logger.info("Building prompt for conflict-aware response")
            
            conflict_instructions = self.templates.CONFLICT_RESOLUTION_PROMPT
            
            prompt = self.templates.QUERY_PROMPT.format(
                context=context_data['context'],
                question=question,
                conflict_instructions=conflict_instructions
            )
            
            if logger:
                logger.info(f"Prompt built successfully, length: {len(prompt)}")
                logger.info(f"Using LLM: {type(self.llm)}")
            
            messages = [
                SystemMessage(content=self.templates.SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            if logger:
                logger.info("Calling LLM with messages")
            
            response = self.llm(messages)
            
            if logger:
                logger.info(f"LLM response received: {response.content[:200]}...")
            
            return response.content
            
        except Exception as e:
            if logger:
                logger.error(f"Error in conflict-aware response generation: {e}")
            raise
    
    def _generate_no_context_response(self, question: str) -> Dict[str, Any]:
        """Generate response when no relevant documents are found."""
        response = {
            'question': question,
            'answer': ("I couldn't find any relevant legal documents in the database "
                      "that address your question. Please ensure that relevant documents "
                      "have been uploaded and indexed, or try rephrasing your question "
                      "with different legal terms."),
            'sources': [],
            'citations': [],
            'has_conflicts': False,
            'conflicts': [],
            'context_length': 0,
            'timestamp': datetime.now().isoformat(),
            'model_used': settings.llm_model,
            'no_context': True
        }
        return response
    
    def _generate_error_response(self, question: str, error_message: str) -> Dict[str, Any]:
        """Generate response for errors."""
        return {
            'question': question,
            'answer': f"I encountered an error while processing your question: {error_message}",
            'sources': [],
            'citations': [],
            'has_conflicts': False,
            'conflicts': [],
            'context_length': 0,
            'timestamp': datetime.now().isoformat(),
            'error': error_message
        }
    
    def _format_section_context(self, context_data: Dict[str, Any]) -> str:
        """Format surrounding context for section analysis."""
        context_parts = []
        
        if context_data.get('preceding_sections'):
            context_parts.append("PRECEDING SECTIONS:")
            for section in context_data['preceding_sections']:
                context_parts.append(f"Section {section['section_number']}: {section['content'][:200]}...")
        
        if context_data.get('following_sections'):
            context_parts.append("\nFOLLOWING SECTIONS:")
            for section in context_data['following_sections']:
                context_parts.append(f"Section {section['section_number']}: {section['content'][:200]}...")
        
        return "\n".join(context_parts)
    
    def _build_document_specific_context(self, results: List[Dict[str, Any]]) -> str:
        """Build context for document-specific analysis."""
        context_parts = []
        
        for result in results:
            citation = result.get('citation', 'Unknown')
            content = result['content']
            context_parts.append(f"[{citation}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _generate_document_comparison_response(self, 
                                             question: str, 
                                             document_name: str, 
                                             context: str) -> str:
        """Generate response for document comparison."""
        prompt = f"""Based on the following content from {document_name}, please answer: {question}

CONTENT FROM {document_name}:
{context}

Please provide a focused analysis of how this document addresses the question."""
        
        messages = [
            SystemMessage(content=self.templates.SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm(messages)
        return response.content
    
    def _generate_overall_comparison(self, question: str, comparisons: List[Dict[str, Any]]) -> str:
        """Generate overall comparison across documents."""
        comparison_summary = "\n\n".join([
            f"**{comp['document_name']}:**\n{comp['response']}"
            for comp in comparisons
        ])
        
        prompt = f"""Based on the following analyses of different documents regarding the question: {question}

{comparison_summary}

Please provide an overall comparison that:
1. Identifies similarities and differences between the documents
2. Notes any conflicts or contradictions
3. Provides a synthesized analysis
4. Suggests which documents might take precedence if applicable"""
        
        messages = [
            SystemMessage(content=self.templates.SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm(messages)
        return response.content


class ResponseFormatter:
    """Formats and enhances generated responses."""
    
    @staticmethod
    def format_for_display(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format response for UI display."""
        formatted_answer = ResponseFormatter._format_answer_text(response_data['answer'])
        
        return {
            **response_data,
            'formatted_answer': formatted_answer,
            'citation_list': ResponseFormatter._format_citations(response_data.get('citations', [])),
            'conflict_summary': ResponseFormatter._format_conflicts(response_data.get('conflicts', [])),
            'source_summary': ResponseFormatter._format_sources(response_data.get('sources', []))
        }
    
    @staticmethod
    def _format_answer_text(answer: str) -> str:
        """Format answer text for better readability."""
        # Add line breaks for better formatting
        answer = answer.replace('. ', '.\n\n')
        
        # Format citations in brackets
        import re
        answer = re.sub(r'\[([^\]]+)\]', r'**[\1]**', answer)
        
        return answer
    
    @staticmethod
    def _format_citations(citations: List[str]) -> List[Dict[str, str]]:
        """Format citations for display."""
        return [{'text': citation, 'id': f'cite_{i}'} for i, citation in enumerate(citations)]
    
    @staticmethod
    def _format_conflicts(conflicts: List[Dict[str, Any]]) -> str:
        """Format conflict information."""
        if not conflicts:
            return ""
        
        conflict_text = "**Potential Conflicts Detected:**\n\n"
        for conflict in conflicts:
            conflict_text += f"- {conflict.get('type', 'Unknown conflict')} between "
            conflict_text += f"{', '.join(conflict.get('documents', []))}\n"
        
        return conflict_text
    
    @staticmethod
    def _format_sources(sources: List[str]) -> str:
        """Format source information."""
        if not sources:
            return "No sources found"
        
        return f"Sources: {', '.join(sources)}"
