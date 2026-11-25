@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3.13 -m venv .venv
    if errorlevel 1 goto :falha
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :falha
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto :falha
exit /b 0
:falha
echo Nao foi possivel iniciar. Confira a mensagem acima e as instrucoes do README.md.
pause
exit /b 1
