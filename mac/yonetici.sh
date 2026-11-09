#!/bin/bash
# Yetki gereken tek betik. Kullanim:
#   yonetici.sh kur    <kullanici> <hosts_yeni> <sni_plist>
#   yonetici.sh kaldir <kullanici>
# root degilse kendini yukseltir: sudo -n calisiyorsa sudo ile, degilse bir kez GUI sifre
# istemiyle (osascript). Sifre bu betikte hic gecmez, yalniz sistem istemi gorur.
# kur: hosts yedegi + blok, LaunchDaemon (root:wheel 644, UserName=kullanici), onbellek
# temizligi, ARDINDAN dogrulama. Dogrulama gecmezse HER SEYI geri alir ve 1 ile cikar.
set -uo pipefail
ETIKET="com.discord-engel-asici-sni"
DAEMON="/Library/LaunchDaemons/$ETIKET.plist"
HOSTS="/etc/hosts"
YEDEK="$HOSTS.discord-engel-asici.yedek"
BASLA="# >>> DiscordEngelAsici >>>"
BITIS="# <<< DiscordEngelAsici <<<"

if [ "$(id -u)" -ne 0 ]; then
  SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  if sudo -n true 2>/dev/null; then
    exec sudo -n "$SELF" "$@"
  fi
  kacis() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
  KOMUT="$(printf '%q ' "$SELF" "$@")"
  exec osascript -e "do shell script \"$(kacis "$KOMUT")\" with administrator privileges with prompt \"Discord Engel Aşıcı kurulumu için yönetici izni gerekiyor.\""
fi

KOMUT_ADI="${1:-}"; KULLANICI="${2:-}"
[ -n "$KULLANICI" ] && [ "$KULLANICI" != "root" ] && id "$KULLANICI" >/dev/null 2>&1 \
  || { echo "HATA: gecersiz kullanici" >&2; exit 2; }

# Bloksuz hosts icerigi (CRLF dahil bayt bayt, yalniz blok satirlari atilir).
blok_at() {
  awk -v b="$BASLA" -v e="$BITIS" '
    { t=$0; sub(/\r$/, "", t) }
    t==b { ic=1; next }
    ic && t==e { ic=0; next }
    !ic { print }
  ' "$1"
}
hosts_yaz() { cat "$1" > "$HOSTS"; }   # yerinde yazar: sahip, izin, inode korunur
onbellek() { dscacheutil -flushcache; killall -HUP mDNSResponder 2>/dev/null || true; }
daemon_kaldir() {
  launchctl bootout "system/$ETIKET" 2>/dev/null || true
  rm -f "$DAEMON"
}
geri_al() {
  daemon_kaldir
  T="$(mktemp)"; blok_at "$HOSTS" > "$T" && hosts_yaz "$T"; rm -f "$T"
  onbellek
}

case "$KOMUT_ADI" in
  kur)
    YENI="${3:-}"; PLIST="${4:-}"
    [ -f "$YENI" ] && [ -f "$PLIST" ] || { echo "HATA: dosyalar yok" >&2; exit 2; }
    # Kullanici yazilabilir dosyalar root tarafindan kullanilacak: icerigi dogrula.
    [ "$(grep -c -F "$BASLA" "$YENI")" = "1" ] && [ "$(grep -c -F "$BITIS" "$YENI")" = "1" ] \
      || { echo "HATA: hosts blogu gecersiz" >&2; exit 2; }
    awk -v b="$BASLA" -v e="$BITIS" '
      { t=$0; sub(/\r$/, "", t) }
      t==b { ic=1; next }
      ic && t==e { ic=0; next }
      ic && t !~ /^(127\.0\.0\.1|::1)[ ]+[a-z0-9][a-z0-9.-]*$/ { kotu=1 }
      END { exit kotu }
    ' "$YENI" || { echo "HATA: blokta beklenmeyen satir" >&2; exit 2; }
    A="$(mktemp)"; B="$(mktemp)"; blok_at "$YENI" > "$A"; blok_at "$HOSTS" > "$B"
    cmp -s "$A" "$B" || { rm -f "$A" "$B"; echo "HATA: hosts blok disinda degismis" >&2; exit 2; }
    rm -f "$A" "$B"
    [ "$(plutil -extract UserName raw "$PLIST" 2>/dev/null)" = "$KULLANICI" ] \
      && [ "$(plutil -extract Label raw "$PLIST" 2>/dev/null)" = "$ETIKET" ] \
      || { echo "HATA: plist UserName/Label beklenenden farkli" >&2; exit 2; }

    [ -e "$YEDEK" ] || cp -p "$HOSTS" "$YEDEK"
    hosts_yaz "$YENI"
    daemon_kaldir
    install -o root -g wheel -m 644 "$PLIST" "$DAEMON"
    launchctl bootstrap system "$DAEMON" || { echo "HATA: bootstrap basarisiz" >&2; geri_al; exit 1; }
    onbellek

    tamam=""
    for _ in 1 2 3 4; do
      kod="$(sudo -u "$KULLANICI" env -u HTTPS_PROXY -u https_proxy curl --noproxy '*' -s -o /dev/null \
        -w '%{http_code}' --max-time 15 https://updates.discord.com/ 2>/dev/null || true)"
      [ -n "$kod" ] && [ "$kod" != "000" ] && { tamam=1; break; }
      sleep 2
    done
    if [ -z "$tamam" ]; then
      echo "HATA: dogrulama basarisiz (updates.discord.com http=${kod:-000}), yonetici adimi geri alindi" >&2
      geri_al
      exit 1
    fi
    echo "Yonetici adimi tamam: hosts blogu, $ETIKET (UserName=$KULLANICI), dogrulama http=$kod"
    ;;
  kaldir)
    daemon_kaldir
    if [ -f "$HOSTS" ] && grep -q -F "$BASLA" "$HOSTS"; then
      T="$(mktemp)"; blok_at "$HOSTS" > "$T" && hosts_yaz "$T"; rm -f "$T"
    fi
    onbellek
    echo "Yonetici adimi geri alindi: hosts blogu ve $ETIKET kaldirildi. Hosts yedegi: $YEDEK"
    ;;
  *) echo "kullanim: yonetici.sh kur|kaldir <kullanici> ..." >&2; exit 2 ;;
esac
