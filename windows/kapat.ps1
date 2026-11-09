# Gecici kapatir: PAC ayari kalkar, gorev devre disi kalir (yeniden baslatmada da kapali).
# Yetki istemez. hosts blogu KALIR: hizmet yokken updates.discord.com baglantisi reddedilir
# (yalniz Discord guncelleyicisi etkilenir). Blogu silmek icin kaldir.ps1.
# Geri acmak: windows\ac.ps1
. (Join-Path $PSScriptRoot 'islevler.ps1')
try {
    Yonlendirmeyi-Kapat
    if (Get-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue) {
        Disable-ScheduledTask -TaskName $GOREV | Out-Null
        Stop-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue
    }
    Surecleri-Durdur
    Write-Host 'KAPATILDI. Geri acmak icin windows\ac.ps1'
    exit 0
} catch {
    Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
