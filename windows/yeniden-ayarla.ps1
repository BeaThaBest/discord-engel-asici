# Stratejiyi yeniden secer (internet saglayicisi degisti ya da Discord yine acilmiyor). Yetki istemez.
# Adaylar sirayla denenir, ilk calisan strateji.json'a yazilir, hizmet yeniden baslatilir.
# Hicbiri calismazsa eski secim ve hizmet oldugu gibi kalir (cikis 2).
# Tam cikti %LOCALAPPDATA%\DiscordEngelAsici\log\yeniden-ayarla-TARIH.log dosyasina yazilir.
. (Join-Path $PSScriptRoot 'islevler.ps1')
$Gunluk = Gunluk-Yolu 'yeniden-ayarla'
Gunluk-Baslat $Gunluk
Write-Host "Log: $Gunluk"
try {
    $g = Get-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue
    if (-not $g -or -not (Test-Path -LiteralPath (Join-Path $APP 'ortak\strateji.py'))) { throw 'Kurulum yok, once windows\KUR.cmd' }
    if (-not ($g.Actions | Where-Object { $_.Arguments -like '*--strateji*' })) { throw 'Kurulum bu ozellikten eski, once windows\KUR.cmd ile yeniden kur.' }
    $k = Strateji-Sec
    if ($k -ne 0) { Write-Host 'Eski ayar degismedi.'; Write-Host "Tam cikti: $Gunluk"; Gunluk-Bitir; exit $k }
    Stop-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue
    Surecleri-Durdur
    Start-ScheduledTask -TaskName $GOREV
    if (-not (Hizmet-Bekle 60)) { throw 'Hizmet 60 sn icinde hazir olmadi. windows\KONTROL.cmd ile bak.' }
    Write-Host 'YENIDEN AYARLANDI. Discord''u tepsiden Cikis ile kapatip yeniden ac.'
    Gunluk-Bitir
    exit 0
} catch {
    Hata-Bildir $_.Exception.Message $Gunluk $false
    Gunluk-Bitir
    exit 1
}
