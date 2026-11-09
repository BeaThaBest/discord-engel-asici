# Ortak islevler. kur, kaldir, ac, kapat betikleri bunu nokta ile yukler.
# Yalniz ASCII: Windows PowerShell 5.1 BOM'suz dosyayi yerel kod sayfasiyla okur.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$APP = Join-Path $env:LOCALAPPDATA 'DiscordEngelAsici'
$GOREV = 'DiscordEngelAsici'
$PAC_URL = 'http://127.0.0.1:1099/proxy.pac'
# Eski surumun yazdigi HTTPS_PROXY degeri. Artik YAZILMAZ, yalniz bizimse temizlenir.
$ESKI_PROXY = 'http://127.0.0.1:1098'
$SNI_PORT = 443
$IS_ANAHTAR = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
$YEDEK = Join-Path $APP 'yedek.json'
$HOSTS = Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'
# Secili ByeDPI ayari, tek kaynak (ortak\strateji.py yazar, hizmet.py okur).
$STRATEJI = Join-Path $APP 'strateji.json'
$PY_APP = Join-Path $APP 'python\python.exe'

function Strateji-Sec {
    # Adaylari dener, ilk calisani $STRATEJI'ye yazar. Cikis kodunu dondurur (0 tamam, 2 hicbiri).
    & $PY_APP -I (Join-Path $APP 'ortak\strateji.py') sec --motor (Join-Path $APP 'ciadpi.exe') --yaz $STRATEJI | Write-Host
    return $LASTEXITCODE
}

function Yonetici-Mi {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function WinInet-Bildir {
    # Acik uygulamalar yeniden baslatma olmadan yeni proxy ayarini okusun.
    if (-not ('DEA.WinInet' -as [type])) {
        Add-Type -Namespace DEA -Name WinInet -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("wininet.dll", SetLastError = true)]
public static extern bool InternetSetOption(System.IntPtr h, int o, System.IntPtr b, int l);
'@
    }
    [void][DEA.WinInet]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0)  # SETTINGS_CHANGED
    [void][DEA.WinInet]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0)  # REFRESH
}

function Deger-Oku($yol, $ad) {
    $o = Get-ItemProperty -Path $yol -Name $ad -ErrorAction SilentlyContinue
    if ($null -eq $o) { return $null }
    return $o.$ad
}

function Deger-Yaz($yol, $ad, $deger, $tur) {
    if ($null -eq $deger) {
        Remove-ItemProperty -Path $yol -Name $ad -ErrorAction SilentlyContinue
    } else {
        New-ItemProperty -Path $yol -Name $ad -Value $deger -PropertyType $tur -Force | Out-Null
    }
}

function Surum-Oku($dosya) {
    $h = @{}
    foreach ($s in Get-Content -LiteralPath $dosya) {
        $s = $s.Trim()
        if ($s -eq '' -or $s.StartsWith('#')) { continue }
        $i = $s.IndexOf('=')
        if ($i -gt 0) { $h[$s.Substring(0, $i)] = $s.Substring($i + 1).Trim('"') }
    }
    return $h
}

function Surecleri-Durdur {
    # Yalniz kurulum klasorunden calisan surecler (pythonw, ciadpi).
    $onek = $APP + '\'
    for ($i = 0; $i -lt 20; $i++) {
        $s = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
            $_.Path -and $_.Path.StartsWith($onek, [StringComparison]::OrdinalIgnoreCase) })
        if ($s.Count -eq 0) { return }
        $s | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
}

function Port-Acik($port) {
    $c = New-Object Net.Sockets.TcpClient
    try { $c.Connect('127.0.0.1', $port); return $true } catch { return $false } finally { $c.Close() }
}

function Socks-Yanitliyor($port) {
    $c = New-Object Net.Sockets.TcpClient
    try {
        $c.ReceiveTimeout = 2000
        $c.SendTimeout = 2000
        $c.Connect('127.0.0.1', $port)
        $st = $c.GetStream()
        $st.Write([byte[]](5, 1, 0), 0, 3)
        $b = New-Object byte[] 2
        $n = $st.Read($b, 0, 2)
        return ($n -eq 2 -and $b[0] -eq 5 -and $b[1] -eq 0)
    } catch { return $false } finally { $c.Close() }
}

function Pac-Al {
    $w = New-Object Net.WebClient
    $w.Proxy = $null
    try { return $w.DownloadString($PAC_URL) } catch { return $null } finally { $w.Dispose() }
}

function Hizmet-Bekle($sn) {
    $son = (Get-Date).AddSeconds($sn)
    while ((Get-Date) -lt $son) {
        $pac = Pac-Al
        if ($pac -and $pac.Contains('FindProxyForURL') -and (Port-Acik $SNI_PORT) -and
            (Socks-Yanitliyor 1080) -and (Socks-Yanitliyor 1091)) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Yedekle {
    # Yalniz ilk kurulumda: sonraki kurulumlar ozgun degerleri ezmesin.
    if (Test-Path -LiteralPath $YEDEK) { return }
    $acu = Deger-Oku $IS_ANAHTAR 'AutoConfigURL'
    if ($acu -eq $PAC_URL) { $acu = $null }
    $hp = [Environment]::GetEnvironmentVariable('HTTPS_PROXY', 'User')
    if ($hp -eq $ESKI_PROXY) { $hp = $null }
    $y = [ordered]@{
        tarih         = (Get-Date).ToString('s')
        AutoConfigURL = $acu
        ProxyEnable   = Deger-Oku $IS_ANAHTAR 'ProxyEnable'
        ProxyServer   = Deger-Oku $IS_ANAHTAR 'ProxyServer'
        HTTPS_PROXY   = $hp
    }
    $y | ConvertTo-Json | Set-Content -LiteralPath $YEDEK -Encoding UTF8
}

function Eski-Proxy-Temizle {
    # Yalniz eski surumun yazdigi degeri kaldirir (kullanicinin kendi HTTPS_PROXY'sine dokunmaz).
    # Eski surum kullanicinin degerini yedege almisti: varsa onu geri koyar.
    $hp = [Environment]::GetEnvironmentVariable('HTTPS_PROXY', 'User')
    if ($hp -ne $ESKI_PROXY) { return }
    $eski = $null
    if (Test-Path -LiteralPath $YEDEK) {
        $y = Get-Content -LiteralPath $YEDEK -Raw | ConvertFrom-Json
        if ($y -and $y.HTTPS_PROXY -and ($y.HTTPS_PROXY -ne $ESKI_PROXY)) { $eski = $y.HTTPS_PROXY }
    }
    # SetEnvironmentVariable WM_SETTINGCHANGE yayinini kendisi yapar.
    [Environment]::SetEnvironmentVariable('HTTPS_PROXY', $eski, 'User')
}

function Yonlendirmeyi-Ac {
    New-ItemProperty -Path $IS_ANAHTAR -Name AutoConfigURL -Value $PAC_URL -PropertyType String -Force | Out-Null
    WinInet-Bildir
    Eski-Proxy-Temizle
}

function Yonlendirmeyi-Kapat([switch]$Tam) {
    # Tam (kaldirma): ProxyEnable ve ProxyServer da yedekteki degere doner.
    $y = $null
    if (Test-Path -LiteralPath $YEDEK) { $y = Get-Content -LiteralPath $YEDEK -Raw | ConvertFrom-Json }
    if ($y) {
        Deger-Yaz $IS_ANAHTAR 'AutoConfigURL' $y.AutoConfigURL 'String'
        if ($Tam) {
            $pe = $null
            if ($null -ne $y.ProxyEnable) { $pe = [int]$y.ProxyEnable }
            Deger-Yaz $IS_ANAHTAR 'ProxyEnable' $pe 'DWord'
            Deger-Yaz $IS_ANAHTAR 'ProxyServer' $y.ProxyServer 'String'
        }
    } elseif ((Deger-Oku $IS_ANAHTAR 'AutoConfigURL') -eq $PAC_URL) {
        Deger-Yaz $IS_ANAHTAR 'AutoConfigURL' $null 'String'
    }
    WinInet-Bildir
    Eski-Proxy-Temizle
}

function Dns-Temizle {
    try { Clear-DnsClientCache -ErrorAction Stop } catch { & ipconfig.exe /flushdns | Out-Null }
}

function Port-Sahibi($port) {
    try {
        $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop | Select-Object -First 1
        $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if ($p) { return "$($p.ProcessName) (PID $($p.Id))" }
        return "PID $($c.OwningProcess)"
    } catch { return 'bilinmeyen surec' }
}

function Hosts-Python-Bul {
    # (python yolu, hosts_blok.py yolu). Once kurulu gomulu Python, yoksa repodaki betik + sistem Python.
    $py = Join-Path $APP 'python\python.exe'
    $bl = Join-Path $APP 'ortak\hosts_blok.py'
    if ((Test-Path -LiteralPath $py) -and (Test-Path -LiteralPath $bl)) { return @($py, $bl) }
    $bl = Join-Path (Split-Path -Parent $PSScriptRoot) 'ortak\hosts_blok.py'
    foreach ($ad in 'python.exe', 'py.exe') {
        $k = Get-Command $ad -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($k -and (Test-Path -LiteralPath $bl)) { return @($k.Source, $bl) }
    }
    throw 'hosts blogu icin Python bulunamadi.'
}

function Hosts-Islem([string]$komut) {
    # Yonetici gerekir. hosts_blok.py CRLF korur ve ilk yazimda yedek alir.
    $pb = Hosts-Python-Bul
    $a = @('-I', $pb[1], $komut, '--hosts', $HOSTS)
    if ($komut -eq 'yaz') { $a += @('--alanlar', (Join-Path $APP 'ortak\alanlar.txt')) }
    & $pb[0] @a
    if ($LASTEXITCODE -ne 0) { throw "hosts blogu ($komut) basarisiz, kod $LASTEXITCODE." }
    Dns-Temizle
}

function Yukselt-Gerekirse([string]$betik, [string]$ek) {
    # Yonetici degilse betigi bir kez UAC ile yeniden baslatir, cikis kodunu dondurur.
    # Zaten yoneticiyse $null doner. Ayni kullanici kimligiyle devam edilir varsayilir.
    if (Yonetici-Mi) { return $null }
    Write-Host 'Yonetici izni isteniyor (tek UAC istemi)...'
    $ps = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $a = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -Yukseltildi {1}' -f $betik, $ek
    try {
        $p = Start-Process -FilePath $ps -ArgumentList $a -Verb RunAs -Wait -PassThru
    } catch {
        throw 'Yonetici izni alinamadi (UAC reddedildi ya da hesap yonetici degil). Standart kullanici icin README bolumune bak.'
    }
    return $p.ExitCode
}

function Gorev-Xml([bool]$s4u) {
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $py = [Security.SecurityElement]::Escape((Join-Path $APP 'python\pythonw.exe'))
    $arg = '"{0}" --alanlar "{1}" --motor-exe "{2}" --log "{3}" --strateji "{4}"' -f (Join-Path $APP 'ortak\hizmet.py'),
        (Join-Path $APP 'ortak\alanlar.txt'), (Join-Path $APP 'ciadpi.exe'), (Join-Path $APP 'log\hizmet.log'), $STRATEJI
    $arg = [Security.SecurityElement]::Escape($arg)
    $dizin = [Security.SecurityElement]::Escape($APP)
    $simdi = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss')
    if ($s4u) {
        # Acilista, oturum acilmadan once; etkilesimsiz oturum, ekranda hicbir sey cikmaz.
        $acilis = '<BootTrigger><Enabled>true</Enabled></BootTrigger>'
        $oturum = 'S4U'
    } else {
        $acilis = ''
        $oturum = 'InteractiveToken'
    }
    return @"
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>Discord Engel Asici</Author>
    <Description>Yalniz Discord trafigi icin yerel proxy (127.0.0.1:1080, 1091, 1099) ve hosts adlari icin 443 SNI dinleyici. Kaldirma: windows\KALDIR.cmd</Description>
  </RegistrationInfo>
  <Triggers>
    $acilis
    <LogonTrigger><Enabled>true</Enabled><UserId>$sid</UserId></LogonTrigger>
    <TimeTrigger>
      <Enabled>true</Enabled>
      <StartBoundary>$simdi</StartBoundary>
      <Repetition><Interval>PT5M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$sid</UserId>
      <LogonType>$oturum</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>4</Priority>
    <RestartOnFailure><Interval>PT1M</Interval><Count>999</Count></RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$py</Command>
      <Arguments>$arg</Arguments>
      <WorkingDirectory>$dizin</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@
}
