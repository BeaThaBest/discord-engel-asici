"""Log siniri, tunel zaman asimi, tek surec hizmeti (Windows giris noktasi) ve PAC sabitligi."""
import glob
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


sys.path.insert(0, ORTAK)
import alanlar  # noqa: E402
import gunluk  # noqa: E402
import hizmet  # noqa: E402


def metin(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


class LogSiniri(unittest.TestCase):
    def tearDown(self):
        gunluk.gunluk_kur(None)

    def test_dosya_boyut_sinirli(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "log", "kopru.log")
            h = gunluk.gunluk_kur(yol)
            self.assertEqual(h.maxBytes, 1_000_000)
            self.assertEqual(h.backupCount, 2)
            for _ in range(40000):
                gunluk.log.warning("x" * 80)
            h.flush()
            dosyalar = sorted(glob.glob(yol + "*"))
            self.assertEqual(dosyalar, [yol, yol + ".1", yol + ".2"])
            for f in dosyalar:
                self.assertLessEqual(os.path.getsize(f), 1_000_000)
            gunluk.gunluk_kur(None)

    def test_baglanti_satiri_varsayilan_yazilmaz(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "k.log")
            gunluk.gunluk_kur(yol)
            gunluk.log.debug("baglanti satiri")
            gunluk.log.warning("hata satiri")
            gunluk.gunluk_kur(None)
            icerik = metin(yol)
            self.assertNotIn("baglanti satiri", icerik)
            self.assertIn("hata satiri", icerik)

    def test_stderr_yoksa_cokmez(self):
        eski = sys.stderr
        sys.stderr = None  # pythonw durumu
        try:
            h = gunluk.gunluk_kur(None)
            gunluk.log.warning("sessiz")
            self.assertIsInstance(h, logging.NullHandler)
        finally:
            sys.stderr = eski


class Hizmet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        gunluk.gunluk_kur(None)
        gunluk.log.setLevel(logging.CRITICAL)
        cls.pac_srv, cls.sni_soketleri, cls.dur = hizmet.baslat(ALANLAR, 0, 0, sni_dinle=("127.0.0.1",), cozucu=lambda ad: ["192.0.2.1"])
        cls.pac_port = cls.pac_srv.getsockname()[1]

    @classmethod
    def tearDownClass(cls):
        cls.dur.set()
        gunluk.gunluk_kur(None)

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
        self.assertEqual([s.getsockname()[0] for s in self.sni_soketleri], ["127.0.0.1"])

    def test_pac_pac_uret_ile_ayni(self):
        bas, govde = self.http_get("/proxy.pac")
        self.assertTrue(bas.startswith("HTTP/1.0 200"), bas)
        self.assertIn("application/x-ns-proxy-autoconfig", bas)
        beklenen = hizmet.pac_uret.uret(alanlar.oku(ALANLAR)).encode()
        self.assertEqual(govde, beklenen)

    def test_pac_disi_404(self):
        bas, govde = self.http_get("/../alanlar.txt")
        self.assertTrue(bas.startswith("HTTP/1.0 404"), bas)
        self.assertEqual(govde, b"")

    def test_sni_dinleyici_kabul_dongusu_calisir(self):
        # Listede olmayan/bozuk istemci baglantiyi kapatir, hizmet ayakta kalir.
        s = socket.create_connection(("127.0.0.1", self.sni_soketleri[0].getsockname()[1]), timeout=5)
        s.sendall(b"GET / HTTP/1.1\r\n\r\n")
        s.settimeout(5)
        self.assertEqual(s.recv(10), b"")
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
        gunluk.gunluk_kur(None)
        gunluk.log.setLevel(logging.CRITICAL)
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
        self.assertEqual(hizmet.pac_uret.uret(alanlar.oku(ALANLAR)), beklenen)


if __name__ == "__main__":
    unittest.main()
