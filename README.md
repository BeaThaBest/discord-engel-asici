# Discord Engel Aşıcı

Discord engelini yalnız Discord trafiği için aşar. Geri kalan internet etkilenmez.

## Kurulum (Mac)

    git clone <repo> && cd Discord-Engel-Asici
    mac/kur.sh

Ya da `mac/KUR.command` dosyasına çift tıkla. Komut soru sormaz, tekrar çalıştırılabilir.
İlk çalıştırmada ByeDPI v0.17.3 kaynağı indirilir, SHA256 doğrulanır ve derlenir (Xcode komut satırı araçları gerekir). Derleme başarısız olursa kurulum durur.

Kurulan her şey `~/Library/Application Support/DiscordEngelAsici/` altına kopyalanır (ikili, köprü, alan listesi, PAC, loglar). Repo tek kaynaktır. Eski plist dosyaları `yedek/<tarih>/` altına alınır.
Sistem ayarlarında "Arka Planda İzin Ver" listesinde anlamlı adlarla görünür: `~/Library/Application Support/Otomasyon/Discord Engel Aşıcı ... (Kapatma)`.

## Geçici kapatma ve açma

    mac/kapat.sh
    mac/ac.sh

## Kaldırma

    mac/kaldir.sh

Hizmetleri, plist dosyalarını, Otomasyon bağlantılarını durdurur ve PAC ayarını kapatır.

## Nasıl çalışır

Beş LaunchAgent çalışır:

* `com.discord-engel-asici`: ByeDPI, port 1080, `-o 8+s` (ana proxy).
* `com.discord-engel-asici-dl`: ByeDPI, port 1091, `-d 8+s` (indirme sunucuları).
* `com.discord-engel-asici-pac`: 1099 portunda `proxy.pac` sunar.
* `com.discord-engel-asici-bridge`: 1098 portunda HTTP CONNECT proxy, Discord alanlarını SOCKS5 ile ByeDPI'ya yollar. Discord güncelleyicisi SOCKS ayarını yok sayıp yalnız HTTPS_PROXY'yi kullandığı için gerekir. Log `log/kopru.log` boyut sınırlıdır (1 MB, 2 yedek) ve yalnız hataları yazar; her bağlantı için `--ayrinti`.
* `com.discord-engel-asici-env`: oturum açılışında bir kez `HTTPS_PROXY=http://127.0.0.1:1098` değerini ayarlar.

Sistem otomatik proxy ayarı `http://127.0.0.1:1099/proxy.pac` adresine bakar.

## Windows

### Kurulum

Repo klasöründe `windows\KUR.cmd` dosyasına çift tıkla. Ya da tek satır:

    powershell -NoProfile -ExecutionPolicy Bypass -File windows\kur.ps1

Soru sormaz, tekrar çalıştırılabilir. Yönetici hesabıyla çalıştırılmalı (UAC kapalıysa çift tık yeter). İnternetten iki sabit dosya indirir ve SHA256 ile doğrular (sürümler `motor/SURUM`): python.org gömülü Python 3.14.10 (64 bit) ve ByeDPI v0.17.3 resmi Windows paketi. Hepsi `%LOCALAPPDATA%\DiscordEngelAsici\` altına kurulur. Hizmet ayağa kalkıp doğrulanmadan proxy ayarına dokunulmaz.

### Geçici kapatma, açma, kaldırma

    powershell -NoProfile -ExecutionPolicy Bypass -File windows\kapat.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File windows\ac.ps1

Kaldırma: `windows\KALDIR.cmd` çift tık. Proxy ayarlarını (AutoConfigURL, ProxyEnable, ProxyServer) ve kullanıcı HTTPS_PROXY değerini kurulum öncesi yedeğe döndürür, görevi ve klasörü siler.

### Nasıl çalışır

Tek bir Görev Zamanlayıcı görevi (`DiscordEngelAsici`) tek bir süreç başlatır: `pythonw.exe ortak\hizmet.py`. Bu süreç PAC sunucusunu (1099) ve köprüyü (1098) çalıştırır, iki ByeDPI sürecini (1080 `-o 8+s`, 1091 `-d 8+s`) başlatır ve düşerse yeniden başlatır. Hepsi yalnız 127.0.0.1 dinler.

* Görünmezlik: görev S4U ile (parola saklanmaz) etkileşimsiz oturumda koşar, masaüstüne hiçbir şey çizemez. Ayrıca `pythonw.exe` konsolsuz bir GUI ikilisidir ve ByeDPI `CREATE_NO_WINDOW` ile açılır. Tepsi ikonu ve bildirim yoktur.
* Açılış yarışı: tetik "bilgisayar açılışında" olduğu için hizmet oturum açılmadan önce hazırdır, Discord'un otomatik başlaması oturum açılışından sonradır. Hızlı Başlangıç açılış tetiğini atlayabildiği için ek tetikler vardır: oturum açılışı ve 5 dakikada bir bekçi (çalışıyorsa yeni kopya açmaz). Yine de Discord önce açılırsa kendini toparlar: Chromium PAC indirilemezse DIRECT'e düşer ve PAC'i 8 sn, 32 sn, 2 dk sonra yeniden dener; Discord ağ geçidine bağlanamazsa yeniden bağlanır, güncelleyici de bekleyip yeniden dener.
* Yönlendirme: kullanıcı WinINet ayarı `AutoConfigURL = http://127.0.0.1:1099/proxy.pac`. Discord (Chromium) bu PAC'i okur. Discord güncelleyicisi (Rust reqwest) PAC okumaz, yalnız HTTPS_PROXY ve elle girilmiş proxy kayıt değerlerine bakar, bu yüzden kullanıcı ortam değişkeni `HTTPS_PROXY=http://127.0.0.1:1098` konur.
* Discord sürüm klasörü (`app-x.y.z`) hiçbir yerde kullanılmaz, güncelleme sonrası da çalışır.
* Sistem DNS, sürücü, ağ bağdaştırıcısı, hosts ve güvenlik duvarı değişmez. Yönetici yalnız açılış tetikli görevi kaydetmek için gerekir; yönetici değilse görev oturum açılışında başlar.

### Bilinen açık (Windows)

HTTPS_PROXY kullanıcı geneli bir değişkendir; curl, git, pip, npm gibi araçlar da onu okur. Hizmet çalışırken Discord dışı istekleri köprü DIRECT geçirir. Hizmet ölürse bu araçlar en çok birkaç saniye (iç yeniden başlatma) ya da 1 ile 5 dakika (görev yeniden başlatma, bekçi) bağlanamaz. Tarayıcılar ve WinINet kullanan uygulamalar etkilenmez: PAC sunucusu yoksa DIRECT'e düşerler. `kapat.ps1` ve kaldırma bu değişkeni de kaldırır.

## Neden yalnız Discord etkilenir

Alan listesi tek kaynaktan gelir: `ortak/alanlar.txt` (satır biçimi `alan_soneki socks_port`). PAC dosyası (`ortak/pac_uret.py`) ve köprü (`ortak/connect-bridge.py`) aynı listeyi kullanır. Eşleşme en uzun sonek kuralıyla yapılır, `evildiscord.com` gibi sahte sonekler eşleşmez. Listede olmayan her şey `DIRECT` gider, yani ByeDPI'dan hiç geçmez.

## Bilinen açık

Env işi `HTTPS_PROXY` değerini oturum boyunca ayarlı bırakır. Köprü ölürse bu değişkeni kullanan uygulamalar etkilenebilir. Köprü KeepAlive ile hemen yeniden başlatılır ve Discord dışı her bağlantıyı DIRECT yapar, bu yüzden etki kısa sürer.

## Testler

    python3 -m unittest discover -s tests

## Yapı

* `ortak/`: alan listesi, PAC üretici, köprü, tek süreç hizmeti `hizmet.py` (yalnız python3 standart kütüphanesi, platformdan bağımsız).
* `motor/`: sabit sürümler (`SURUM`), `derle-mac.sh`, `derle-windows.sh` (mingw-w64 ile aynı kaynaktan çapraz derleme, karşılaştırma için).
* `mac/`: kurulum betikleri ve plist şablonları.
* `windows/`: `kur.ps1`, `kaldir.ps1`, `ac.ps1`, `kapat.ps1`, ortak `islevler.ps1`, çift tık için `KUR.cmd` ve `KALDIR.cmd`, `internet-testi.ps1` (`-Durum A|B|C`, `-Birlestir`).
