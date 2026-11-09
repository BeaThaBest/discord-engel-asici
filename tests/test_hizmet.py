"""Log siniri, tunel zaman asimi, tek surec hizmeti (Windows giris noktasi) ve PAC sabitligi."""
import glob
import importlib.util
import logging
import os
import plistlib
import socket
import sys
import tempfile
import threading
import time
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORTAK = os.path.join(KOK, "ortak")
ALANLAR = os.path.join(ORTAK, "alanlar.txt")


def yukle(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(ORTAK, dosya))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


hizmet = yukle("hizmet", "hizmet.py")
kopru = hizmet.kopru


def metin(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def connect(port, hedef, bekle=5):
    s = socket.create_connection(("127.0.0.1", port), timeout=bekle)
    s.sendall(f"CONNECT {hedef} HTTP/1.1\r\nHost: {hedef}\r\n\r\n".encode())
    yanit = b""
    while b"\r\n\r\n" not in yanit:
        p = s.recv(4096)
        if not p:
            break
        yanit += p
    return s, yanit


class LogSiniri(unittest.TestCase):
    def tearDown(self):
        kopru.gunluk_kur(None)

    def test_dosya_boyut_sinirli(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "log", "kopru.log")
            h = kopru.gunluk_kur(yol)
            self.assertEqual(h.maxBytes, 1_000_000)
            self.assertEqual(h.backupCount, 2)
            for _ in range(40000):
                kopru.log.warning("x" * 80)
            h.flush()
            dosyalar = sorted(glob.glob(yol + "*"))
            self.assertEqual(dosyalar, [yol, yol + ".1", yol + ".2"])
            for f in dosyalar:
                self.assertLessEqual(os.path.getsize(f), 1_000_000)
            kopru.gunluk_kur(None)

    def test_baglanti_satiri_varsayilan_yazilmaz(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "k.log")
            kopru.gunluk_kur(yol)
            kopru.log.debug("baglanti satiri")
            kopru.log.warning("hata satiri")
            kopru.gunluk_kur(None)
            icerik = metin(yol)
            self.assertNotIn("baglanti satiri", icerik)
            self.assertIn("hata satiri", icerik)

    def test_stderr_yoksa_cokmez(self):
        eski = sys.stderr
        sys.stderr = None  # pythonw durumu
        try:
            h = kopru.gunluk_kur(None)
            kopru.log.warning("sessiz")
            self.assertIsInstance(h, logging.NullHandler)
        finally:
            sys.stderr = eski


class Hizmet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        kopru.gunluk_kur(None)
        kopru.log.setLevel(logging.CRITICAL)
        cls.pac_srv, cls.kopru_srv, cls.dur = hizmet.baslat(ALANLAR, 0, 0)
        cls.pac_port = cls.pac_srv.getsockname()[1]
        cls.kopru_port = cls.kopru_srv.getsockname()[1]

    @classmethod
    def tearDownClass(cls):
        cls.dur.set()
        kopru.gunluk_kur(None)

    def http_get(self, yol):
        s = socket.create_connection(("127.0.0.1", self.pac_port), timeout=5)
        s.sendall(f"GET {yol} HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n".encode())
        veri = b""
        while True:
            p = s.recv(65536)
            if not p:
                break
            veri += p
        s.close()
        bas, _, govde = veri.partition(b"\r\n\r\n")
        return bas.decode(), govde

    def test_yalniz_loopback(self):
        self.assertEqual(self.pac_srv.getsockname()[0], "127.0.0.1")
        self.assertEqual(self.kopru_srv.getsockname()[0], "127.0.0.1")

    def test_pac_pac_uret_ile_ayni(self):
        bas, govde = self.http_get("/proxy.pac")
        self.assertTrue(bas.startswith("HTTP/1.0 200"), bas)
        self.assertIn("application/x-ns-proxy-autoconfig", bas)
        beklenen = hizmet.pac_uret.uret(kopru.oku(ALANLAR)).encode()
        self.assertEqual(govde, beklenen)

    def test_pac_disi_404(self):
        bas, govde = self.http_get("/../alanlar.txt")
        self.assertTrue(bas.startswith("HTTP/1.0 404"), bas)
        self.assertEqual(govde, b"")

    def test_kopru_direct_bosta_kopmaz(self):
        # Discord disi hedef DIRECT gider; tunel BAGLANTI_SURESI'nden uzun bosta kalsa da kopmaz.
        hedef = socket.create_server(("127.0.0.1", 0))
        hport = hedef.getsockname()[1]

        def sunucu():
            c, _ = hedef.accept()
            time.sleep(1.2)
            c.sendall(b"merhaba")
            c.close()

        threading.Thread(target=sunucu, daemon=True).start()
        eski = kopru.BAGLANTI_SURESI
        kopru.BAGLANTI_SURESI = 0.4
        try:
            s, yanit = connect(self.kopru_port, f"127.0.0.1:{hport}")
            self.assertIn(b"200 Connection Established", yanit)
            s.settimeout(5)
            self.assertEqual(s.recv(100), b"merhaba")
            s.close()
        finally:
            kopru.BAGLANTI_SURESI = eski
            hedef.close()

    def test_kopru_ulasilamaz_hedef_502(self):
        bos = socket.create_server(("127.0.0.1", 0))
        bport = bos.getsockname()[1]
        bos.close()
        s, yanit = connect(self.kopru_port, f"127.0.0.1:{bport}")
        self.assertIn(b"502", yanit)
        s.close()


class Motor(unittest.TestCase):
    def test_komut_mac_plist_ile_ayni(self):
        for port, ek in hizmet.MOTORLAR:
            plistler = glob.glob(os.path.join(KOK, "mac", "plist", "*.plist"))
            bulunan = None
            for p in plistler:
                with open(p, "rb") as f:
                    a = plistlib.load(f)["ProgramArguments"]
                if "-p" in a and a[a.index("-p") + 1] == str(port):
                    bulunan = a[1:]
            self.assertEqual(hizmet.motor_komutu("x", port, ek)[1:], bulunan, port)

    def test_cikan_motor_yeniden_baslar(self):
        kopru.gunluk_kur(None)
        kopru.log.setLevel(logging.CRITICAL)
        with tempfile.TemporaryDirectory() as d:
            sayac = os.path.join(d, "sayac")
            komut = [sys.executable, "-c", f"open({sayac!r}, 'a').write('.')"]
            dur = threading.Event()
            t = threading.Thread(target=hizmet.motor_gozet, args=(komut, dur, 0.05, 0.1), daemon=True)
            t.start()
            son = time.monotonic() + 10
            while time.monotonic() < son:
                if os.path.exists(sayac) and len(metin(sayac)) >= 3:
                    break
                time.sleep(0.1)
            dur.set()
            t.join(5)
            self.assertGreaterEqual(len(metin(sayac)), 3)
            self.assertFalse(t.is_alive())


class PacSabit(unittest.TestCase):
    def test_pac_ciktisi_degismedi(self):
        # Windows ve Mac ayni PAC'i alir; bu dosya Mac'te kurulu proxy.pac ile birebir ayniydi.
        with open(os.path.join(KOK, "tests", "beklenen_proxy.pac"), encoding="utf-8") as f:
            beklenen = f.read()
        self.assertEqual(hizmet.pac_uret.uret(kopru.oku(ALANLAR)), beklenen)


if __name__ == "__main__":
    unittest.main()
