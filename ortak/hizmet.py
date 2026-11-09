#!/usr/bin/env python3
"""
Tek surec, platformdan bagimsiz giris noktasi (Windows bunu kullanir, Mac ayri
LaunchAgent'larla ayni parcalari calistirir):
  * 1099: proxy.pac (pac_uret.py ciktisinin aynisi, bellekten sunulur)
  * 1098: HTTP CONNECT koprusu (connect-bridge.py)
  * --motor-exe verilirse ByeDPI surecleri (1080 -o 8+s, 1091 -d 8+s) gozetilir,
    cikarsa yeniden baslatilir. Windows'ta konsol penceresi acilmaz.
Hepsi yalniz 127.0.0.1 dinler. Yalniz standart kutuphane.
"""
import argparse
import importlib.util
import os
import subprocess
import sys
import threading
import time

_DIZIN = os.path.dirname(os.path.abspath(__file__))


def _yukle(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(_DIZIN, dosya))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


kopru = _yukle("connect_bridge", "connect-bridge.py")
pac_uret = _yukle("pac_uret", "pac_uret.py")
log = kopru.log

# Mac plist'leriyle ayni (tests/ bunu karsilastirir).
MOTORLAR = ((1080, ("-o", "8+s")), (1091, ("-d", "8+s")))
PAC_YOLU = "/proxy.pac"
# Windows: alt surec icin konsol penceresi olusturma.
PENCERESIZ = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def motor_komutu(exe, port, ek):
    return [exe, "-i", "127.0.0.1", "-p", str(port), *ek]


def pac_yaniti(istek, pac):
    """Ham HTTP isteginden yanit baytlarini uretir. Yalniz GET/HEAD /proxy.pac."""
    satir = istek.split(b"\r\n", 1)[0].decode("latin1").split()
    if len(satir) >= 2 and satir[0] in ("GET", "HEAD") and satir[1].split("?", 1)[0] == PAC_YOLU:
        govde = b"" if satir[0] == "HEAD" else pac
        bas = ("HTTP/1.0 200 OK\r\n"
               "Content-Type: application/x-ns-proxy-autoconfig\r\n"
               f"Content-Length: {len(pac)}\r\n"
               "Cache-Control: no-cache\r\nConnection: close\r\n\r\n")
        return bas.encode() + govde
    return b"HTTP/1.0 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"


def pac_handle(client, pac):
    try:
        client.settimeout(10)
        istek = b""
        while b"\r\n\r\n" not in istek and len(istek) < 16384:
            parca = client.recv(4096)
            if not parca:
                break
            istek += parca
        client.sendall(pac_yaniti(istek, pac))
    except OSError as e:
        log.warning("pac istek hatasi: %s", e)
    finally:
        try:
            client.close()
        except OSError:
            pass


def motor_gozet(komut, dur, ilk_bekleme=1.0, en_cok=30.0):
    """Motoru calistirir, cikarsa artan beklemeyle yeniden baslatir."""
    bekle = ilk_bekleme
    while not dur.is_set():
        bas = time.monotonic()
        try:
            p = subprocess.Popen(komut, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, creationflags=PENCERESIZ)
            while p.poll() is None:
                if dur.wait(0.5):
                    p.terminate()
                    p.wait(5)
                    return
            log.warning("motor cikti (kod %s): %s", p.returncode, " ".join(komut[1:]))
        except OSError as e:
            log.error("motor baslatilamadi: %s", e)
        if time.monotonic() - bas > 60:
            bekle = ilk_bekleme
        if dur.wait(bekle):
            return
        bekle = min(bekle * 2, en_cok)


def sunucu_ac_bekle(port, sure=60):
    """Port kisa sure mesgulse (eski surec kapaniyor) bekleyip yeniden dener."""
    son = time.monotonic() + sure
    while True:
        try:
            return kopru.sunucu_ac(port)
        except OSError as e:
            if time.monotonic() > son:
                raise
            log.warning("port %s acilamadi, yeniden denenecek: %s", port, e)
            time.sleep(2)


def baslat(alanlar, pac_port, kopru_port, motor_exe=None, dur=None):
    """Sunuculari ve motorlari arka planda baslatir. (pac_srv, kopru_srv, dur) dondurur."""
    dur = dur or threading.Event()
    kayitlar = kopru.oku(alanlar)
    pac = pac_uret.uret(kayitlar).encode("utf-8")
    if motor_exe:
        for port, ek in MOTORLAR:
            threading.Thread(target=motor_gozet, args=(motor_komutu(motor_exe, port, ek), dur),
                             daemon=True).start()
    kopru_srv = sunucu_ac_bekle(kopru_port)
    pac_srv = sunucu_ac_bekle(pac_port)
    threading.Thread(target=kopru.dinle, args=(kopru_srv, kopru.handle, kayitlar), daemon=True).start()
    threading.Thread(target=kopru.dinle, args=(pac_srv, pac_handle, pac), daemon=True).start()
    log.warning("hizmet hazir: pac %s, kopru %s, motor %s, %s alan",
                pac_srv.getsockname()[1], kopru_srv.getsockname()[1],
                "var" if motor_exe else "yok", len(kayitlar))
    return pac_srv, kopru_srv, dur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alanlar", default=kopru.VARSAYILAN)
    ap.add_argument("--pac-port", type=int, default=1099)
    ap.add_argument("--kopru-port", type=int, default=1098)
    ap.add_argument("--motor-exe", help="ciadpi yolu; verilirse 1080 ve 1091 gozetilir")
    ap.add_argument("--log", help="boyut sinirli log dosyasi")
    ap.add_argument("--ayrinti", action="store_true")
    a = ap.parse_args()
    kopru.gunluk_kur(a.log, a.ayrinti)
    try:
        _, _, dur = baslat(a.alanlar, a.pac_port, a.kopru_port, a.motor_exe)
        dur.wait()
    except Exception:
        log.exception("hizmet durdu")
        sys.exit(1)


if __name__ == "__main__":
    main()
