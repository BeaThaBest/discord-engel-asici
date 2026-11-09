#!/bin/bash
# kapat.sh sonrasi tekrar acar (yetki istemez). Kalici kurulum icin kur.sh kullan.
# Her hizmet yeniden yuklenir ve YENI PID'in kendi portunu dinledigi dogrulanir; olmazsa cikis 1.
set -uo pipefail
MAC="$(cd "$(dirname "$0")" && pwd)"
. "$MAC/hizmetler.sh"
PAC_URL="http://127.0.0.1:1099/proxy.pac"

for h in "${HIZMETLER[@]}"; do
  [ -e "$LA/${h%%|*}.plist" ] || { echo "HATA: $LA/${h%%|*}.plist yok, once mac/kur.sh" >&2; exit 1; }
done
hizmetleri_yeniden_yukle || { echo "HATA: ACILAMADI, PAC ayari acilmadi." >&2; exit 1; }
networksetup -setautoproxyurl Wi-Fi "$PAC_URL" || exit 1
networksetup -setautoproxystate Wi-Fi on || exit 1
echo "ACILDI."
