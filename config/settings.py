"""
Configuration management for the Legal Research Assistant.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_api_key_from_sources(key_name: str) -> str:
    """Get API key from multiple sources in order of priority."""
    # 1. Try Streamlit secrets first
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        pass
    
    # 2. Try environment variable
    env_value = os.getenv(key_name)
    if env_value:
        return env_value
    
    # 3. Return empty string if not found
    return ""

class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # Application Info
    app_name: str = Field(default="Legal Research Assistant", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Provider Selection
    api_provider: str = Field(default="gemini", env="API_PROVIDER")  # "openai" or "gemini"
    
    # API Keys - with dynamic loading
    openai_api_key: str = Field(default_factory=lambda: get_api_key_from_sources("OPENAI_API_KEY"))
    gemini_api_key: str = Field(default_factory=lambda: get_api_key_from_sources("GEMINI_API_KEY"))
    huggingface_api_token: Optional[str] = Field(default=None, env="HUGGINGFACE_API_TOKEN")
    pinecone_api_key: Optional[str] = Field(default=None, env="PINECONE_API_KEY")
    
    # Vector Database Configuration
    chroma_persist_directory: str = Field(default="./data/chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    pinecone_environment: Optional[str] = Field(default=None, env="PINECONE_ENVIRONMENT")
    pinecone_index_name: Optional[str] = Field(default="legal-research-index", env="PINECONE_INDEX_NAME")
    
    # Document Processing
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    max_tokens_per_chunk: int = Field(default=1500, env="MAX_TOKENS_PER_CHUNK")
    
    # Retrieval Configuration
    top_k_retrievals: int = Field(default=5, env="TOP_K_RETRIEVALS")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    
    # Generation Configuration
    max_output_tokens: int = Field(default=2000, env="MAX_OUTPUT_TOKENS")
    temperature: float = Field(default=0.3, env="TEMPERATURE")
    
    # UI Configuration
    streamlit_theme: str = Field(default="light", env="STREAMLIT_THEME")
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    
    # Model Configuration - OpenAI
    openai_embedding_model: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    openai_llm_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_LLM_MODEL")
    
    # Model Configuration - Gemini
    gemini_embedding_model: str = Field(default="models/text-embedding-004", env="GEMINI_EMBEDDING_MODEL")
    gemini_llm_model: str = Field(default="gemini-1.5-flash", env="GEMINI_LLM_MODEL")
    
    # Legacy fields for backward compatibility
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    llm_model: str = Field(default="gpt-4-turbo-preview", env="LLM_MODEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma_db"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
for directory in [DATA_DIR, UPLOAD_DIR, CHROMA_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

def get_settings() -> Settings:
    """Get application settings."""
    return settings
