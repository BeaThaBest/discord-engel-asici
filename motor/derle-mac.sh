#!/bin/bash
# ByeDPI sabit surumunu kaynaktan derler. Cikti: motor/bin/ciadpi
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$ROOT/SURUM"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/byedpi-derle.XXXXXX")"
mkdir "$TMP/src"

echo "Indiriliyor: $BYEDPI_URL"
curl -fsSL -o "$TMP/kaynak.tar.gz" "$BYEDPI_URL"

HESAP="$(shasum -a 256 "$TMP/kaynak.tar.gz" | awk '{print $1}')"
if [ "$HESAP" != "$BYEDPI_SHA256" ]; then
  echo "HATA: SHA256 uyusmuyor. Beklenen $BYEDPI_SHA256, gelen $HESAP" >&2
  exit 1
fi

tar -xzf "$TMP/kaynak.tar.gz" -C "$TMP/src" --strip-components=1
make -C "$TMP/src" -j4 >"$TMP/derleme.log" 2>&1 || { tail -20 "$TMP/derleme.log" >&2; echo "HATA: derleme basarisiz" >&2; exit 1; }

SURUM_CIKTI="$("$TMP/src/ciadpi" --version)"
if [ "$SURUM_CIKTI" != "$BYEDPI_SURUM_CIKTISI" ]; then
  echo "HATA: derlenen surum $SURUM_CIKTI, beklenen $BYEDPI_SURUM_CIKTISI" >&2
  exit 1
fi

mkdir -p "$ROOT/bin"
cp "$TMP/src/ciadpi" "$ROOT/bin/ciadpi"
chmod 755 "$ROOT/bin/ciadpi"
echo "Tamam: $ROOT/bin/ciadpi (surum $SURUM_CIKTI, $BYEDPI_ETIKET)"
echo "Gecici dizin silinmedi (rm yok): $TMP"
