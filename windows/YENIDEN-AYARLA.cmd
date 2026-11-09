@echo off
rem Discord Engel Asici: stratejiyi yeniden sec (saglayici degisti ya da Discord acilmiyor).
rem Hata olursa pencere Enter beklenene kadar acik kalir; tam cikti log dosyasinda (yolu yukarida yazar).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0yeniden-ayarla.ps1"
set KOD=%ERRORLEVEL%
if not "%KOD%"=="0" goto hata
echo.
pause
exit /b 0
:hata
echo.
echo YENIDEN AYARLAMA BASARISIZ (cikis kodu %KOD%). Hata, adim ve log dosyasinin yolu yukarida.
pause
exit /b %KOD%
