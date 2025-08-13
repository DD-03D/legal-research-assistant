"""
Test citation formatting and conflict detection for the Legal Research Assistant.
"""

import sys
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple
from rapidfuzz import fuzz

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.generation.legal_rag import LegalResponseGenerator
    from src.utils import ConflictDetector
    from verification.tests.test_dataset import GoldenDataset
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")


class CitationAndConflictTest:
    """Test citation formatting and conflict detection."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.dataset = GoldenDataset(config_path)
        self.similarity_threshold = self.config['similarity_threshold']
        
        # Initialize components if available
        self.response_generator = None
        self.conflict_detector = None
        
        try:
            self.response_generator = LegalResponseGenerator()
            self.conflict_detector = ConflictDetector()
        except Exception as e:
            print(f"Warning: Could not initialize components: {e}")
    
    def extract_citations(self, text: str) -> List[str]:
        """Extract citations from response text."""
        # Look for common citation patterns
        patterns = [
            r'([A-Za-z_]+)[\s,]*[—-][\s,]*([A-Za-z]+\s+\d+)',  # Document — Section 1
            r'([A-Za-z_]+)[\s,]*,[\s,]*([A-Za-z]+\s+\d+)',      # Document, Section 1
            r'\[([A-Za-z_]+)[\s,]*[—-,][\s,]*([A-Za-z]+\s+\d+)\]',  # [Document — Section 1]
            r'([A-Za-z_]+)[\s,]*([A-Za-z]+\s+\d+)',             # Document Section 1
        ]
        
        citations = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    doc_name, section = match
                    citations.append(f"{doc_name.strip()}, {section.strip()}")
        
        return citations
    
    def test_citation_format(self) -> Dict[str, Any]:
        """Test that responses include proper section-specific citations."""
        result = {
            'test': 'citation_format',
            'status': 'FAIL',
            'message': '',
            'questions_tested': 0,
            'questions_with_citations': 0,
            'citation_details': []
        }
        
        if not self.response_generator:
            result['message'] = "Response generator not available"
            return result
        
        try:
            questions = self.dataset.get_simple_questions()  # Test simple questions first
            questions_with_citations = 0
            
            for question in questions:
                q_id = question['id']
                query = question['question']
                expected_citation = question['expected_citation']
                
                try:
                    response = self.response_generator.generate_response(query)
                    answer_text = response.get('answer', '')
                    
                    # Extract citations from response
                    found_citations = self.extract_citations(answer_text)
                    
                    # Check if expected citation pattern is present
                    has_valid_citation = False
                    if isinstance(expected_citation, str):
                        has_valid_citation = any(
                            fuzz.partial_ratio(expected_citation.lower(), citation.lower()) > 70
                            for citation in found_citations
                        )
                    elif isinstance(expected_citation, list):
                        has_valid_citation = any(
                            any(fuzz.partial_ratio(exp_cit.lower(), citation.lower()) > 70
                                for exp_cit in expected_citation)
                            for citation in found_citations
                        )
                    
                    if found_citations:
                        questions_with_citations += 1
                    
                    result['citation_details'].append({
                        'question_id': q_id,
                        'query': query,
                        'expected_citation': expected_citation,
                        'found_citations': found_citations,
                        'has_valid_citation': has_valid_citation,
                        'answer_snippet': answer_text[:200] + "..." if len(answer_text) > 200 else answer_text
                    })
                    
                except Exception as e:
                    result['citation_details'].append({
                        'question_id': q_id,
                        'query': query,
                        'error': str(e)
                    })
            
            result['questions_tested'] = len(questions)
            result['questions_with_citations'] = questions_with_citations
            
            citation_rate = questions_with_citations / len(questions) if questions else 0
            
            if citation_rate >= 0.8:  # 80% should have citations
                result['status'] = 'PASS'
                result['message'] = f"Citation rate: {citation_rate:.1%} ({questions_with_citations}/{len(questions)})"
            else:
                result['message'] = f"Low citation rate: {citation_rate:.1%} (threshold: 80%)"
                
        except Exception as e:
            result['message'] = f"Error during citation testing: {str(e)}"
        
        return result
    
    def test_section_specific_references(self) -> Dict[str, Any]:
        """Test that citations include specific section/clause references."""
        result = {
            'test': 'section_references',
            'status': 'FAIL',
            'message': '',
            'section_keywords_found': 0,
            'total_responses': 0
        }
        
        if not self.response_generator:
            result['message'] = "Response generator not available"
            return result
        
        try:
            questions = self.dataset.get_questions()[:3]  # Test subset
            section_keywords = ['clause', 'section', 'article', 'paragraph']
            section_keyword_count = 0
            
            for question in questions:
                query = question['question']
                try:
                    response = self.response_generator.generate_response(query)
                    answer_text = response.get('answer', '').lower()
                    
                    # Check for section-specific keywords
                    if any(keyword in answer_text for keyword in section_keywords):
                        section_keyword_count += 1
                        
                except Exception as e:
                    print(f"Response generation failed for: {query[:50]}... Error: {e}")
            
            result['section_keywords_found'] = section_keyword_count
            result['total_responses'] = len(questions)
            
            if section_keyword_count > 0:
                result['status'] = 'PASS'
                result['message'] = f"Found section keywords in {section_keyword_count}/{len(questions)} responses"
            else:
                result['message'] = "No section-specific keywords found in responses"
                
        except Exception as e:
            result['message'] = f"Error during section reference testing: {str(e)}"
        
        return result
    
    def test_conflict_detection(self) -> Dict[str, Any]:
        """Test conflict detection between multiple sources."""
        result = {
            'test': 'conflict_detection',
            'status': 'FAIL',
            'message': '',
            'conflict_questions_tested': 0,
            'conflicts_detected': 0,
            'conflict_details': []
        }
        
        if not self.response_generator:
            result['message'] = "Response generator not available"
            return result
        
        try:
            conflict_questions = self.dataset.get_conflict_questions()
            conflicts_detected = 0
            
            for question in conflict_questions:
                q_id = question['id']
                query = question['question']
                expected_docs = question['expected_docs']
                
                try:
                    response = self.response_generator.generate_response(query)
                    answer_text = response.get('answer', '')
                    
                    # Check if multiple sources are mentioned
                    sources_mentioned = []
                    for doc in expected_docs:
                        if doc.lower().replace('_', ' ') in answer_text.lower():
                            sources_mentioned.append(doc)
                    
                    # Look for conflict indicators
                    conflict_indicators = [
                        'however', 'but', 'while', 'whereas', 'different', 
                        'conflict', 'contradicts', 'differs', 'varies'
                    ]
                    
                    has_conflict_language = any(
                        indicator in answer_text.lower() 
                        for indicator in conflict_indicators
                    )
                    
                    conflict_detected = (
                        len(sources_mentioned) >= 2 and 
                        has_conflict_language
                    )
                    
                    if conflict_detected:
                        conflicts_detected += 1
                    
                    result['conflict_details'].append({
                        'question_id': q_id,
                        'query': query,
                        'expected_docs': expected_docs,
                        'sources_mentioned': sources_mentioned,
                        'has_conflict_language': has_conflict_language,
                        'conflict_detected': conflict_detected,
                        'answer_snippet': answer_text[:300] + "..." if len(answer_text) > 300 else answer_text
                    })
                    
                except Exception as e:
                    result['conflict_details'].append({
                        'question_id': q_id,
                        'query': query,
                        'error': str(e)
                    })
            
            result['conflict_questions_tested'] = len(conflict_questions)
            result['conflicts_detected'] = conflicts_detected
            
            if len(conflict_questions) > 0:
                conflict_rate = conflicts_detected / len(conflict_questions)
                if conflict_rate >= 0.5:  # 50% of conflict questions should detect conflicts
                    result['status'] = 'PASS'
                    result['message'] = f"Conflict detection rate: {conflict_rate:.1%} ({conflicts_detected}/{len(conflict_questions)})"
                else:
                    result['message'] = f"Low conflict detection rate: {conflict_rate:.1%} (threshold: 50%)"
            else:
                result['status'] = 'SKIP'
                result['message'] = "No conflict questions to test"
                
        except Exception as e:
            result['message'] = f"Error during conflict detection testing: {str(e)}"
        
        return result
    
    def test_legal_terminology(self) -> Dict[str, Any]:
        """Test that responses use proper legal terminology."""
        result = {
            'test': 'legal_terminology',
            'status': 'FAIL',
            'message': '',
            'terminology_score': 0.0
        }
        
        if not self.response_generator:
            result['message'] = "Response generator not available"
            return result
        
        try:
            questions = self.dataset.get_questions()[:3]  # Test subset
            legal_terms = [
                'clause', 'section', 'statute', 'contract', 'agreement',
                'obligation', 'party', 'breach', 'material', 'notice',
                'delivery', 'payment', 'termination'
            ]
            
            total_responses = 0
            responses_with_legal_terms = 0
            
            for question in questions:
                query = question['question']
                try:
                    response = self.response_generator.generate_response(query)
                    answer_text = response.get('answer', '').lower()
                    
                    # Check for legal terminology
                    if any(term in answer_text for term in legal_terms):
                        responses_with_legal_terms += 1
                    
                    total_responses += 1
                    
                except Exception as e:
                    print(f"Response generation failed for: {query[:50]}... Error: {e}")
            
            if total_responses > 0:
                result['terminology_score'] = responses_with_legal_terms / total_responses
                
                if result['terminology_score'] >= 0.7:  # 70% should use legal terms
                    result['status'] = 'PASS'
                    result['message'] = f"Legal terminology usage: {result['terminology_score']:.1%}"
                else:
                    result['message'] = f"Low legal terminology usage: {result['terminology_score']:.1%} (threshold: 70%)"
            else:
                result['message'] = "No responses generated to test terminology"
                
        except Exception as e:
            result['message'] = f"Error during terminology testing: {str(e)}"
        
        return result
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all citation and conflict tests."""
        tests = [
            self.test_citation_format,
            self.test_section_specific_references,
            self.test_conflict_detection,
            self.test_legal_terminology
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


def test_citations_and_conflicts():
    """Run citation and conflict tests using pytest."""
    test_suite = CitationAndConflictTest()
    results = test_suite.run_all_tests()
    
    # At least terminology test should pass
    passed_tests = [r for r in results if r['status'] == 'PASS']
    assert len(passed_tests) > 0, f"No citation/conflict tests passed. Results: {results}"


if __name__ == "__main__":
    test_suite = CitationAndConflictTest()
    results = test_suite.run_all_tests()
    
    print(f"\n📊 Citation & Conflict Test Summary:")
    for result in results:
        print(f"  {result['test']}: {result['status']}")
