# Windows internet testi 2026-11-09

Uretici: `windows/internet-testi.ps1`. Hucre bos ise o durum olculmedi. Kod 000: baglanti kurulamadi.

## Durumlar

| | A | B | C |
|---|---|---|---|
| aciklama | GoodbyeDPI acik, bizimki kapali | ikisi kapali | GoodbyeDPI kapali, bizimki acik |
| zaman | 2026-11-09T18:05:35 | 2026-11-09T18:08:35 | 2026-11-09T18:10:36 |
| dns_onbellek | temizlendi | temizlendi | temizlendi |
| goodbyedpi_servis |  |  |  |
| windivert_surucu | WinDivert=Running/Disabled |  |  |
| goodbyedpi_surec | 1 | 0 | 0 |
| bizim_gorev | yok | yok | Running |
| bizim_portlar |  |  | ::1:443 127.0.0.1:1080 127.0.0.1:1091 127.0.0.1:1099 127.0.0.1:443 |
| sni_443_dinliyor | False | False | True |
| hosts_blogu | False | False | True |
| AutoConfigURL |  |  | http://127.0.0.1:1099/proxy.pac |
| HTTPS_PROXY_kullanici |  |  |  |

## DNS cozumleme (ms, sonuc)

| Alan | A | B | C |
|---|---|---|---|
| discord.com | 4756.9 ms  discord.com : DNS sunucusu hatası | 63 ms 162.159.136.232,162.159.137.232,162.159.138.232,162.159.128.233,162.159.135.232 | 41.3 ms 162.159.137.232,162.159.138.232,162.159.128.233,162.159.135.232,162.159.136.232 |
| gateway.discord.gg | 4737.5 ms  gateway.discord.gg : DNS sunucusu hatası | 5.6 ms 162.159.135.234,162.159.133.234,162.159.134.234,162.159.136.234,162.159.130.234 | 4.9 ms 162.159.134.234,162.159.133.234,162.159.135.234,162.159.130.234,162.159.136.234 |
| cdn.discordapp.com | 4702.5 ms  cdn.discordapp.com : DNS sunucusu hatası | 7.9 ms 162.159.134.233,162.159.135.233,162.159.129.233,162.159.130.233,162.159.133.233 | 5.1 ms 162.159.129.233,162.159.130.233,162.159.133.233,162.159.134.233,162.159.135.233 |
| google.com | 4725.3 ms  google.com : DNS sunucusu hatası | 10.2 ms 142.251.208.110 | 5.4 ms 142.251.208.110 |
| microsoft.com | 4726.8 ms  microsoft.com : DNS sunucusu hatası | 8 ms 150.171.109.107 | 4.7 ms 150.171.109.103 |
| cloudflare.com | 4728.5 ms  cloudflare.com : DNS sunucusu hatası | 6.9 ms 104.16.132.229,104.16.133.229 | 4.9 ms 104.16.132.229,104.16.133.229 |

## HTTPS TTFB, Discord disi, dogrudan (kod / TTFB ms)

| Site | A | B | C |
|---|---|---|---|
| https://www.google.com/ | 000 / 2360 | 200 / 341 | 200 / 436 |
| https://www.microsoft.com/ | 000 / 4811 | 200 / 124 | 200 / 98 |
| https://www.cloudflare.com/ | 000 / 1276 | 200 / 238 | 200 / 185 |
| https://www.wikipedia.org/ | 000 / 1070 | 200 / 323 | 200 / 228 |
| https://github.com/ | 000 / 4798 | 200 / 278 | 200 / 197 |
| https://www.youtube.com/ | 000 / 38 | 200 / 263 | 200 / 242 |
| https://www.amazon.com/ | 000 / 2146 | 503 / 326 | 503 / 278 |
| https://www.apple.com/ | 000 / 4803 | 200 / 414 | 200 / 39 |

## Indirme ve ping

| Olcum | A | B | C |
|---|---|---|---|
| Indirme 25 MB (Mbit/sn) | 0 (000) | 555.5 (200) | 738.3 (200) |
| Ping 1.1.1.1 (ort ms, kayip) | 2.2, 0/5 | 2.2, 0/5 | 2, 0/5 |
| Ping 8.8.8.8 (ort ms, kayip) | 14.6, 0/5 | 14, 0/5 | 14, 0/5 |

## Discord uclari (kod / toplam ms)

| Uc | Yol | A | B | C |
|---|---|---|---|---|
| https://discord.com/api/v9/gateway | dogrudan | 000 / 2158 | 000 / 21 | 000 / 37 |
| https://discord.com/api/v9/gateway | socks1080 | 000 / 2047 | 000 / 2047 | 200 / 29 |
| https://cdn.discordapp.com/ | dogrudan | 000 / 4791 | 000 / 25 | 000 / 27 |
| https://cdn.discordapp.com/ | socks1080 | 000 / 2057 | 000 / 2050 | 403 / 24 |
| https://updates.discord.com/ | dogrudan | 000 / 4773 | 000 / 28 | 404 / 56 |
| https://updates.discord.com/ | socks1080 | 000 / 2038 | 000 / 2047 | 404 / 25 |
| https://dl2.discordapp.net/ | dogrudan | 000 / 2162 | 404 / 277 | 404 / 115 |
| https://dl2.discordapp.net/ | socks1080 | 000 / 2039 | 000 / 2054 | 000 / 15027 |
| https://media.discordapp.net/ | dogrudan | 000 / 4777 | 401 / 294 | 401 / 253 |
| https://media.discordapp.net/ | socks1080 | 000 / 2049 | 000 / 2044 | 401 / 215 |

## Notlar (elle eklendi)

* A koşulu: GoodbyeDPI PC'de hizmet değil, elle çalıştırılıyor ve keşif anında kapalıydı (`docs/windows-onceki-durum-2026-11-09.md`). Ölçüm için `x86_64\goodbyedpi.exe` argümansız (varsayılan `-9`, başlangıç kısayolunun aynısı) SSH oturumundan (Session 0, yönetici) gizli başlatıldı, ölçümden sonra durduruldu, WinDivert sürücüsü durdu.
* A sonucu tekrar denendi, aynı: sistem çözücüsü (Dnscache) her adda 4,7 sn sonra "DNS sunucusu hatası" veriyor, `nslookup google.com 1.1.1.1` (UDP) ise yanıt alıyor; IP ile `https://www.google.com` 15 sn zaman aşımı, Discord IP ile rc 35. Yorum: DNS sunucuları 1.1.1.1 ve 1.0.0.1 için Windows DoH otomatik yükseltme açık (`Get-DnsClientDohServerAddress` AutoUpgrade True), yani sistem DNS'i de TCP 443 üzerinden gidiyor; GoodbyeDPI bu PC'de (bu başlatma biçimiyle) tüm TCP 443'ü bozdu, DNS de onunla düştü. Bartın'ın masaüstünde elle çift tıkladığında davranış farklı olabilir, o ayrıca denenmedi.
* B: Discord dışı her şey normal, Discord ana adları DPI engelli (rc 35); `dl2.discordapp.net` ve `media.discordapp.net` doğrudan açık.
* C: Discord dışı değerler B ile aynı düzeyde (TTFB, DNS, ping farkı ölçüm gürültüsü). `updates.discord.com` proxysiz 404 (hosts bloğu ve 443 SNI dinleyici), gateway SOCKS 1080 ile 200.
* C `dl2.discordapp.net` socks1080 satırı 15 sn zaman aşımı: bu ad PAC'te 1091'e (`-d 8+s`) gider, 1080 yolu kullanılmaz. Ayrı denemede `-x socks5h://127.0.0.1:1091` ile 404 (yanıt var).
* PAC (C): sunulan `proxy.pac` PC'de JScript ile değerlendirildi: discord.com, gateway.discord.gg, cdn.discordapp.com, media.discordapp.net, discordstatus.com SOCKS5 1080; dl2 ve `*.dl2-*.discordapp.net` SOCKS5 1091; updates.discord.com, evildiscord.com, discord.com.evil.net, google, github DIRECT. WinHTTP (`WinHttpGetProxyForUrl`) SOCKS desteklemediği için her ada DIRECT döner, yani WinHTTP kullanan Discord dışı uygulamalar PAC'ten hiç etkilenmez.
