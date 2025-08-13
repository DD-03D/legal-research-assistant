"""
Test retrieval accuracy and metrics for the Legal Research Assistant.
"""

import sys
import os
import time
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple
from rapidfuzz import fuzz

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.ingestion.vector_store import DocumentIngestionPipeline
    from src.retrieval.retriever import LegalDocumentRetriever
    from verification.tests.test_dataset import GoldenDataset
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")


class RetrievalMetrics:
    """Test retrieval accuracy and compute metrics."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.dataset = GoldenDataset(config_path)
        self.top_k = self.config['top_k']
        self.similarity_threshold = self.config['similarity_threshold']
        
        # Initialize components if available
        self.retriever = None
        self.ingestion_pipeline = None
        
        try:
            self.ingestion_pipeline = DocumentIngestionPipeline()
            self.retriever = LegalDocumentRetriever()
        except Exception as e:
            print(f"Warning: Could not initialize retrieval components: {e}")
    
    def setup_test_documents(self) -> Dict[str, Any]:
        """Ingest test documents into the vector store."""
        result = {
            'test': 'setup_documents',
            'status': 'FAIL',
            'message': '',
            'documents_processed': 0
        }
        
        if not self.ingestion_pipeline:
            result['message'] = "Ingestion pipeline not available"
            return result
        
        try:
            docs_path = Path(self.config['docs_path'])
            if not docs_path.exists():
                result['message'] = f"Documents path does not exist: {docs_path}"
                return result
            
            processed_count = 0
            for doc_file in docs_path.glob("*.txt"):  # Start with TXT files for simplicity
                try:
                    self.ingestion_pipeline.ingest_file(str(doc_file))
                    processed_count += 1
                except Exception as e:
                    print(f"Failed to process {doc_file}: {e}")
            
            result['documents_processed'] = processed_count
            if processed_count > 0:
                result['status'] = 'PASS'
                result['message'] = f"Processed {processed_count} documents"
            else:
                result['message'] = "No documents were processed successfully"
                
        except Exception as e:
            result['message'] = f"Error during document setup: {str(e)}"
        
        return result
    
    def test_retrieval_accuracy(self) -> Dict[str, Any]:
        """Test retrieval accuracy for golden questions."""
        result = {
            'test': 'retrieval_accuracy',
            'status': 'FAIL',
            'message': '',
            'accuracy_at_k': 0.0,
            'questions_tested': 0,
            'questions_passed': 0,
            'details': []
        }
        
        if not self.retriever:
            result['message'] = "Retriever not available"
            return result
        
        try:
            questions = self.dataset.get_questions()
            questions_passed = 0
            
            for question in questions:
                q_id = question['id']
                query = question['question']
                expected_docs = question['expected_docs']
                
                try:
                    # Retrieve relevant documents
                    start_time = time.time()
                    retrieved_docs = self.retriever.retrieve_relevant_documents(
                        query, max_results=self.top_k
                    )
                    retrieval_time = time.time() - start_time
                    
                    # Check if expected documents are in top-k
                    retrieved_doc_names = [
                        doc.get('source', '').split('.')[0] for doc in retrieved_docs
                    ]
                    
                    found_expected = any(
                        any(exp_doc in ret_doc for exp_doc in expected_docs)
                        for ret_doc in retrieved_doc_names
                    )
                    
                    if found_expected:
                        questions_passed += 1
                    
                    result['details'].append({
                        'question_id': q_id,
                        'query': query,
                        'expected_docs': expected_docs,
                        'retrieved_docs': retrieved_doc_names[:3],  # Top 3
                        'found_expected': found_expected,
                        'retrieval_time': retrieval_time
                    })
                    
                except Exception as e:
                    result['details'].append({
                        'question_id': q_id,
                        'query': query,
                        'error': str(e)
                    })
            
            result['questions_tested'] = len(questions)
            result['questions_passed'] = questions_passed
            result['accuracy_at_k'] = questions_passed / len(questions) if questions else 0
            
            if result['accuracy_at_k'] >= 0.7:  # 70% threshold
                result['status'] = 'PASS'
                result['message'] = f"Accuracy@{self.top_k}: {result['accuracy_at_k']:.2%}"
            else:
                result['message'] = f"Low accuracy@{self.top_k}: {result['accuracy_at_k']:.2%} (threshold: 70%)"
                
        except Exception as e:
            result['message'] = f"Error during retrieval testing: {str(e)}"
        
        return result
    
    def test_context_precision(self) -> Dict[str, Any]:
        """Test context precision - how relevant retrieved documents are."""
        result = {
            'test': 'context_precision',
            'status': 'SKIP',
            'message': 'Context precision requires manual relevance judgments',
            'precision': 0.0
        }
        
        # This would require manual annotation of relevance
        # For now, we'll use a simple heuristic based on document matching
        
        return result
    
    def test_latency(self) -> Dict[str, Any]:
        """Test retrieval latency."""
        result = {
            'test': 'retrieval_latency',
            'status': 'FAIL',
            'message': '',
            'avg_latency': 0.0,
            'max_latency': 0.0,
            'min_latency': 0.0
        }
        
        if not self.retriever:
            result['message'] = "Retriever not available"
            return result
        
        try:
            test_queries = [q['question'] for q in self.dataset.get_questions()]
            latencies = []
            
            for query in test_queries:
                start_time = time.time()
                try:
                    self.retriever.retrieve_relevant_documents(query, max_results=self.top_k)
                    latency = time.time() - start_time
                    latencies.append(latency)
                except Exception as e:
                    print(f"Query failed: {query[:50]}... Error: {e}")
            
            if latencies:
                result['avg_latency'] = sum(latencies) / len(latencies)
                result['max_latency'] = max(latencies)
                result['min_latency'] = min(latencies)
                
                # Pass if average latency is reasonable (< 5s)
                if result['avg_latency'] < 5.0:
                    result['status'] = 'PASS'
                    result['message'] = f"Avg latency: {result['avg_latency']:.2f}s"
                else:
                    result['message'] = f"High latency: {result['avg_latency']:.2f}s (threshold: 5s)"
            else:
                result['message'] = "No successful retrievals to measure latency"
                
        except Exception as e:
            result['message'] = f"Error during latency testing: {str(e)}"
        
        return result
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all retrieval metric tests."""
        tests = [
            self.setup_test_documents,
            self.test_retrieval_accuracy,
            self.test_context_precision,
            self.test_latency
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
                status_emoji = '✅' if result['status'] == 'PASS' else '❌' if result['status'] == 'FAIL' else '⏭️'
                print(f"{status_emoji} {result['test']}: {result['message']}")
            except Exception as e:
                results.append({
                    'test': test.__name__,
                    'status': 'ERROR',
                    'message': f"Test error: {str(e)}"
                })
                print(f"💥 {test.__name__}: ERROR - {str(e)}")
        
        return results


def test_retrieval_metrics():
    """Run retrieval metrics tests using pytest."""
    metrics = RetrievalMetrics()
    results = metrics.run_all_tests()
    
    # At least setup should pass
    setup_results = [r for r in results if r['test'] == 'setup_documents' and r['status'] == 'PASS']
    assert len(setup_results) > 0, "Document setup failed"


if __name__ == "__main__":
    metrics = RetrievalMetrics()
    results = metrics.run_all_tests()
    
    print(f"\n📊 Retrieval Metrics Summary:")
    for result in results:
        print(f"  {result['test']}: {result['status']}")
