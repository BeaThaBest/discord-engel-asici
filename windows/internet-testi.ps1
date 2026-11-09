# Genel internet testi, uc durumda ayni olcum seti. GoodbyeDPI'yi bu betik YONETMEZ,
# yalniz mevcut durumunu yazar.
#   A: GoodbyeDPI acik, bizimki kapali
#   B: ikisi kapali
#   C: GoodbyeDPI kapali, bizimki acik
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\internet-testi.ps1 -Durum A
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\internet-testi.ps1 -Birlestir
# Cikti: $env:TEMP\dea-internet-testi-<Durum>.json; -Birlestir: docs\windows-internet-testi-<tarih>.md
param(
    [ValidateSet('A', 'B', 'C')][string]$Durum,
    [switch]$Birlestir,
    [string]$Klasor = $env:TEMP
)
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
$REPO = Split-Path -Parent $PSScriptRoot
$ACIKLAMA = @{ A = 'GoodbyeDPI acik, bizimki kapali'; B = 'ikisi kapali'; C = 'GoodbyeDPI kapali, bizimki acik' }
$DNS_ALANLAR = 'discord.com', 'gateway.discord.gg', 'cdn.discordapp.com', 'google.com', 'microsoft.com', 'cloudflare.com'
$SITELER = 'https://www.google.com/', 'https://www.microsoft.com/', 'https://www.cloudflare.com/', 'https://www.wikipedia.org/',
    'https://github.com/', 'https://www.youtube.com/', 'https://www.amazon.com/', 'https://www.apple.com/'
$DISCORD_UCLAR = 'https://discord.com/api/v9/gateway', 'https://cdn.discordapp.com/', 'https://updates.discord.com/',
    'https://dl2.discordapp.net/', 'https://media.discordapp.net/'
$INDIRME = 'https://speed.cloudflare.com/__down?bytes=25000000'
$PING_HEDEF = '1.1.1.1', '8.8.8.8'
# Discord dogrudan (proxysiz; updates.discord.com hosts blogu ile 443 SNI dinleyiciye gider) ve ana SOCKS (1080) ile denenir.
$YOLLAR = [ordered]@{
    dogrudan = @('--noproxy', '*')
    socks1080 = @('-x', 'socks5h://127.0.0.1:1080')
}

function Json-Yolu($d) { return (Join-Path $Klasor "dea-internet-testi-$d.json") }

function Curl-Olc($url, $ek) {
    $bicim = '%{http_code} %{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer} %{time_total}'
    $a = @('-s', '-o', 'NUL', '--max-time', '20', '-w', $bicim) + $ek + @($url)
    $c = & curl.exe @a 2>$null
    $p = ("$c".Trim() -split '\s+')
    if ($p.Count -lt 6) { $p = @('000', '0', '0', '0', '0', '0') }
    return [ordered]@{
        url = $url; kod = $p[0]
        dns_ms = [math]::Round([double]$p[1] * 1000); baglanti_ms = [math]::Round([double]$p[2] * 1000)
        tls_ms = [math]::Round([double]$p[3] * 1000); ttfb_ms = [math]::Round([double]$p[4] * 1000)
        toplam_ms = [math]::Round([double]$p[5] * 1000)
    }
}

function Dns-Olc($ad) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $ips = ''; $hata = $null
    try {
        $r = Resolve-DnsName -Name $ad -Type A -DnsOnly -ErrorAction Stop
        $ips = (@($r | Where-Object { $_.Type -eq 'A' } | ForEach-Object { $_.IPAddress }) -join ',')
    } catch { $hata = $_.Exception.Message }
    $sw.Stop()
    return [ordered]@{ ad = $ad; ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 1); sonuc = $ips; hata = $hata }
}

function Ping-Olc($ip) {
    $p = New-Object Net.NetworkInformation.Ping
    $sureler = @(); $kayip = 0
    foreach ($i in 1..5) {
        try {
            $r = $p.Send($ip, 2000)
            if ($r.Status -eq 'Success') { $sureler += [int]$r.RoundtripTime } else { $kayip++ }
        } catch { $kayip++ }
    }
    $ort = $null
    if ($sureler.Count -gt 0) { $ort = [math]::Round(($sureler | Measure-Object -Average).Average, 1) }
    return [ordered]@{ hedef = $ip; ort_ms = $ort; kayip = "$kayip/5" }
}

function Port-Dinliyor($port) {
    $c = New-Object Net.Sockets.TcpClient
    try { $c.Connect('127.0.0.1', $port); return $true } catch { return $false } finally { $c.Close() }
}

function Hosts-Blogu-Var {
    $h = Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'
    return [bool](Select-String -LiteralPath $h -Pattern '>>> DiscordEngelAsici >>>' -SimpleMatch -Quiet -ErrorAction SilentlyContinue)
}

function Durum-Bilgisi {
    $gs = @(Get-Service -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*GoodbyeDPI*' -or $_.DisplayName -like '*GoodbyeDPI*' } |
        ForEach-Object { "$($_.Name)=$($_.Status)/$($_.StartType)" })
    $wd = @(Get-CimInstance Win32_SystemDriver -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'WinDivert*' } |
        ForEach-Object { "$($_.Name)=$($_.State)/$($_.StartMode)" })
    $gp = @(Get-Process -Name 'goodbyedpi*' -ErrorAction SilentlyContinue).Count
    $gorev = Get-ScheduledTask -TaskName 'DiscordEngelAsici' -ErrorAction SilentlyContinue
    $dinleyen = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -in 1080, 1091, 1099, 443 } | ForEach-Object { "$($_.LocalAddress):$($_.LocalPort)" } | Sort-Object -Unique)
    $acu = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue).AutoConfigURL
    $gorevDurum = 'yok'
    if ($gorev) { $gorevDurum = "$($gorev.State)" }
    return [ordered]@{
        goodbyedpi_servis = ($gs -join '; '); windivert_surucu = ($wd -join '; '); goodbyedpi_surec = $gp
        bizim_gorev = $gorevDurum; bizim_portlar = ($dinleyen -join ' '); sni_443_dinliyor = (Port-Dinliyor 443); hosts_blogu = (Hosts-Blogu-Var)
        AutoConfigURL = $acu; HTTPS_PROXY_kullanici = [Environment]::GetEnvironmentVariable('HTTPS_PROXY', 'User')
    }
}

function Olc {
    if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) { throw 'curl.exe yok (Windows 10 1803+ gerekir).' }
    Write-Host "Durum $Durum ($($ACIKLAMA[$Durum])) olculuyor..."
    $onbellek = 'temizlendi'
    try { Clear-DnsClientCache -ErrorAction Stop } catch { $onbellek = 'temizlenemedi' }
    $s = [ordered]@{
        durum = $Durum; aciklama = $ACIKLAMA[$Durum]; zaman = (Get-Date).ToString('s'); bilgisayar = $env:COMPUTERNAME
        sistem = Durum-Bilgisi; dns_onbellek = $onbellek
        dns = @($DNS_ALANLAR | ForEach-Object { Dns-Olc $_ })
        ttfb = @($SITELER | ForEach-Object { Curl-Olc $_ $YOLLAR.dogrudan })
        indirme = $null
        ping = @($PING_HEDEF | ForEach-Object { Ping-Olc $_ })
        discord = @()
        guncelleyici = $null
    }
    $c = & curl.exe -s -o NUL --noproxy '*' --max-time 90 -w '%{http_code} %{size_download} %{time_total} %{speed_download}' $INDIRME 2>$null
    $p = ("$c".Trim() -split '\s+')
    if ($p.Count -ge 4) {
        $s.indirme = [ordered]@{ url = $INDIRME; kod = $p[0]; bayt = [int64][double]$p[1]; sure_sn = [math]::Round([double]$p[2], 2)
            mbps = [math]::Round([double]$p[3] * 8 / 1e6, 1) }
    }
    # Guncelleyici yolu: proxysiz updates.discord.com
    $s.guncelleyici = Curl-Olc 'https://updates.discord.com/' $YOLLAR.dogrudan
    foreach ($u in $DISCORD_UCLAR) {
        foreach ($y in $YOLLAR.Keys) {
            $o = Curl-Olc $u $YOLLAR[$y]
            $o.yol = $y
            $s.discord += $o
        }
    }
    $yol = Json-Yolu $Durum
    $s | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $yol -Encoding UTF8
    Write-Host "JSON: $yol"
    # Markdown satirlari (tek durum)
    Write-Output "| Olcum | $Durum |"
    Write-Output '|---|---|'
    foreach ($d in $s.dns) { Write-Output "| DNS $($d.ad) | $($d.ms) ms $($d.sonuc) $($d.hata) |" }
    foreach ($t in $s.ttfb) { Write-Output "| TTFB $($t.url) | $($t.kod) / $($t.ttfb_ms) ms |" }
    if ($s.indirme) { Write-Output "| Indirme | $($s.indirme.mbps) Mbit/sn ($($s.indirme.kod)) |" }
    foreach ($g in $s.ping) { Write-Output "| Ping $($g.hedef) | $($g.ort_ms) ms, kayip $($g.kayip) |" }
    Write-Output "| Guncelleyici (proxysiz updates.discord.com) | $($s.guncelleyici.kod) / $($s.guncelleyici.toplam_ms) ms |"
    foreach ($o in $s.discord) { Write-Output "| $($o.url) ($($o.yol)) | $($o.kod) / $($o.toplam_ms) ms |" }
}

function Hucre($v, $f) {
    if ($null -eq $v) { return 'olculmedi' }
    return (& $f $v)
}

function Birlestir-Rapor {
    $v = [ordered]@{}
    foreach ($d in 'A', 'B', 'C') {
        $f = Json-Yolu $d
        if (Test-Path -LiteralPath $f) { $v[$d] = Get-Content -LiteralPath $f -Raw | ConvertFrom-Json } else { $v[$d] = $null }
    }
    $L = New-Object Collections.Generic.List[string]
    $L.Add("# Windows internet testi $((Get-Date).ToString('yyyy-MM-dd'))")
    $L.Add('')
    $L.Add('Uretici: `windows/internet-testi.ps1`. Hucre bos ise o durum olculmedi. Kod 000: baglanti kurulamadi.')
    $L.Add('')
    $L.Add('## Durumlar')
    $L.Add('')
    $L.Add('| | A | B | C |')
    $L.Add('|---|---|---|---|')
    foreach ($k in 'aciklama', 'zaman', 'dns_onbellek') {
        $L.Add("| $k | " + (($v.Keys | ForEach-Object { Hucre $v[$_] { param($x) $x.$k } }) -join ' | ') + ' |')
    }
    foreach ($k in 'goodbyedpi_servis', 'windivert_surucu', 'goodbyedpi_surec', 'bizim_gorev', 'bizim_portlar', 'sni_443_dinliyor', 'hosts_blogu', 'AutoConfigURL', 'HTTPS_PROXY_kullanici') {
        $L.Add("| $k | " + (($v.Keys | ForEach-Object { Hucre $v[$_] { param($x) $x.sistem.$k } }) -join ' | ') + ' |')
    }
    $L.Add('')
    $L.Add('## DNS cozumleme (ms, sonuc)')
    $L.Add('')
    $L.Add('| Alan | A | B | C |')
    $L.Add('|---|---|---|---|')
    foreach ($ad in $DNS_ALANLAR) {
        $L.Add("| $ad | " + (($v.Keys | ForEach-Object { Hucre $v[$_] { param($x) $o = $x.dns | Where-Object { $_.ad -eq $ad }; "$($o.ms) ms $($o.sonuc) $($o.hata)".Trim() } }) -join ' | ') + ' |')
    }
    $L.Add('')
    $L.Add('## HTTPS TTFB, Discord disi, dogrudan (kod / TTFB ms)')
    $L.Add('')
    $L.Add('| Site | A | B | C |')
    $L.Add('|---|---|---|---|')
    foreach ($u in $SITELER) {
        $L.Add("| $u | " + (($v.Keys | ForEach-Object { Hucre $v[$_] { param($x) $o = $x.ttfb | Where-Object { $_.url -eq $u }; "$($o.kod) / $($o.ttfb_ms)" } }) -join ' | ') + ' |')
    }
    $L.Add('')
    $L.Add('## Indirme ve ping')
    $L.Add('')
    $L.Add('| Olcum | A | B | C |')
    $L.Add('|---|---|---|---|')
    $L.Add('| Indirme 25 MB (Mbit/sn) | ' + (($v.Keys | ForEach-Object { Hucre $v[$_] { param($x) if ($x.indirme) { "$($x.indirme.mbps) ($($x.indirme.kod))" } else { 'hata' } } }) -join ' | ') + ' |')
    foreach ($ip in $PING_HEDEF) {
        $L.Add("| Ping $ip (ort ms, kayip) | " + (($v.Keys | ForEach-Object { Hucre $v[$_] { param($x) $o = $x.ping | Where-Object { $_.hedef -eq $ip }; "$($o.ort_ms), $($o.kayip)" } }) -join ' | ') + ' |')
    }
    $L.Add('')
    $L.Add('## Discord uclari (kod / toplam ms)')
    $L.Add('')
    $L.Add('| Uc | Yol | A | B | C |')
    $L.Add('|---|---|---|---|---|')
    foreach ($u in $DISCORD_UCLAR) {
        foreach ($y in $YOLLAR.Keys) {
            $L.Add("| $u | $y | " + (($v.Keys | ForEach-Object { Hucre $v[$_] { param($x) $o = $x.discord | Where-Object { $_.url -eq $u -and $_.yol -eq $y }; "$($o.kod) / $($o.toplam_ms)" } }) -join ' | ') + ' |')
        }
    }
    $docs = Join-Path $REPO 'docs'
    New-Item -ItemType Directory -Force -Path $docs | Out-Null
    $yol = Join-Path $docs "windows-internet-testi-$((Get-Date).ToString('yyyy-MM-dd')).md"
    [IO.File]::WriteAllText($yol, (($L -join "`n") + "`n"), (New-Object Text.UTF8Encoding $false))
    Write-Host "Rapor: $yol"
}

if ($Birlestir) { Birlestir-Rapor; exit 0 }
if (-not $Durum) { Write-Host 'Kullanim: -Durum A|B|C ya da -Birlestir'; exit 2 }
Olc
