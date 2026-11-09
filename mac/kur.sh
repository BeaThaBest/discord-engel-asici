#!/bin/bash
# Discord Engel Asici Mac kurulumu. Tek komut, soru sormaz, tekrar calistirilabilir.
set -euo pipefail
MAC="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$MAC")"
UID_NUM="$(id -u)"
LA="$HOME/Library/LaunchAgents"
APP="$HOME/Library/Application Support/DiscordEngelAsici"
OTO="$HOME/Library/Application Support/Otomasyon"
PAC_URL="http://127.0.0.1:1099/proxy.pac"
PY="$(command -v python3)"
[ -n "$PY" ] || { echo "HATA: python3 yok" >&2; exit 1; }

# etiket|port
HIZMETLER=(
  "com.discord-engel-asici|1080"
  "com.discord-engel-asici-dl|1091"
  "com.discord-engel-asici-pac|1099"
  "com.discord-engel-asici-bridge|1098"
)
ENV_ETIKET="com.discord-engel-asici-env"
ADLAR_ANA="Discord Engel Aşıcı Ana Proxy (Kapatma)"
ADLAR_DL="Discord Engel Aşıcı İndirme Proxy (Kapatma)"
ADLAR_PAC="Discord Engel Aşıcı PAC Sunucusu (Kapatma)"
ADLAR_KOPRU="Discord Engel Aşıcı Güncelleme Köprüsü (Kapatma)"
ADLAR_ENV="Discord Engel Aşıcı Proxy Ayarı (Kapatma)"

pid_of() { launchctl list | awk -v l="$1" '$3==l && $1!="-" {print $1}'; }
port_pid() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -1 || true; }

echo "1/6 Motor"
[ -x "$REPO/motor/bin/ciadpi" ] || "$REPO/motor/derle-mac.sh"
[ -x "$REPO/motor/bin/ciadpi" ] || { echo "HATA: motor yok, derleme basarisiz" >&2; exit 1; }

echo "2/6 Mevcut plist yedegi"
YEDEK="$APP/yedek/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$YEDEK" "$APP/log" "$OTO" "$LA"
for p in "$LA"/com.discord-engel-asici*.plist; do
  [ -e "$p" ] && cp "$p" "$YEDEK/"
done

echo "3/6 Calisma dosyalari"
cp "$REPO/motor/bin/ciadpi" "$APP/DiscordEngelAsici.yeni" && mv -f "$APP/DiscordEngelAsici.yeni" "$APP/DiscordEngelAsici"
cp "$REPO/ortak/connect-bridge.py" "$APP/connect-bridge.py"
cp "$REPO/ortak/alanlar.txt" "$APP/alanlar.txt"
"$PY" "$REPO/ortak/pac_uret.py" --alanlar "$REPO/ortak/alanlar.txt" --cikti "$APP/proxy.pac"
ln -sfn "$APP/DiscordEngelAsici" "$OTO/$ADLAR_ANA"
ln -sfn "$APP/DiscordEngelAsici" "$OTO/$ADLAR_DL"
ln -sfn "$PY" "$OTO/$ADLAR_PAC"
ln -sfn "$PY" "$OTO/$ADLAR_KOPRU"
ln -sfn /bin/launchctl "$OTO/$ADLAR_ENV"

echo "4/6 Plist yazimi"
for sablon in "$MAC"/plist/*.plist; do
  sed -e "s|@OTO@|$OTO|g" -e "s|@APP@|$APP|g" "$sablon" > "$LA/$(basename "$sablon")"
  plutil -lint "$LA/$(basename "$sablon")" >/dev/null
done

echo "5/6 Hizmetleri yeniden yukle"
for h in "${HIZMETLER[@]}"; do
  etiket="${h%%|*}"; port="${h##*|}"
  eski="$(pid_of "$etiket" || true)"
  launchctl bootout "gui/$UID_NUM/$etiket" 2>/dev/null || true
  # Eski surecin bitmesini ve portun bosalmasini bekle (en cok 20 sn).
  for _ in $(seq 1 40); do
    kalan=""
    [ -n "$eski" ] && kill -0 "$eski" 2>/dev/null && kalan=1
    [ -n "$(port_pid "$port")" ] && kalan=1
    [ -z "$kalan" ] && break
    sleep 0.5
  done
  if [ -n "$(port_pid "$port")" ]; then
    echo "HATA: $etiket icin port $port bosalmadi" >&2; exit 1
  fi
  launchctl bootstrap "gui/$UID_NUM" "$LA/$etiket.plist"
  # Yeni PID ve porta sahip olma dogrulamasi (en cok 30 sn).
  tamam=""
  for _ in $(seq 1 60); do
    yeni="$(pid_of "$etiket" || true)"
    sahip="$(port_pid "$port")"
    if [ -n "$yeni" ] && [ "$yeni" != "$eski" ] && [ "$sahip" = "$yeni" ]; then tamam=1; break; fi
    sleep 0.5
  done
  [ -n "$tamam" ] || { echo "HATA: $etiket calismadi (eski=$eski yeni=${yeni:-yok} port sahibi=${sahip:-yok})" >&2; exit 1; }
  echo "  $etiket: PID $yeni, port $port"
done
launchctl bootout "gui/$UID_NUM/$ENV_ETIKET" 2>/dev/null || true
sleep 1
launchctl bootstrap "gui/$UID_NUM" "$LA/$ENV_ETIKET.plist"
echo "  $ENV_ETIKET: tek seferlik is yuklendi"

echo "6/6 Sistem PAC ayari"
if [ "$(networksetup -getautoproxyurl Wi-Fi | awk -F': ' '/^URL/ {print $2}')" != "$PAC_URL" ]; then
  networksetup -setautoproxyurl Wi-Fi "$PAC_URL"
  networksetup -setautoproxystate Wi-Fi on
fi
echo "Kurulum tamam. Yedek: $YEDEK"
