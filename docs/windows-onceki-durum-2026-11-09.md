# Windows PC önceki durum (2026-11-09, kurulumdan önce)

Amaç: geri dönüş. Keşif SSH ile salt okunur yapıldı (Session 0, yönetici token).

## Sistem

* Bilgisayar: test PC'si, Windows 11 Pro 10.0.26200, 64 bit, Windows PowerShell 5.1.26100.
* Kullanıcı: yerel yönetici hesabı, profil `C:\Users\<kullanici>`, konsol oturumu 1 açık (13:13 açılış).
* DNS: Ethernet `1.1.1.1, 1.0.0.1` (dokunulmadı).
* Defender: gerçek zamanlı koruma açık, kurcalama koruması açık.

## GoodbyeDPI

* Sürüm 0.2.3rc3, klasör `C:\Users\<kullanici>\Desktop\...\goodbyedpi-0.2.3rc3-2` (x86, x86_64, cmd betikleri).
* Hizmet olarak KURULU DEĞİL (`GoodbyeDPI` hizmeti yok, `service_install_*.cmd` kullanılmamış).
* Başlangıç: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\goodbyedpi.exe - Kısayol.lnk`, hedef `x86_64\goodbyedpi.exe`, argüman yok (varsayılan `-9`). Bu girdi 2025-01-29'dan beri Görev Yöneticisi ile DEVRE DIŞI (`HKCU\...\Explorer\StartupApproved\StartupFolder` değeri `03 00 00 00 ...`).
* Kullanım biçimi: elle başlatılıyor. Olay günlüğü 7045 (WinDivert hizmeti yüklendi) 06, 07, 08 (iki kez) ve 09 Kasım 00:02; Prefetch son çalışma 2026-11-09 00:20.
* Keşif anında: süreç YOK, WinDivert sürücüsü yüklü DEĞİL (`sc query WinDivert` 1060, hizmet anahtarı yok). Yani PC zaten GoodbyeDPI kapalı hâldeydi.

## Discord

* Kurulu: `%LOCALAPPDATA%\Discord`, sürüm klasörü `app-1.0.9267`.
* Başlangıçta: `HKCU\...\Run\Discord` = `Discord.exe --processStart Discord.exe --process-start-args "--start-inactive"` (açılışta kendiliğinden açılır, açılış yarışı geçerli). Ayrıca `HKLM\SOFTWARE\WOW6432Node\...\Run\Discord` = `C:\ProgramData\SquirrelMachineInstalls\Discord.exe --checkInstall`.
* Keşif anında Discord süreci yok.

## Ağ ayarları

* WinINet (HKCU Internet Settings): `ProxyEnable=0`, `ProxyServer` yok, `AutoConfigURL` yok, `ProxyOverride` yok.
* WinHTTP: doğrudan erişim.
* Ortam: `HTTPS_PROXY`, `HTTP_PROXY`, `ALL_PROXY`, `NO_PROXY` kullanıcı ve sistem düzeyinde boş.
* hosts: 824 bayt, yalnız yorum satırları, Discord satırı yok.
* 443, 1080, 1091, 1099 portlarında dinleyen yok.

## Araçlar

* Python: `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`, `py.exe` başlatıcı, WindowsApps takma adları.
* `curl.exe`: `C:\WINDOWS\system32\curl.exe`. git: YOK.
* Bizim kurulum: yok (`%LOCALAPPDATA%\DiscordEngelAsici` yok, `DiscordEngelAsici` görevi yok).

## Geri dönüş

* GoodbyeDPI dosyalarına ve başlangıç girdisine dokunulmadı. Önceki hâl "kapalı, başlangıçta devre dışı" olduğundan geri dönüş için bir şey yapmak gerekmez; elle `x86_64\goodbyedpi.exe` çalıştırmak yeterlidir (önce bizimkini `windows\kapat.ps1` ya da `KALDIR.cmd` ile kapat).
* Bizimkini kaldırmak: `windows\KALDIR.cmd` (hosts bloğu, PAC ayarı, görev, klasör).
