#!/usr/bin/env python3
"""
ByeDPI strateji secimi. Tek kaynak: calisma kopyasindaki strateji.json (hizmet onu okur;
Mac'te kur.sh ve yeniden-ayarla.sh plist'leri ondan uretir).

Her aday icin motor gecici olarak rastgele bir yerel portta baslatilir, SOCKS5 uzerinden
  * ana argumanlarla: https://discord.com/api/v9/gateway (200 sart) ve
    https://cdn.discordapp.com/ (herhangi bir HTTP yaniti: TLS gecti demektir)
  * indirme argumanlariyla: https://dl.discordapp.net/ (herhangi bir HTTP yaniti)
olculur. Ilk gecen aday secilir. Hicbiri gecmezse cikis kodu 2, sessiz gecis yok.

Kullanim:
  python3 strateji.py sec --motor <ciadpi> [--yaz <strateji.json>]   # --yaz yoksa kurulum degismez
  python3 strateji.py goster --strateji <strateji.json>
  python3 strateji.py plist --strateji <strateji.json> --rol ana|indirme --plist <dosya>
Yalniz standart kutuphane.
"""
import argparse
import json
import os
import plistlib
import socket
import ssl
import subprocess
import sys
import time
from collections import namedtuple

ANA_PORT = 1080
INDIRME_PORT = 1091
OLCUM_SURESI = 8           # her istek icin sn
MOTOR_HAZIR_SURESI = 5     # gecici motorun portu acmasi icin sn
PENCERESIZ = getattr(subprocess, "CREATE_NO_WINDOW", 0)

GATEWAY = ("discord.com", "/api/v9/gateway")
CDN = ("cdn.discordapp.com", "/")
INDIRME = ("dl.discordapp.net", "/")
DISCORD_DISI = ("www.google.com", "/")

Aday = namedtuple("Aday", "ad ana indirme kaynak")

# Sira onemli: ilk gecen secilir. Butun bayraklar ByeDPI v0.17.3 `ciadpi --help` ciktisinda
# vardir (tests/test_strateji.py motor varsa bunu dogrular). Mac derlemesinde --fake ve
# --timeout yok, bu yuzden listede de yok.
ADAYLAR = (
    # Bu repoda 2026-11-09 olculdu (Mac ve Windows, tek saglayici): 1080 -o 8+s, 1091 -d 8+s.
    Aday("oob-8s", ("-o", "8+s"), ("-d", "8+s"), "bu repo, 2026-11-09 olcumu"),
    # ByeDPI v0.17.3 README.md, "Usage example" ilk satiri.
    Aday("readme-ornek", ("--disorder", "1", "--auto=torst", "--tlsrec", "1+s"),
         ("--disorder", "1", "--auto=torst", "--tlsrec", "1+s"), "ByeDPI README, Usage example"),
    # ByeDPI v0.17.3 README.md, --disorder bolumu: Windows icin onerilen.
    Aday("split-disorder", ("--split", "1+s", "--disorder", "3+s"),
         ("--split", "1+s", "--disorder", "3+s"), "ByeDPI README, --disorder (Windows)"),
    # ByeDPI v0.17.3 README.md, --tlsrec bolumu (--timeout olmadan; Mac derlemesinde yok).
    Aday("tlsrec-sni", ("--tlsrec", "3+s"), ("--tlsrec", "3+s"), "ByeDPI README, --tlsrec"),
    # ByeDPI v0.17.3 README.md, --disorder bolumu: Linux icin onerilen.
    Aday("disorder-1", ("--disorder", "1"), ("--disorder", "1"), "ByeDPI README, --disorder (Linux)"),
)
VARSAYILAN = ADAYLAR[0]


class StratejiHatasi(Exception):
    pass


def tls_baglami():
    """Dogrulamali TLS. python.org Mac Python'unun kendi sertifika deposu bos olabilir;
    o durumda macOS'un /etc/ssl/cert.pem dosyasi yuklenir (dogrulama kapatilmaz)."""
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats().get("x509_ca", 0) == 0 and os.path.exists("/etc/ssl/cert.pem"):
        ctx.load_verify_locations("/etc/ssl/cert.pem")
    return ctx


def _tam_oku(s, n):
    veri = b""
    while len(veri) < n:
        p = s.recv(n - len(veri))
        if not p:
            raise OSError("SOCKS baglantisi kapandi")
        veri += p
    return veri


def socks5_baglan(socks, host, port, sure):
    """SOCKS5 CONNECT, ad uzak tarafta cozulur (socks5h)."""
    s = socket.create_connection(socks, timeout=sure)
    try:
        s.sendall(b"\x05\x01\x00")
        if _tam_oku(s, 2) != b"\x05\x00":
            raise OSError("SOCKS el sikismasi reddedildi")
        ad = host.encode("idna")
        s.sendall(b"\x05\x01\x00\x03" + bytes([len(ad)]) + ad + port.to_bytes(2, "big"))
        bas = _tam_oku(s, 4)
        if bas[1] != 0:
            raise OSError(f"SOCKS CONNECT hata kodu {bas[1]}")
        kalan = {1: 4, 4: 16}.get(bas[3])
        if kalan is None:
            kalan = _tam_oku(s, 1)[0]
        _tam_oku(s, kalan + 2)
        return s
    except BaseException:
        s.close()
        raise


def https_kod(host, yol, socks=None, sure=OLCUM_SURESI, baglam=None):
    """HTTPS GET, ilk satirdaki durum kodu (int). Ortam proxy degiskenleri ve PAC kullanilmaz.
    socks None ise dogrudan baglanir. Hata olursa OSError/ssl.SSLError firlatir."""
    if socks:
        ham = socks5_baglan(socks, host, 443, sure)
    else:
        ham = socket.create_connection((host, 443), timeout=sure)
    ham.settimeout(sure)
    baglam = baglam or tls_baglami()
    with baglam.wrap_socket(ham, server_hostname=host) as s:
        s.sendall((f"GET {yol} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: discord-engel-asici\r\n"
                   "Accept: */*\r\nConnection: close\r\n\r\n").encode())
        veri = b""
        while b"\r\n" not in veri and len(veri) < 4096:
            p = s.recv(1024)
            if not p:
                break
            veri += p
    satir = veri.split(b"\r\n", 1)[0].split()
    if len(satir) < 2 or not satir[0].startswith(b"HTTP/") or not satir[1].isdigit():
        raise OSError("gecersiz HTTP yaniti")
    return int(satir[1])


def olc(host, yol, socks=None, sure=OLCUM_SURESI):
    """(kod, hata). kod None ise baglanti/TLS kurulamadi."""
    try:
        return https_kod(host, yol, socks, sure), ""
    except (OSError, ssl.SSLError, ValueError) as e:
        return None, f"{type(e).__name__}: {e}"


def bos_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def motor_komutu(exe, port, ek):
    return [exe, "-i", "127.0.0.1", "-p", str(port), *ek]


class GeciciMotor:
    """with GeciciMotor(exe, args) as port: ... Motor yerel rastgele portta, is bitince durur."""

    def __init__(self, exe, ek):
        self.exe, self.ek, self.p = exe, ek, None

    def __enter__(self):
        port = bos_port()
        self.p = subprocess.Popen(motor_komutu(self.exe, port, self.ek), stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  creationflags=PENCERESIZ)
        son = time.monotonic() + MOTOR_HAZIR_SURESI
        while time.monotonic() < son:
            if self.p.poll() is not None:
                raise StratejiHatasi(f"motor hemen cikti (kod {self.p.returncode}): {' '.join(self.ek)}")
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.3).close()
                return port
            except OSError:
                time.sleep(0.1)
        raise StratejiHatasi(f"motor {MOTOR_HAZIR_SURESI} sn icinde port acmadi")

    def __exit__(self, *_):
        if self.p and self.p.poll() is None:
            self.p.terminate()
            try:
                self.p.wait(5)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait(5)


def aday_dene(exe, aday, olcer=olc):
    """[(etiket, kod, hata)], gecti_mi."""
    sonuc = []
    try:
        with GeciciMotor(exe, aday.ana) as port:
            for etiket, (host, yol) in (("gateway", GATEWAY), ("cdn", CDN)):
                kod, hata = olcer(host, yol, ("127.0.0.1", port))
                sonuc.append((etiket, kod, hata))
        if sonuc[0][1] == 200 and sonuc[1][1] is not None:
            with GeciciMotor(exe, aday.indirme) as port:
                kod, hata = olcer(*INDIRME, ("127.0.0.1", port))
                sonuc.append(("indirme", kod, hata))
    except StratejiHatasi as e:
        sonuc.append(("motor", None, str(e)))
    gecti = (len(sonuc) == 3 and sonuc[0][1] == 200 and sonuc[1][1] is not None
             and sonuc[2][1] is not None)
    return sonuc, gecti


def sec(exe, adaylar=ADAYLAR, dene=aday_dene, yaz=print):
    """Ilk gecen Aday ya da None. Her adayin sonucunu yazar."""
    for i, aday in enumerate(adaylar, 1):
        yaz(f"  [{i}/{len(adaylar)}] {aday.ad}: ana {' '.join(aday.ana)} | indirme {' '.join(aday.indirme)}")
        sonuc, gecti = dene(exe, aday)
        for etiket, kod, hata in sonuc:
            yaz(f"        {etiket}: {kod if kod is not None else '000'} {hata}".rstrip())
        if gecti:
            return aday
    return None


def kaydet(yol, aday):
    """strateji.json'u atomik yazar."""
    veri = {"ad": aday.ad, "ana": list(aday.ana), "indirme": list(aday.indirme),
            "kaynak": aday.kaynak, "secim": time.strftime("%Y-%m-%dT%H:%M:%S")}
    os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
    gecici = yol + ".yeni"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(gecici, yol)


def oku(yol):
    """strateji.json -> Aday. Bozuksa StratejiHatasi (sessiz varsayilan yok)."""
    try:
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
    except (OSError, ValueError) as e:
        raise StratejiHatasi(f"strateji dosyasi okunamadi: {yol}: {e}") from e
    ana, indirme = v.get("ana"), v.get("indirme")
    for ad, deger in (("ana", ana), ("indirme", indirme)):
        if (not isinstance(deger, list) or not deger
                or not all(isinstance(x, str) and x and "\n" not in x for x in deger)
                or not deger[0].startswith("-")):
            raise StratejiHatasi(f"strateji dosyasi gecersiz ({ad}): {yol}")
        if any(x in ("-i", "--ip", "-p", "--port") for x in deger):
            raise StratejiHatasi(f"strateji {ad} dinleme adresini degistiremez: {yol}")
    return Aday(str(v.get("ad", "?")), tuple(ana), tuple(indirme), str(v.get("kaynak", "")))


def plist_guncelle(plist_yolu, ek):
    """Mac plist'inde ProgramArguments: [exe, -i, 127.0.0.1, -p, port] + ek."""
    with open(plist_yolu, "rb") as f:
        p = plistlib.load(f)
    a = p["ProgramArguments"]
    if "-p" not in a:
        raise StratejiHatasi(f"plist'te -p yok: {plist_yolu}")
    p["ProgramArguments"] = a[:a.index("-p") + 2] + list(ek)
    with open(plist_yolu, "wb") as f:
        plistlib.dump(p, f)


def main(argv=None):
    ap = argparse.ArgumentParser(description="ByeDPI strateji secimi")
    alt = ap.add_subparsers(dest="komut", required=True)
    s = alt.add_parser("sec")
    s.add_argument("--motor", required=True)
    s.add_argument("--yaz", help="strateji.json yolu; verilmezse hicbir sey yazilmaz")
    g = alt.add_parser("goster")
    g.add_argument("--strateji", required=True)
    p = alt.add_parser("plist")
    p.add_argument("--strateji", required=True)
    p.add_argument("--rol", choices=("ana", "indirme"), required=True)
    p.add_argument("--plist", required=True)
    a = ap.parse_args(argv)

    try:
        if a.komut == "goster":
            x = oku(a.strateji)
            print(f"{x.ad}: ana {' '.join(x.ana)} | indirme {' '.join(x.indirme)} ({x.kaynak})")
            return 0
        if a.komut == "plist":
            x = oku(a.strateji)
            plist_guncelle(a.plist, x.ana if a.rol == "ana" else x.indirme)
            return 0
        if not os.path.isfile(a.motor):
            raise StratejiHatasi(f"motor yok: {a.motor}")
        print("Strateji secimi: Discord'a dogrudan erisim olculuyor...")
        kod, hata = olc(*GATEWAY)
        if kod == 200:
            print("  NOT: discord.com bu agda dogrudan aciliyor (200), engel yok gibi gorunuyor."
                  " Yine de engel gelirse diye bir strateji seciliyor.")
        else:
            print(f"  Dogrudan: {kod if kod is not None else '000'} {hata}".rstrip()
                  + " (engel var, adaylar deneniyor)")
        secilen = sec(a.motor)
        if secilen is None:
            print("HATA: hicbir strateji Discord'a ulasamadi. Bu ag ya IP/DNS duzeyinde engelliyor"
                  " ya da adaylar bu saglayicida ise yaramiyor. Kurulum degistirilmedi.", file=sys.stderr)
            return 2
        print(f"SECILEN: {secilen.ad} (ana {' '.join(secilen.ana)} | indirme {' '.join(secilen.indirme)})")
        if a.yaz:
            kaydet(a.yaz, secilen)
            print(f"Yazildi: {a.yaz}")
        else:
            print("Deneme modu: hicbir dosya yazilmadi.")
        return 0
    except StratejiHatasi as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
