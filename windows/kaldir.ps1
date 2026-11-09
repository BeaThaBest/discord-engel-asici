# Tamamen kaldirir: proxy ayari ve HTTPS_PROXY kurulum oncesi degerlerine doner,
# gorev silinir, surecler durur, %LOCALAPPDATA%\DiscordEngelAsici silinir.
. (Join-Path $PSScriptRoot 'islevler.ps1')
try {
    Write-Host '1/4 Proxy ayari ve HTTPS_PROXY geri yukleniyor'
    Yonlendirmeyi-Kapat -Tam

    Write-Host '2/4 Gorev siliniyor'
    if (Get-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue) {
        Disable-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue | Out-Null
        Stop-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $GOREV -Confirm:$false
    }

    Write-Host '3/4 Surecler durduruluyor'
    Surecleri-Durdur

    Write-Host '4/4 Dosyalar siliniyor'
    $beklenen = Join-Path $env:LOCALAPPDATA 'DiscordEngelAsici'
    if ($APP -ne $beklenen) { throw "Beklenmeyen klasor: $APP" }
    for ($i = 0; ($i -lt 10) -and (Test-Path -LiteralPath $APP); $i++) {
        Remove-Item -LiteralPath $APP -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $APP) { Start-Sleep -Seconds 1 }
    }
    if (Test-Path -LiteralPath $APP) { Write-Warning "Klasor tamamen silinemedi: $APP" }

    Write-Host ''
    Write-Host 'KALDIRILDI. Internet ayarlari kurulum oncesine dondu.'
    exit 0
} catch {
    Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
