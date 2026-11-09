#!/bin/bash
# Kurulum kontrolu: GECTI/KALDI listesi, her KALDI icin ne yapilacagi. Hicbir ayari degistirmez.
MAC="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "HATA: python3 yok. Once 'xcode-select --install'." >&2; exit 1; }
exec "$PY" "$(dirname "$MAC")/ortak/doktor.py" --app "$HOME/Library/Application Support/DiscordEngelAsici"
