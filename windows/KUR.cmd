@echo off
rem Discord Engel Asici kurulumu: cift tikla. Soru sormaz.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0kur.ps1"
echo.
echo Bu pencere 20 saniye sonra kendiliginden kapanir.
timeout /t 20 >nul
