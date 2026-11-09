#!/bin/bash
# Discord Engel Asici Mac kurulumu. Tek komut, soru sormaz, tekrar calistirilabilir.
set -euo pipefail
MAC="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$MAC")"
APP="$HOME/Library/Application Support/DiscordEngelAsici"
OTO="$HOME/Library/Application Support/Otomasyon"
PAC_URL="http://127.0.0.1:1099/proxy.pac"
PY="$(command -v python3)"
[ -n "$PY" ] || { echo "HATA: python3 yok" >&2; exit 1; }

# HIZMETLER, LA, UID_NUM ve durdur/baslat islevleri tek kaynaktan.
. "$MAC/hizmetler.sh"
# Eski tasarim (genel HTTPS_PROXY + kopru). Yeni sistem dogrulaninca kaldirilir.
ESKI_ETIKETLER=(com.discord-engel-asici-bridge com.discord-engel-asici-env)
ESKI_PROXY="http://127.0.0.1:1098"
ADLAR_ANA="Discord Engel Aşıcı Ana Proxy (Kapatma)"
ADLAR_DL="Discord Engel Aşıcı İndirme Proxy (Kapatma)"
ADLAR_PAC="Discord Engel Aşıcı PAC Sunucusu (Kapatma)"
ADLAR_SNI="Discord Engel Aşıcı SNI Dinleyici (Kapatma)"
ESKI_ADLAR=("Discord Engel Aşıcı Güncelleme Köprüsü (Kapatma)" "Discord Engel Aşıcı Proxy Ayarı (Kapatma)")

echo "1/8 Motor"
[ -x "$REPO/motor/bin/ciadpi" ] || "$REPO/motor/derle-mac.sh"
[ -x "$REPO/motor/bin/ciadpi" ] || { echo "HATA: motor yok, derleme basarisiz" >&2; exit 1; }

echo "2/8 Mevcut plist yedegi"
YEDEK="$APP/yedek/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$YEDEK" "$APP/log" "$OTO" "$LA"
for p in "$LA"/com.discord-engel-asici*.plist; do
  [ -e "$p" ] && cp "$p" "$YEDEK/"
done

echo "3/8 Calisma dosyalari"
cp "$REPO/motor/bin/ciadpi" "$APP/DiscordEngelAsici.yeni" && mv -f "$APP/DiscordEngelAsici.yeni" "$APP/DiscordEngelAsici"
for f in alanlar.py gunluk.py dns_a.py sni_dinleyici.py hosts_blok.py; do
  cp "$REPO/ortak/$f" "$APP/$f"
done
cp "$REPO/ortak/alanlar.txt" "$APP/alanlar.txt"
"$PY" "$REPO/ortak/pac_uret.py" --alanlar "$REPO/ortak/alanlar.txt" --cikti "$APP/proxy.pac"
ln -sfn "$APP/DiscordEngelAsici" "$OTO/$ADLAR_ANA"
ln -sfn "$APP/DiscordEngelAsici" "$OTO/$ADLAR_DL"
ln -sfn "$PY" "$OTO/$ADLAR_PAC"
ln -sfn "$PY" "$OTO/$ADLAR_SNI"

echo "4/8 Plist yazimi (kullanici agent'lari)"
for h in "${HIZMETLER[@]}"; do
  sablon="$MAC/plist/${h%%|*}.plist"
  sed -e "s|@OTO@|$OTO|g" -e "s|@APP@|$APP|g" "$sablon" > "$LA/$(basename "$sablon")"
  plutil -lint "$LA/$(basename "$sablon")" >/dev/null
done

echo "5/8 Hizmetleri yeniden yukle"
hizmetleri_yeniden_yukle || exit 1

echo "6/8 Yonetici adimi (hosts blogu + 443 LaunchDaemon + dogrulama)"
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

echo "7/8 Eski sistem kaldiriliyor (dogrulama gecti)"
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

echo "8/8 Sistem PAC ayari"
if [ "$(networksetup -getautoproxyurl Wi-Fi | awk -F': ' '/^URL/ {print $2}')" != "$PAC_URL" ]; then
  networksetup -setautoproxyurl Wi-Fi "$PAC_URL"
  networksetup -setautoproxystate Wi-Fi on
fi
echo "Kurulum tamam. Yedek: $YEDEK"
