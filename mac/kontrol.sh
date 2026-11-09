#!/bin/bash
# Kurulum kontrolu: GECTI/KALDI listesi, her KALDI icin ne yapilacagi. Hicbir ayari degistirmez.
# Tam cikti $APP/log/kontrol-TARIH.log (kurulum yoksa gecici dizin).
MAC="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Library/Application Support/DiscordEngelAsici"
. "$MAC/hizmetler.sh"
ADIM="kontrol"
if [ -d "$APP" ]; then gunluk_baslat kontrol "$APP/log"; else gunluk_baslat kontrol "${TMPDIR:-/tmp}/DiscordEngelAsici"; fi
PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "HATA: python3 yok. Once 'xcode-select --install'." >&2; exit 1; }
"$PY" "$(dirname "$MAC")/ortak/doktor.py" --app "$APP"
