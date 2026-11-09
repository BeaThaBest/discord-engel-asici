#!/bin/bash
# Kullanici LaunchAgent'larini durdurma ve baslatma: kur.sh, ac.sh, kapat.sh tek kaynak olarak source eder.
# Neden bekleme: launchctl bootout hemen 0 doner ama KeepAlive surec (ByeDPI) SIGTERM sonrasi
# birkac saniye yasar. O surede bootstrap "Bootstrap failed: 5" verir ve is yuklenmeden kalir;
# eski PID portu tutmaya devam ettigi icin yalniz port kontrolu de yalanci yesil verir.

# etiket|port
HIZMETLER=(
  "com.discord-engel-asici|1080"
  "com.discord-engel-asici-dl|1091"
  "com.discord-engel-asici-pac|1099"
)
LA="$HOME/Library/LaunchAgents"
UID_NUM="$(id -u)"
DURMA_SURESI="${DURMA_SURESI:-40}"    # x 0.5 sn
BASLAMA_SURESI="${BASLAMA_SURESI:-60}"  # x 0.5 sn

pid_of() { launchctl list | awk -v l="$1" '$3==l && $1!="-" {print $1}'; }
port_pid() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -1 || true; }
yuklu_mu() { launchctl print "gui/$UID_NUM/$1" >/dev/null 2>&1; }

# hizmet_durdur etiket port: isi bosaltir, eski surecin bitmesini ve portun bosalmasini bekler.
# Basarida eski PID'i (yoksa bos) HIZMET_ESKI_PID'e yazar.
hizmet_durdur() {
  local etiket="$1" port="$2" eski kalan
  eski="$(pid_of "$etiket" || true)"
  HIZMET_ESKI_PID="$eski"
  if yuklu_mu "$etiket"; then
    launchctl bootout "gui/$UID_NUM/$etiket" || { echo "HATA: $etiket bootout basarisiz" >&2; return 1; }
  fi
  for _ in $(seq 1 "$DURMA_SURESI"); do
    kalan=""
    [ -n "$eski" ] && kill -0 "$eski" 2>/dev/null && kalan=1
    yuklu_mu "$etiket" && kalan=1
    [ -n "$(port_pid "$port")" ] && kalan=1
    [ -z "$kalan" ] && return 0
    sleep 0.5
  done
  echo "HATA: $etiket durmadi (eski PID ${eski:-yok}, port $port sahibi $(port_pid "$port"))" >&2
  return 1
}

# hizmet_baslat etiket port eski_pid: bootstrap eder, YENI PID'in portu dinledigini dogrular.
hizmet_baslat() {
  local etiket="$1" port="$2" eski="$3" yeni="" sahip=""
  launchctl bootstrap "gui/$UID_NUM" "$LA/$etiket.plist" || { echo "HATA: $etiket bootstrap basarisiz" >&2; return 1; }
  for _ in $(seq 1 "$BASLAMA_SURESI"); do
    yeni="$(pid_of "$etiket" || true)"
    sahip="$(port_pid "$port")"
    if [ -n "$yeni" ] && [ "$yeni" != "$eski" ] && [ "$sahip" = "$yeni" ]; then
      echo "  $etiket: PID $yeni, port $port"
      return 0
    fi
    sleep 0.5
  done
  echo "HATA: $etiket calismadi (eski=${eski:-yok} yeni=${yeni:-yok} port $port sahibi=${sahip:-yok})" >&2
  return 1
}

# Tum hizmetler. Ilk hatada durur, sifir olmayan doner.
hizmetleri_durdur() {
  local h
  for h in "${HIZMETLER[@]}"; do hizmet_durdur "${h%%|*}" "${h##*|}" || return 1; done
}
hizmetleri_yeniden_yukle() {
  local h
  for h in "${HIZMETLER[@]}"; do
    hizmet_durdur "${h%%|*}" "${h##*|}" || return 1
    hizmet_baslat "${h%%|*}" "${h##*|}" "$HIZMET_ESKI_PID" || return 1
  done
}

# Sistem otomatik proxy (PAC) ayari. Kablolu ya da Wi-Fi, etkin her ag hizmetine uygulanir;
# kapatma yalniz URL'si bizim PAC olan hizmetlere dokunur.
PAC_URL="http://127.0.0.1:1099/proxy.pac"
ag_servisleri() { networksetup -listallnetworkservices | tail -n +2 | grep -v '^\*' || true; }
pac_url_oku() { networksetup -getautoproxyurl "$1" | awk -F': ' '/^URL/ {print $2}'; }
pac_ac() {
  local s
  while IFS= read -r s; do
    [ -n "$s" ] || continue
    networksetup -setautoproxyurl "$s" "$PAC_URL" || return 1
    networksetup -setautoproxystate "$s" on || return 1
  done < <(ag_servisleri)
}
pac_kapat() {
  local s
  while IFS= read -r s; do
    [ -n "$s" ] || continue
    if [ "$(pac_url_oku "$s")" = "$PAC_URL" ]; then
      networksetup -setautoproxystate "$s" off || return 1
    fi
  done < <(ag_servisleri)
}

# Motor LaunchAgent plist'leri: sablondan uretilir, ByeDPI argumanlari strateji.json'dan
# (tek kaynak) eklenir. Gerekenler: MAC, APP, OTO, PY; $APP/strateji.py ve $APP/strateji.json.
plistleri_yaz() {
  local h sablon hedef rol
  for h in "${HIZMETLER[@]}"; do
    sablon="$MAC/plist/${h%%|*}.plist"
    hedef="$LA/$(basename "$sablon")"
    sed -e "s|@OTO@|$OTO|g" -e "s|@APP@|$APP|g" "$sablon" > "$hedef" || return 1
    rol=""
    case "${h%%|*}" in
      com.discord-engel-asici) rol=ana ;;
      com.discord-engel-asici-dl) rol=indirme ;;
    esac
    if [ -n "$rol" ]; then
      "$PY" "$APP/strateji.py" plist --strateji "$APP/strateji.json" --rol "$rol" --plist "$hedef" || return 1
    fi
    plutil -lint "$hedef" >/dev/null || return 1
  done
}
