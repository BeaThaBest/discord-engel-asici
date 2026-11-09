#!/bin/bash
# Tamamen kaldirir: LaunchDaemon, hosts blogu (yetki bir kez istenir), kullanici hizmetleri,
# plistler, Otomasyon symlinkleri, PAC ayari; eski tasarimin kopru ve env kalintilari.
# Calisma klasoru (log, yedek) kalir.
set -u
MAC="$(cd "$(dirname "$0")" && pwd)"
UID_NUM="$(id -u)"
LA="$HOME/Library/LaunchAgents"
OTO="$HOME/Library/Application Support/Otomasyon"

# Once yetkili adim: basarisizsa (sifre iptal) hicbir sey yarim kalmaz.
if [ -e /Library/LaunchDaemons/com.discord-engel-asici-sni.plist ] || grep -q -F "# >>> DiscordEngelAsici >>>" /etc/hosts 2>/dev/null; then
  # Repo TCC korumali klasorde olabilir (~/Desktop): root betigi korumasiz temp dizinden calisir.
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  chmod 700 "$TMP"
  cp "$MAC/yonetici.sh" "$TMP/yonetici.sh"
  chmod 700 "$TMP/yonetici.sh"
  "$TMP/yonetici.sh" kaldir "$(id -un)" || { echo "HATA: yonetici adimi basarisiz, kaldirma durdu." >&2; exit 3; }
fi

networksetup -setautoproxystate Wi-Fi off
for e in com.discord-engel-asici com.discord-engel-asici-dl com.discord-engel-asici-pac com.discord-engel-asici-bridge com.discord-engel-asici-env; do
  launchctl bootout "gui/$UID_NUM/$e" 2>/dev/null || true
  rm -f "$LA/$e.plist"
done
if [ "$(launchctl getenv HTTPS_PROXY 2>/dev/null)" = "http://127.0.0.1:1098" ]; then
  launchctl unsetenv HTTPS_PROXY
fi
rm -f "$OTO"/Discord\ Engel\ Aşıcı\ *\(Kapatma\)
echo "KALDIRILDI. Internet normale dondu."
