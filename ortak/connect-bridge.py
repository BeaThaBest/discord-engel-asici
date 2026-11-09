#!/usr/bin/env python3
"""
HTTP CONNECT -> SOCKS5 koprusu.
Discord updater'i (reqwest, SOCKS env'ini yok sayar ama HTTP proxy'yi onurlandirir)
ByeDPI proxylerine yonlendirmek icin.

Alan listesi alanlar.txt dosyasindan okunur (varsayilan: bu dosyanin dizini).
Discord alani: ilgili SOCKS portu. Discord disi: DIRECT, sistem etkilenmez.
"""
import argparse
import fnmatch
import logging
import logging.handlers
import os
import socket
import struct
import sys
import threading

VARSAYILAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alanlar.txt")
# Yalniz baglanti kurulurken gecerli sure. Kurulan tunel bekleyebilir (uzun bosta kalan
# HTTP/2 ve indirme baglantilari kopmasin diye tunelde zaman asimi yok).
BAGLANTI_SURESI = 15
# Log boyut siniri: 1 MB x (1 + 2 yedek). Bakim istemez.
LOG_BOYUT = 1_000_000
LOG_YEDEK = 2
log = logging.getLogger("discord-engel-asici")


def gunluk_kur(yol=None, ayrinti=False):
    """Logu kurar. yol verilirse boyut sinirli dosya, yoksa stderr.
    Varsayilan duzey WARNING: her baglanti degil, yalniz hatalar yazilir."""
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    if yol:
        os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
        h = logging.handlers.RotatingFileHandler(
            yol, maxBytes=LOG_BOYUT, backupCount=LOG_YEDEK, encoding="utf-8")
    elif sys.stderr is not None:
        h = logging.StreamHandler(sys.stderr)
    else:  # pythonw: stderr yok
        h = logging.NullHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.DEBUG if ayrinti else logging.WARNING)
    log.propagate = False
    return h


def sunucu_ac(port, host="127.0.0.1"):
    """Yalniz loopback dinler. create_server POSIX'te SO_REUSEADDR koyar,
    Windows'ta koymaz (orada portun baska surecle paylasilmasina izin verirdi)."""
    return socket.create_server((host, port), backlog=128)


def dinle(srv, isleyici, *args):
    """Her baglanti icin ayri is parcacigi. Sonsuza kadar doner."""
    while True:
        try:
            c, _ = srv.accept()
        except OSError as e:
            log.error("accept hatasi: %s", e)
            continue
        threading.Thread(target=isleyici, args=(c, *args), daemon=True).start()


def oku(yol=VARSAYILAN):
    """alanlar.txt dosyasini [(desen, port)] listesi olarak dondurur."""
    kayitlar = []
    with open(yol, encoding="utf-8") as f:
        for satir in f:
            satir = satir.split("#", 1)[0].strip()
            if not satir:
                continue
            desen, port = satir.split()
            kayitlar.append((desen.lower(), int(port)))
    return kayitlar


def _eslesir(desen, host):
    if "*" in desen:
        return fnmatch.fnmatchcase(host, desen)
    return host == desen or host.endswith("." + desen)


def host_temizle(host):
    h = host.strip().lower()
    if h.startswith("[") and "]" in h:
        return h[1:h.index("]")]
    if h.count(":") == 1:
        h = h.split(":", 1)[0]
    return h.rstrip(".")


def socks_port(host, kayitlar):
    """Discord alani ise en uzun eslesen satirin portu, degilse None (DIRECT)."""
    h = host_temizle(host)
    en_iyi = None
    for desen, port in kayitlar:
        if _eslesir(desen, h) and (en_iyi is None or len(desen) > len(en_iyi[0])):
            en_iyi = (desen, port)
    return en_iyi[1] if en_iyi else None


def socks5_connect(upstream, host, port):
    s = socket.create_connection(upstream, timeout=BAGLANTI_SURESI)
    s.sendall(b"\x05\x01\x00")
    if s.recv(2) != b"\x05\x00":
        s.close()
        raise OSError("socks no-auth reddedildi")
    hb = host.encode()
    s.sendall(b"\x05\x01\x00\x03" + bytes([len(hb)]) + hb + struct.pack(">H", port))
    resp = s.recv(4)
    if len(resp) < 4 or resp[1] != 0x00:
        s.close()
        raise OSError("socks connect basarisiz")
    atyp = resp[3]
    if atyp == 1:
        s.recv(4 + 2)
    elif atyp == 3:
        ln = s.recv(1)[0]
        s.recv(ln + 2)
    elif atyp == 4:
        s.recv(16 + 2)
    s.settimeout(None)
    return s


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


def handle(client, kayitlar):
    try:
        req = b""
        while b"\r\n\r\n" not in req:
            chunk = client.recv(4096)
            if not chunk:
                client.close()
                return
            req += chunk
        line = req.split(b"\r\n", 1)[0].decode("latin1")
        method, target, _ = line.split(" ", 2)
        if method.upper() != "CONNECT":
            client.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            client.close()
            return
        host, port = target.rsplit(":", 1)
        port = int(port)
        sp = socks_port(host, kayitlar)
        try:
            if sp is None:
                remote = socket.create_connection((host, port), timeout=BAGLANTI_SURESI)
                remote.settimeout(None)
            else:
                remote = socks5_connect(("127.0.0.1", sp), host, port)
        except OSError as e:
            log.warning("%s:%s -> %s HATA: %s", host, port, sp or "DIRECT", e)
            client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            client.close()
            return
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        log.debug("%s:%s -> %s", host, port, f"SOCKS {sp}" if sp else "DIRECT")
        threading.Thread(target=pump, args=(client, remote), daemon=True).start()
        pump(remote, client)
    except Exception as e:
        log.warning("istek hatasi: %s", e)
        try:
            client.close()
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=1098)
    ap.add_argument("--alanlar", default=VARSAYILAN)
    ap.add_argument("--log", help="boyut sinirli log dosyasi (yoksa stderr)")
    ap.add_argument("--ayrinti", action="store_true", help="her baglantiyi da logla")
    a = ap.parse_args()
    gunluk_kur(a.log, a.ayrinti)
    kayitlar = oku(a.alanlar)
    srv = sunucu_ac(a.port)
    log.warning("CONNECT proxy 127.0.0.1:%s, %s alan", a.port, len(kayitlar))
    dinle(srv, handle, kayitlar)


if __name__ == "__main__":
    main()
