#!/bin/bash
# Tamamen kaldirir: LaunchDaemon, hosts blogu (yetki bir kez istenir), kullanici hizmetleri,
# plistler, Otomasyon symlinkleri, PAC ayari; eski tasarimin kopru ve env kalintilari.
# Son adimda calisma klasoru (~/Library/Application Support/DiscordEngelAsici) silinir.
# Yerinde kalan tek sey root sahipli hosts yedegi: /etc/hosts.discord-engel-asici.yedek
set -u
MAC="$(cd "$(dirname "$0")" && pwd)"
UID_NUM="$(id -u)"
LA="$HOME/Library/LaunchAgents"
OTO="$HOME/Library/Application Support/Otomasyon"
. "$MAC/hizmetler.sh"   # pac_kapat, gunluk_baslat
# Calisma klasoru silinecegi icin tam cikti gecici dizine yazilir.
gunluk_baslat kaldir "${TMPDIR:-/tmp}/DiscordEngelAsici"

# Once yetkili adim: basarisizsa (sifre iptal) hicbir sey yarim kalmaz.
if [ -e /Library/LaunchDaemons/com.discord-engel-asici-sni.plist ] || grep -q -F "# >>> DiscordEngelAsici >>>" /etc/hosts 2>/dev/null; then
  # Repo TCC korumali klasorde olabilir (~/Desktop): root betigi korumasiz temp dizinden calisir.
  TMP="$(mktemp -d)"
  GECICI_DIZIN="$TMP"   # gunluk_bitis cikista siler
  chmod 700 "$TMP"
  cp "$MAC/yonetici.sh" "$TMP/yonetici.sh"
  chmod 700 "$TMP/yonetici.sh"
  "$TMP/yonetici.sh" kaldir "$(id -un)" || { echo "HATA: yonetici adimi basarisiz, kaldirma durdu." >&2; exit 3; }
fi

pac_kapat || echo "UYARI: PAC ayari bir ag hizmetinde kapatilamadi (Sistem Ayarlari > Ag > Proxyler)." >&2
for e in com.discord-engel-asici com.discord-engel-asici-dl com.discord-engel-asici-pac com.discord-engel-asici-bridge com.discord-engel-asici-env; do
  launchctl bootout "gui/$UID_NUM/$e" 2>/dev/null || true
  rm -f "$LA/$e.plist"
done
if [ "$(launchctl getenv HTTPS_PROXY 2>/dev/null)" = "http://127.0.0.1:1098" ]; then
  launchctl unsetenv HTTPS_PROXY
fi
rm -f "$OTO"/Discord\ Engel\ Aşıcı\ *\(Kapatma\)
APP="$HOME/Library/Application Support/DiscordEngelAsici"
[ -d "$APP" ] && rm -rf "$APP"
rmdir "$OTO" 2>/dev/null || true
echo "KALDIRILDI. Internet normale dondu."
