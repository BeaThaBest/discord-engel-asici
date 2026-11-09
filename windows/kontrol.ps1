# Kurulum kontrolu: GECTI/KALDI listesi, her KALDI icin ne yapilacagi. Hicbir ayari degistirmez.
# Mac'teki mac/kontrol.sh ile ayni Python modulunu (ortak\doktor.py) calistirir.
$APP = Join-Path $env:LOCALAPPDATA 'DiscordEngelAsici'
$py = Join-Path $APP 'python\python.exe'
if (-not (Test-Path -LiteralPath $py)) {
    $k = Get-Command python.exe, py.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $k) { Write-Host 'KALDI: kurulum yok (gomulu Python bulunamadi). Ne yapmali: windows\KUR.cmd'; exit 1 }
    $py = $k.Source
}
& $py -I (Join-Path (Split-Path -Parent $PSScriptRoot) 'ortak\doktor.py') --app $APP
exit $LASTEXITCODE
