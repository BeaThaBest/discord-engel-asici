@echo off
rem Discord Engel Asici kontrol: cift tikla. Hicbir ayari degistirmez.
rem Hata olursa pencere Enter beklenene kadar acik kalir; tam cikti log dosyasinda (yolu yukarida yazar).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0kontrol.ps1"
set KOD=%ERRORLEVEL%
if not "%KOD%"=="0" goto hata
echo.
pause
exit /b 0
:hata
echo.
echo KONTROL BASARISIZ (cikis kodu %KOD%). Hata, adim ve log dosyasinin yolu yukarida.
pause
exit /b %KOD%
