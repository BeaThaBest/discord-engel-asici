# Tamamen kaldirir: hosts blogu silinir (yonetici ister, kendini bir kez UAC ile yeniden baslatir),
# proxy ayari kurulum oncesi degerine doner, eski surumden kalan HTTPS_PROXY bizimse silinir, gorev silinir, surecler durur, %LOCALAPPDATA%\DiscordEngelAsici silinir.
param([switch]$Yukseltildi)
. (Join-Path $PSScriptRoot 'islevler.ps1')
function Pencere-Bekle {
    if ($Yukseltildi) { Write-Host 'Bu pencere 20 saniye sonra kapanir.'; Start-Sleep -Seconds 20 }
}
if (-not $Yukseltildi -and -not (Yonetici-Mi)) {
    try {
        $k = Yukselt-Gerekirse $PSCommandPath ''
        exit $k
    } catch {
        Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
        exit 5
    }
}
try {
    Write-Host '1/5 hosts blogu siliniyor'
    Hosts-Islem 'kaldir'

    Write-Host '2/5 Proxy ayari geri yukleniyor, eski HTTPS_PROXY temizleniyor'
    Yonlendirmeyi-Kapat -Tam

    Write-Host '3/5 Gorev siliniyor'
    if (Get-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue) {
        Disable-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue | Out-Null
        Stop-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $GOREV -Confirm:$false
    }

    Write-Host '4/5 Surecler durduruluyor'
    Surecleri-Durdur

    Write-Host '5/5 Dosyalar siliniyor'
    $beklenen = Join-Path $env:LOCALAPPDATA 'DiscordEngelAsici'
    if ($APP -ne $beklenen) { throw "Beklenmeyen klasor: $APP" }
    for ($i = 0; ($i -lt 10) -and (Test-Path -LiteralPath $APP); $i++) {
        Remove-Item -LiteralPath $APP -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $APP) { Start-Sleep -Seconds 1 }
    }
    if (Test-Path -LiteralPath $APP) { Write-Warning "Klasor tamamen silinemedi: $APP" }

    Write-Host ''
    Write-Host 'KALDIRILDI. hosts blogu silindi, internet ayarlari kurulum oncesine dondu.'
    Pencere-Bekle
    exit 0
} catch {
    Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
    Pencere-Bekle
    exit 1
}
