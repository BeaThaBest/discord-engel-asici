#!/usr/bin/env python3
"""
Yerel 443 SNI dinleyici. hosts dosyasi bazi Discord adlarini 127.0.0.1 ve ::1'e cevirir;
bu surec TLS'i ACMADAN ClientHello'yu okur, SNI'yi cikarir, yalniz alanlar.txt'de
"hosts" isaretli tam adlari kabul eder (digerleri kapatilir), gercek IPv4 adresi hosts'u
atlayan cozucuyle bulur, satirdaki porttaki ByeDPI'ye SOCKS5 CONNECT (IP:443) acar ve
ClientHello baytlarini AYNEN iletip iki yonlu tunel kurar. Sertifika yok, MITM yok.

ByeDPI calismiyorsa (SOCKS portu reddediyor) baglanti hemen kapatilir. Dogrudan baglanti
denenmez: o yol DPI engelli oldugu icin ise yaramaz, ve ByeDPI disinda hicbir yol acilmaz.
Etkilenen yalniz hosts blogundaki adlardir (su an updates.discord.com).

Mac: --launchd <ad> ile dinleme soketleri launchd'den alinir (443'u root olmayan surec
bind edemez). Windows: hizmet.py calistir()/baslat() ile thread olarak baslatir.
Yalniz standart kutuphane.
"""
import argparse
import ctypes
import os
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alanlar  # noqa: E402
import dns_a  # noqa: E402
from gunluk import gunluk_kur, log  # noqa: E402

HEDEF_PORT = 443
MAX_HELLO = 32768          # ClientHello govdesi ust siniri (gercekte < 2 KB, PQ ile ~ 2 KB)
HELLO_SURESI = 10          # ClientHello'nun tamamlanmasi icin toplam sure (sn)
BAGLANTI_SURESI = 15       # SOCKS el sikismasi (CONNECT yaniti; ByeDPI uzak sunucuya baglanir)
# 127.0.0.1'deki ByeDPI'ye TCP baglantisi. Canli motor aninda kabul eder. Windows reddedilen
# baglantida SYN'i yaklasik 2 sn yeniden dener (Mac/Linux aninda ECONNREFUSED): motor yokken
# istemcinin 2 sn takilmamasi icin ilk yeniden denemeden (~0,5 sn) once vazgecilir.
YEREL_BAGLANTI_SURESI = 0.3
MAX_IP = 3                 # denenecek en cok gercek adres


class HataliVeri(ValueError):
    pass


def _handshake_govdesi(tampon):
    """Birden cok TLS kaydina yayilmis ClientHello govdesi (4 bayt baslik dahil),
    veri eksikse None. Gecersizse HataliVeri."""
    poz = 0
    govde = bytearray()
    toplam = None
    while True:
        if len(tampon) > poz and tampon[poz] != 22:
            raise HataliVeri("handshake kaydi degil")
        if len(tampon) - poz < 5:
            return None
        _, major, _, uzun = struct.unpack_from(">BBBH", tampon, poz)
        if major != 3 or uzun == 0 or uzun > 16384:
            raise HataliVeri("gecersiz kayit basligi")
        if len(tampon) - poz - 5 < uzun:
            return None
        govde += tampon[poz + 5:poz + 5 + uzun]
        poz += 5 + uzun
        if toplam is None and len(govde) >= 4:
            if govde[0] != 1:
                raise HataliVeri("ClientHello degil")
            toplam = 4 + int.from_bytes(govde[1:4], "big")
            if toplam > MAX_HELLO:
                raise HataliVeri("ClientHello cok buyuk")
        if toplam is not None and len(govde) >= toplam:
            return bytes(govde[:toplam])


def _sni_cikar(hello):
    """ClientHello govdesinden SNI (kucuk harf) ya da None (uzanti yok)."""
    try:
        poz = 4 + 2 + 32
        poz += 1 + hello[poz]                                  # session id
        poz += 2 + struct.unpack_from(">H", hello, poz)[0]     # cipher suites
        poz += 1 + hello[poz]                                  # compression
        if poz == len(hello):
            return None
        uz = struct.unpack_from(">H", hello, poz)[0]
        poz += 2
        son = poz + uz
        if son > len(hello):
            raise HataliVeri("uzanti listesi tasiyor")
        while poz + 4 <= son:
            tur, ul = struct.unpack_from(">HH", hello, poz)
            poz += 4
            if poz + ul > son:
                raise HataliVeri("uzanti tasiyor")
            if tur == 0:
                liste = hello[poz:poz + ul]
                lp = 2
                while lp + 3 <= len(liste):
                    nt, nl = struct.unpack_from(">BH", liste, lp)
                    lp += 3
                    if lp + nl > len(liste):
                        raise HataliVeri("ad tasiyor")
                    if nt == 0:
                        try:
                            ad = liste[lp:lp + nl].decode("ascii")
                        except UnicodeDecodeError:
                            raise HataliVeri("ascii olmayan SNI")
                        return alanlar.host_temizle(ad) or None
                    lp += nl
                return None
            poz += ul
        return None
    except (IndexError, struct.error):
        raise HataliVeri("kesik ClientHello")


def ayristir(tampon):
    """(tamam, sni). Veri eksikse (False, None). SNI uzantisi yoksa (True, None).
    Bozuksa HataliVeri."""
    hello = _handshake_govdesi(bytes(tampon))
    if hello is None:
        if len(tampon) > MAX_HELLO + 5 * 4:
            raise HataliVeri("cok fazla veri")
        return False, None
    return True, _sni_cikar(hello)


def hello_oku(sock, sure=HELLO_SURESI, saat=time.monotonic):
    """(tampon, sni). Okunan TUM baytlar tamponda kalir (aynen iletilir)."""
    son = saat() + sure
    tampon = bytearray()
    while True:
        tamam, sni = ayristir(tampon)
        if tamam:
            return bytes(tampon), sni
        kalan = son - saat()
        if kalan <= 0:
            raise socket.timeout("ClientHello zaman asimi")
        sock.settimeout(kalan)
        parca = sock.recv(4096)
        if not parca:
            raise HataliVeri("ClientHello tamamlanmadan kapandi")
        tampon += parca


class SocksYok(OSError):
    """SOCKS (ByeDPI) portuna TCP baglantisi kurulamadi."""


def _tam_oku(s, n):
    veri = b""
    while len(veri) < n:
        p = s.recv(n - len(veri))
        if not p:
            raise OSError("socks erken kapandi")
        veri += p
    return veri


def socks5_connect_ip(upstream, ip, port, sure=BAGLANTI_SURESI):
    """IPv4 ADRESLE CONNECT (ad vermek hosts yuzunden dongu yapar)."""
    try:
        s = socket.create_connection(upstream, timeout=YEREL_BAGLANTI_SURESI)
    except OSError as e:
        raise SocksYok(f"{upstream[0]}:{upstream[1]} motor yanit vermedi: {e}")
    try:
        s.settimeout(sure)
        s.sendall(b"\x05\x01\x00")
        if _tam_oku(s, 2) != b"\x05\x00":
            raise OSError("socks no-auth reddedildi")
        s.sendall(b"\x05\x01\x00\x01" + socket.inet_aton(ip) + struct.pack(">H", port))
        bas = _tam_oku(s, 4)
        if bas[1] != 0:
            raise OSError(f"socks connect basarisiz ({bas[1]})")
        kalan = {1: 4, 4: 16}.get(bas[3])
        if kalan is None:
            kalan = _tam_oku(s, 1)[0] if bas[3] == 3 else 0
        _tam_oku(s, kalan + 2)
        s.settimeout(None)
        return s
    except Exception:
        s.close()
        raise


def pump(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            b.sendall(d)
    except OSError:
        pass
    finally:
        for x in (a, b):
            try:
                x.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def uzak_baglan(sp, ipler):
    """Yalniz ByeDPI (SOCKS) uzerinden. (soket, yontem). ByeDPI yoksa SocksYok, dogrudan yok."""
    son = None
    for ip in ipler[:MAX_IP]:
        try:
            return socks5_connect_ip(("127.0.0.1", sp), ip, HEDEF_PORT), f"SOCKS {sp}"
        except SocksYok:
            raise
        except OSError as e:
            son = e
    raise son or OSError("adres yok")


def isle(istemci, kayitlar, cozucu, hello_suresi=HELLO_SURESI):
    uzak = None
    try:
        tampon, sni = hello_oku(istemci, hello_suresi)
        sp = alanlar.dinleyici_port(sni, kayitlar) if sni else None
        if sp is None:
            log.debug("reddedildi: sni=%s", sni)
            istemci.close()
            return
        ipler = cozucu(sni)
        uzak, yontem = uzak_baglan(sp, ipler)
        uzak.sendall(tampon)
        istemci.settimeout(None)
        log.debug("%s -> %s %s", sni, ipler[0], yontem)
        threading.Thread(target=pump, args=(istemci, uzak), daemon=True).start()
        pump(uzak, istemci)
    except (OSError, HataliVeri) as e:
        # Bozuk ya da yarim kalan istemciler (port taramasi vb.) hata sayilmaz.
        if isinstance(e, HataliVeri) or isinstance(e, socket.timeout):
            log.debug("istemci hatasi: %s", e)
        else:
            log.warning("baglanti hatasi: %s", e)
        for x in (istemci, uzak):
            try:
                if x is not None:
                    x.close()
            except OSError:
                pass
    except Exception as e:
        log.warning("beklenmeyen hata: %s", e)
        istemci.close()


def kabul_dongusu(srv, kayitlar, cozucu, dur):
    srv.settimeout(0.5)
    while not dur.is_set():
        try:
            c, _ = srv.accept()
        except socket.timeout:
            continue
        except OSError as e:
            if dur.is_set():
                return
            log.error("accept hatasi: %s", e)
            time.sleep(0.2)
            continue
        threading.Thread(target=isle, args=(c, kayitlar, cozucu), daemon=True).start()


def soketleri_ac(port, adresler=("127.0.0.1", "::1")):
    """Yalniz loopback. Biri acilamazsa (ornegin IPv6 yok) loglanir, hic biri acilamazsa OSError."""
    soketler = []
    son = None
    for adres in adresler:
        try:
            ailesi = socket.AF_INET6 if ":" in adres else socket.AF_INET
            s = socket.socket(ailesi, socket.SOCK_STREAM)
            if os.name != "nt":
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if ailesi == socket.AF_INET6:
                s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            s.bind((adres, port))
            s.listen(128)
            soketler.append(s)
        except OSError as e:
            son = e
            log.warning("%s:%s dinlenemedi: %s", adres, port, e)
    if not soketler:
        raise son or OSError("dinlenecek adres yok")
    return soketler


def launchd_soketleri(ad):
    """launch_activate_socket ile launchd'nin bind ettigi soketler (yalniz macOS)."""
    lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    fn = lib.launch_activate_socket
    fn.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_int)), ctypes.POINTER(ctypes.c_size_t)]
    fn.restype = ctypes.c_int
    fds = ctypes.POINTER(ctypes.c_int)()
    sayi = ctypes.c_size_t()
    rc = fn(ad.encode(), ctypes.byref(fds), ctypes.byref(sayi))
    if rc != 0:
        raise OSError(rc, f"launch_activate_socket({ad!r}) basarisiz")
    try:
        return [socket.socket(fileno=fds[i]) for i in range(sayi.value)]
    finally:
        lib.free(fds)


def baslat(kayitlar, soketler, cozucu=None, dur=None):
    """Kabul dongulerini arka plan thread'lerinde baslatir. (soketler, dur) dondurur."""
    dur = dur or threading.Event()
    cozucu = cozucu or dns_a.varsayilan_cozucu()
    for s in soketler:
        threading.Thread(target=kabul_dongusu, args=(s, kayitlar, cozucu, dur), daemon=True).start()
    return soketler, dur


def calistir(alan_yolu=alanlar.VARSAYILAN, port=HEDEF_PORT, dinle=("127.0.0.1", "::1"),
             cozucu=None, dur=None, launchd=None, soketler=None):
    """Engelleyici API: dur set edilene kadar doner. hizmet.py bunu thread'de calistirabilir."""
    dur = dur or threading.Event()
    kayitlar = alanlar.oku(alan_yolu)
    if soketler is None:
        soketler = launchd_soketleri(launchd) if launchd else soketleri_ac(port, dinle)
    baslat(kayitlar, soketler, cozucu, dur)
    log.warning("SNI dinleyici hazir: %s, %s tam ad",
                ", ".join("%s:%s" % s.getsockname()[:2] for s in soketler),
                len(alanlar.hosts_adlari(kayitlar)))
    dur.wait()
    for s in soketler:
        try:
            s.close()
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alanlar", default=alanlar.VARSAYILAN)
    ap.add_argument("--port", type=int, default=HEDEF_PORT)
    ap.add_argument("--dinle", nargs="+", default=["127.0.0.1", "::1"])
    ap.add_argument("--log", help="boyut sinirli log dosyasi (yoksa stderr)")
    ap.add_argument("--ayrinti", action="store_true", help="her baglantiyi da logla")
    ap.add_argument("--launchd", metavar="SOKET_ADI", help="soketleri launchd'den al (macOS)")
    a = ap.parse_args()
    gunluk_kur(a.log, a.ayrinti)
    try:
        calistir(a.alanlar, a.port, tuple(a.dinle), launchd=a.launchd)
    except Exception:
        log.exception("SNI dinleyici durdu")
        sys.exit(1)


if __name__ == "__main__":
    main()
