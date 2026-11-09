import os
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORTAK = os.path.join(KOK, "ortak")
sys.path.insert(0, ORTAK)

import hosts_blok as hb  # noqa: E402

ADLAR = ["updates.discord.com", "b.discord.com"]
ORNEK = b"127.0.0.1\tlocalhost\n255.255.255.255\tbroadcasthost\n::1             localhost\n# yorum \xc3\xa7\n"


class HostsBlok(unittest.TestCase):
    def test_ekle_blok_icerigi(self):
        s = hb.ekle(ORNEK, ADLAR)
        self.assertTrue(s.startswith(ORNEK))
        ek = s[len(ORNEK):].decode()
        self.assertEqual(ek.splitlines(), [
            "# >>> DiscordEngelAsici >>>",
            "127.0.0.1 updates.discord.com", "::1 updates.discord.com",
            "127.0.0.1 b.discord.com", "::1 b.discord.com",
            "# <<< DiscordEngelAsici <<<"])

    def test_iki_kez_ekle_tek_blok(self):
        bir = hb.ekle(ORNEK, ADLAR)
        iki = hb.ekle(bir, ADLAR)
        self.assertEqual(bir, iki)
        self.assertEqual(iki.count(hb.BASLA), 1)

    def test_guncelle_yerinde(self):
        ara = ORNEK + hb.blok_olustur(["eski.discord.com"]) + b"10.0.0.1 sonraki\n"
        yeni = hb.ekle(ara, ADLAR)
        self.assertNotIn(b"eski.discord.com", yeni)
        self.assertEqual(yeni.count(hb.BASLA), 1)
        self.assertTrue(yeni.startswith(ORNEK + hb.BASLA))
        self.assertTrue(yeni.endswith(hb.BITIS + b"\n10.0.0.1 sonraki\n"))

    def test_kaldir_aynen_geri(self):
        self.assertEqual(hb.kaldir(hb.ekle(ORNEK, ADLAR)), ORNEK)
        ara = ORNEK + hb.blok_olustur(ADLAR) + b"10.0.0.1 sonraki\n"
        self.assertEqual(hb.kaldir(ara), ORNEK + b"10.0.0.1 sonraki\n")

    def test_blok_yokken_kaldir_noop(self):
        self.assertIs(hb.kaldir(ORNEK), ORNEK)
        self.assertEqual(hb.kaldir(b""), b"")

    def test_crlf_korunur(self):
        crlf = ORNEK.replace(b"\n", b"\r\n")
        s = hb.ekle(crlf, ADLAR)
        self.assertTrue(s.startswith(crlf))
        self.assertEqual(s.count(b"\r\n"), crlf.count(b"\r\n") + 6)
        self.assertEqual(s.count(b"\n"), s.count(b"\r\n"))
        self.assertEqual(hb.ekle(s, ADLAR), s)
        self.assertEqual(hb.kaldir(s), crlf)

    def test_karisik_satir_sonu_diger_satirlar_bayt_bayt(self):
        karisik = b"a\r\nb\nc\r\n"
        s = hb.ekle(karisik, ADLAR)
        self.assertEqual(hb.kaldir(s), karisik)

    def test_sonda_satir_sonu_yoksa(self):
        s = hb.ekle(b"1.1.1.1 x", ADLAR)
        self.assertTrue(s.startswith(b"1.1.1.1 x\n" + hb.BASLA))

    def test_bos_dosya(self):
        s = hb.ekle(b"", ADLAR)
        self.assertTrue(s.startswith(hb.BASLA))
        self.assertEqual(hb.kaldir(s), b"")

    def test_ad_listesi_bos_blogu_kaldirir(self):
        self.assertEqual(hb.ekle(hb.ekle(ORNEK, ADLAR), []), ORNEK)

    def test_gecersiz_ad_reddedilir(self):
        for kotu in ("a b", "x\n127.0.0.1 evil", "", "-a.com"):
            with self.assertRaises(ValueError):
                hb.ekle(ORNEK, [kotu])

    def test_bitisi_olmayan_blok_dokunmaz(self):
        bozuk = ORNEK + hb.BASLA + b"\n127.0.0.1 x\n"
        with self.assertRaises(ValueError):
            hb.ekle(bozuk, ADLAR)
        with self.assertRaises(ValueError):
            hb.kaldir(bozuk)


class Cli(unittest.TestCase):
    def test_yaz_kaldir_ve_yedek(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "hosts")
            al = os.path.join(d, "alanlar.txt")
            with open(yol, "wb") as f:
                f.write(ORNEK)
            with open(al, "w") as f:
                f.write("discord.com 1080\nx.discord.com 1080 hosts\ny.discord.com 1091 hosts\n")
            self.assertEqual(hb.main(["yaz", "--hosts", yol, "--alanlar", al]), 0)
            with open(yol, "rb") as f:
                yazilan = f.read()
            self.assertIn(b"127.0.0.1 x.discord.com", yazilan)
            self.assertIn(b"::1 y.discord.com", yazilan)
            yedek = yol + hb.YEDEK_SONEK
            with open(yedek, "rb") as f:
                self.assertEqual(f.read(), ORNEK)
            # Ikinci yazim yedegi ezmez (yedek ozgun dosyadir).
            al2 = os.path.join(d, "a2.txt")
            with open(al2, "w") as f:
                f.write("z.discord.com 1080 hosts\n")
            self.assertEqual(hb.main(["yaz", "--hosts", yol, "--alanlar", al2]), 0)
            with open(yedek, "rb") as f:
                self.assertEqual(f.read(), ORNEK)
            self.assertEqual(hb.main(["kaldir", "--hosts", yol]), 0)
            with open(yol, "rb") as f:
                self.assertEqual(f.read(), ORNEK)

    def test_cikti_secenegi_hostsa_dokunmaz(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "hosts")
            cikti = os.path.join(d, "yeni")
            with open(yol, "wb") as f:
                f.write(ORNEK)
            self.assertEqual(hb.main(["yaz", "--hosts", yol, "--cikti", cikti]), 0)
            with open(yol, "rb") as f:
                self.assertEqual(f.read(), ORNEK)
            self.assertFalse(os.path.exists(yol + hb.YEDEK_SONEK))
            with open(cikti, "rb") as f:
                self.assertIn(b"updates.discord.com", f.read())

    def test_hosts_yoksa_olusturur(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "hosts")
            self.assertEqual(hb.main(["yaz", "--hosts", yol]), 0)
            self.assertTrue(os.path.exists(yol))


if __name__ == "__main__":
    unittest.main()
