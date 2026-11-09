#!/usr/bin/env python3
"""
hosts dosyasinda yonetilen blok. Saf fonksiyonlar bayt uzerinde calisir: blok disindaki
satirlar bayt bayt aynen kalir, CRLF korunur (Windows ve Mac ayni kodu kullanir).

  hosts_blok.py yaz    [--hosts YOL] [--alanlar YOL] [--cikti YOL]
  hosts_blok.py kaldir [--hosts YOL] [--cikti YOL]

--cikti verilirse sonuc oraya yazilir, hosts'a dokunulmaz (yetkisiz onhazirlik icin).
Yoksa hosts yerinde yazilir. Yedek: <hosts>.discord-engel-asici.yedek, YALNIZ yoksa
alinir. Gerekce: ilk yedek bizim blogumuz girmeden onceki ozgun dosyadir. Her yazimda
zaman damgali yedek alsaydik sonrakiler blok iceren dosyalari saklar, ozgun olan kaybolur
ve dizin cop dolar.
"""
import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alanlar  # noqa: E402

BASLA = b"# >>> DiscordEngelAsici >>>"
BITIS = b"# <<< DiscordEngelAsici <<<"
YEDEK_SONEK = ".discord-engel-asici.yedek"


def varsayilan_hosts():
    if sys.platform == "win32":
        kok = os.environ.get("SystemRoot", r"C:\Windows")
        return os.path.join(kok, "System32", "drivers", "etc", "hosts")
    return "/etc/hosts"


def _satir_sonu(satir):
    if satir.endswith(b"\r\n"):
        return b"\r\n"
    if satir.endswith(b"\n"):
        return b"\n"
    if satir.endswith(b"\r"):
        return b"\r"
    return b""


def _bloklar(satirlar):
    """[(basla_indeks, bitis_indeks)] (bitis dahil). Bitisi olmayan BASLA ValueError."""
    sonuc = []
    i = 0
    while i < len(satirlar):
        if satirlar[i].strip() == BASLA:
            j = i + 1
            while j < len(satirlar) and satirlar[j].strip() != BITIS:
                if satirlar[j].strip() == BASLA:
                    raise ValueError("ic ice blok basi")
                j += 1
            if j >= len(satirlar):
                raise ValueError("blok bitisi yok, dosyaya dokunulmadi")
            sonuc.append((i, j))
            i = j + 1
        else:
            i += 1
    return sonuc


def _eol_sec(veri, satirlar, bloklar):
    if bloklar:
        e = _satir_sonu(satirlar[bloklar[0][0]])
        if e:
            return e
    crlf = veri.count(b"\r\n")
    lf = veri.count(b"\n") - crlf
    return b"\r\n" if crlf > lf else b"\n"


def blok_olustur(adlar, eol=b"\n"):
    satirlar = [BASLA]
    for ad in adlar:
        satirlar.append(f"127.0.0.1 {ad}".encode("ascii"))
        satirlar.append(f"::1 {ad}".encode("ascii"))
    satirlar.append(BITIS)
    return b"".join(s + eol for s in satirlar)


def kaldir(veri):
    """Tum yonetilen bloklari siler. Blok yoksa veri aynen doner."""
    satirlar = veri.splitlines(keepends=True)
    bloklar = _bloklar(satirlar)
    if not bloklar:
        return veri
    at = set()
    for b, e in bloklar:
        at.update(range(b, e + 1))
    return b"".join(s for i, s in enumerate(satirlar) if i not in at)


def ekle(veri, adlar):
    """Blogu ekler, varsa YERINDE gunceller (idempotent). Ad yoksa blogu kaldirir."""
    adlar = list(adlar)
    for ad in adlar:
        if not alanlar._TAM_AD.match(ad):
            raise ValueError(f"gecersiz ad: {ad!r}")
    satirlar = veri.splitlines(keepends=True)
    bloklar = _bloklar(satirlar)
    if not adlar:
        return kaldir(veri)
    blok = blok_olustur(adlar, _eol_sec(veri, satirlar, bloklar))
    if not bloklar:
        son = _satir_sonu(satirlar[-1]) if satirlar else b"\n"
        onek = b"" if son else _eol_sec(veri, satirlar, bloklar)
        return veri + onek + blok
    b0, e0 = bloklar[0]
    at = set()
    for b, e in bloklar:
        at.update(range(b, e + 1))
    cikti = []
    for i, s in enumerate(satirlar):
        if i == b0:
            cikti.append(blok)
        if i not in at:
            cikti.append(s)
    return b"".join(cikti)


def dosyaya_yaz(yol, yeni, yedek_al=True):
    """Degisiklik yoksa dokunmaz. Yedek yalniz yoksa alinir. Gecici dosya + os.replace."""
    try:
        with open(yol, "rb") as f:
            eski = f.read()
    except FileNotFoundError:
        eski = None
    if eski == yeni:
        return False
    yedek = yol + YEDEK_SONEK
    if yedek_al and eski is not None and not os.path.exists(yedek):
        shutil.copy2(yol, yedek)
    try:
        fd, gecici = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(yol)), prefix=".dea-")
        with os.fdopen(fd, "wb") as f:
            f.write(yeni)
        if eski is not None:
            shutil.copymode(yol, gecici)
            if hasattr(os, "chown") and os.geteuid() == 0:
                st = os.stat(yol)
                os.chown(gecici, st.st_uid, st.st_gid)
        os.replace(gecici, yol)
    except OSError:
        try:
            os.unlink(gecici)
        except (OSError, UnboundLocalError):
            pass
        with open(yol, "wb") as f:  # son care: yerinde yaz
            f.write(yeni)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("komut", choices=("yaz", "kaldir"))
    ap.add_argument("--hosts", default=varsayilan_hosts())
    ap.add_argument("--alanlar", default=alanlar.VARSAYILAN)
    ap.add_argument("--cikti")
    a = ap.parse_args(argv)
    try:
        with open(a.hosts, "rb") as f:
            veri = f.read()
    except FileNotFoundError:
        veri = b""
    try:
        if a.komut == "yaz":
            yeni = ekle(veri, alanlar.hosts_adlari(alanlar.oku(a.alanlar)))
        else:
            yeni = kaldir(veri)
    except ValueError as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 2
    if a.cikti:
        with open(a.cikti, "wb") as f:
            f.write(yeni)
    else:
        dosyaya_yaz(a.hosts, yeni)
    return 0


if __name__ == "__main__":
    sys.exit(main())
