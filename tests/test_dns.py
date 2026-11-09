import os
import socket
import struct
import sys
import threading
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "ortak"))

import dns_a  # noqa: E402


def yanit_kur(sorgu, ipler, ttl=60, rcode=0, cname=True, kimlik=None):
    """Sorguya sahte yanit: soru + (istege bagli) CNAME + A kayitlari, isaretci sikistirmali."""
    kim = struct.unpack_from(">H", sorgu)[0] if kimlik is None else kimlik
    soru = sorgu[12:]
    adet = len(ipler) + (1 if cname else 0)
    p = struct.pack(">HHHHHH", kim, 0x8180 | rcode, 1, adet if not rcode else 0, 0, 0) + soru
    if cname and not rcode:
        hedef = b"\x03cdn\xc0\x0c"
        p += b"\xc0\x0c" + struct.pack(">HHIH", 5, 1, ttl, len(hedef)) + hedef
    if not rcode:
        for ip in ipler:
            p += b"\xc0\x0c" + struct.pack(">HHIH", 1, 1, ttl, 4) + socket.inet_aton(ip)
    return p


class SahteDns:
    def __init__(self, ipler=("93.184.216.34",), **kw):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("127.0.0.1", 0))
        self.port = self.s.getsockname()[1]
        self.ipler, self.kw, self.sorgular = ipler, kw, []
        threading.Thread(target=self.dongu, daemon=True).start()

    def dongu(self):
        while True:
            try:
                veri, adr = self.s.recvfrom(1024)
            except OSError:
                return
            self.sorgular.append(veri)
            self.s.sendto(yanit_kur(veri, self.ipler, **self.kw), adr)

    def kapat(self):
        self.s.close()


class Paket(unittest.TestCase):
    def test_sorgu_kur(self):
        p = dns_a.sorgu_kur("updates.discord.com.", 0x1234)
        self.assertEqual(p[:12], struct.pack(">HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0))
        self.assertEqual(p[12:], b"\x07updates\x07discord\x03com\x00" + struct.pack(">HH", 1, 1))

    def test_gecersiz_ad(self):
        with self.assertRaises(dns_a.DnsHata):
            dns_a.sorgu_kur("a" * 64 + ".com", 1)

    def test_yanit_ayristir_cname_ve_a(self):
        s = dns_a.sorgu_kur("updates.discord.com", 7)
        ipler, ttl = dns_a.yanit_ayristir(yanit_kur(s, ["1.2.3.4", "5.6.7.8"], ttl=42), 7, "updates.discord.com")
        self.assertEqual(ipler, ["1.2.3.4", "5.6.7.8"])
        self.assertEqual(ttl, 42)

    def test_hatali_yanitlar(self):
        s = dns_a.sorgu_kur("x.com", 7)
        with self.assertRaises(dns_a.DnsHata):
            dns_a.yanit_ayristir(yanit_kur(s, ["1.2.3.4"], kimlik=8), 7, "x.com")
        with self.assertRaises(dns_a.DnsHata):
            dns_a.yanit_ayristir(yanit_kur(s, [], rcode=3), 7, "x.com")
        with self.assertRaises(dns_a.DnsHata):
            dns_a.yanit_ayristir(yanit_kur(s, [], cname=False), 7, "x.com")
        with self.assertRaises(dns_a.DnsHata):
            dns_a.yanit_ayristir(yanit_kur(s, ["1.2.3.4"], cname=False)[:-2], 7, "x.com")
        with self.assertRaises(dns_a.DnsHata):
            dns_a.yanit_ayristir(b"\x00" * 5, 7, "x.com")

    def test_isaretci_dongusu(self):
        paket = b"\x00" * 12 + b"\xc0\x0c"
        with self.assertRaises(dns_a.DnsHata):
            dns_a._ad_oku(paket, 12)

    def test_resolv_ve_scutil(self):
        self.assertEqual(dns_a.resolv_ayristir("# x\nnameserver 1.1.1.1\nsearch a\n nameserver fe80::1%en0\n"),
                         ["1.1.1.1", "fe80::1%en0"])
        self.assertEqual(dns_a.scutil_ayristir("resolver #1\n  nameserver[0] : 8.8.8.8\n  nameserver[1] : 9.9.9.9\n"),
                         ["8.8.8.8", "9.9.9.9"])


class Cozucu(unittest.TestCase):
    def test_sahte_sunucu_ve_onbellek(self):
        d = SahteDns(["93.184.216.34"], ttl=60)
        self.addCleanup(d.kapat)
        c = dns_a.UdpCozucu([("127.0.0.1", d.port)], zaman_asimi=2)
        self.assertEqual(c("Updates.Discord.com."), ["93.184.216.34"])
        self.assertEqual(c("updates.discord.com"), ["93.184.216.34"])
        self.assertEqual(len(d.sorgular), 1)  # ikincisi onbellekten

    def test_ttl_dolunca_yeniden_sorar(self):
        d = SahteDns(["93.184.216.34"], ttl=1)
        self.addCleanup(d.kapat)
        t = [0.0]
        c = dns_a.UdpCozucu([("127.0.0.1", d.port)], saat=lambda: t[0])
        c("x.com")
        t[0] += dns_a.TTL_EN_AZ + 1
        c("x.com")
        self.assertEqual(len(d.sorgular), 2)

    def test_olu_sunucudan_sonrakine_gecer(self):
        olu = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        olu.bind(("127.0.0.1", 0))  # okuyan yok, yanit vermez
        self.addCleanup(olu.close)
        d = SahteDns(["93.184.216.34"])
        self.addCleanup(d.kapat)
        c = dns_a.UdpCozucu([("127.0.0.1", olu.getsockname()[1]), ("127.0.0.1", d.port)], zaman_asimi=0.3)
        self.assertEqual(c("x.com"), ["93.184.216.34"])

    def test_zaman_asimi(self):
        olu = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        olu.bind(("127.0.0.1", 0))
        self.addCleanup(olu.close)
        c = dns_a.UdpCozucu([("127.0.0.1", olu.getsockname()[1])], zaman_asimi=0.2, tur=1)
        with self.assertRaises(OSError):
            c("x.com")

    def test_loopback_yaniti_reddedilir(self):
        d = SahteDns(["127.0.0.1"])
        self.addCleanup(d.kapat)
        c = dns_a.UdpCozucu([("127.0.0.1", d.port)], zaman_asimi=0.5, tur=1)
        with self.assertRaises(OSError):
            c("x.com")

    def test_nxdomain(self):
        d = SahteDns([], rcode=3)
        self.addCleanup(d.kapat)
        c = dns_a.UdpCozucu([("127.0.0.1", d.port)], zaman_asimi=0.5, tur=1)
        with self.assertRaises(dns_a.DnsHata):
            c("yok.example")


if __name__ == "__main__":
    unittest.main()
