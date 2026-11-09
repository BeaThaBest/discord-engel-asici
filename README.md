# Discord Engel Aşıcı

Discord engelini yalnız Discord trafiği için aşar. Geri kalan internet etkilenmez.

## Kurulum (Mac)

    git clone <repo> && cd Discord-Engel-Asici
    mac/kur.sh

Ya da `mac/KUR.command` dosyasına çift tıkla. Komut soru sormaz, tekrar çalıştırılabilir.
İlk çalıştırmada ByeDPI v0.17.3 kaynağı indirilir, SHA256 doğrulanır ve derlenir (Xcode komut satırı araçları gerekir). Derleme başarısız olursa kurulum durur.

Kurulan her şey `~/Library/Application Support/DiscordEngelAsici/` altına kopyalanır (ikili, SNI dinleyici ve yardımcı betikler, alan listesi, PAC, loglar). Repo tek kaynaktır. Eski plist dosyaları `yedek/<tarih>/` altına alınır.
Kurulum bir kez yönetici şifresi ister (hosts bloğu ve 443 LaunchDaemon için). Sistem ayarlarında "Arka Planda İzin Ver" listesinde anlamlı adlarla görünür: `~/Library/Application Support/Otomasyon/Discord Engel Aşıcı ... (Kapatma)`.

## Geçici kapatma ve açma

    mac/kapat.sh
    mac/ac.sh

`kapat.sh` yetki istemez: PAC ayarını kapatır, üç kullanıcı hizmetini (ByeDPI 1080 ve 1091, PAC 1099) durdurur ve süreçlerin gerçekten bitmesini bekler. Sonra `launchctl list | grep discord-engel` boş döner.

Kapalıyken yerinde kalan iki şey root sahipli kurulum parçasıdır ve yalnız `kaldir.sh` siler:

* hosts bloğu: `updates.discord.com` hâlâ `127.0.0.1` ve `::1`'e çözülür.
* 443 LaunchDaemon (`com.discord-engel-asici-sni`): soket launchd'de bekler. ByeDPI yokken dinleyici bağlantıyı hemen kapatır, doğrudan bağlanmayı denemez (o yol DPI engelli, ayrıca ByeDPI dışında yol açılmaz).

Sonuç: kapalıyken yalnız Discord güncelleyicisi bağlanamaz, geri kalan internet tamamen normaldir. Discord'un kendisi de PAC kapalı olduğu için doğrudan gider (engel varsa açılmaz).

`ac.sh` her hizmeti yeniden yükler ve yeni PID'in kendi portunu dinlediğini doğrular, olmazsa sıfırdan farklı kodla çıkar ve PAC'i açmaz. Durdurma ve başlatma mantığı tek kaynaktır: `mac/hizmetler.sh` (`kur.sh`, `ac.sh`, `kapat.sh` kullanır).

## Kaldırma

    mac/kaldir.sh

Hizmetleri, plist dosyalarını, Otomasyon bağlantılarını, 443 LaunchDaemon'u ve hosts bloğunu kaldırır, PAC ayarını kapatır. Her şeyi geri alır.

## Nasıl çalışır (Mac)

Üç LaunchAgent ve bir LaunchDaemon çalışır:

* `com.discord-engel-asici`: ByeDPI, port 1080, `-o 8+s` (ana proxy).
* `com.discord-engel-asici-dl`: ByeDPI, port 1091, `-d 8+s` (indirme sunucuları).
* `com.discord-engel-asici-pac`: 1099 portunda `proxy.pac` sunar.
* `com.discord-engel-asici-sni` (LaunchDaemon): launchd yalnız 443 soketini bağlar (ayrıcalıklı port), iş kullanıcı kimliğinde yapılır. RunAtLoad ve KeepAlive yoktur: soket launchd'de durur, süreç ölse bir sonraki bağlantıda yeniden başlar.

Discord güncelleyicisi (Rust) PAC ve SOCKS ayarını yok sayar. Bu yüzden `ortak/alanlar.txt` içinde `hosts` işaretli tam adlar (şu an `updates.discord.com`) için hosts dosyasına işaretli bir blok yazılır ve ad `127.0.0.1` ile `::1`'e çözülür. 443'teki SNI dinleyici TLS'i açmadan SNI'yi okur, yalnız `hosts` adlarını kabul eder, gerçek IP'yi hosts dosyasını atlayarak çözer ve ByeDPI'ya SOCKS5 ile bu IP'yi verir. Genel `HTTPS_PROXY` ve HTTP köprüsü yoktur.

Sistem otomatik proxy ayarı `http://127.0.0.1:1099/proxy.pac` adresine bakar (PAC, `hosts` adlarına DIRECT döner).

## Windows

### Kurulum

Repo klasöründe `windows\KUR.cmd` dosyasına çift tıkla. Ya da tek satır:

    powershell -NoProfile -ExecutionPolicy Bypass -File windows\kur.ps1

Soru sormaz, tekrar çalıştırılabilir. hosts dosyası için yönetici gerekir: yükseltilmediyse betik kendini bir kez UAC ile yeniden başlatır (tek onay). Yükseltilmiş süreç aynı kullanıcı kimliğiyle devam eder varsayılır. Standart kullanıcı hesabında UAC başka bir yönetici hesabının parolasını isterse görev ve kullanıcı ayarları (PAC, `%LOCALAPPDATA%`) o yöneticinin hesabına yazılır ve Discord'un kullandığı hesapta çalışmaz. Bu durumda kurulumu, Discord'u kullanan hesabın kendisi yönetici olarak çalıştırmalıdır.

İnternetten iki sabit dosya indirir ve SHA256 ile doğrular (sürümler `motor/SURUM`): python.org gömülü Python 3.14.10 (64 bit) ve ByeDPI v0.17.3 resmi Windows paketi. Hepsi `%LOCALAPPDATA%\DiscordEngelAsici\` altına kurulur.

Sıra: hizmet kurulur ve doğrulanır (PAC 1099, SOCKS 1080 ve 1091, 443 dinliyor), sonra hosts bloğu yazılır ve `https://updates.discord.com/` proxysiz denenir. Bu geçmezse hosts bloğu geri alınır, proxy ayarı açılmaz ve kurulum hata koduyla çıkar (3: doğrulama, 4: port 443 dolu, 5: yönetici izni yok). 127.0.0.1:443 başka süreçte doluysa (IIS, VMware, Skype) hangi süreç olduğu yazılır. Son adımda PAC ayarı açılır; önceki sürümün yazdığı `HTTPS_PROXY=http://127.0.0.1:1098` varsa silinir, başka bir değere dokunulmaz.

### Geçici kapatma, açma, kaldırma

    powershell -NoProfile -ExecutionPolicy Bypass -File windows\kapat.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File windows\ac.ps1

`kapat.ps1` görevi durdurur ve PAC ayarını kapatır, yetki istemez. hosts bloğu kalır: hizmet yokken `updates.discord.com` bağlantısı reddedilir, yalnız Discord güncelleyicisi etkilenir (Mac'te de aynı sonuç).

Kaldırma: `windows\KALDIR.cmd` çift tık (UAC ister). hosts bloğunu siler, PAC ayarlarını (AutoConfigURL, ProxyEnable, ProxyServer) kurulum öncesi yedeğe döndürür, eski sürümden kalan bizim `HTTPS_PROXY` değerini kaldırır, görevi ve klasörü siler.

### Nasıl çalışır (Windows)

Tek bir Görev Zamanlayıcı görevi (`DiscordEngelAsici`) tek bir süreç başlatır: `pythonw.exe ortak\hizmet.py`. Bu süreç PAC sunucusunu (1099) ve SNI dinleyiciyi (127.0.0.1 ve ::1, 443) çalıştırır, iki ByeDPI sürecini (1080 `-o 8+s`, 1091 `-d 8+s`) başlatır ve düşerse yeniden başlatır. Hepsi yalnız loopback dinler.

* Görünmezlik: görev S4U ile (parola saklanmaz) etkileşimsiz oturumda koşar, masaüstüne hiçbir şey çizemez. `pythonw.exe` konsolsuz bir GUI ikilisidir ve ByeDPI `CREATE_NO_WINDOW` ile açılır. Tepsi ikonu ve bildirim yoktur.
* Açılış yarışı: tetik "bilgisayar açılışında" olduğu için hizmet oturum açılmadan önce hazırdır. Ek tetikler: oturum açılışı ve 5 dakikada bir bekçi (çalışıyorsa yeni kopya açmaz). Discord önce açılırsa kendini toparlar: Chromium PAC indirilemezse DIRECT'e düşer ve yeniden dener, güncelleyici bekleyip yeniden dener.
* Yönlendirme: WinINet ayarı `AutoConfigURL = http://127.0.0.1:1099/proxy.pac`. Discord (Chromium) bu PAC'i okur. Güncelleyici (Rust reqwest) PAC okumaz; onun için `updates.discord.com` hosts bloğuyla yerel 443 dinleyiciye çevrilir, dinleyici gerçek IP'yi hosts'u atlayarak çözer (`DnsQuery_W`, NO_HOSTS_FILE) ve ByeDPI'ya SOCKS5 ile verir.
* Discord sürüm klasörü (`app-x.y.z`) hiçbir yerde kullanılmaz, güncelleme sonrası da çalışır.

## Neden yalnız Discord etkilenir

Alan listesi tek kaynaktan gelir: `ortak/alanlar.txt` (satır biçimi `alan_soneki socks_port [hosts]`). PAC (`ortak/pac_uret.py`), hosts bloğu (`ortak/hosts_blok.py`) ve SNI dinleyici aynı listeyi kullanır. PAC eşleşmesi en uzun sonek kuralıyla yapılır, `evildiscord.com` gibi sahte sonekler eşleşmez. Listede olmayan her şey `DIRECT` gider, ByeDPI'dan hiç geçmez.

hosts dosyasına yalnız işaretli bir blok (`# >>> DiscordEngelAsici >>>` ile `# <<< DiscordEngelAsici <<<` arası) yazılır, yalnız listedeki `hosts` tam adları için. Blok dışındaki satırlar bayt bayt aynen kalır (CRLF dahil), ilk yazımda yedek alınır. 443 dinleyici bu adlar dışında hiçbir SNI'yi kabul etmez. Servis ölürse yalnız bu adlar etkilenir. DNS ayarı, sürücü ve güvenlik duvarı değişmez.

## Testler

    python3 -m unittest discover -s tests

## Yapı

* `ortak/`: alan listesi, PAC üretici, SNI dinleyici, hosts bloğu, tek süreç hizmeti `hizmet.py` (yalnız python3 standart kütüphanesi, platformdan bağımsız).
* `motor/`: sabit sürümler (`SURUM`), `derle-mac.sh`, `derle-windows.sh` (mingw-w64 ile aynı kaynaktan çapraz derleme, karşılaştırma için).
* `mac/`: kurulum betikleri, ortak hizmet işlevleri (`hizmetler.sh`) ve plist şablonları.
* `windows/`: `kur.ps1`, `kaldir.ps1`, `ac.ps1`, `kapat.ps1`, ortak `islevler.ps1`, çift tık için `KUR.cmd` ve `KALDIR.cmd`, `internet-testi.ps1` (`-Durum A|B|C`, `-Birlestir`).
