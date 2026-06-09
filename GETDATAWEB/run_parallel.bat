@echo off
cd /d "%~dp0"
echo ============================================================
echo STARTING PARALLEL EXTRACTION ORCHESTRATOR
echo ============================================================
echo.
echo [INFO] Menggunakan 'py' launcher untuk menghindari masalah Microsoft Store.
echo [INFO] Script ini akan membagi data (3000 item) dan membuka 6 worker otomatis.
echo.

py run_parallel.py

echo.
echo ============================================================
echo PROSES SELESAI ATAU TERHENTI
echo ============================================================
pause
