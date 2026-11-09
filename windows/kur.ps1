# Discord Engel Asici Windows kurulumu. Tek adim, soru sormaz, tekrar calistirilabilir.
# Kullanim: windows\KUR.cmd cift tik, ya da:
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\kur.ps1
# -MotorYolu: indirme yerine yerel ciadpi.exe (ornegin motor/derle-windows.sh ciktisi).
param([string]$MotorYolu)
. (Join-Path $PSScriptRoot 'islevler.ps1')
$REPO = Split-Path -Parent $PSScriptRoot

function Indir-Dogrula($url, $sha, $hedef) {
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $hedef
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath $hedef).Hash.ToLower()
    if ($h -ne $sha.ToLower()) { throw "SHA256 uyusmuyor: $url (beklenen $sha, gelen $h)" }
}

function Ozet($yol) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $yol).Hash.ToLower() }

try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw '64 bit Windows gerekir.' }
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $S = Surum-Oku (Join-Path $REPO 'motor\SURUM')
    $TMP = Join-Path $env:TEMP ('dea-kur-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $APP, (Join-Path $APP 'log'), (Join-Path $APP 'ortak'), $TMP | Out-Null

    Write-Host '1/6 Onceki proxy ayarlarinin yedegi'
    Yedekle

    Write-Host '2/6 Eski hizmet durduruluyor (varsa)'
    if (Get-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue) {
        # Once devre disi: 5 dk bekcisi dosyalar degisirken yeniden baslatmasin.
        Disable-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue | Out-Null
        Stop-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue
    }
    Surecleri-Durdur

    Write-Host "3/6 Python $($S.PYTHON_WIN_SURUM) (gomulu, konsolsuz pythonw)"
    $pyDizin = Join-Path $APP 'python'
    $pyIsaret = Join-Path $pyDizin 'DEA-SURUM.txt'
    $pyTamam = (Test-Path -LiteralPath (Join-Path $pyDizin 'pythonw.exe')) -and (Test-Path -LiteralPath $pyIsaret) -and
        ((Get-Content -LiteralPath $pyIsaret -Raw).Trim() -eq $S.PYTHON_WIN_SURUM)
    if (-not $pyTamam) {
        $z = Join-Path $TMP 'python.zip'
        Indir-Dogrula $S.PYTHON_WIN_URL $S.PYTHON_WIN_SHA256 $z
        if (Test-Path -LiteralPath $pyDizin) { Remove-Item -LiteralPath $pyDizin -Recurse -Force }
        Expand-Archive -LiteralPath $z -DestinationPath $pyDizin
        Set-Content -LiteralPath $pyIsaret -Value $S.PYTHON_WIN_SURUM -Encoding ASCII
    }

    Write-Host '4/6 Motor (ByeDPI) ve ortak dosyalar'
    $motor = Join-Path $APP 'ciadpi.exe'
    if ($MotorYolu) {
        Copy-Item -LiteralPath $MotorYolu -Destination $motor -Force
    } elseif (-not ((Test-Path -LiteralPath $motor) -and ((Ozet $motor) -eq $S.BYEDPI_WIN_EXE_SHA256))) {
        $z = Join-Path $TMP 'byedpi.zip'
        Indir-Dogrula $S.BYEDPI_WIN_URL $S.BYEDPI_WIN_SHA256 $z
        $ac = Join-Path $TMP 'byedpi'
        Expand-Archive -LiteralPath $z -DestinationPath $ac
        $exe = Get-ChildItem -LiteralPath $ac -Recurse -Filter 'ciadpi.exe' | Select-Object -First 1
        if (-not $exe) { throw 'Arsivde ciadpi.exe yok.' }
        if ((Ozet $exe.FullName) -ne $S.BYEDPI_WIN_EXE_SHA256) { throw 'ciadpi.exe SHA256 uyusmuyor.' }
        Copy-Item -LiteralPath $exe.FullName -Destination $motor -Force
    }
    foreach ($f in 'connect-bridge.py', 'pac_uret.py', 'hizmet.py', 'alanlar.txt') {
        Copy-Item -LiteralPath (Join-Path $REPO "ortak\$f") -Destination (Join-Path $APP "ortak\$f") -Force
    }

    Write-Host '5/6 Gorev Zamanlayici'
    $tur = $null
    if (Yonetici-Mi) {
        try {
            Register-ScheduledTask -TaskName $GOREV -Xml (Gorev-Xml $true) -Force | Out-Null
            $tur = 'acilista (oturum acilmadan once, S4U, etkilesimsiz) + oturum acilisi + 5 dk bekci'
        } catch {
            Write-Warning "S4U gorevi kaydedilemedi: $($_.Exception.Message)"
        }
    }
    if (-not $tur) {
        Register-ScheduledTask -TaskName $GOREV -Xml (Gorev-Xml $false) -Force | Out-Null
        $tur = 'oturum acilisinda (yonetici degil, acilis yarisina karsi yalniz Discord yeniden denemesi) + 5 dk bekci'
    }
    Start-ScheduledTask -TaskName $GOREV
    if (-not (Hizmet-Bekle 60)) {
        $log = Join-Path $APP 'log\hizmet.log'
        if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Tail 15 | Write-Host }
        throw 'Hizmet 60 sn icinde hazir olmadi. Proxy ayari ACILMADI, internet etkilenmedi.'
    }

    Write-Host '6/6 Yalniz Discord icin yonlendirme (PAC + HTTPS_PROXY)'
    Yonlendirmeyi-Ac
    Remove-Item -LiteralPath $TMP -Recurse -Force -ErrorAction SilentlyContinue

    Write-Host ''
    Write-Host "KURULUM TAMAM. Gorev: $GOREV, $tur"
    Write-Host "Klasor: $APP"
    if (Get-Process -Name Discord -ErrorAction SilentlyContinue) {
        Write-Host 'Discord acik: bir kez tamamen kapatip (tepsiden Cikis) yeniden ac.'
    }
    exit 0
} catch {
    Write-Host ''
    Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
