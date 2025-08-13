@echo off
echo ⚖️  Legal Research Assistant - Windows Setup
echo ==========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.9+ and try again
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Run the setup script
echo 🚀 Running setup script...
python setup.py

echo.
echo Setup complete! 
echo.
echo To start the application:
echo 1. Activate virtual environment: venv\Scripts\activate
echo 2. Run the app: streamlit run app.py
echo 3. Open browser to: http://localhost:8501
echo.
pause
