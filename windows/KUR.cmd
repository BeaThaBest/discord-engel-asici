@echo off
rem Discord Engel Asici kurulumu: cift tikla. Soru sormaz.
rem Hata olursa pencere Enter beklenene kadar acik kalir; tam cikti log dosyasinda (yolu yukarida yazar).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0kur.ps1"
set KOD=%ERRORLEVEL%
if not "%KOD%"=="0" goto hata
echo.
echo Bu pencere 20 saniye sonra kendiliginden kapanir.
timeout /t 20 >nul
exit /b 0
:hata
echo.
echo KURULUM BASARISIZ (cikis kodu %KOD%). Hata, adim ve log dosyasinin yolu yukarida.
pause
exit /b %KOD%
