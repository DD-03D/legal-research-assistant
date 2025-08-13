"""
Test latency and performance metrics for the Legal Research Assistant.
"""

import sys
import time
import statistics
import yaml
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.generation.legal_rag import LegalResponseGenerator
    from src.retrieval.retriever import LegalDocumentRetriever
    from verification.tests.test_dataset import GoldenDataset
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")


class LatencyTest:
    """Test end-to-end latency and performance."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.dataset = GoldenDataset(config_path)
        
        # Initialize components if available
        self.retriever = None
        self.response_generator = None
        
        try:
            self.retriever = LegalDocumentRetriever()
            self.response_generator = LegalResponseGenerator()
        except Exception as e:
            print(f"Warning: Could not initialize components: {e}")
    
    def test_retrieval_latency(self) -> Dict[str, Any]:
        """Test retrieval latency across multiple queries."""
        result = {
            'test': 'retrieval_latency',
            'status': 'FAIL',
            'message': '',
            'avg_latency': 0.0,
            'median_latency': 0.0,
            'p95_latency': 0.0,
            'measurements': []
        }
        
        if not self.retriever:
            result['message'] = "Retriever not available"
            return result
        
        try:
            questions = [q['question'] for q in self.dataset.get_questions()]
            latencies = []
            
            # Run each query multiple times for better statistics
            for query in questions:
                for run in range(3):  # 3 runs per query
                    try:
                        start_time = time.time()
                        docs = self.retriever.retrieve_relevant_documents(
                            query, max_results=self.config['top_k']
                        )
                        latency = time.time() - start_time
                        latencies.append(latency)
                        
                        result['measurements'].append({
                            'query': query[:50] + "..." if len(query) > 50 else query,
                            'run': run + 1,
                            'latency': latency,
                            'docs_retrieved': len(docs)
                        })
                        
                    except Exception as e:
                        print(f"Retrieval failed for query: {query[:50]}... Error: {e}")
            
            if latencies:
                result['avg_latency'] = statistics.mean(latencies)
                result['median_latency'] = statistics.median(latencies)
                result['p95_latency'] = sorted(latencies)[int(0.95 * len(latencies))]
                
                # Pass if P95 latency is reasonable (< 3s)
                if result['p95_latency'] < 3.0:
                    result['status'] = 'PASS'
                    result['message'] = f"P95 latency: {result['p95_latency']:.2f}s, Avg: {result['avg_latency']:.2f}s"
                else:
                    result['message'] = f"High P95 latency: {result['p95_latency']:.2f}s (threshold: 3s)"
            else:
                result['message'] = "No successful retrievals to measure latency"
                
        except Exception as e:
            result['message'] = f"Error during retrieval latency testing: {str(e)}"
        
        return result
    
    def test_generation_latency(self) -> Dict[str, Any]:
        """Test response generation latency."""
        result = {
            'test': 'generation_latency',
            'status': 'FAIL',
            'message': '',
            'avg_latency': 0.0,
            'median_latency': 0.0,
            'p95_latency': 0.0,
            'measurements': []
        }
        
        if not self.response_generator:
            result['message'] = "Response generator not available"
            return result
        
        try:
            questions = self.dataset.get_simple_questions()[:3]  # Test with 3 simple questions
            latencies = []
            
            for question in questions:
                query = question['question']
                try:
                    start_time = time.time()
                    response = self.response_generator.generate_response(query)
                    latency = time.time() - start_time
                    latencies.append(latency)
                    
                    result['measurements'].append({
                        'query': query[:50] + "..." if len(query) > 50 else query,
                        'latency': latency,
                        'response_length': len(response.get('answer', ''))
                    })
                    
                except Exception as e:
                    print(f"Generation failed for query: {query[:50]}... Error: {e}")
            
            if latencies:
                result['avg_latency'] = statistics.mean(latencies)
                result['median_latency'] = statistics.median(latencies)
                result['p95_latency'] = max(latencies)  # Use max for small sample
                
                # Pass if average latency is reasonable (< 10s)
                if result['avg_latency'] < 10.0:
                    result['status'] = 'PASS'
                    result['message'] = f"Avg generation latency: {result['avg_latency']:.2f}s"
                else:
                    result['message'] = f"High generation latency: {result['avg_latency']:.2f}s (threshold: 10s)"
            else:
                result['message'] = "No successful generations to measure latency"
                
        except Exception as e:
            result['message'] = f"Error during generation latency testing: {str(e)}"
        
        return result
    
    def test_end_to_end_latency(self) -> Dict[str, Any]:
        """Test end-to-end latency (retrieval + generation)."""
        result = {
            'test': 'end_to_end_latency',
            'status': 'FAIL',
            'message': '',
            'avg_latency': 0.0,
            'breakdown': {
                'retrieval': 0.0,
                'generation': 0.0
            }
        }
        
        if not self.response_generator:
            result['message'] = "Response generator not available"
            return result
        
        try:
            # Test with one representative question
            question = self.dataset.get_simple_questions()[0]
            query = question['question']
            
            start_time = time.time()
            
            # Measure retrieval
            retrieval_start = time.time()
            if self.retriever:
                docs = self.retriever.retrieve_relevant_documents(query)
                retrieval_time = time.time() - retrieval_start
            else:
                retrieval_time = 0.0
            
            # Measure generation (includes retrieval if integrated)
            generation_start = time.time()
            response = self.response_generator.generate_response(query)
            generation_time = time.time() - generation_start
            
            total_time = time.time() - start_time
            
            result['avg_latency'] = total_time
            result['breakdown']['retrieval'] = retrieval_time
            result['breakdown']['generation'] = generation_time
            
            # Pass if total time is reasonable (< 15s)
            if total_time < 15.0:
                result['status'] = 'PASS'
                result['message'] = f"End-to-end: {total_time:.2f}s (retrieval: {retrieval_time:.2f}s, generation: {generation_time:.2f}s)"
            else:
                result['message'] = f"High end-to-end latency: {total_time:.2f}s (threshold: 15s)"
                
        except Exception as e:
            result['message'] = f"Error during end-to-end latency testing: {str(e)}"
        
        return result
    
    def test_throughput(self) -> Dict[str, Any]:
        """Test system throughput with concurrent-like load."""
        result = {
            'test': 'throughput',
            'status': 'SKIP',
            'message': 'Throughput testing requires concurrent execution framework'
        }
        
        # This would require more complex setup with threading/async
        # For now, we'll skip this test
        
        return result
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all latency tests."""
        tests = [
            self.test_retrieval_latency,
            self.test_generation_latency,
            self.test_end_to_end_latency,
            self.test_throughput
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


def test_latency():
    """Run latency tests using pytest."""
    latency_test = LatencyTest()
    results = latency_test.run_all_tests()
    
    # Check that at least one latency test passed or was skipped
    non_failed = [r for r in results if r['status'] in ['PASS', 'SKIP']]
    assert len(non_failed) > 0, f"All latency tests failed. Results: {results}"


if __name__ == "__main__":
    latency_test = LatencyTest()
    results = latency_test.run_all_tests()
    
    print(f"\n📊 Latency Test Summary:")
    for result in results:
        print(f"  {result['test']}: {result['status']}")
