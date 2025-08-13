"""
Utility functions and shared components for the Legal Research Assistant.
"""

import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import tiktoken
from config.settings import settings

# Import SQLite fix utilities
try:
    from .sqlite_fix import fix_sqlite, get_sqlite_info
    __all__ = ['DocumentUtils', 'CitationFormatter', 'ConflictDetector', 
               'setup_logging', 'validate_file_type', 'format_file_size',
               'fix_sqlite', 'get_sqlite_info']
except ImportError:
    __all__ = ['DocumentUtils', 'CitationFormatter', 'ConflictDetector', 
               'setup_logging', 'validate_file_type', 'format_file_size']


class DocumentUtils:
    """Utility functions for document processing."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text content."""
        try:
            # Remove excessive whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove special characters but preserve legal formatting - properly escaped
            text = re.sub(r'[^\w\s\.\,\;\:\!\?\(\)\[\]\"\'%\$&\-]', '', text)
            
            # Normalize quotes
            text = re.sub(r'["""]', '"', text)
            text = re.sub(r'['']', "'", text)
            
            return text.strip()
        except re.error as e:
            if logger:
                logger.warning(f"Text cleaning error: {e}, returning original text")
            return text.strip()
    
    @staticmethod
    def extract_sections(text: str) -> List[Dict[str, Any]]:
        """Extract legal sections from text based on common patterns."""
        sections = []
        
        # Common legal section patterns - made safer
        patterns = [
            r'(?i)section\s+(\d+(?:\.\d+)*)[:\.]?\s*(.*?)(?=section\s+\d+|$)',
            r'(?i)clause\s+(\d+(?:\.\d+)*)[:\.]?\s*(.*?)(?=clause\s+\d+|$)',
            r'(?i)article\s+(\d+(?:\.\d+)*)[:\.]?\s*(.*?)(?=article\s+\d+|$)',
            r'(?i)paragraph\s+(\d+(?:\.\d+)*)[:\.]?\s*(.*?)(?=paragraph\s+\d+|$)',
            r'(\d+(?:\.\d+)*)\.\s+(.*?)(?=\d+(?:\.\d+)*\.|$)',
        ]
        
        for pattern in patterns:
            try:
                matches = re.finditer(pattern, text, re.DOTALL)
                for match in matches:
                    section_num = match.group(1)
                    content = match.group(2).strip()
                    
                    if content and len(content) > 50:  # Filter out very short sections
                        sections.append({
                            'section_number': section_num,
                            'content': DocumentUtils.clean_text(content),
                            'type': 'section'
                        })
            except re.error as e:
                if logger:
                    logger.warning(f"Regex pattern error: {e}")
                continue
        
        # If no sections found, create numbered chunks
        if not sections:
            chunks = DocumentUtils.split_into_chunks(text, settings.chunk_size)
            sections = [
                {
                    'section_number': str(i + 1),
                    'content': chunk,
                    'type': 'chunk'
                }
                for i, chunk in enumerate(chunks)
            ]
        
        return sections
    
    @staticmethod
    def split_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    @staticmethod
    def count_tokens(text: str, model: str = "cl100k_base") -> int:
        """Count tokens in text using tiktoken."""
        try:
            encoding = tiktoken.get_encoding(model)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}, using approximate count")
            return len(text.split()) * 1.3  # Rough approximation
    
    @staticmethod
    def generate_document_id(content: str, filename: str) -> str:
        """Generate unique document ID based on content and filename."""
        combined = f"{filename}_{content[:1000]}"
        return hashlib.md5(combined.encode()).hexdigest()


class CitationFormatter:
    """Utility class for formatting legal citations."""
    
    @staticmethod
    def format_citation(document_name: str, section_number: str, page_number: Optional[int] = None) -> str:
        """Format a legal citation."""
        citation = f"{document_name}"
        
        if section_number:
            citation += f", Section {section_number}"
        
        if page_number:
            citation += f", p. {page_number}"
        
        return citation
    
    @staticmethod
    def extract_citations_from_text(text: str) -> List[str]:
        """Extract existing citations from text."""
        citation_patterns = [
            r'(?i)\b(?:see|cf\.|compare|citing)\s+([^\.]+)',
            r'\b\d+\s+[A-Z][a-z]+\s+\d+',  # Basic case citation pattern
            r'\b\d+\s+U\.S\.C\.\s+§\s*\d+',  # USC citations
        ]
        
        citations = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, text)
            citations.extend(matches)
        
        return citations


class ConflictDetector:
    """Utility class for detecting conflicting information."""
    
    @staticmethod
    def detect_conflicts(responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect potential conflicts between multiple responses."""
        conflicts = []
        
        # Simple keyword-based conflict detection
        conflict_indicators = [
            ('shall', 'shall not'),
            ('must', 'must not'),
            ('required', 'prohibited'),
            ('mandatory', 'optional'),
            ('yes', 'no'),
            ('allowed', 'forbidden'),
            ('valid', 'invalid'),
            ('legal', 'illegal'),
        ]
        
        for i, response1 in enumerate(responses):
            for j, response2 in enumerate(responses[i+1:], i+1):
                content1 = response1.get('content', '').lower()
                content2 = response2.get('content', '').lower()
                
                for positive, negative in conflict_indicators:
                    if positive in content1 and negative in content2:
                        conflicts.append({
                            'type': 'contradiction',
                            'documents': [response1.get('source'), response2.get('source')],
                            'keywords': [positive, negative],
                            'confidence': 0.7
                        })
                    elif negative in content1 and positive in content2:
                        conflicts.append({
                            'type': 'contradiction',
                            'documents': [response1.get('source'), response2.get('source')],
                            'keywords': [negative, positive],
                            'confidence': 0.7
                        })
        
        return conflicts


def setup_logging():
    """Setup logging configuration."""
    logger.remove()  # Remove default handler
    
    # Console logging
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # File logging
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )


def validate_file_type(filename: str) -> bool:
    """Validate if file type is supported."""
    supported_extensions = {'.pdf', '.docx', '.txt', '.doc'}
    file_path = Path(filename)
    return file_path.suffix.lower() in supported_extensions


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"
