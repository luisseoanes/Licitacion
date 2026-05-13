@echo off
title Chernovia Health System
echo.
echo  ======================================
echo   Sistema de Salud Chernovia - POC
echo   Big Data COIL 2026
echo  ======================================
echo.

echo [1/2] Iniciando backend (FastAPI)...
start "Backend - Chernovia" cmd /k "cd /d "%~dp0backend" && pip install -r requirements.txt -q && echo Backend listo en http://localhost:8000 && uvicorn main:app --reload --port 8000"

timeout /t 4 /nobreak > nul

echo [2/2] Iniciando frontend (React + Vite)...
start "Frontend - Chernovia" cmd /k "cd /d "%~dp0frontend" && npm install && echo Frontend listo en http://localhost:5173 && npm run dev"

echo.
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:5173
echo  API docs: http://localhost:8000/docs
echo.
echo  Espera unos segundos y abre http://localhost:5173 en tu navegador.
echo.
pause
