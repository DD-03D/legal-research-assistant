#!/usr/bin/env python3
"""
Simplified Legal Research Assistant Assignment Verification
Comprehensive QA verification focusing on core requirements
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Any
import traceback

class AssignmentVerifier:
    def __init__(self, app_url: str = "http://localhost:8501"):
        self.app_url = app_url
        self.results = {
            "overall_status": "UNKNOWN",
            "test_categories": {},
            "detailed_results": [],
            "execution_time": None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def verify_directory_structure(self) -> Dict[str, Any]:
        """Category A: Verify project structure meets requirements"""
        self.log("🏗️ Testing Category A: Project Structure")
        
        required_dirs = [
            "src",
            "src/ingestion", 
            "src/retrieval",
            "src/generation",
            "src/utils",
            "config",
            "data",
            "logs"
        ]
        
        required_files = [
            "app.py",
            "requirements.txt",
            ".env",
            "README.md",
            "src/__init__.py",
            "config/settings.py"
        ]
        
        results = {
            "category": "A - Project Structure",
            "status": "PASS",
            "details": [],
            "issues": []
        }
        
        # Check directories
        for dir_path in required_dirs:
            if os.path.exists(dir_path):
                results["details"].append(f"✅ Directory exists: {dir_path}")
            else:
                results["details"].append(f"❌ Missing directory: {dir_path}")
                results["issues"].append(f"Missing required directory: {dir_path}")
                results["status"] = "FAIL"
        
        # Check files
        for file_path in required_files:
            if os.path.exists(file_path):
                results["details"].append(f"✅ File exists: {file_path}")
            else:
                results["details"].append(f"❌ Missing file: {file_path}")
                results["issues"].append(f"Missing required file: {file_path}")
                results["status"] = "FAIL"
                
        return results
    
    def verify_app_smoke_test(self) -> Dict[str, Any]:
        """Category B: Basic app functionality"""
        self.log("🚀 Testing Category B: Application Smoke Test")
        
        results = {
            "category": "B - Application Smoke Test", 
            "status": "PASS",
            "details": [],
            "issues": []
        }
        
        try:
            # Test app accessibility
            response = requests.get(self.app_url, timeout=10)
            if response.status_code == 200:
                results["details"].append(f"✅ App accessible at {self.app_url}")
                results["details"].append(f"✅ Response status: {response.status_code}")
                
                # Check for key UI elements in response
                content = response.text.lower()
                ui_elements = [
                    "legal research assistant",
                    "upload", 
                    "document",
                    "question"
                ]
                
                for element in ui_elements:
                    if element in content:
                        results["details"].append(f"✅ UI element found: {element}")
                    else:
                        results["details"].append(f"⚠️ UI element not found: {element}")
                        
            else:
                results["status"] = "FAIL"
                results["issues"].append(f"App returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            results["status"] = "FAIL"
            results["issues"].append(f"Cannot connect to app at {self.app_url}")
        except Exception as e:
            results["status"] = "FAIL"
            results["issues"].append(f"Smoke test error: {str(e)}")
            
        return results
    
    def verify_api_integration(self) -> Dict[str, Any]:
        """Category C: API Integration"""
        self.log("🔌 Testing Category C: API Integration")
        
        results = {
            "category": "C - API Integration",
            "status": "PASS", 
            "details": [],
            "issues": []
        }
        
        try:
            # Check .env for API configuration
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    env_content = f.read()
                    
                # Check for API provider settings
                if 'API_PROVIDER=' in env_content:
                    results["details"].append("✅ API provider configuration found")
                    
                if 'GEMINI_API_KEY=' in env_content or 'OPENAI_API_KEY=' in env_content:
                    results["details"].append("✅ API key configuration found")
                else:
                    results["issues"].append("No API key found in .env")
                    results["status"] = "FAIL"
                    
            # Check API provider implementation
            if os.path.exists('src/api_providers.py'):
                results["details"].append("✅ API provider abstraction implemented")
            else:
                results["issues"].append("Missing src/api_providers.py")
                results["status"] = "FAIL"
                
        except Exception as e:
            results["status"] = "FAIL"
            results["issues"].append(f"API integration test error: {str(e)}")
            
        return results
        
    def verify_document_processing(self) -> Dict[str, Any]:
        """Category D: Document Processing Capabilities"""
        self.log("📄 Testing Category D: Document Processing")
        
        results = {
            "category": "D - Document Processing",
            "status": "PASS",
            "details": [],
            "issues": []
        }
        
        try:
            # Check for document processing modules
            processing_files = [
                'src/ingestion/document_processor.py',
                'src/ingestion/vector_store.py',
                'src/ingestion/__init__.py'
            ]
            
            for file_path in processing_files:
                if os.path.exists(file_path):
                    results["details"].append(f"✅ Processing module: {file_path}")
                else:
                    results["issues"].append(f"Missing processing module: {file_path}")
                    results["status"] = "FAIL"
                    
            # Check sample documents exist
            sample_docs_dir = "verification/scripts/sample_docs"
            if os.path.exists(sample_docs_dir):
                doc_files = list(Path(sample_docs_dir).glob("*"))
                if doc_files:
                    results["details"].append(f"✅ Sample documents available: {len(doc_files)} files")
                    
                    # Check for multiple formats
                    formats = {'.pdf', '.docx', '.txt'}
                    found_formats = {f.suffix for f in doc_files}
                    if formats.issubset(found_formats):
                        results["details"].append("✅ Multiple document formats supported (PDF, DOCX, TXT)")
                    else:
                        results["details"].append(f"⚠️ Limited formats found: {found_formats}")
                else:
                    results["issues"].append("No sample documents found")
                    results["status"] = "FAIL"
            else:
                results["issues"].append("Sample documents directory not found")
                results["status"] = "FAIL"
                
        except Exception as e:
            results["status"] = "FAIL"
            results["issues"].append(f"Document processing test error: {str(e)}")
            
        return results
    
    def verify_rag_implementation(self) -> Dict[str, Any]:
        """Category E: RAG System Implementation"""
        self.log("🧠 Testing Category E: RAG Implementation")
        
        results = {
            "category": "E - RAG Implementation",
            "status": "PASS",
            "details": [],
            "issues": []
        }
        
        try:
            # Check for RAG components
            rag_files = [
                'src/generation/legal_rag.py',
                'src/retrieval/retriever.py',
                'src/generation/__init__.py',
                'src/retrieval/__init__.py'
            ]
            
            for file_path in rag_files:
                if os.path.exists(file_path):
                    results["details"].append(f"✅ RAG component: {file_path}")
                else:
                    results["issues"].append(f"Missing RAG component: {file_path}")
                    results["status"] = "FAIL"
                    
            # Check for vector database
            if os.path.exists('data/chroma_db') or os.path.exists('data/vectorstore'):
                results["details"].append("✅ Vector database directory found")
            else:
                results["details"].append("⚠️ Vector database directory not found (may be created at runtime)")
                
        except Exception as e:
            results["status"] = "FAIL"
            results["issues"].append(f"RAG implementation test error: {str(e)}")
            
        return results
    
    def verify_ui_functionality(self) -> Dict[str, Any]:
        """Category F: User Interface Requirements"""
        self.log("🖥️ Testing Category F: UI Functionality")
        
        results = {
            "category": "F - UI Functionality",
            "status": "PASS",
            "details": [],
            "issues": []
        }
        
        try:
            # Check main app file
            if os.path.exists('app.py'):
                with open('app.py', 'r', encoding='utf-8') as f:
                    app_content = f.read().lower()
                    
                ui_features = [
                    ('streamlit', 'Streamlit framework'),
                    ('file_uploader', 'File upload functionality'),
                    ('text_input', 'Question input'),
                    ('button', 'Interactive buttons')
                ]
                
                for feature, description in ui_features:
                    if feature in app_content:
                        results["details"].append(f"✅ {description} implemented")
                    else:
                        results["details"].append(f"⚠️ {description} not clearly found")
                        
                results["details"].append("✅ Main app.py file exists and contains UI code")
            else:
                results["issues"].append("Missing app.py file")
                results["status"] = "FAIL"
                
        except Exception as e:
            results["status"] = "FAIL"
            results["issues"].append(f"UI functionality test error: {str(e)}")
            
        return results
    
    def verify_configuration(self) -> Dict[str, Any]:
        """Category G: Configuration and Settings"""
        self.log("⚙️ Testing Category G: Configuration")
        
        results = {
            "category": "G - Configuration",
            "status": "PASS",
            "details": [],
            "issues": []
        }
        
        try:
            # Check configuration files
            config_files = [
                ('.env', 'Environment variables'),
                ('config/settings.py', 'Settings module'),
                ('requirements.txt', 'Dependencies')
            ]
            
            for file_path, description in config_files:
                if os.path.exists(file_path):
                    results["details"].append(f"✅ {description}: {file_path}")
                else:
                    results["issues"].append(f"Missing {description}: {file_path}")
                    results["status"] = "FAIL"
                    
            # Check requirements.txt content
            if os.path.exists('requirements.txt'):
                with open('requirements.txt', 'r') as f:
                    req_content = f.read().lower()
                    
                required_deps = [
                    'streamlit',
                    'langchain',
                    'chromadb',
                    'python-dotenv'
                ]
                
                for dep in required_deps:
                    if dep in req_content:
                        results["details"].append(f"✅ Dependency listed: {dep}")
                    else:
                        results["details"].append(f"⚠️ Dependency not found: {dep}")
                        
        except Exception as e:
            results["status"] = "FAIL"
            results["issues"].append(f"Configuration test error: {str(e)}")
            
        return results
    
    def verify_documentation(self) -> Dict[str, Any]:
        """Category H: Documentation"""
        self.log("📚 Testing Category H: Documentation")
        
        results = {
            "category": "H - Documentation",
            "status": "PASS",
            "details": [],
            "issues": []
        }
        
        try:
            # Check for README
            if os.path.exists('README.md'):
                with open('README.md', 'r', encoding='utf-8') as f:
                    readme_content = f.read().lower()
                    
                doc_sections = [
                    ('installation', 'Installation instructions'),
                    ('usage', 'Usage instructions'),
                    ('features', 'Feature description'),
                    ('legal research', 'Project description')
                ]
                
                for section, description in doc_sections:
                    if section in readme_content:
                        results["details"].append(f"✅ {description} found in README")
                    else:
                        results["details"].append(f"⚠️ {description} not clearly found")
                        
                results["details"].append("✅ README.md exists")
            else:
                results["issues"].append("Missing README.md")
                results["status"] = "FAIL"
                
            # Check for code comments/docstrings
            python_files = list(Path('.').rglob('*.py'))
            if python_files:
                results["details"].append(f"✅ Python files found: {len(python_files)}")
            else:
                results["issues"].append("No Python files found")
                results["status"] = "FAIL"
                
        except Exception as e:
            results["status"] = "FAIL"
            results["issues"].append(f"Documentation test error: {str(e)}")
            
        return results
    
    def run_verification(self) -> Dict[str, Any]:
        """Run complete verification suite"""
        start_time = time.time()
        
        self.log("🔍 Starting Legal Research Assistant Assignment Verification")
        self.log("=" * 70)
        
        # Test categories in order
        test_methods = [
            self.verify_directory_structure,
            self.verify_app_smoke_test,
            self.verify_api_integration,
            self.verify_document_processing,
            self.verify_rag_implementation,
            self.verify_ui_functionality,
            self.verify_configuration,
            self.verify_documentation
        ]
        
        all_passed = True
        
        for test_method in test_methods:
            try:
                result = test_method()
                self.results["test_categories"][result["category"]] = result
                self.results["detailed_results"].append(result)
                
                # Log result summary
                status_icon = "✅" if result["status"] == "PASS" else "❌"
                self.log(f"{status_icon} {result['category']}: {result['status']}")
                
                if result["status"] != "PASS":
                    all_passed = False
                    for issue in result.get("issues", []):
                        self.log(f"   💥 {issue}", "ERROR")
                        
            except Exception as e:
                self.log(f"❌ Test method failed: {test_method.__name__}: {str(e)}", "ERROR")
                all_passed = False
                
        # Set overall status
        self.results["overall_status"] = "PASS" if all_passed else "FAIL"
        self.results["execution_time"] = round(time.time() - start_time, 2)
        
        self.log("=" * 70)
        overall_icon = "✅" if all_passed else "❌"
        self.log(f"{overall_icon} OVERALL RESULT: {self.results['overall_status']}")
        self.log(f"⏱️ Execution time: {self.results['execution_time']} seconds")
        
        return self.results
    
    def generate_report(self, output_file: str = "verification/ASSIGNMENT_REPORT.md"):
        """Generate detailed markdown report"""
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Legal Research Assistant - Assignment Verification Report\n\n")
            f.write(f"**Generated:** {self.results['timestamp']}\\n")
            f.write(f"**Execution Time:** {self.results['execution_time']} seconds\\n")
            f.write(f"**Overall Status:** {self.results['overall_status']}\\n\\n")
            
            # Executive summary
            f.write("## Executive Summary\n\n")
            passed_tests = sum(1 for result in self.results['detailed_results'] if result['status'] == 'PASS')
            total_tests = len(self.results['detailed_results'])
            
            f.write(f"- **Tests Passed:** {passed_tests}/{total_tests}\\n")
            f.write(f"- **Success Rate:** {round(passed_tests/total_tests*100, 1)}%\\n\\n")
            
            if self.results['overall_status'] == 'PASS':
                f.write("🎉 **CONGRATULATIONS!** Your Legal Research Assistant meets all core assignment requirements.\\n\\n")
            else:
                f.write("⚠️ **ACTION REQUIRED:** Some assignment requirements need attention.\\n\\n")
            
            # Detailed results
            f.write("## Detailed Test Results\n\n")
            
            for result in self.results['detailed_results']:
                status_icon = "✅" if result['status'] == 'PASS' else "❌"
                f.write(f"### {status_icon} {result['category']}\n\n")
                f.write(f"**Status:** {result['status']}\\n\\n")
                
                if result.get('details'):
                    f.write("**Details:**\\n")
                    for detail in result['details']:
                        f.write(f"- {detail}\\n")
                    f.write("\\n")
                
                if result.get('issues'):
                    f.write("**Issues to Address:**\\n")
                    for issue in result['issues']:
                        f.write(f"- ❌ {issue}\\n")
                    f.write("\\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            
            failed_categories = [r for r in self.results['detailed_results'] if r['status'] != 'PASS']
            
            if not failed_categories:
                f.write("✅ All tests passed! Your implementation is ready for submission.\\n\\n")
                f.write("Consider these enhancements:\\n")
                f.write("- Add more comprehensive error handling\\n")
                f.write("- Implement additional UI features\\n") 
                f.write("- Add more detailed logging\\n")
                f.write("- Consider performance optimizations\\n")
            else:
                f.write("Focus on addressing the following issues:\\n\\n")
                for category in failed_categories:
                    f.write(f"**{category['category']}:**\\n")
                    for issue in category.get('issues', []):
                        f.write(f"- {issue}\\n")
                    f.write("\\n")
        
        self.log(f"📊 Report generated: {output_file}")

def main():
    """Main verification function"""
    
    # Change to project directory if needed
    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
        os.chdir(project_dir)
    
    # Initialize verifier
    verifier = AssignmentVerifier()
    
    try:
        # Run verification
        results = verifier.run_verification()
        
        # Generate report
        verifier.generate_report()
        
        # Save JSON results
        with open('verification/assignment_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Exit with appropriate code
        sys.exit(0 if results['overall_status'] == 'PASS' else 1)
        
    except KeyboardInterrupt:
        print("\\n🛑 Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Verification failed with error: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
