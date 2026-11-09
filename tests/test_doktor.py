"""Doktor (kontrol) komutu: GECTI/KALDI cikti bicimi, her KALDI icin oneri, ayar degistirmez."""
import contextlib
import io
import os
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "ortak"))
import doktor  # noqa: E402
import hosts_blok  # noqa: E402
import strateji  # noqa: E402


class Doktor(unittest.TestCase):
    def test_sekiz_madde_ve_her_birinin_onerisi_var(self):
        m = doktor.maddeler("/yok")
        self.assertEqual([x[0] for x in m], [
            "Hizmet calisiyor", "Yerel portlar", "PAC sunucusu", "Sistem PAC ayari", "hosts blogu",
            "Secili strateji", "Discord gateway 200", "Discord disi site 200"])
        for ad, kontrol, oneri in m:
            self.assertTrue(callable(kontrol), ad)
            self.assertTrue(oneri.strip(), ad)

    def test_klasor_yoksa_kaldi_ve_kur_onerisi(self):
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti):
            kod = doktor.main(["--app", os.path.join(KOK, "yok-boyle-klasor")])
        self.assertEqual(kod, 1)
        self.assertIn("[KALDI]", cikti.getvalue())
        self.assertIn(doktor.KUR, cikti.getvalue())

    def test_kontrol_hatasi_kaldi_sayilir_gizlenmez(self):
        eski = doktor.maddeler
        doktor.maddeler = lambda app: [("a", lambda: (True, "tamam"), "x"),
                                       ("b", lambda: 1 / 0, "bunu yap")]
        try:
            cikti = io.StringIO()
            with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(cikti):
                kod = doktor.main(["--app", d])
        finally:
            doktor.maddeler = eski
        metin = cikti.getvalue()
        self.assertEqual(kod, 1)
        self.assertIn("[GECTI] a: tamam", metin)
        self.assertIn("[KALDI] b: kontrol hatasi: ZeroDivisionError", metin)
        self.assertIn("Ne yapmali: bunu yap", metin)
        self.assertIn("Sonuc: 1/2 GECTI", metin)

    def test_strateji_dosyasi(self):
        with tempfile.TemporaryDirectory() as d:
            ok, _ = doktor.strateji_kontrol(d)
            self.assertFalse(ok)
            strateji.kaydet(os.path.join(d, "strateji.json"), strateji.VARSAYILAN)
            ok, ayrinti = doktor.strateji_kontrol(d)
            self.assertTrue(ok)
            self.assertIn("oob-8s", ayrinti)

    def test_hosts_blogu(self):
        eski = hosts_blok.varsayilan_hosts
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "hosts")
            hosts_blok.varsayilan_hosts = lambda: yol
            try:
                with open(yol, "wb") as f:
                    f.write(b"127.0.0.1 localhost\n")
                self.assertFalse(doktor.hosts_kontrol(d)[0])
                with open(yol, "wb") as f:
                    f.write(b"127.0.0.1 localhost\n" + hosts_blok.blok_olustur(["updates.discord.com"]))
                self.assertTrue(doktor.hosts_kontrol(d)[0])
            finally:
                hosts_blok.varsayilan_hosts = eski


if __name__ == "__main__":
    unittest.main()
