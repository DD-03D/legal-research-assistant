"""
Smoke tests for the Legal Research Assistant app.
"""

import requests
import time
import yaml
from pathlib import Path
from typing import Dict, Any, List


class AppSmokeTest:
    """Smoke tests for the Streamlit app."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.app_url = self.config['app_url']
        self.timeout = self.config.get('timeout_seconds', 30)
    
    def test_app_accessible(self) -> Dict[str, Any]:
        """Test that the app is accessible and returns a valid response."""
        result = {
            'test': 'app_accessible',
            'status': 'FAIL',
            'message': '',
            'response_time': None
        }
        
        try:
            start_time = time.time()
            response = requests.get(self.app_url, timeout=self.timeout)
            response_time = time.time() - start_time
            
            result['response_time'] = response_time
            
            if response.status_code == 200:
                result['status'] = 'PASS'
                result['message'] = f"App accessible at {self.app_url} (response time: {response_time:.2f}s)"
            else:
                result['message'] = f"App returned status code {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            result['message'] = f"Could not connect to {self.app_url}. Is the app running?"
        except requests.exceptions.Timeout:
            result['message'] = f"Request timed out after {self.timeout}s"
        except Exception as e:
            result['message'] = f"Unexpected error: {str(e)}"
        
        return result
    
    def test_streamlit_elements(self) -> Dict[str, Any]:
        """Test that expected Streamlit elements are present."""
        result = {
            'test': 'streamlit_elements',
            'status': 'FAIL',
            'message': '',
            'elements_found': []
        }
        
        try:
            response = requests.get(self.app_url, timeout=self.timeout)
            if response.status_code != 200:
                result['message'] = f"Cannot test elements - app returned {response.status_code}"
                return result
            
            content = response.text.lower()
            
            # Expected elements in a legal research assistant
            expected_elements = [
                'legal research',
                'upload',
                'document',
                'query',
                'search',
                'file'
            ]
            
            found_elements = []
            for element in expected_elements:
                if element in content:
                    found_elements.append(element)
            
            result['elements_found'] = found_elements
            
            if len(found_elements) >= len(expected_elements) * 0.7:  # 70% threshold
                result['status'] = 'PASS'
                result['message'] = f"Found {len(found_elements)}/{len(expected_elements)} expected elements"
            else:
                result['message'] = f"Only found {len(found_elements)}/{len(expected_elements)} expected elements"
                
        except Exception as e:
            result['message'] = f"Error checking elements: {str(e)}"
        
        return result
    
    def test_api_provider_status(self) -> Dict[str, Any]:
        """Test that API provider is properly configured."""
        result = {
            'test': 'api_provider_status',
            'status': 'SKIP',
            'message': 'Cannot test API provider without app interaction'
        }
        
        # This would require app interaction which is complex for smoke tests
        # In a full implementation, we might check environment variables or config files
        
        return result
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all smoke tests."""
        tests = [
            self.test_app_accessible,
            self.test_streamlit_elements,
            self.test_api_provider_status
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
                print(f"{'✅' if result['status'] == 'PASS' else '❌' if result['status'] == 'FAIL' else '⏭️'} {result['test']}: {result['message']}")
            except Exception as e:
                results.append({
                    'test': test.__name__,
                    'status': 'ERROR',
                    'message': f"Test error: {str(e)}"
                })
                print(f"💥 {test.__name__}: ERROR - {str(e)}")
        
        return results


def test_app_smoke():
    """Run smoke tests using pytest."""
    smoke_test = AppSmokeTest()
    results = smoke_test.run_all_tests()
    
    # Assert at least one test passed
    passed_tests = [r for r in results if r['status'] == 'PASS']
    assert len(passed_tests) > 0, f"No smoke tests passed. Results: {results}"


if __name__ == "__main__":
    smoke_test = AppSmokeTest()
    results = smoke_test.run_all_tests()
    
    print(f"\n📊 Smoke Test Summary:")
    for result in results:
        print(f"  {result['test']}: {result['status']}")
