import os
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORTAK = os.path.join(KOK, "ortak")
sys.path.insert(0, ORTAK)

import alanlar as kopru  # noqa: E402
import pac_uret as pac  # noqa: E402

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
        for k in KAYIT:
            self.assertIn(k.desen, cikti)
            if not k.hosts:
                self.assertIn(f"127.0.0.1:{k.port}", cikti)
        self.assertIn('return "DIRECT";', cikti)
        # Ozel alan genel alandan once gelmeli.
        self.assertLess(cikti.index('"dl.discordapp.net"'), cikti.index('"discordapp.net"'))

    def test_hosts_isareti(self):
        self.assertIn("updates.discord.com", kopru.hosts_adlari(KAYIT))
        self.assertEqual(kopru.dinleyici_port("updates.discord.com", KAYIT), 1080)
        self.assertEqual(kopru.dinleyici_port("UPDATES.Discord.com.", KAYIT), 1080)

    def test_hosts_tam_ad_sahte_sonek(self):
        # hosts satiri sonek degil: alt alan ve sahte onek dinleyiciye kabul edilmez.
        for h in ("a.updates.discord.com", "evilupdates.discord.com", "updates.discord.com.evil.org",
                  "discord.com", "cdn.discordapp.com"):
            self.assertIsNone(kopru.dinleyici_port(h, KAYIT), h)
        # PAC/SOCKS secimi alt ad icin discord.com sonegine duser.
        self.assertEqual(kopru.socks_port("a.updates.discord.com", KAYIT), 1080)
        self.assertIsNone(kopru.socks_port("updates.discord.com.evil.org", KAYIT))

    def test_hosts_satiri_glob_olamaz(self):
        with tempfile.TemporaryDirectory() as d:
            y = os.path.join(d, "a.txt")
            for kotu in ("*.ornek.com 1 hosts\n", "ornek.com 1 baska\n", "ornek.com 1 hosts x\n"):
                with open(y, "w") as f:
                    f.write(kotu)
                with self.assertRaises(ValueError):
                    kopru.oku(y)

    def test_pac_hosts_direct(self):
        cikti = pac.uret(KAYIT)
        self.assertIn('if (host === "updates.discord.com") return "DIRECT";', cikti)
        # En uzun eslesme: tam ad discord.com sonegi satirindan once gelir.
        self.assertLess(cikti.index('"updates.discord.com"'), cikti.index('".discord.com"'))

    def test_ozel_dosya(self):
        with tempfile.TemporaryDirectory() as d:
            y = os.path.join(d, "a.txt")
            with open(y, "w") as f:
                f.write("# yorum\nornek.com 1111\n")
            k = kopru.oku(y)
            self.assertEqual(kopru.socks_port("a.ornek.com", k), 1111)
            self.assertIsNone(kopru.socks_port("discord.com", k))
            self.assertIn("ornek.com", pac.uret(k))
            self.assertEqual([x.hosts for x in k], [False])


if __name__ == "__main__":
    unittest.main()
