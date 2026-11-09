# kapat.ps1 sonrasi tekrar acar. Ilk kurulum icin kur.ps1 kullan.
. (Join-Path $PSScriptRoot 'islevler.ps1')
try {
    if (-not (Get-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue)) { throw 'Gorev yok, once kur.ps1' }
    Enable-ScheduledTask -TaskName $GOREV | Out-Null
    Start-ScheduledTask -TaskName $GOREV
    if (-not (Hizmet-Bekle 60)) { throw 'Hizmet 60 sn icinde hazir olmadi. Yonlendirme ACILMADI.' }
    Yonlendirmeyi-Ac
    Write-Host 'ACILDI.'
    exit 0
} catch {
    Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
