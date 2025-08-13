@echo off
echo Stopping any running Streamlit instances...
taskkill /f /im streamlit.exe > nul 2>&1

echo Starting Legal Research Assistant...
cd /d "C:\Users\LENOVO\OneDrive\Desktop\NS\legal-research-assistant"
call venv\Scripts\activate
C:\Users\LENOVO\OneDrive\Desktop\NS\legal-research-assistant\venv\Scripts\streamlit.exe run app.py

pause
