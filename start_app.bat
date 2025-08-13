@echo off
cd /d "c:\Users\LENOVO\OneDrive\Desktop\NS\legal-research-assistant"
call .\venv\Scripts\Activate.ps1
streamlit run src\ui\streamlit_app.py
pause
