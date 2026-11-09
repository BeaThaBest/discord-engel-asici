import logging
import os
import socket
import ssl
import struct
import sys
import threading
import time
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORTAK = os.path.join(KOK, "ortak")
sys.path.insert(0, ORTAK)

import alanlar  # noqa: E402
import gunluk  # noqa: E402
import sni_dinleyici as sni  # noqa: E402

ALANLAR = os.path.join(ORTAK, "alanlar.txt")


def client_hello(ad, alpn=True):
    """Gercek ClientHello: SSLContext + MemoryBIO, el handshake'ine baslar."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if alpn:
        ctx.set_alpn_protocols(["h2", "http/1.1"])
    gelen, giden = ssl.MemoryBIO(), ssl.MemoryBIO()
    nesne = ctx.wrap_bio(gelen, giden, server_hostname=ad)
    try:
        nesne.do_handshake()
    except ssl.SSLWantReadError:
        pass
    return giden.read()


def kayit_sar(govde, parca):
    """Handshake govdesini `parca` baytlik birden cok TLS kaydina boler."""
    out = b""
    for i in range(0, len(govde), parca):
        p = govde[i:i + parca]
        out += struct.pack(">BHH", 22, 0x0301, len(p)) + p
    return out


class Ayristirma(unittest.TestCase):
    def test_gercek_client_hello(self):
        for ad in ("updates.discord.com", "Updates.Discord.COM"):
            self.assertEqual(sni.ayristir(client_hello(ad)), (True, "updates.discord.com"))

    def test_alpn_olmadan(self):
        self.assertEqual(sni.ayristir(client_hello("a.b.example", alpn=False)), (True, "a.b.example"))

    def test_sondaki_nokta_atilir(self):
        h = client_hello("updates.discord.com.")
        self.assertEqual(sni.ayristir(h), (True, "updates.discord.com"))

    def test_parca_parca_gelme(self):
        h = client_hello("updates.discord.com")
        for n in range(0, len(h)):
            self.assertEqual(sni.ayristir(h[:n]), (False, None), n)
        self.assertEqual(sni.ayristir(h + b"fazlalik"), (True, "updates.discord.com"))

    def test_birden_cok_tls_kaydina_yayilmis(self):
        h = client_hello("updates.discord.com")
        govde = h[5:]
        bolunmus = kayit_sar(govde, 100)
        self.assertGreater(bolunmus.count(b"\x16\x03\x01"), 2)
        self.assertEqual(sni.ayristir(bolunmus), (True, "updates.discord.com"))
        self.assertEqual(sni.ayristir(bolunmus[:-1]), (False, None))

    def test_sni_yok(self):
        h = bytearray(client_hello("updates.discord.com"))
        # Uzanti listesini kes: kayit ve el sikisma uzunluklarini yeniden hesapla.
        govde = bytes(h[5:])
        poz = 4 + 2 + 32
        poz += 1 + govde[poz]
        poz += 2 + struct.unpack_from(">H", govde, poz)[0]
        poz += 1 + govde[poz]
        govde = govde[:poz]
        govde = bytes([1]) + (len(govde) - 4).to_bytes(3, "big") + govde[4:]
        self.assertEqual(sni.ayristir(kayit_sar(govde, 16000)), (True, None))

    def test_bozuk_veri(self):
        for kotu in (b"GET / HTTP/1.1\r\n\r\n", b"\x15\x03\x03\x00\x02\x02\x28", b"\x16\x02\x00\x00\x10",
                     b"\x16\x03\x01\x00\x00", b"\x16\x03\x01\xff\xff"):
            with self.assertRaises(sni.HataliVeri, msg=kotu):
                sni.ayristir(kotu)
        # el sikisma turu ClientHello degil
        with self.assertRaises(sni.HataliVeri):
            sni.ayristir(kayit_sar(b"\x02\x00\x00\x01\x00", 100))
        # kisaltilmis ama uzunlugu tutarli ClientHello govdesi
        with self.assertRaises(sni.HataliVeri):
            sni.ayristir(kayit_sar(b"\x01\x00\x00\x03abc", 100))

    def test_cok_buyuk_hello_reddedilir(self):
        with self.assertRaises(sni.HataliVeri):
            sni.ayristir(kayit_sar(b"\x01\xff\xff\xff" + b"\x00" * 100, 200))

    def test_hello_oku_zaman_asimi_ve_kapanis(self):
        a, b = socket.socketpair()
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        b.sendall(client_hello("x.com")[:10])
        with self.assertRaises(socket.timeout):
            sni.hello_oku(a, sure=0.3)
        c, d = socket.socketpair()
        d.sendall(b"\x16\x03")
        d.close()
        with self.assertRaises(sni.HataliVeri):
            sni.hello_oku(c, sure=2)
        c.close()

    def test_hello_oku_damla_damla(self):
        a, b = socket.socketpair()
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        h = client_hello("updates.discord.com")

        def gonder():
            for i in range(0, len(h), 7):
                b.sendall(h[i:i + 7])
                time.sleep(0.001)

        threading.Thread(target=gonder, daemon=True).start()
        tampon, ad = sni.hello_oku(a, sure=5)
        self.assertEqual((tampon, ad), (h, "updates.discord.com"))


class SahteSocks:
    """SOCKS5 sunucusu: istegi kaydeder, sonra gelen baytlari kaydeder ve cevap verir."""

    def __init__(self, cevap=b"SUNUCU-YANITI", reddet=False):
        self.srv = socket.create_server(("127.0.0.1", 0))
        self.port = self.srv.getsockname()[1]
        self.cevap, self.reddet = cevap, reddet
        self.istek = None
        self.alinan = b""
        self.bitti = threading.Event()
        threading.Thread(target=self.calis, daemon=True).start()

    def oku(self, c, n):
        v = b""
        while len(v) < n:
            p = c.recv(n - len(v))
            if not p:
                raise OSError
            v += p
        return v

    def calis(self):
        try:
            c, _ = self.srv.accept()
        except OSError:
            return
        try:
            self.oku(c, 3)
            c.sendall(b"\x05\x00")
            bas = self.oku(c, 4)
            ip = socket.inet_ntoa(self.oku(c, 4))
            port = struct.unpack(">H", self.oku(c, 2))[0]
            self.istek = (bas, ip, port)
            if self.reddet:
                c.sendall(b"\x05\x05\x00\x01" + b"\x00" * 6)
                return
            c.sendall(b"\x05\x00\x00\x01" + b"\x00" * 6)
            c.settimeout(2)
            try:
                while True:
                    p = c.recv(65536)
                    if not p:
                        break
                    self.alinan += p
                    if not self.alinan.startswith(b"\x16"):
                        break
                    c.sendall(self.cevap)
                    break
            except OSError:
                pass
            time.sleep(0.2)
        finally:
            c.close()
            self.bitti.set()

    def kapat(self):
        self.srv.close()


def baslat_dinleyici(cozucu, kayitlar=None):
    kayitlar = kayitlar or alanlar.oku(ALANLAR)
    soketler = sni.soketleri_ac(0, ("127.0.0.1",))
    sni.baslat(kayitlar, soketler, cozucu)
    return soketler[0].getsockname()[1]


class UctanUca(unittest.TestCase):
    def setUp(self):
        gunluk.gunluk_kur(None)
        gunluk.log.setLevel(logging.CRITICAL)

    def kayitlar(self, socks_port):
        return [alanlar.Kayit("discord.com", socks_port, False),
                alanlar.Kayit("updates.discord.com", socks_port, True)]

    def test_kabul_edilen_ad_socksa_ip_ve_443_ile_gider(self):
        socks = SahteSocks()
        self.addCleanup(socks.kapat)
        sorulan = []

        def cozucu(ad):
            sorulan.append(ad)
            return ["192.0.2.55"]

        port = baslat_dinleyici(cozucu, self.kayitlar(socks.port))
        hello = client_hello("Updates.Discord.com.")
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        # ClientHello'yu bilerek parcalayarak gonder.
        s.sendall(hello[:3])
        time.sleep(0.05)
        s.sendall(hello[3:40])
        time.sleep(0.05)
        s.sendall(hello[40:])
        self.assertEqual(s.recv(100), b"SUNUCU-YANITI")
        s.close()
        socks.bitti.wait(5)
        self.assertEqual(sorulan, ["updates.discord.com"])
        bas, ip, hedef_port = socks.istek
        self.assertEqual(bas, b"\x05\x01\x00\x01")  # CONNECT, IPv4 adres (ad degil)
        self.assertEqual((ip, hedef_port), ("192.0.2.55", 443))
        self.assertEqual(socks.alinan, hello)  # ClientHello aynen

    def test_listede_olmayan_sni_reddedilir(self):
        socks = SahteSocks()
        self.addCleanup(socks.kapat)
        cozulen = []
        port = baslat_dinleyici(lambda ad: cozulen.append(ad) or ["192.0.2.1"], self.kayitlar(socks.port))
        for ad in ("www.google.com", "a.updates.discord.com", "discord.com", "evilupdates.discord.com"):
            s = socket.create_connection(("127.0.0.1", port), timeout=5)
            s.sendall(client_hello(ad))
            self.assertEqual(s.recv(100), b"", ad)
            s.close()
        self.assertEqual(cozulen, [])
        self.assertIsNone(socks.istek)

    def test_sni_siz_ve_bozuk_baglanti_kapanir(self):
        port = baslat_dinleyici(lambda ad: ["192.0.2.1"])
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        s.sendall(b"GET / HTTP/1.1\r\nHost: updates.discord.com\r\n\r\n")
        self.assertEqual(s.recv(10), b"")
        s.close()

    def test_cozulemezse_kapanir(self):
        socks = SahteSocks()
        self.addCleanup(socks.kapat)

        def cozucu(ad):
            raise OSError("cozulemedi")

        port = baslat_dinleyici(cozucu, self.kayitlar(socks.port))
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        s.sendall(client_hello("updates.discord.com"))
        self.assertEqual(s.recv(10), b"")
        s.close()

    def test_socks_reddederse_kapanir(self):
        socks = SahteSocks(reddet=True)
        self.addCleanup(socks.kapat)
        port = baslat_dinleyici(lambda ad: ["192.0.2.1"], self.kayitlar(socks.port))
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        s.sendall(client_hello("updates.discord.com"))
        self.assertEqual(s.recv(10), b"")
        s.close()

    def test_byedpi_yoksa_kapanir_dogrudan_gitmez(self):
        # SOCKS portu kapali: baglanti hemen kapanir, gercek adrese dogrudan GIDILMEZ.
        bos = socket.create_server(("127.0.0.1", 0))
        olu_port = bos.getsockname()[1]
        bos.close()
        hedef = socket.create_server(("127.0.0.1", 0))
        hedef.settimeout(0.5)
        orijinal = sni.HEDEF_PORT
        sni.HEDEF_PORT = hedef.getsockname()[1]
        self.addCleanup(lambda: setattr(sni, "HEDEF_PORT", orijinal))
        self.addCleanup(hedef.close)
        port = baslat_dinleyici(lambda ad: ["127.0.0.1"], self.kayitlar(olu_port))
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        bas = time.monotonic()
        s.sendall(client_hello("updates.discord.com"))
        self.assertEqual(s.recv(100), b"")
        self.assertLess(time.monotonic() - bas, 2)
        s.close()
        with self.assertRaises(socket.timeout):
            hedef.accept()

    def test_yalniz_istenen_adreste_dinler(self):
        soketler = sni.soketleri_ac(0, ("127.0.0.1",))
        self.assertEqual(soketler[0].getsockname()[0], "127.0.0.1")
        for s in soketler:
            s.close()

    def test_calistir_api_durdurulabilir(self):
        dur = threading.Event()
        soketler = sni.soketleri_ac(0, ("127.0.0.1",))
        t = threading.Thread(target=sni.calistir, kwargs=dict(
            alan_yolu=ALANLAR, soketler=soketler, cozucu=lambda ad: ["192.0.2.1"], dur=dur), daemon=True)
        t.start()
        time.sleep(0.2)
        dur.set()
        t.join(5)
        self.assertFalse(t.is_alive())


if __name__ == "__main__":
    unittest.main()
