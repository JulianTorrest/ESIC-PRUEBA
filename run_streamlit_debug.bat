@echo off
cls
echo Cerrando instancias anteriores de Python/Streamlit...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM streamlit.exe 2>nul

echo Iniciando Streamlit con logs...
streamlit run streamlit_app.py > streamlit_debug.log 2>&1
echo Streamlit termino con codigo: %ERRORLEVEL%
echo %ERRORLEVEL% > streamlit_exitcode.txt
