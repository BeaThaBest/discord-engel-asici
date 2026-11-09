# Ortak islevler. kur, kaldir, ac, kapat betikleri bunu nokta ile yukler.
# Yalniz ASCII: Windows PowerShell 5.1 BOM'suz dosyayi yerel kod sayfasiyla okur.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$APP = Join-Path $env:LOCALAPPDATA 'DiscordEngelAsici'
$GOREV = 'DiscordEngelAsici'
$PAC_URL = 'http://127.0.0.1:1099/proxy.pac'
$KOPRU_URL = 'http://127.0.0.1:1098'
$IS_ANAHTAR = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
$YEDEK = Join-Path $APP 'yedek.json'

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
        if ($pac -and $pac.Contains('FindProxyForURL') -and (Port-Acik 1098) -and
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
    if ($hp -eq $KOPRU_URL) { $hp = $null }
    $y = [ordered]@{
        tarih         = (Get-Date).ToString('s')
        AutoConfigURL = $acu
        ProxyEnable   = Deger-Oku $IS_ANAHTAR 'ProxyEnable'
        ProxyServer   = Deger-Oku $IS_ANAHTAR 'ProxyServer'
        HTTPS_PROXY   = $hp
    }
    $y | ConvertTo-Json | Set-Content -LiteralPath $YEDEK -Encoding UTF8
}

function Yonlendirmeyi-Ac {
    New-ItemProperty -Path $IS_ANAHTAR -Name AutoConfigURL -Value $PAC_URL -PropertyType String -Force | Out-Null
    WinInet-Bildir
    # Discord guncelleyicisi PAC okumaz, yalniz HTTPS_PROXY (bkz. README).
    [Environment]::SetEnvironmentVariable('HTTPS_PROXY', $KOPRU_URL, 'User')
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
        $hp = $y.HTTPS_PROXY
    } else {
        if ((Deger-Oku $IS_ANAHTAR 'AutoConfigURL') -eq $PAC_URL) { Deger-Yaz $IS_ANAHTAR 'AutoConfigURL' $null 'String' }
        $hp = [Environment]::GetEnvironmentVariable('HTTPS_PROXY', 'User')
        if ($hp -eq $KOPRU_URL) { $hp = $null }
    }
    WinInet-Bildir
    [Environment]::SetEnvironmentVariable('HTTPS_PROXY', $hp, 'User')
}

function Gorev-Xml([bool]$s4u) {
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $py = [Security.SecurityElement]::Escape((Join-Path $APP 'python\pythonw.exe'))
    $arg = '"{0}" --alanlar "{1}" --motor-exe "{2}" --log "{3}"' -f (Join-Path $APP 'ortak\hizmet.py'),
        (Join-Path $APP 'ortak\alanlar.txt'), (Join-Path $APP 'ciadpi.exe'), (Join-Path $APP 'log\hizmet.log')
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
    <Description>Yalniz Discord trafigi icin yerel proxy (127.0.0.1:1080, 1091, 1098, 1099). Kaldirma: windows\KALDIR.cmd</Description>
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
