#!/bin/bash
# Stratejiyi yeniden secer (internet saglayicisi degisti ya da Discord yine acilmiyor).
# Yetki istemez. Adaylar sirayla denenir, ilk calisan strateji.json'a yazilir, motor
# plist'leri ondan yeniden uretilir ve kullanici hizmetleri yeniden baslatilir.
# Hicbiri calismazsa eski secim ve hizmetler oldugu gibi kalir (cikis 2).
set -uo pipefail
MAC="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Library/Application Support/DiscordEngelAsici"
OTO="$HOME/Library/Application Support/Otomasyon"
PY="$(command -v python3 || true)"
. "$MAC/hizmetler.sh"
[ -n "$PY" ] || { echo "HATA: python3 yok" >&2; exit 1; }
[ -x "$APP/DiscordEngelAsici" ] && [ -f "$APP/strateji.py" ] || { echo "HATA: kurulum yok ya da eski, once mac/KUR.command" >&2; exit 1; }

"$PY" "$APP/strateji.py" sec --motor "$APP/DiscordEngelAsici" --yaz "$APP/strateji.json"
kod=$?
[ "$kod" -eq 0 ] || { echo "Eski ayar degismedi." >&2; exit "$kod"; }
plistleri_yaz || { echo "HATA: plist yazilamadi" >&2; exit 1; }
hizmetleri_yeniden_yukle || { echo "HATA: hizmetler yeniden baslamadi. mac/kontrol.sh ile bak." >&2; exit 1; }
echo "YENIDEN AYARLANDI. Discord'u tamamen kapatip (Cmd+Q) yeniden ac."
