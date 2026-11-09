@echo off
rem Discord Engel Asici kaldirma: cift tikla. Her seyi geri alir.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0kaldir.ps1"
echo.
echo Bu pencere 20 saniye sonra kendiliginden kapanir.
timeout /t 20 >nul
