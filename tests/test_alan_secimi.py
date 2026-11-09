import importlib.util
import os
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORTAK = os.path.join(KOK, "ortak")


def yukle(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(ORTAK, dosya))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


kopru = yukle("kopru", "connect-bridge.py")
pac = yukle("pac", "pac_uret.py")
KAYIT = kopru.oku(os.path.join(ORTAK, "alanlar.txt"))


class AlanSecimi(unittest.TestCase):
    def p(self, h):
        return kopru.socks_port(h, KAYIT)

    def test_discord_ana_port(self):
        self.assertEqual(self.p("discord.com"), 1080)
        self.assertEqual(self.p("gateway.discord.gg"), 1080)
        self.assertEqual(self.p("cdn.discordapp.com"), 1080)

    def test_indirme_portu(self):
        self.assertEqual(self.p("dl.discordapp.net"), 1091)
        self.assertEqual(self.p("dl2.discordapp.net"), 1091)
        self.assertEqual(self.p("x.dl2.discordapp.net"), 1091)
        self.assertEqual(self.p("a.dl2-3.discordapp.net"), 1091)
        self.assertEqual(self.p("media.discordapp.net"), 1080)

    def test_discord_degil(self):
        for h in ("google.com", "evildiscord.com", "discord.com.evil.org",
                  "notdiscordapp.net", "fakediscord.gg"):
            self.assertIsNone(self.p(h), h)

    def test_bicim(self):
        self.assertEqual(self.p("DISCORD.COM"), 1080)
        self.assertEqual(self.p("discord.com."), 1080)
        self.assertEqual(self.p("discord.com:443"), 1080)
        self.assertEqual(self.p("DL.Discordapp.net.:443"), 1091)
        self.assertIsNone(self.p("evildiscord.com:443"))

    def test_pac_ayni_liste(self):
        cikti = pac.uret(KAYIT)
        for desen, port in KAYIT:
            self.assertIn(desen, cikti)
            self.assertIn(f"127.0.0.1:{port}", cikti)
        self.assertIn('return "DIRECT";', cikti)
        # Ozel alan genel alandan once gelmeli.
        self.assertLess(cikti.index('"dl.discordapp.net"'), cikti.index('"discordapp.net"'))

    def test_ozel_dosya(self):
        with tempfile.TemporaryDirectory() as d:
            y = os.path.join(d, "a.txt")
            with open(y, "w") as f:
                f.write("# yorum\nornek.com 1111\n")
            k = kopru.oku(y)
            self.assertEqual(kopru.socks_port("a.ornek.com", k), 1111)
            self.assertIsNone(kopru.socks_port("discord.com", k))
            self.assertIn("ornek.com", pac.uret(k))


if __name__ == "__main__":
    unittest.main()
