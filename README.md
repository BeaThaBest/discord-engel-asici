# Discord Engel Aşıcı

Discord engelini yalnız Discord trafiği için aşar. Geri kalan internet etkilenmez.

## Arkadaşlar için kurulum

Mac ve Windows (64 bit) için. Kurulum soru sormaz, ekranda pencere ya da simge bırakmaz, bilgisayar açılınca kendiliğinden çalışır.

### 1. İndir

İki yoldan biri:

* ZIP: https://github.com/BeaThaBest/discord-engel-asici sayfasında yeşil **Code** düğmesi, sonra **Download ZIP**. ZIP'i aç, klasörü kalıcı bir yere koy (ör. Belgeler).
* git: `git clone https://github.com/BeaThaBest/discord-engel-asici.git`

### 2. Kur

**Windows:** `windows` klasöründe `KUR.cmd` dosyasına sağ tıkla, **Yönetici olarak çalıştır**. Bir kez UAC onayı ister.

**Mac:** `mac` klasöründe `KUR.command` dosyasına çift tıkla. Bir kez Mac şifreni ister.

* ZIP'ten indirdiysen macOS "açılamıyor" diyebilir: **Sistem Ayarları, Gizlilik ve Güvenlik** sayfasının altında **Yine de Aç**'a bas, sonra tekrar çift tıkla.
* Mac'te ilk kurulum ByeDPI'ı derler, bunun için Xcode komut satırı araçları gerekir. Yoksa kurulum bunu söyler ve yükleme penceresini açar: **Yükle**'ye bas, bitince `KUR.command`'a yeniden çift tıkla.

Süre: Windows'ta yaklaşık 1 ile 3 dakika (iki küçük dosya indirilir). Mac'te yaklaşık 2 ile 5 dakika; Xcode araçları yoksa onların yüklenmesi ayrıca 5 ile 15 dakika sürer.

Kurulum senin internet sağlayıcında hangi ayarın çalıştığını kendisi dener (bkz. Strateji). Hiçbiri çalışmazsa açık bir hata mesajıyla durur ve hiçbir ayarı değiştirmez. Discord senin ağında zaten engelli değilse bunu da yazar.

Kurulum bitince Discord'u tamamen kapatıp yeniden aç (Windows: tepsi simgesinden Çıkış; Mac: Cmd+Q).

### 3. Kontrol

Bir şey ters giderse:

* Windows: `windows\KONTROL.cmd` çift tık
* Mac: `mac/KONTROL.command` çift tık (ya da `mac/kontrol.sh`)

Her madde için GEÇTİ ya da KALDI yazar (hizmet, yerel portlar, PAC, hosts bloğu, seçili strateji, Discord bağlantısı, Discord dışı site). Her KALDI'nın altında ne yapman gerektiği tek satırla yazar. Bu komut hiçbir ayarı değiştirmez.

İnternet sağlayıcın değiştiyse ya da Discord bir gün yine açılmazsa: Windows `windows\YENIDEN-AYARLA.cmd`, Mac `mac/YENIDEN-AYARLA.command`. Ayarları yeniden dener, çalışanı seçer. Yönetici izni istemez.

### 4. Kaldır

* Windows: `windows\KALDIR.cmd` çift tık (UAC ister)
* Mac: `mac/KALDIR.command` çift tık (şifre ister)

hosts bloğunu, proxy ayarını, arka plan hizmetlerini ve kurulum klasörünü siler. İnternet ayarların kurulumdan önceki hâline döner.

### Sınırlar

* Yalnız SNI tabanlı engeli (sağlayıcının TLS bağlantısındaki site adına bakarak kesmesini) aşar. IP engeli ve DNS engeli aşılmaz. Bu sistem DNS ayarına dokunmaz.
* Sesli kanal ve yayın UDP ile gider; bu sistem UDP için hiçbir şey yapmaz. Test PC'sinde yayın izleme çalıştı (2026-11-09, tek sağlayıcı). Başka sağlayıcılarda sesli kanal denenmedi.
* Strateji adayları şimdiye kadar tek bir Türkiye sağlayıcısında ölçüldü. Senin sağlayıcında hiçbiri çalışmayabilir; o zaman kurulum bunu açıkça söyler.
* Mac'te bir ağ hizmetinde (Wi-Fi, Ethernet) daha önce kendi otomatik proxy (PAC) ayarın varsa kurulum onun yerine bizimkini yazar, kaldırma bizimkini kapatır ama eskisini geri yazmaz.

## Strateji

ByeDPI'ın hangi ayarla çalışacağı sağlayıcıya göre değişir. `ortak/strateji.py` içinde kısa bir aday listesi var (her birinin kaynağı satırının üstünde yazar: bu repodaki ölçüm ya da ByeDPI v0.17.3 README örnekleri; hepsi `ciadpi --help` çıktısında olan bayraklar). Kurulum her adayı sırayla dener: motor geçici olarak boş bir yerel portta başlatılır, `https://discord.com/api/v9/gateway` (200 şart), `cdn.discordapp.com` ve `dl.discordapp.net` SOCKS üzerinden ölçülür, ilk geçen seçilir ve kurulum klasöründeki `strateji.json` dosyasına yazılır. Tek kaynak bu dosyadır: Windows hizmeti onu okur, Mac'te LaunchAgent dosyaları ondan üretilir.

Kurulumu değiştirmeden yalnız denemek için:

    python3 ortak/strateji.py sec --motor motor/bin/ciadpi

## Kurulum ayrıntısı (Mac)

    git clone https://github.com/BeaThaBest/discord-engel-asici.git && cd discord-engel-asici
    mac/kur.sh

Ya da `mac/KUR.command` dosyasına çift tıkla. Komut soru sormaz, tekrar çalıştırılabilir.
İlk çalıştırmada ByeDPI v0.17.3 kaynağı indirilir, SHA256 doğrulanır ve derlenir (Xcode komut satırı araçları gerekir). Derleme başarısız olursa kurulum durur.

Kurulan her şey `~/Library/Application Support/DiscordEngelAsici/` altına kopyalanır (ikili, SNI dinleyici ve yardımcı betikler, alan listesi, `strateji.json`, `pac/proxy.pac`, loglar). Repo tek kaynaktır. Eski plist dosyaları `yedek/<tarih>/` altına alınır.
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

Hizmetleri, plist dosyalarını, Otomasyon bağlantılarını, 443 LaunchDaemon'u, hosts bloğunu ve kurulum klasörünü kaldırır, PAC ayarını kapatır. Yerinde kalan tek dosya root sahipli hosts yedeğidir (`/etc/hosts.discord-engel-asici.yedek`).

## Nasıl çalışır (Mac)

Üç LaunchAgent ve bir LaunchDaemon çalışır:

* `com.discord-engel-asici`: ByeDPI, port 1080, `strateji.json` içindeki `ana` ayarı (ana proxy).
* `com.discord-engel-asici-dl`: ByeDPI, port 1091, `strateji.json` içindeki `indirme` ayarı (indirme sunucuları).
* `com.discord-engel-asici-pac`: 1099 portunda yalnız `pac/proxy.pac` klasörünü sunar.
* `com.discord-engel-asici-sni` (LaunchDaemon): launchd yalnız 443 soketini bağlar (ayrıcalıklı port), iş kullanıcı kimliğinde yapılır. RunAtLoad ve KeepAlive yoktur: soket launchd'de durur, süreç ölse bir sonraki bağlantıda yeniden başlar.

Discord güncelleyicisi (Rust) PAC ve SOCKS ayarını yok sayar. Bu yüzden `ortak/alanlar.txt` içinde `hosts` işaretli tam adlar (şu an `updates.discord.com`) için hosts dosyasına işaretli bir blok yazılır ve ad `127.0.0.1` ile `::1`'e çözülür. 443'teki SNI dinleyici TLS'i açmadan SNI'yi okur, yalnız `hosts` adlarını kabul eder, gerçek IP'yi hosts dosyasını atlayarak çözer ve ByeDPI'ya SOCKS5 ile bu IP'yi verir. Genel `HTTPS_PROXY` ve HTTP köprüsü yoktur.

Sistem otomatik proxy ayarı (etkin her ağ hizmetinde: Wi-Fi, Ethernet) `http://127.0.0.1:1099/proxy.pac` adresine bakar (PAC, `hosts` adlarına DIRECT döner). `kapat.sh` ve `kaldir.sh` yalnız URL'si bizim PAC olan hizmetleri kapatır.

## Windows

### Kurulum

Repo klasöründe `windows\KUR.cmd` dosyasına çift tıkla. Ya da tek satır:

    powershell -NoProfile -ExecutionPolicy Bypass -File windows\kur.ps1

Soru sormaz, tekrar çalıştırılabilir. hosts dosyası için yönetici gerekir: yükseltilmediyse betik kendini bir kez UAC ile yeniden başlatır (tek onay). Yükseltilmiş süreç aynı kullanıcı kimliğiyle devam eder varsayılır. Standart kullanıcı hesabında UAC başka bir yönetici hesabının parolasını isterse görev ve kullanıcı ayarları (PAC, `%LOCALAPPDATA%`) o yöneticinin hesabına yazılır ve Discord'un kullandığı hesapta çalışmaz. Bu durumda kurulumu, Discord'u kullanan hesabın kendisi yönetici olarak çalıştırmalıdır.

İnternetten iki sabit dosya indirir ve SHA256 ile doğrular (sürümler `motor/SURUM`): python.org gömülü Python 3.14.10 (64 bit) ve ByeDPI v0.17.3 resmi Windows paketi. Hepsi `%LOCALAPPDATA%\DiscordEngelAsici\` altına kurulur.

Sıra: strateji seçilir (`strateji.json` yoksa), hizmet kurulur ve doğrulanır (PAC 1099, SOCKS 1080 ve 1091, 443 dinliyor), sonra hosts bloğu yazılır ve `https://updates.discord.com/` proxysiz denenir. Bu geçmezse hosts bloğu geri alınır, proxy ayarı açılmaz ve kurulum hata koduyla çıkar (3: doğrulama, 4: port 443 dolu, 5: yönetici izni yok, 6: çalışan strateji yok). 127.0.0.1:443 başka süreçte doluysa (IIS, VMware, Skype) hangi süreç olduğu yazılır. Son adımda PAC ayarı açılır; önceki sürümün yazdığı `HTTPS_PROXY=http://127.0.0.1:1098` varsa silinir, başka bir değere dokunulmaz.

### Geçici kapatma, açma, kaldırma

    powershell -NoProfile -ExecutionPolicy Bypass -File windows\kapat.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File windows\ac.ps1

`kapat.ps1` görevi durdurur ve PAC ayarını kapatır, yetki istemez. hosts bloğu kalır: hizmet yokken `updates.discord.com` bağlantısı reddedilir, yalnız Discord güncelleyicisi etkilenir (Mac'te de aynı sonuç).

Kaldırma: `windows\KALDIR.cmd` çift tık (UAC ister). hosts bloğunu siler, PAC ayarlarını (AutoConfigURL, ProxyEnable, ProxyServer) kurulum öncesi yedeğe döndürür, eski sürümden kalan bizim `HTTPS_PROXY` değerini kaldırır, görevi ve klasörü siler.

### Nasıl çalışır (Windows)

Tek bir Görev Zamanlayıcı görevi (`DiscordEngelAsici`) tek bir süreç başlatır: `pythonw.exe ortak\hizmet.py`. Bu süreç PAC sunucusunu (1099) ve SNI dinleyiciyi (127.0.0.1 ve ::1, 443) çalıştırır, iki ByeDPI sürecini (1080 ve 1091, ayarlar `strateji.json`'dan) başlatır ve düşerse yeniden başlatır. Hepsi yalnız loopback dinler.

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

* `ortak/`: alan listesi, PAC üretici, SNI dinleyici, hosts bloğu, strateji seçici `strateji.py`, kontrol `doktor.py`, tek süreç hizmeti `hizmet.py` (yalnız python3 standart kütüphanesi, platformdan bağımsız).
* `motor/`: sabit sürümler (`SURUM`), `derle-mac.sh`, `derle-windows.sh` (mingw-w64 ile aynı kaynaktan çapraz derleme, karşılaştırma için).
* `mac/`: kurulum betikleri, `kontrol.sh`, `yeniden-ayarla.sh`, ortak hizmet işlevleri (`hizmetler.sh`), plist şablonları ve çift tık için `.command` dosyaları.
* `windows/`: `kur.ps1`, `kaldir.ps1`, `ac.ps1`, `kapat.ps1`, `kontrol.ps1`, `yeniden-ayarla.ps1`, ortak `islevler.ps1`, çift tık için `KUR.cmd`, `KALDIR.cmd`, `KONTROL.cmd`, `YENIDEN-AYARLA.cmd`, `internet-testi.ps1` (`-Durum A|B|C`, `-Birlestir`).
