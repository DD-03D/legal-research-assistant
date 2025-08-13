"""
Simple script to configure API provider and API keys.
"""

import os
from pathlib import Path

def main():
    print("🔧 Legal Research Assistant - API Configuration")
    print("=" * 50)
    
    env_file = Path(".env")
    
    # Ask user for API provider choice
    print("\n📡 Choose your API provider:")
    print("1. Gemini (Google) - Free tier available")
    print("2. OpenAI - Paid service")
    
    while True:
        choice = input("\nEnter choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Please enter 1 or 2")
    
    provider = "gemini" if choice == "1" else "openai"
    
    # Get API key
    if provider == "gemini":
        print("\n🔑 Enter your Gemini API key:")
        print("Get it from: https://makersuite.google.com/app/apikey")
        api_key = input("Gemini API Key: ").strip()
        key_var = "GEMINI_API_KEY"
    else:
        print("\n🔑 Enter your OpenAI API key:")
        print("Get it from: https://platform.openai.com/api-keys")
        api_key = input("OpenAI API Key: ").strip()
        key_var = "OPENAI_API_KEY"
    
    if not api_key:
        print("❌ No API key provided. Exiting.")
        return
    
    # Read current .env file
    env_content = ""
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # Update or add configurations
    lines = env_content.split('\n') if env_content else []
    new_lines = []
    provider_set = False
    key_set = False
    
    for line in lines:
        if line.startswith('API_PROVIDER='):
            new_lines.append(f'API_PROVIDER={provider}')
            provider_set = True
        elif line.startswith(f'{key_var}='):
            new_lines.append(f'{key_var}={api_key}')
            key_set = True
        else:
            new_lines.append(line)
    
    # Add missing configurations
    if not provider_set:
        new_lines.append(f'API_PROVIDER={provider}')
    if not key_set:
        new_lines.append(f'{key_var}={api_key}')
    
    # Write updated .env file
    with open(env_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print(f"\n✅ Configuration saved!")
    print(f"   Provider: {provider.title()}")
    print(f"   API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '****'}")
    print(f"\n🚀 You can now run the application with: streamlit run src/ui/streamlit_app.py")

if __name__ == "__main__":
    main()
