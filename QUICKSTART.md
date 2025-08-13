# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Setup Environment

```bash
# Clone or download the project
cd legal-research-assistant

# Run the automated setup (recommended)
python setup.py

# OR Manual setup:
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run the Application

```bash
# Activate virtual environment if not already active
# Windows: venv\Scripts\activate  
# macOS/Linux: source venv/bin/activate

# Start the application
streamlit run app.py
```

### 4. Use the Application

1. **Open Browser**: Navigate to `http://localhost:8501`
2. **Upload Documents**: Click "Browse files" and upload PDF, DOCX, or TXT legal documents
3. **Process Documents**: Click "Process Documents" to index them
4. **Ask Questions**: Enter legal questions in the query box
5. **Get Answers**: Receive detailed analysis with citations and conflict detection

## 🔍 Example Questions

- "What are the termination clauses in the contract?"
- "What are the liability limitations?"  
- "What intellectual property rights are mentioned?"
- "What are the payment terms and conditions?"
- "Are there any confidentiality obligations?"

## 📊 Features Overview

- **Multi-format Support**: PDF, DOCX, TXT documents
- **Semantic Search**: AI-powered document retrieval
- **Legal Citations**: Proper section and clause references
- **Conflict Detection**: Identifies contradictory information
- **Performance Metrics**: Built-in evaluation and timing
- **Export Results**: Download analysis as JSON

## 🆘 Troubleshooting

### Common Issues

**Import Errors**
```bash
pip install -r requirements.txt
```

**Missing API Key**
```bash
# Check .env file exists and contains:
OPENAI_API_KEY=your_actual_api_key
```

**Port Already in Use**
```bash
streamlit run app.py --server.port 8502
```

**Memory Issues**
- Reduce `CHUNK_SIZE` in .env
- Process fewer documents at once
- Restart the application

### Getting Help

- 📖 **Full Documentation**: README.md
- 🐛 **Report Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions

## 🎯 Next Steps

1. **Try Sample Documents**: Use the included sample legal documents in `/data/sample_documents/`
2. **Customize Settings**: Modify configuration in `.env` file
3. **Explore Advanced Features**: Document comparison, section analysis
4. **Deploy**: Use Streamlit Cloud or HuggingFace Spaces for sharing

Happy legal research! ⚖️
