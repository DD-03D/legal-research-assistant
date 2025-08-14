"""
API Provider Factory for managing different AI providers (OpenAI, Gemini).
"""

import asyncio
import nest_asyncio
from typing import Any, Optional
from abc import ABC, abstractmethod
from loguru import logger

from config.settings import settings

# Enable nested event loops for Streamlit compatibility
nest_asyncio.apply()


def ensure_event_loop():
    """Ensure there's an event loop in the current thread."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        # No event loop in current thread, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def get_embeddings(self):
        """Get embeddings instance."""
        pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def get_llm(self):
        """Get LLM instance."""
        pass


class OpenAIProvider(EmbeddingProvider, LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required")
    
    def get_embeddings(self):
        """Get OpenAI embeddings."""
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                openai_api_key=settings.openai_api_key
            )
        except ImportError as e:
            logger.error(f"Failed to import OpenAI embeddings: {e}")
            raise
    
    def get_llm(self):
        """Get OpenAI LLM."""
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.openai_llm_model,
                temperature=settings.temperature,
                max_tokens=settings.max_output_tokens,
                openai_api_key=settings.openai_api_key
            )
        except ImportError as e:
            logger.error(f"Failed to import OpenAI LLM: {e}")
            raise


class GeminiProvider(EmbeddingProvider, LLMProvider):
    """Gemini provider implementation."""
    
    def __init__(self):
        # Check for API key in multiple sources
        api_key = self._get_gemini_api_key()
        if not api_key:
            raise ValueError(
                "Gemini API key is required. Please set it in:\n"
                "1. Streamlit Cloud secrets (GEMINI_API_KEY)\n"
                "2. Environment variable (GEMINI_API_KEY)\n"
                "3. .env file (GEMINI_API_KEY)"
            )
        # Ensure event loop exists for async operations
        ensure_event_loop()
    
    def _get_gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key from various sources."""
        import os
        
        # Try Streamlit secrets first
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'GEMINI_API_KEY' in st.secrets:
                return st.secrets['GEMINI_API_KEY']
        except Exception:
            pass
        
        # Try GOOGLE_API_KEY as fallback
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'GOOGLE_API_KEY' in st.secrets:
                return st.secrets['GOOGLE_API_KEY']
        except Exception:
            pass
        
        # Try environment variable
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            return api_key
        
        # Try GOOGLE_API_KEY environment variable as fallback
        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key:
            return api_key
        
        # Try settings
        return getattr(settings, 'gemini_api_key', None)
    
    def get_embeddings(self):
        """Get Gemini embeddings."""
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            # Ensure event loop for embeddings
            ensure_event_loop()
            
            # Get API key dynamically
            api_key = self._get_gemini_api_key()
            
            return GoogleGenerativeAIEmbeddings(
                model=settings.gemini_embedding_model,
                google_api_key=api_key
            )
        except ImportError as e:
            logger.error(f"Failed to import Gemini embeddings: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Gemini embeddings: {e}")
            raise
    
    def get_llm(self):
        """Get Gemini LLM."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            # Ensure event loop for LLM
            ensure_event_loop()
            
            # Get API key dynamically
            api_key = self._get_gemini_api_key()
            
            return ChatGoogleGenerativeAI(
                model=settings.gemini_llm_model,
                temperature=settings.temperature,
                max_tokens=settings.max_output_tokens,
                google_api_key=api_key
            )
        except ImportError as e:
            logger.error(f"Failed to import Gemini LLM: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM: {e}")
            raise


class APIProviderFactory:
    """Factory for creating API providers."""
    
    _providers = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider
    }
    
    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> tuple[EmbeddingProvider, LLMProvider]:
        """
        Get embedding and LLM providers.
        
        Args:
            provider_name: Name of the provider ("openai" or "gemini")
                          If None, uses settings.api_provider
        
        Returns:
            Tuple of (embedding_provider, llm_provider)
        """
        if provider_name is None:
            provider_name = settings.api_provider
        
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"Unknown provider: {provider_name}. Available: {available}")
        
        try:
            provider_class = cls._providers[provider_name]
            provider = provider_class()
            logger.info(f"Successfully initialized {provider_name} provider")
            return provider, provider
        except Exception as e:
            logger.error(f"Failed to initialize {provider_name} provider: {e}")
            raise
    
    @classmethod
    def get_embeddings(cls, provider_name: Optional[str] = None):
        """Get embeddings instance."""
        embedding_provider, _ = cls.get_provider(provider_name)
        return embedding_provider.get_embeddings()
    
    @classmethod
    def get_llm(cls, provider_name: Optional[str] = None):
        """Get LLM instance."""
        _, llm_provider = cls.get_provider(provider_name)
        return llm_provider.get_llm()
