@echo off
echo ⚖️  Starting Legal Research Assistant...
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Virtual environment not found
    echo Please run setup.py first
    pause
    exit /b 1
)

REM Activate virtual environment and run the app
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

echo 🚀 Starting Streamlit application...
echo 🌐 Open your browser to: http://localhost:8501
echo 💡 Press Ctrl+C to stop the application
echo.

streamlit run app.py
