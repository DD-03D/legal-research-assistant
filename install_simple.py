"""
Simple installation script for Legal Research Assistant.
This is a minimal version that avoids pip upgrade issues.
"""

import os
import sys
import subprocess
from pathlib import Path

def simple_install():
    """Simple installation without pip upgrade."""
    print("🚀 Legal Research Assistant - Simple Installation")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 9):
        print(f"❌ Python 3.9+ required, but you have {sys.version_info.major}.{sys.version_info.minor}")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Create virtual environment if it doesn't exist
    venv_path = Path("venv")
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ Virtual environment created")
        except Exception as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
    else:
        print("✅ Virtual environment exists")
    
    # Get pip command
    if os.name == 'nt':  # Windows
        pip_cmd = str(venv_path / "Scripts" / "pip.exe")
        python_cmd = str(venv_path / "Scripts" / "python.exe")
    else:  # macOS/Linux
        pip_cmd = str(venv_path / "bin" / "pip")
        python_cmd = str(venv_path / "bin" / "python")
    
    # Install packages one by one (more reliable)
    print("📚 Installing core dependencies...")
    
    core_packages = [
        "streamlit",
        "python-dotenv",
        "pydantic",
        "pydantic-settings", 
        "requests",
        "tqdm",
        "loguru",
        "pandas",
        "numpy"
    ]
    
    for package in core_packages:
        try:
            print(f"  Installing {package}...")
            subprocess.run([pip_cmd, "install", package], check=True, capture_output=True)
        except Exception as e:
            print(f"  ⚠️ Warning: Failed to install {package}: {e}")
    
    # Try to install AI packages
    ai_packages = [
        "openai",
        "tiktoken",
        "langchain",
        "langchain-openai",
        "langchain-community",
        "chromadb",
        "sentence-transformers"
    ]
    
    print("🤖 Installing AI dependencies...")
    for package in ai_packages:
        try:
            print(f"  Installing {package}...")
            subprocess.run([pip_cmd, "install", package], check=True, capture_output=True)
        except Exception as e:
            print(f"  ⚠️ Warning: Failed to install {package}: {e}")
    
    # Try document processing packages
    doc_packages = [
        "PyMuPDF",
        "python-docx",
        "pypdf"
    ]
    
    print("📄 Installing document processing dependencies...")
    for package in doc_packages:
        try:
            print(f"  Installing {package}...")
            subprocess.run([pip_cmd, "install", package], check=True, capture_output=True)
        except Exception as e:
            print(f"  ⚠️ Warning: Failed to install {package}: {e}")
    
    # Create .env file if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        print("🔐 Creating .env file...")
        try:
            with open(".env.example", "r") as f:
                content = f.read()
            with open(".env", "w") as f:
                f.write(content)
            print("✅ .env file created from template")
        except Exception as e:
            print(f"⚠️ Warning: Could not create .env file: {e}")
    
    # Create directories
    print("📁 Creating directories...")
    directories = ["data/chroma_db", "data/uploads", "logs"]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("\n🎉 Installation complete!")
    print("\nNext steps:")
    print("1. Edit .env file and add your OpenAI API key")
    print("2. Activate virtual environment:")
    if os.name == 'nt':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("3. Run: streamlit run app.py")
    print("4. Open browser to: http://localhost:8501")
    
    return True

if __name__ == "__main__":
    simple_install()
