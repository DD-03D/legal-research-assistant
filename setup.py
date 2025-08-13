"""
Setup script for the Legal Research Assistant.
This script helps users set up the environment and get started quickly.
"""

import os
import sys
import subprocess
from pathlib import Path
import shutil

def print_banner():
    """Print setup banner."""
    print("""
    ⚖️  Legal Research Assistant Setup
    ================================
    
    This script will help you set up the Legal Research Assistant
    with all required dependencies and configuration.
    """)

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 3.9+ required, but you have {version.major}.{version.minor}")
        print("Please upgrade Python and try again.")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def create_virtual_environment():
    """Create a virtual environment."""
    print("\n📦 Setting up virtual environment...")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("⚠️  Virtual environment already exists")
        response = input("Do you want to recreate it? (y/N): ").lower().strip()
        if response == 'y':
            print("🗑️  Removing existing virtual environment...")
            shutil.rmtree(venv_path)
        else:
            print("✅ Using existing virtual environment")
            return True
    
    try:
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False

def get_python_command():
    """Get the appropriate Python command for the platform."""
    if os.name == 'nt':  # Windows
        return str(Path("venv") / "Scripts" / "python.exe")
    else:  # macOS/Linux
        return str(Path("venv") / "bin" / "python")

def get_pip_command():
    """Get the appropriate pip command for the platform."""
    if os.name == 'nt':  # Windows
        return str(Path("venv") / "Scripts" / "pip.exe")
    else:  # macOS/Linux
        return str(Path("venv") / "bin" / "pip")

def install_dependencies():
    """Install required dependencies."""
    print("\n📚 Installing dependencies...")
    
    python_cmd = get_python_command()
    pip_cmd = get_pip_command()
    
    if not Path(python_cmd).exists():
        print("❌ Virtual environment not properly created")
        return False
    
    try:
        # Upgrade pip using Python -m pip (more reliable on Windows)
        print("⬆️  Upgrading pip...")
        subprocess.run([python_cmd, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        
        # Install requirements
        print("📦 Installing project dependencies...")
        subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
        
        print("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("Trying alternative installation method...")
        
        # Fallback: try without pip upgrade
        try:
            print("📦 Installing dependencies without pip upgrade...")
            subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
            print("✅ Dependencies installed successfully (pip upgrade skipped)")
            return True
        except subprocess.CalledProcessError as e2:
            print(f"❌ Alternative installation also failed: {e2}")
            return False

def setup_environment_file():
    """Set up the environment configuration file."""
    print("\n🔐 Setting up environment configuration...")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("⚠️  .env file already exists")
        response = input("Do you want to recreate it? (y/N): ").lower().strip()
        if response != 'y':
            print("✅ Using existing .env file")
            return True
    
    if not env_example.exists():
        print("❌ .env.example file not found")
        return False
    
    # Copy example file
    shutil.copy(env_example, env_file)
    print("✅ Created .env file from template")
    
    # Get OpenAI API key
    print("\n🔑 OpenAI API Key Setup")
    print("You need an OpenAI API key to use this application.")
    print("Get one at: https://platform.openai.com/api-keys")
    
    api_key = input("\nEnter your OpenAI API key (or press Enter to skip): ").strip()
    
    if api_key:
        # Update .env file with API key
        with open(env_file, 'r') as f:
            content = f.read()
        
        content = content.replace('your_openai_api_key_here', api_key)
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print("✅ OpenAI API key configured")
    else:
        print("⚠️  OpenAI API key skipped - you'll need to add it manually to .env")
    
    return True

def create_directories():
    """Create necessary directories."""
    print("\n📁 Creating project directories...")
    
    directories = [
        "data/chroma_db",
        "data/uploads",
        "logs"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}")
    
    print("✅ Project directories created")
    return True

def run_system_test():
    """Run system validation test."""
    print("\n🧪 Running system validation...")
    
    python_cmd = get_python_command()
    
    try:
        result = subprocess.run(
            [python_cmd, "tests/test_system.py"], 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("✅ System validation passed")
            return True
        else:
            print("❌ System validation failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏱️  System test timed out (this may be normal for first run)")
        return True
    except Exception as e:
        print(f"❌ Error running system test: {e}")
        return False

def print_completion_message():
    """Print setup completion message."""
    print("""
    🎉 Setup Complete!
    ==================
    
    Your Legal Research Assistant is ready to use!
    
    Next Steps:
    1. Activate the virtual environment:
       Windows: venv\\Scripts\\activate
       macOS/Linux: source venv/bin/activate
    
    2. Start the application:
       streamlit run app.py
    
    3. Open your browser to: http://localhost:8501
    
    4. Upload legal documents and start asking questions!
    
    📚 Documentation: README.md
    🐛 Issues: https://github.com/yourusername/legal-research-assistant/issues
    
    Happy legal research! ⚖️
    """)

def main():
    """Main setup function."""
    print_banner()
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    # Setup steps
    setup_steps = [
        ("Virtual Environment", create_virtual_environment),
        ("Dependencies", install_dependencies),
        ("Environment Config", setup_environment_file),
        ("Project Directories", create_directories),
    ]
    
    for step_name, step_function in setup_steps:
        if not step_function():
            print(f"\n❌ Setup failed at step: {step_name}")
            print("Please resolve the issue and run setup again.")
            sys.exit(1)
    
    # Optional system test
    print("\n🧪 System Test")
    response = input("Do you want to run the system validation test? (Y/n): ").lower().strip()
    
    if response != 'n':
        # Only run if OpenAI API key is configured
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()
                if 'your_openai_api_key_here' not in content:
                    run_system_test()
                else:
                    print("⚠️  Skipping system test - OpenAI API key not configured")
        else:
            print("⚠️  Skipping system test - .env file not found")
    
    print_completion_message()

if __name__ == "__main__":
    main()
