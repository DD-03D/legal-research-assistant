# 🚀 Streamlit Cloud Deployment Guide

## Quick Deploy to Streamlit Cloud

### Prerequisites
- GitHub repository (✅ Already done!)
- Streamlit Cloud account (free)
- API keys (OpenAI or Google Gemini)

### Step-by-Step Deployment

#### 1. 🌐 Access Streamlit Cloud
- Go to [share.streamlit.io](https://share.streamlit.io)
- Sign in with your GitHub account

#### 2. 📱 Create New App
- Click **"New app"**
- Choose **"From existing repo"**
- Repository: `karthiksuresh007/legal-research-assistant`
- Branch: `main`
- Main file path: `app.py`
- App URL: Choose a custom URL (e.g., `legal-research-assistant`)

#### 3. 🔑 Configure Secrets
Click **"Advanced settings"** → **"Secrets"** and add:

```toml
API_PROVIDER = "gemini"
GEMINI_API_KEY = "your_actual_gemini_api_key_here"
OPENAI_API_KEY = "your_actual_openai_api_key_here"

APP_NAME = "Legal Research Assistant"
CHUNK_SIZE = 1000
TOP_K_RETRIEVALS = 5
TEMPERATURE = 0.3
```

#### 4. 🚀 Deploy
- Click **"Deploy!"**
- Wait for deployment (usually 2-5 minutes)
- Your app will be live at: `https://your-app-name.streamlit.app`

### 🎯 Expected Live URL Format
`https://legal-research-assistant-[random].streamlit.app`

### 📊 Performance Optimization for Cloud
The app is optimized for Streamlit Cloud with:
- ✅ Efficient memory usage
- ✅ Fast startup time
- ✅ Proper error handling
- ✅ Caching strategies
- ✅ Resource management

### 🔧 Troubleshooting
If deployment fails:
1. Check secrets are properly formatted
2. Verify API keys are valid
3. Check logs in Streamlit Cloud dashboard
4. Ensure all dependencies are in requirements.txt

### 🎉 Post-Deployment
Once deployed:
1. Test document upload functionality
2. Verify API connections
3. Test sample queries
4. Update README with live demo link
