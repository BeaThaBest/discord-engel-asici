# Kurulum kontrolu: GECTI/KALDI listesi, her KALDI icin ne yapilacagi. Hicbir ayari degistirmez.
# Mac'teki mac/kontrol.sh ile ayni Python modulunu (ortak\doktor.py) calistirir.
# Tam cikti kurulum klasorundeki log\kontrol-TARIH.log dosyasina (kurulum yoksa %TEMP%\DiscordEngelAsici altina) yazilir.
. (Join-Path $PSScriptRoot 'islevler.ps1')
if (Test-Path -LiteralPath $APP) { $Gunluk = Gunluk-Yolu 'kontrol' } else { $Gunluk = Gunluk-Yolu 'kontrol' -Gecici }
Gunluk-Baslat $Gunluk
$py = $PY_APP
if (-not (Test-Path -LiteralPath $py)) {
    $k = Get-Command python.exe, py.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $k) {
        Write-Host 'KALDI: kurulum yok (gomulu Python bulunamadi). Ne yapmali: windows\KUR.cmd'
        Write-Host "Tam cikti: $Gunluk"
        Gunluk-Bitir
        exit 1
    }
    $py = $k.Source
}
$kod = Yerel-Calistir $py @('-I', (Join-Path (Split-Path -Parent $PSScriptRoot) 'ortak\doktor.py'), '--app', $APP)
Write-Host "Tam cikti: $Gunluk"
Gunluk-Bitir
exit $kod
