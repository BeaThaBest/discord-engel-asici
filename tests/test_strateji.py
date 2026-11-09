"""Strateji secimi: aday listesi, secim sirasi, strateji.json tek kaynak, SOCKS5 istemci."""
import json
import os
import plistlib
import re
import socket
import subprocess
import sys
import tempfile
import threading
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "ortak"))
import strateji  # noqa: E402

MOTOR = os.path.join(KOK, "motor", "bin", "ciadpi.exe" if os.name == "nt" else "ciadpi")


class AdayListesi(unittest.TestCase):
    def test_ilk_aday_olculen_varsayilan(self):
        self.assertEqual(strateji.VARSAYILAN.ana, ("-o", "8+s"))
        self.assertEqual(strateji.VARSAYILAN.indirme, ("-d", "8+s"))

    def test_her_adayin_kaynagi_var_ve_adlar_tekil(self):
        adlar = [a.ad for a in strateji.ADAYLAR]
        self.assertEqual(len(adlar), len(set(adlar)))
        for a in strateji.ADAYLAR:
            self.assertTrue(a.kaynak, a.ad)
            self.assertNotIn("-i", a.ana + a.indirme)
            self.assertNotIn("-p", a.ana + a.indirme)

    @unittest.skipUnless(os.path.isfile(MOTOR), "motor derlenmemis")
    def test_bayraklar_ciadpi_help_ciktisinda_var(self):
        yardim = subprocess.run([MOTOR, "--help"], capture_output=True, text=True, timeout=10)
        metin = yardim.stdout + yardim.stderr
        for a in strateji.ADAYLAR:
            for x in a.ana + a.indirme:
                if x.startswith("-"):
                    bayrak = x.split("=", 1)[0]
                    self.assertRegex(metin, r"(^|[\s,])" + re.escape(bayrak) + r"([\s,]|$)", f"{a.ad}: {bayrak}")


class Secim(unittest.TestCase):
    def test_ilk_gecen_secilir_sonrakiler_denenmez(self):
        denenen = []

        def dene(exe, aday):
            denenen.append(aday.ad)
            return [("gateway", 200 if aday.ad == "readme-ornek" else None, "")], aday.ad == "readme-ornek"

        s = strateji.sec("x", dene=dene, yaz=lambda *_: None)
        self.assertEqual(s.ad, "readme-ornek")
        self.assertEqual(denenen, ["oob-8s", "readme-ornek"])

    def test_hicbiri_gecmezse_none(self):
        s = strateji.sec("x", dene=lambda e, a: ([("gateway", None, "x")], False), yaz=lambda *_: None)
        self.assertIsNone(s)

    def test_aday_dene_gateway_200_sart(self):
        class SahteMotor:
            def __init__(self, exe, ek):
                pass

            def __enter__(self):
                return 1

            def __exit__(self, *_):
                pass

        eski = strateji.GeciciMotor
        strateji.GeciciMotor = SahteMotor
        try:
            kodlar = {"discord.com": 200, "cdn.discordapp.com": 403, "dl.discordapp.net": 301}
            _, gecti = strateji.aday_dene("x", strateji.VARSAYILAN, olcer=lambda h, y, s: (kodlar[h], ""))
            self.assertTrue(gecti)
            kodlar["discord.com"] = 403
            sonuc, gecti = strateji.aday_dene("x", strateji.VARSAYILAN, olcer=lambda h, y, s: (kodlar[h], ""))
            self.assertFalse(gecti)
            self.assertEqual(len(sonuc), 2, "gateway gecmezse indirme olculmez")
            kodlar["discord.com"] = 200
            kodlar["dl.discordapp.net"] = None
            _, gecti = strateji.aday_dene("x", strateji.VARSAYILAN, olcer=lambda h, y, s: (kodlar[h], ""))
            self.assertFalse(gecti)
        finally:
            strateji.GeciciMotor = eski

    def test_cli_motor_yoksa_hata(self):
        self.assertEqual(strateji.main(["sec", "--motor", os.path.join(KOK, "yok", "ciadpi")]), 1)


class Dosya(unittest.TestCase):
    def test_kaydet_oku_ayni(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "alt", "strateji.json")
            strateji.kaydet(yol, strateji.ADAYLAR[1])
            x = strateji.oku(yol)
            self.assertEqual((x.ana, x.indirme), (strateji.ADAYLAR[1].ana, strateji.ADAYLAR[1].indirme))
            self.assertFalse(os.path.exists(yol + ".yeni"))

    def test_bozuk_dosya_sessiz_varsayilana_dusmez(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "s.json")
            with self.assertRaises(strateji.StratejiHatasi):
                strateji.oku(yol)
            for v in ({"ana": [], "indirme": ["-o", "1"]}, {"ana": ["-o", "1"]},
                      {"ana": ["-o", "1"], "indirme": ["-i", "0.0.0.0"]}, {"ana": ["x"], "indirme": ["-o", "1"]}):
                with open(yol, "w", encoding="utf-8") as f:
                    json.dump(v, f)
                with self.assertRaises(strateji.StratejiHatasi, msg=v):
                    strateji.oku(yol)

    def test_plist_guncelle_yalniz_kuyrugu_degistirir(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "a.plist")
            with open(yol, "wb") as f:
                plistlib.dump({"Label": "x", "ProgramArguments": ["m", "-i", "127.0.0.1", "-p", "1080", "-o", "8+s"]}, f)
            strateji.plist_guncelle(yol, ("--tlsrec", "3+s"))
            with open(yol, "rb") as f:
                p = plistlib.load(f)
            self.assertEqual(p["ProgramArguments"], ["m", "-i", "127.0.0.1", "-p", "1080", "--tlsrec", "3+s"])
            self.assertEqual(p["Label"], "x")


class Socks(unittest.TestCase):
    def test_socks5_alan_adiyla_connect(self):
        srv = socket.create_server(("127.0.0.1", 0))
        alinan = {}

        def sunucu():
            c, _ = srv.accept()
            with c:
                alinan["selam"] = c.recv(3)
                c.sendall(b"\x05\x00")
                istek = c.recv(300)
                alinan["istek"] = istek
                c.sendall(b"\x05\x00\x00\x01" + bytes(4) + b"\x00\x00")
                alinan["veri"] = c.recv(10)

        t = threading.Thread(target=sunucu, daemon=True)
        t.start()
        s = strateji.socks5_baglan(srv.getsockname(), "discord.com", 443, 5)
        s.sendall(b"merhaba")
        t.join(5)
        s.close()
        srv.close()
        self.assertEqual(alinan["selam"], b"\x05\x01\x00")
        self.assertEqual(alinan["istek"], b"\x05\x01\x00\x03\x0bdiscord.com\x01\xbb")
        self.assertEqual(alinan["veri"], b"merhaba")

    def test_baglanti_yoksa_olc_none_doner(self):
        port = strateji.bos_port()
        kod, hata = strateji.olc("discord.com", "/", ("127.0.0.1", port), sure=1)
        self.assertIsNone(kod)
        self.assertTrue(hata)

    def test_tls_baglami_dogrulamali(self):
        ctx = strateji.tls_baglami()
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, strateji.ssl.CERT_REQUIRED)


class KurulumBaglantisi(unittest.TestCase):
    def oku(self, *yol):
        with open(os.path.join(KOK, *yol), encoding="utf-8") as f:
            return f.read()

    def test_windows_hizmeti_strateji_dosyasini_okur(self):
        self.assertIn("--strateji", self.oku("windows", "islevler.ps1"))
        self.assertIn("strateji.py", self.oku("windows", "kur.ps1"))

    def test_mac_plistleri_stratejiden_uretilir(self):
        s = self.oku("mac", "kur.sh")
        self.assertIn("strateji.py", s)
        self.assertNotIn("8+s", s)


if __name__ == "__main__":
    unittest.main()
