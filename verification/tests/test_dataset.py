"""
Golden dataset for testing Legal Research Assistant.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, List, Any


class GoldenDataset:
    """Manages golden questions and expected responses for testing."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.questions = self.config['golden_questions']
    
    def get_questions(self) -> List[Dict[str, Any]]:
        """Get all golden questions."""
        return self.questions
    
    def get_question_by_id(self, question_id: str) -> Dict[str, Any]:
        """Get a specific question by ID."""
        for q in self.questions:
            if q['id'] == question_id:
                return q
        raise ValueError(f"Question {question_id} not found")
    
    def get_conflict_questions(self) -> List[Dict[str, Any]]:
        """Get questions that should test conflict handling."""
        return [q for q in self.questions if q.get('conflict_aware', False)]
    
    def get_simple_questions(self) -> List[Dict[str, Any]]:
        """Get questions with single expected answers."""
        return [q for q in self.questions if not q.get('conflict_aware', False)]


def test_dataset_structure():
    """Test that the golden dataset is properly structured."""
    dataset = GoldenDataset()
    
    # Test that we have questions
    questions = dataset.get_questions()
    assert len(questions) > 0, "No golden questions found"
    
    # Test question structure
    for i, q in enumerate(questions):
        assert 'id' in q, f"Question {i} missing 'id'"
        assert 'question' in q, f"Question {i} missing 'question'"
        assert 'expected_answer' in q, f"Question {i} missing 'expected_answer'"
        assert 'expected_citation' in q, f"Question {i} missing 'expected_citation'"
        assert 'expected_docs' in q, f"Question {i} missing 'expected_docs'"
        
        # Test types
        assert isinstance(q['question'], str), f"Question {i} 'question' not string"
        assert isinstance(q['expected_docs'], list), f"Question {i} 'expected_docs' not list"
    
    print(f"✅ Dataset contains {len(questions)} well-structured questions")


def test_conflict_questions():
    """Test that conflict questions are properly marked."""
    dataset = GoldenDataset()
    
    conflict_questions = dataset.get_conflict_questions()
    simple_questions = dataset.get_simple_questions()
    
    assert len(conflict_questions) > 0, "No conflict-aware questions found"
    assert len(simple_questions) > 0, "No simple questions found"
    
    # Conflict questions should expect multiple citations
    for q in conflict_questions:
        citations = q['expected_citation']
        assert isinstance(citations, list), f"Conflict question {q['id']} should have list of citations"
        assert len(citations) >= 2, f"Conflict question {q['id']} should have multiple citations"
    
    print(f"✅ Found {len(conflict_questions)} conflict questions and {len(simple_questions)} simple questions")


if __name__ == "__main__":
    test_dataset_structure()
    test_conflict_questions()
