#!/bin/bash
# Gecici kapatir (yetki istemez): PAC ayari kapanir, kullanici hizmetleri (ByeDPI 1080 ve 1091,
# PAC sunucusu 1099) durdurulur ve sureclerinin bitmesi beklenir.
# Yerinde kalan (root, yalniz kaldir.sh siler): hosts blogu ve 443 SNI daemon'u. ByeDPI yokken
# dinleyici baglantiyi hemen kapatir, yani yalniz updates.discord.com (Discord guncelleyicisi)
# baglanamaz; baska hicbir trafik etkilenmez.
# Geri acmak: ac.sh
set -uo pipefail
MAC="$(cd "$(dirname "$0")" && pwd)"
. "$MAC/hizmetler.sh"

networksetup -setautoproxystate Wi-Fi off || exit 1
hizmetleri_durdur || { echo "HATA: hizmetler tam durmadi." >&2; exit 1; }
# Eski tasarimdan kalma kopru ve genel HTTPS_PROXY (kur.sh tamamlanmamis).
if yuklu_mu com.discord-engel-asici-bridge; then
  launchctl bootout "gui/$UID_NUM/com.discord-engel-asici-bridge" || exit 1
fi
if [ "$(launchctl getenv HTTPS_PROXY 2>/dev/null)" = "http://127.0.0.1:1098" ]; then
  launchctl unsetenv HTTPS_PROXY
fi
echo "KAPATILDI. Geri acmak icin mac/ac.sh"
