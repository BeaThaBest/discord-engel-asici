#!/bin/bash
# Discord Engel Asici Mac kurulumu. Tek komut, soru sormaz, tekrar calistirilabilir.
set -euo pipefail
MAC="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$MAC")"
APP="$HOME/Library/Application Support/DiscordEngelAsici"
OTO="$HOME/Library/Application Support/Otomasyon"

# Onkosul: ByeDPI kaynaktan derlenir (make, cc) ve /usr/bin/python3 de bu araclarla gelir.
if [ ! -x "$REPO/motor/bin/ciadpi" ] && ! xcode-select -p >/dev/null 2>&1; then
  echo "Xcode komut satiri araclari gerekli (ByeDPI derlemesi ve python3 icin)."
  echo "Simdi acilan pencerede Yukle'ye bas. Yukleme bitince (5 ile 15 dakika) bu kurulumu yeniden calistir."
  xcode-select --install >/dev/null 2>&1 || true
  exit 10
fi
PY="$(command -v python3 || true)"
if [ -z "$PY" ] || ! "$PY" -c 'import ssl' >/dev/null 2>&1; then
  echo "HATA: calisan python3 yok. Once 'xcode-select --install' ile komut satiri araclarini kur." >&2
  exit 1
fi

# HIZMETLER, LA, UID_NUM, PAC_URL, durdur/baslat, PAC ve plist islevleri tek kaynaktan.
. "$MAC/hizmetler.sh"
# Eski tasarim (genel HTTPS_PROXY + kopru). Yeni sistem dogrulaninca kaldirilir.
ESKI_ETIKETLER=(com.discord-engel-asici-bridge com.discord-engel-asici-env)
ESKI_PROXY="http://127.0.0.1:1098"
ADLAR_ANA="Discord Engel Aşıcı Ana Proxy (Kapatma)"
ADLAR_DL="Discord Engel Aşıcı İndirme Proxy (Kapatma)"
ADLAR_PAC="Discord Engel Aşıcı PAC Sunucusu (Kapatma)"
ADLAR_SNI="Discord Engel Aşıcı SNI Dinleyici (Kapatma)"
ESKI_ADLAR=("Discord Engel Aşıcı Güncelleme Köprüsü (Kapatma)" "Discord Engel Aşıcı Proxy Ayarı (Kapatma)")

echo "1/9 Motor"
[ -x "$REPO/motor/bin/ciadpi" ] || "$REPO/motor/derle-mac.sh"
[ -x "$REPO/motor/bin/ciadpi" ] || { echo "HATA: motor yok, derleme basarisiz" >&2; exit 1; }

echo "2/9 Strateji (bu internet saglayicisinda calisan ByeDPI ayari)"
mkdir -p "$APP"
if [ -f "$APP/strateji.json" ]; then
  "$PY" "$REPO/ortak/strateji.py" goster --strateji "$APP/strateji.json" \
    || { echo "HATA: $APP/strateji.json bozuk. mac/yeniden-ayarla.sh calistir." >&2; exit 6; }
  echo "  Var olan secim korunuyor (degistirmek icin mac/yeniden-ayarla.sh)."
else
  "$PY" "$REPO/ortak/strateji.py" sec --motor "$REPO/motor/bin/ciadpi" --yaz "$APP/strateji.json" \
    || { echo "HATA: calisan strateji bulunamadi, kurulum durdu. Hicbir ayar degismedi." >&2; exit 6; }
fi

echo "3/9 Mevcut plist yedegi"
YEDEK="$APP/yedek/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$YEDEK" "$APP/log" "$OTO" "$LA"
for p in "$LA"/com.discord-engel-asici*.plist; do
  [ -e "$p" ] && cp "$p" "$YEDEK/"
done

echo "4/9 Calisma dosyalari"
cp "$REPO/motor/bin/ciadpi" "$APP/DiscordEngelAsici.yeni" && mv -f "$APP/DiscordEngelAsici.yeni" "$APP/DiscordEngelAsici"
for f in alanlar.py gunluk.py dns_a.py sni_dinleyici.py hosts_blok.py strateji.py; do
  cp "$REPO/ortak/$f" "$APP/$f"
done
cp "$REPO/ortak/alanlar.txt" "$APP/alanlar.txt"
# PAC sunucusu yalniz bu alt klasoru sunar (log ve yedekler 127.0.0.1:1099'dan okunamaz).
mkdir -p "$APP/pac"
"$PY" "$REPO/ortak/pac_uret.py" --alanlar "$REPO/ortak/alanlar.txt" --cikti "$APP/pac/proxy.pac"
ln -sfn "$APP/DiscordEngelAsici" "$OTO/$ADLAR_ANA"
ln -sfn "$APP/DiscordEngelAsici" "$OTO/$ADLAR_DL"
ln -sfn "$PY" "$OTO/$ADLAR_PAC"
ln -sfn "$PY" "$OTO/$ADLAR_SNI"

echo "5/9 Plist yazimi (kullanici agent'lari, motor argumanlari strateji.json'dan)"
plistleri_yaz || { echo "HATA: plist yazilamadi" >&2; exit 1; }

echo "6/9 Hizmetleri yeniden yukle"
hizmetleri_yeniden_yukle || exit 1
rm -f "$APP/proxy.pac"   # eski surumun kok klasordeki kopyasi

echo "7/9 Yonetici adimi (hosts blogu + 443 LaunchDaemon + dogrulama)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
chmod 700 "$TMP"
# Repo ~/Desktop gibi TCC korumali klasorde olabilir: root yetki adimi oradan calistirilamaz
# (Operation not permitted). Root'un calistiracagi betik korumasiz temp dizinden calisir.
cp "$MAC/yonetici.sh" "$TMP/yonetici.sh"
chmod 700 "$TMP/yonetici.sh"
sed -e "s|@OTO@|$OTO|g" -e "s|@APP@|$APP|g" -e "s|@KULLANICI@|$(id -un)|g" \
  "$MAC/plist/com.discord-engel-asici-sni.plist" > "$TMP/sni.plist"
plutil -lint "$TMP/sni.plist" >/dev/null
"$PY" "$REPO/ortak/hosts_blok.py" yaz --hosts /etc/hosts --alanlar "$APP/alanlar.txt" --cikti "$TMP/hosts.yeni"
if ! "$TMP/yonetici.sh" kur "$(id -un)" "$TMP/hosts.yeni" "$TMP/sni.plist"; then
  echo "HATA: yeni sistem dogrulanamadi. Eski sistem yerinde birakildi, yonetici adimi geri alindi." >&2
  exit 3
fi

echo "8/9 Eski sistem kaldiriliyor (dogrulama gecti)"
for e in "${ESKI_ETIKETLER[@]}"; do
  launchctl bootout "gui/$UID_NUM/$e" 2>/dev/null || true
  rm -f "$LA/$e.plist"   # yedegi adim 2'de $YEDEK altina alindi
done
for a in "${ESKI_ADLAR[@]}"; do rm -f "$OTO/$a"; done
rm -f "$APP/connect-bridge.py"
# Yalniz bizim koydugumuz degeri kaldir; kullanicinin kendi HTTPS_PROXY'sine dokunma.
if [ "$(launchctl getenv HTTPS_PROXY 2>/dev/null || true)" = "$ESKI_PROXY" ]; then
  launchctl unsetenv HTTPS_PROXY
fi

echo "9/9 Sistem PAC ayari (etkin butun ag hizmetleri)"
pac_ac || { echo "HATA: PAC ayari yazilamadi" >&2; exit 1; }
echo "Kurulum tamam. Yedek: $YEDEK"
echo "Kontrol: mac/kontrol.sh"
