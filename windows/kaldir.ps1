# Tamamen kaldirir: hosts blogu silinir (yonetici ister, kendini bir kez UAC ile yeniden baslatir),
# proxy ayari kurulum oncesi degerine doner, eski surumden kalan HTTPS_PROXY bizimse silinir, gorev silinir, surecler durur, %LOCALAPPDATA%\DiscordEngelAsici silinir.
# Tam cikti %TEMP%\DiscordEngelAsici\kaldir-TARIH.log dosyasina yazilir (kurulum klasoru silindigi icin).
param([switch]$Yukseltildi, [string]$Gunluk)
. (Join-Path $PSScriptRoot 'islevler.ps1')
if (-not $Gunluk) { $Gunluk = Gunluk-Yolu 'kaldir' -Gecici }
Gunluk-Baslat $Gunluk
Write-Host "Log: $Gunluk"
if (-not $Yukseltildi -and -not (Yonetici-Mi)) {
    try {
        Gunluk-Bitir  # yukseltilmis cocuk ayni dosyaya yazar
        $k = Yukselt-Gerekirse $PSCommandPath ('-Gunluk "{0}"' -f $Gunluk)
        Gunluk-Baslat $Gunluk
    } catch {
        Gunluk-Baslat $Gunluk
        Hata-Bildir $_.Exception.Message $Gunluk $false
        Gunluk-Bitir
        exit 5
    }
    if ($k -eq 0) {
        Write-Host 'KALDIRILDI (yukseltilmis pencerede).'
    } else {
        Write-Host "HATA: kaldirma basarisiz, cikis kodu $k. Hata ve adim yukseltilmis pencerede ve log dosyasinda: $Gunluk" -ForegroundColor Red
    }
    Gunluk-Bitir
    exit $k
}
try {
    Adim '1/5' 'hosts blogu siliniyor'
    Hosts-Islem 'kaldir'

    Adim '2/5' 'Proxy ayari geri yukleniyor, eski HTTPS_PROXY temizleniyor'
    Yonlendirmeyi-Kapat -Tam

    Adim '3/5' 'Gorev siliniyor'
    if (Get-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue) {
        Disable-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue | Out-Null
        Stop-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $GOREV -Confirm:$false
    }

    Adim '4/5' 'Surecler durduruluyor'
    Surecleri-Durdur

    Adim '5/5' 'Dosyalar siliniyor'
    $beklenen = Join-Path $env:LOCALAPPDATA 'DiscordEngelAsici'
    if ($APP -ne $beklenen) { throw "Beklenmeyen klasor: $APP" }
    for ($i = 0; ($i -lt 10) -and (Test-Path -LiteralPath $APP); $i++) {
        Remove-Item -LiteralPath $APP -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $APP) { Start-Sleep -Seconds 1 }
    }
    if (Test-Path -LiteralPath $APP) { Write-Warning "Klasor tamamen silinemedi: $APP" }

    Write-Host ''
    Write-Host 'KALDIRILDI. hosts blogu silindi, internet ayarlari kurulum oncesine dondu.'
    Gunluk-Bitir
    exit 0
} catch {
    Hata-Bildir $_.Exception.Message $Gunluk $Yukseltildi
    Gunluk-Bitir
    exit 1
}
