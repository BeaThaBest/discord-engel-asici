#!/bin/bash
# ByeDPI sabit surumunu Mac'te mingw-w64 ile Windows icin capraz derler.
# Cikti: motor/bin/ciadpi.exe. Kurulumun kendisi resmi release varligini kullanir
# (bkz. SURUM); bu betik ayni kaynaktan bagimsiz derleme ve karsilastirma icindir.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$ROOT/SURUM"
CC_WIN="${CC_WIN:-x86_64-w64-mingw32-gcc}"
command -v "$CC_WIN" >/dev/null || { echo "HATA: $CC_WIN yok (brew install mingw-w64)" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/byedpi-derle-win.XXXXXX")"
mkdir "$TMP/src"

echo "Indiriliyor: $BYEDPI_URL"
curl -fsSL -o "$TMP/kaynak.tar.gz" "$BYEDPI_URL"

HESAP="$(shasum -a 256 "$TMP/kaynak.tar.gz" | awk '{print $1}')"
if [ "$HESAP" != "$BYEDPI_SHA256" ]; then
  echo "HATA: SHA256 uyusmuyor. Beklenen $BYEDPI_SHA256, gelen $HESAP" >&2
  exit 1
fi

tar -xzf "$TMP/kaynak.tar.gz" -C "$TMP/src" --strip-components=1
make -C "$TMP/src" -j4 windows CC="$CC_WIN" WIN_LDFLAGS="-lws2_32 -lmswsock -static -s" \
  >"$TMP/derleme.log" 2>&1 || { tail -20 "$TMP/derleme.log" >&2; echo "HATA: derleme basarisiz" >&2; exit 1; }

TUR="$(file -b "$TMP/src/ciadpi.exe")"
case "$TUR" in
  *"PE32+ executable"*x86-64*) ;;
  *) echo "HATA: beklenmeyen ikili turu: $TUR" >&2; exit 1 ;;
esac
# Windows disi bir DLL'e (libwinpthread vb.) bagimlilik olmamali.
DIS="$(strings -a "$TMP/src/ciadpi.exe" | grep -iE '\.dll$' | grep -viE '^(kernel32|ws2_32|mswsock|msvcrt|advapi32|api-ms-win-[a-z0-9-]+)\.dll$' || true)"
[ -z "$DIS" ] || { echo "HATA: beklenmeyen DLL bagimliligi: $DIS" >&2; exit 1; }

mkdir -p "$ROOT/bin"
cp "$TMP/src/ciadpi.exe" "$ROOT/bin/ciadpi.exe"
echo "Tamam: $ROOT/bin/ciadpi.exe ($TUR, $BYEDPI_ETIKET)"
echo "SHA256: $(shasum -a 256 "$ROOT/bin/ciadpi.exe" | awk '{print $1}')"
echo "Gecici dizin silinmedi (rm yok): $TMP"
