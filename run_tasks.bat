@echo off
cd /d "C:\Users\adm\Documents\Flask\BlockchainAI"

set "PYTHON_EXE=C:\Users\adm\Documents\Flask\BlockchainAI\.venv\Scripts\python.exe"
set "PING_SCRIPT=C:\Users\adm\Documents\Flask\BlockchainAI\flask_ui_app\ping.py"
set "SIMULATOR_SCRIPT=C:\Users\adm\Documents\Flask\BlockchainAI\run_simulation.py"

:: Check if ping.py is already running.
:: Note: This check looks for the script path in the command line of python.exe processes.
:: It might not be foolproof if python.exe is run in very unusual ways, but it's generally effective.
tasklist /FI "IMAGENAME eq python.exe" /FO CSV | findstr /I "%PING_SCRIPT%" >nul
if %errorlevel% neq 0 (
    echo [%date% %time%] Launching ping.py in background...
    start /b "" "%PYTHON_EXE%" "%PING_SCRIPT%"
) else (
    echo [%date% %time%] ping.py is already running.
)

echo [%date% %time%] Launching run_simulation.py...
"%PYTHON_EXE%" "%SIMULATOR_SCRIPT%"

echo [%date% %time%] Batch file finished.
