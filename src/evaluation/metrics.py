"""
Evaluation metrics and assessment tools for the Legal Research Assistant.
Includes retrieval accuracy, response quality, and performance metrics.
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import statistics

try:
    from loguru import logger
    import pandas as pd
    from sklearn.metrics import precision_score, recall_score, f1_score
except ImportError as e:
    logger = None
    print(f"Import warning: {e}")

from config.settings import settings


class RetrievalEvaluator:
    """Evaluates retrieval performance using precision@k and other metrics."""
    
    def __init__(self):
        """Initialize retrieval evaluator."""
        self.evaluation_results = []
    
    def evaluate_precision_at_k(self, 
                               query: str,
                               retrieved_docs: List[Dict[str, Any]], 
                               relevant_docs: List[str],
                               k_values: List[int] = None) -> Dict[str, float]:
        """
        Calculate precision@k for retrieved documents.
        
        Args:
            query: The search query
            retrieved_docs: List of retrieved document results
            relevant_docs: List of known relevant document IDs/names
            k_values: List of k values to evaluate (default: [1, 3, 5, 10])
            
        Returns:
            Dictionary with precision@k scores
        """
        if k_values is None:
            k_values = [1, 3, 5, 10]
        
        # Extract document names from retrieved results
        retrieved_names = [doc.get('document_name', '') for doc in retrieved_docs]
        
        precision_scores = {}
        
        for k in k_values:
            if k > len(retrieved_docs):
                k = len(retrieved_docs)
            
            if k == 0:
                precision_scores[f'precision@{k}'] = 0.0
                continue
            
            # Get top k retrieved documents
            top_k_docs = retrieved_names[:k]
            
            # Count relevant documents in top k
            relevant_in_top_k = sum(1 for doc in top_k_docs if doc in relevant_docs)
            
            # Calculate precision@k
            precision_at_k = relevant_in_top_k / k
            precision_scores[f'precision@{k}'] = precision_at_k
        
        return precision_scores
    
    def evaluate_recall_at_k(self, 
                            query: str,
                            retrieved_docs: List[Dict[str, Any]], 
                            relevant_docs: List[str],
                            k_values: List[int] = None) -> Dict[str, float]:
        """
        Calculate recall@k for retrieved documents.
        
        Args:
            query: The search query
            retrieved_docs: List of retrieved document results
            relevant_docs: List of known relevant document IDs/names
            k_values: List of k values to evaluate
            
        Returns:
            Dictionary with recall@k scores
        """
        if k_values is None:
            k_values = [1, 3, 5, 10]
        
        if not relevant_docs:
            return {f'recall@{k}': 0.0 for k in k_values}
        
        retrieved_names = [doc.get('document_name', '') for doc in retrieved_docs]
        
        recall_scores = {}
        
        for k in k_values:
            if k > len(retrieved_docs):
                k = len(retrieved_docs)
            
            if k == 0:
                recall_scores[f'recall@{k}'] = 0.0
                continue
            
            # Get top k retrieved documents
            top_k_docs = retrieved_names[:k]
            
            # Count relevant documents in top k
            relevant_in_top_k = sum(1 for doc in top_k_docs if doc in relevant_docs)
            
            # Calculate recall@k
            recall_at_k = relevant_in_top_k / len(relevant_docs)
            recall_scores[f'recall@{k}'] = recall_at_k
        
        return recall_scores
    
    def evaluate_retrieval_quality(self, 
                                  test_cases: List[Dict[str, Any]],
                                  retriever) -> Dict[str, Any]:
        """
        Evaluate retrieval quality across multiple test cases.
        
        Args:
            test_cases: List of test cases with queries and expected results
            retriever: The retriever instance to evaluate
            
        Returns:
            Comprehensive evaluation results
        """
        all_results = []
        
        for test_case in test_cases:
            query = test_case['query']
            expected_docs = test_case.get('relevant_documents', [])
            
            # Perform retrieval
            start_time = time.time()
            retrieved_docs = retriever.retrieve_relevant_documents(query)
            retrieval_time = time.time() - start_time
            
            # Calculate metrics
            precision_scores = self.evaluate_precision_at_k(query, retrieved_docs, expected_docs)
            recall_scores = self.evaluate_recall_at_k(query, retrieved_docs, expected_docs)
            
            # Store results
            result = {
                'query': query,
                'retrieval_time': retrieval_time,
                'num_retrieved': len(retrieved_docs),
                'num_expected': len(expected_docs),
                **precision_scores,
                **recall_scores
            }
            
            all_results.append(result)
        
        # Calculate aggregate metrics
        aggregate_results = self._calculate_aggregate_metrics(all_results)
        
        evaluation_summary = {
            'individual_results': all_results,
            'aggregate_metrics': aggregate_results,
            'total_test_cases': len(test_cases),
            'evaluation_timestamp': datetime.now().isoformat()
        }
        
        self.evaluation_results.append(evaluation_summary)
        
        if logger:
            logger.info(f"Completed retrieval evaluation for {len(test_cases)} test cases")
        
        return evaluation_summary
    
    def _calculate_aggregate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate aggregate metrics across all test cases."""
        aggregate = {}
        
        # Get all metric keys
        metric_keys = [key for key in results[0].keys() 
                      if key not in ['query', 'num_retrieved', 'num_expected']]
        
        for key in metric_keys:
            values = [result[key] for result in results if key in result]
            if values:
                aggregate[f'avg_{key}'] = statistics.mean(values)
                aggregate[f'std_{key}'] = statistics.stdev(values) if len(values) > 1 else 0.0
                aggregate[f'min_{key}'] = min(values)
                aggregate[f'max_{key}'] = max(values)
        
        return aggregate


class ResponseEvaluator:
    """Evaluates response quality and accuracy."""
    
    def __init__(self):
        """Initialize response evaluator."""
        self.evaluation_results = []
    
    def evaluate_response_quality(self, 
                                 response: str,
                                 expected_answer: str = None,
                                 criteria: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Evaluate response quality based on various criteria.
        
        Args:
            response: Generated response
            expected_answer: Expected/reference answer (optional)
            criteria: Custom evaluation criteria
            
        Returns:
            Dictionary with quality metrics
        """
        metrics = {}
        
        # Basic metrics
        metrics['response_length'] = len(response)
        metrics['word_count'] = len(response.split())
        metrics['sentence_count'] = len([s for s in response.split('.') if s.strip()])
        
        # Citation analysis
        metrics.update(self._evaluate_citations(response))
        
        # Legal terminology analysis
        metrics.update(self._evaluate_legal_terminology(response))
        
        # Structure analysis
        metrics.update(self._evaluate_structure(response))
        
        # If expected answer is provided, calculate similarity
        if expected_answer:
            metrics['similarity_score'] = self._calculate_similarity(response, expected_answer)
        
        return metrics
    
    def evaluate_citation_accuracy(self, 
                                  response: str,
                                  source_documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate accuracy of citations in the response.
        
        Args:
            response: Generated response with citations
            source_documents: List of source documents used
            
        Returns:
            Citation accuracy metrics
        """
        # Extract citations from response
        citations = self._extract_citations_from_response(response)
        
        # Verify citations against source documents
        verified_citations = 0
        total_citations = len(citations)
        
        for citation in citations:
            if self._verify_citation(citation, source_documents):
                verified_citations += 1
        
        citation_accuracy = verified_citations / total_citations if total_citations > 0 else 0.0
        
        return {
            'total_citations': total_citations,
            'verified_citations': verified_citations,
            'citation_accuracy': citation_accuracy,
            'citations': citations
        }
    
    def evaluate_conflict_handling(self, 
                                  response: str,
                                  known_conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate how well the response handles conflicting information.
        
        Args:
            response: Generated response
            known_conflicts: List of known conflicts in the source material
            
        Returns:
            Conflict handling metrics
        """
        response_lower = response.lower()
        
        # Check if conflicts are acknowledged
        conflict_indicators = [
            'conflict', 'contradiction', 'differs', 'disagree', 'however',
            'on the other hand', 'alternatively', 'in contrast'
        ]
        
        conflict_acknowledgment = any(indicator in response_lower for indicator in conflict_indicators)
        
        # Check if multiple perspectives are presented
        perspective_indicators = [
            'document a', 'document b', 'first document', 'second document',
            'source 1', 'source 2', 'according to', 'states that'
        ]
        
        multiple_perspectives = sum(1 for indicator in perspective_indicators 
                                  if indicator in response_lower)
        
        # Check conflict resolution attempts
        resolution_indicators = [
            'therefore', 'thus', 'consequently', 'suggest', 'recommend',
            'precedence', 'hierarchy', 'more recent', 'controlling'
        ]
        
        resolution_attempts = any(indicator in response_lower for indicator in resolution_indicators)
        
        return {
            'conflict_acknowledgment': conflict_acknowledgment,
            'multiple_perspectives_count': multiple_perspectives,
            'resolution_attempts': resolution_attempts,
            'known_conflicts_count': len(known_conflicts),
            'conflict_handling_score': self._calculate_conflict_handling_score(
                conflict_acknowledgment, multiple_perspectives, resolution_attempts
            )
        }
    
    def _evaluate_citations(self, response: str) -> Dict[str, Any]:
        """Analyze citation usage in the response."""
        import re
        
        # Count different citation patterns
        bracket_citations = len(re.findall(r'\[([^\]]+)\]', response))
        section_references = len(re.findall(r'(?i)section\s+\d+', response))
        clause_references = len(re.findall(r'(?i)clause\s+\d+', response))
        
        return {
            'bracket_citations': bracket_citations,
            'section_references': section_references,
            'clause_references': clause_references,
            'total_legal_references': bracket_citations + section_references + clause_references
        }
    
    def _evaluate_legal_terminology(self, response: str) -> Dict[str, Any]:
        """Analyze use of legal terminology."""
        legal_terms = [
            'pursuant', 'whereas', 'heretofore', 'notwithstanding', 'thereunder',
            'shall', 'may', 'covenant', 'provision', 'obligation', 'liability',
            'indemnify', 'breach', 'remedy', 'jurisdiction', 'governing law'
        ]
        
        response_lower = response.lower()
        legal_term_count = sum(1 for term in legal_terms if term in response_lower)
        legal_term_density = legal_term_count / len(response.split()) if response.split() else 0
        
        return {
            'legal_term_count': legal_term_count,
            'legal_term_density': legal_term_density,
            'legal_terminology_score': min(legal_term_density * 100, 1.0)  # Cap at 1.0
        }
    
    def _evaluate_structure(self, response: str) -> Dict[str, Any]:
        """Analyze response structure and organization."""
        paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
        
        # Check for structured elements
        has_introduction = len(paragraphs) > 0 and len(paragraphs[0]) > 100
        has_conclusion = len(paragraphs) > 1 and any(
            word in paragraphs[-1].lower() 
            for word in ['conclusion', 'summary', 'therefore', 'thus', 'in conclusion']
        )
        
        # Check for numbered or bulleted lists
        has_lists = any('1.' in p or '•' in p or '-' in p for p in paragraphs)
        
        return {
            'paragraph_count': len(paragraphs),
            'has_introduction': has_introduction,
            'has_conclusion': has_conclusion,
            'has_structured_lists': has_lists,
            'structure_score': self._calculate_structure_score(
                len(paragraphs), has_introduction, has_conclusion, has_lists
            )
        }
    
    def _calculate_similarity(self, response: str, expected: str) -> float:
        """Calculate semantic similarity between response and expected answer."""
        # Simple implementation using word overlap
        response_words = set(response.lower().split())
        expected_words = set(expected.lower().split())
        
        if not expected_words:
            return 0.0
        
        intersection = response_words.intersection(expected_words)
        union = response_words.union(expected_words)
        
        jaccard_similarity = len(intersection) / len(union) if union else 0.0
        return jaccard_similarity
    
    def _extract_citations_from_response(self, response: str) -> List[str]:
        """Extract citations from response text."""
        import re
        
        # Extract bracket citations
        bracket_citations = re.findall(r'\[([^\]]+)\]', response)
        
        # Extract section references
        section_refs = re.findall(r'(?i)(section\s+\d+(?:\.\d+)*)', response)
        
        # Extract clause references
        clause_refs = re.findall(r'(?i)(clause\s+\d+(?:\.\d+)*)', response)
        
        all_citations = bracket_citations + section_refs + clause_refs
        return list(set(all_citations))  # Remove duplicates
    
    def _verify_citation(self, citation: str, source_documents: List[Dict[str, Any]]) -> bool:
        """Verify if a citation exists in the source documents."""
        citation_lower = citation.lower()
        
        for doc in source_documents:
            doc_name = doc.get('document_name', '').lower()
            section_num = str(doc.get('section_number', '')).lower()
            
            # Check if citation matches document name or section
            if doc_name in citation_lower or section_num in citation_lower:
                return True
        
        return False
    
    def _calculate_conflict_handling_score(self, 
                                         acknowledgment: bool, 
                                         perspectives: int, 
                                         resolution: bool) -> float:
        """Calculate conflict handling score."""
        score = 0.0
        
        if acknowledgment:
            score += 0.4
        
        if perspectives >= 2:
            score += 0.3
        elif perspectives == 1:
            score += 0.15
        
        if resolution:
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_structure_score(self, 
                                 paragraphs: int, 
                                 intro: bool, 
                                 conclusion: bool, 
                                 lists: bool) -> float:
        """Calculate structure score."""
        score = 0.0
        
        # Paragraph structure
        if paragraphs >= 3:
            score += 0.3
        elif paragraphs >= 2:
            score += 0.2
        elif paragraphs >= 1:
            score += 0.1
        
        # Introduction and conclusion
        if intro:
            score += 0.25
        if conclusion:
            score += 0.25
        
        # Structured lists
        if lists:
            score += 0.2
        
        return min(score, 1.0)


class PerformanceEvaluator:
    """Evaluates system performance metrics like latency and throughput."""
    
    def __init__(self):
        """Initialize performance evaluator."""
        self.performance_logs = []
    
    def measure_end_to_end_latency(self, 
                                  query: str,
                                  response_generator) -> Dict[str, Any]:
        """
        Measure end-to-end response latency.
        
        Args:
            query: Test query
            response_generator: Response generator instance
            
        Returns:
            Latency measurements
        """
        start_time = time.time()
        
        # Generate response
        response = response_generator.generate_response(query)
        
        end_time = time.time()
        total_latency = end_time - start_time
        
        # Extract component latencies if available
        retrieval_time = response.get('response_time_seconds', 0.0)
        generation_time = total_latency - retrieval_time
        
        latency_data = {
            'query': query,
            'total_latency': total_latency,
            'retrieval_latency': retrieval_time,
            'generation_latency': generation_time,
            'timestamp': datetime.now().isoformat(),
            'response_length': len(response.get('answer', ''))
        }
        
        self.performance_logs.append(latency_data)
        
        return latency_data
    
    def benchmark_performance(self, 
                             test_queries: List[str],
                             response_generator,
                             iterations: int = 1) -> Dict[str, Any]:
        """
        Benchmark system performance across multiple queries.
        
        Args:
            test_queries: List of test queries
            response_generator: Response generator instance
            iterations: Number of iterations per query
            
        Returns:
            Comprehensive performance benchmark
        """
        all_measurements = []
        
        for query in test_queries:
            query_measurements = []
            
            for i in range(iterations):
                measurement = self.measure_end_to_end_latency(query, response_generator)
                query_measurements.append(measurement)
            
            all_measurements.extend(query_measurements)
        
        # Calculate aggregate statistics
        latencies = [m['total_latency'] for m in all_measurements]
        retrieval_times = [m['retrieval_latency'] for m in all_measurements]
        generation_times = [m['generation_latency'] for m in all_measurements]
        
        benchmark_results = {
            'total_queries': len(test_queries),
            'total_iterations': len(all_measurements),
            'latency_stats': {
                'mean': statistics.mean(latencies),
                'median': statistics.median(latencies),
                'std': statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
                'min': min(latencies),
                'max': max(latencies),
                'p95': self._percentile(latencies, 95),
                'p99': self._percentile(latencies, 99)
            },
            'retrieval_stats': {
                'mean': statistics.mean(retrieval_times),
                'median': statistics.median(retrieval_times)
            },
            'generation_stats': {
                'mean': statistics.mean(generation_times),
                'median': statistics.median(generation_times)
            },
            'throughput_qps': len(all_measurements) / sum(latencies),
            'measurements': all_measurements,
            'benchmark_timestamp': datetime.now().isoformat()
        }
        
        if logger:
            logger.info(f"Performance benchmark completed: "
                       f"Mean latency: {benchmark_results['latency_stats']['mean']:.2f}s, "
                       f"Throughput: {benchmark_results['throughput_qps']:.2f} QPS")
        
        return benchmark_results
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


def create_test_cases() -> List[Dict[str, Any]]:
    """Create sample test cases for evaluation."""
    return [
        {
            'query': 'What are the termination clauses in the contract?',
            'relevant_documents': ['contract_a.pdf', 'employment_agreement.docx'],
            'expected_sections': ['termination', 'clause 12', 'section 8']
        },
        {
            'query': 'What are the liability limitations?',
            'relevant_documents': ['contract_a.pdf', 'service_agreement.pdf'],
            'expected_sections': ['liability', 'limitation', 'clause 15']
        },
        {
            'query': 'What are the intellectual property rights?',
            'relevant_documents': ['ip_agreement.pdf', 'contract_b.docx'],
            'expected_sections': ['intellectual property', 'copyright', 'clause 7']
        }
    ]
