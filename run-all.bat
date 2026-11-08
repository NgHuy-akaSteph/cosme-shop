@echo off
REM ============================================================
REM  Chay dong thoi Backend (FastAPI) + Frontend (Vite) tren Windows
REM  Dung: run-all.bat
REM ============================================================
setlocal EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"

if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8000"
if "%FRONTEND_PORT%"=="" set "FRONTEND_PORT=5173"

where python >nul 2>&1
if errorlevel 1 (
    echo [dev][error] Khong tim thay python. Cai Python 3.12+ truoc khi chay.
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [dev][error] Khong tim thay npm. Cai Node.js 20+ truoc khi chay.
    exit /b 1
)

REM ---------------------------------------------------------- Backend
if not exist "%BACKEND_DIR%\.venv\Scripts\python.exe" (
    echo [dev] Tao virtualenv cho backend...
    python -m venv "%BACKEND_DIR%\.venv"
    if errorlevel 1 (
        echo [dev][error] Khong tao duoc venv
        exit /b 1
    )
    "%BACKEND_DIR%\.venv\Scripts\python.exe" -m pip install -r "%BACKEND_DIR%\requirements.txt"
    if errorlevel 1 (
        echo [dev][error] Cai dependencies that bai
        exit /b 1
    )
    "%BACKEND_DIR%\.venv\Scripts\python.exe" -m pip install -r "%BACKEND_DIR%\requirements-dev.txt"
    if errorlevel 1 (
        echo [dev][error] Cai dev dependencies that bai
        exit /b 1
    )
)

if not exist "%BACKEND_DIR%\.env" (
    copy /Y "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
    echo [dev] Da tao backend\.env tu .env.example ^(NHớ dien DATABASE_URL, JWT_SECRET_KEY...^)
)

echo [dev] Khoi dong backend tai http://localhost:%BACKEND_PORT%
start "cosme-backend" /D "%BACKEND_DIR%" cmd /k ""%BACKEND_DIR%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"

REM ---------------------------------------------------------- Frontend
if not exist "%FRONTEND_DIR%\node_modules" (
    echo [dev] Cai dependencies cho frontend...
    pushd "%FRONTEND_DIR%"
    call npm install
    popd
)

if not exist "%FRONTEND_DIR%\.env" (
    echo VITE_API_URL=http://localhost:%BACKEND_PORT%> "%FRONTEND_DIR%\.env"
    echo [dev] Da tao frontend\.env ^(VITE_API_URL=http://localhost:%BACKEND_PORT%^)
)

echo [dev] Khoi dong frontend tai http://localhost:%FRONTEND_PORT%
start "cosme-frontend" /D "%FRONTEND_DIR%" cmd /k "call npm run dev -- --port %FRONTEND_PORT%"

REM ---------------------------------------------------------- Ngrok
set "NGROK_URL=https://habitat-diligence-various.ngrok-free.dev"
where ngrok >nul 2>&1
if errorlevel 1 (
    echo [dev][error] Khong tim thay ngrok. Cai ngrok de mo tunnel ^(https://ngrok.com/download^).
) else (
    echo [dev] Khoi dong ngrok cho backend tai %NGROK_URL%
    start "cosme-ngrok" cmd /k "ngrok http %BACKEND_PORT% --url %NGROK_URL%"
)

echo.
echo [dev] FE: http://localhost:%FRONTEND_PORT%   BE: http://localhost:%BACKEND_PORT%
echo [dev] Dong cua so cua 2 tien trinh de dung.
echo.

endlocal
