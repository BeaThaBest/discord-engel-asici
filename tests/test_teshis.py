"""Teshis edilebilirlik: kur, kaldir, kontrol ve yeniden ayarla her calismada tam ciktiyi
bir log dosyasina yazar; hata olursa pencere kapanmadan adim, hata ve log yolu gorunur.
Neden: UAC ile acilan yukseltilmis pencere hata verip kapaniyordu, mesaj okunamiyordu."""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
WIN = KOK / "windows"
MAC = KOK / "mac"
ISLER = ("kur", "kaldir", "kontrol", "yeniden-ayarla")
CMD = {"kur": "KUR.cmd", "kaldir": "KALDIR.cmd", "kontrol": "KONTROL.cmd", "yeniden-ayarla": "YENIDEN-AYARLA.cmd"}


def oku(p):
    return p.read_text(encoding="utf-8")


class WindowsGunluk(unittest.TestCase):
    def test_her_betik_gunluk_tutar(self):
        for ad in ISLER:
            s = oku(WIN / f"{ad}.ps1")
            self.assertIn("islevler.ps1", s, ad)
            self.assertRegex(s, r"Gunluk-Yolu '" + re.escape(ad) + "'", ad)
            self.assertIn("Gunluk-Baslat", s, ad)

    def test_kaldirma_gunlugu_silinen_klasorde_degil(self):
        # kaldir.ps1 %LOCALAPPDATA%\DiscordEngelAsici'yi siler; acik transcript silmeyi engeller.
        self.assertIn("Gunluk-Yolu 'kaldir' -Gecici", oku(WIN / "kaldir.ps1"))

    def test_gunluk_yolu_tek_kaynak(self):
        s = oku(WIN / "islevler.ps1")
        self.assertIn("function Gunluk-Yolu", s)
        self.assertIn("Join-Path $APP 'log'", s)
        self.assertIn("Start-Transcript", s)
        for ad in ISLER:
            self.assertNotIn("Start-Transcript", oku(WIN / f"{ad}.ps1"), ad)

    def test_uac_cocugu_ayni_gunluge_yazar(self):
        for ad in ("kur", "kaldir"):
            s = oku(WIN / f"{ad}.ps1")
            self.assertIn("[string]$Gunluk", s, ad)
            self.assertRegex(s, r"-Gunluk \"\{0\}\"", ad)

    def test_hata_penceresi_enter_bekler_basari_beklemez(self):
        isl = oku(WIN / "islevler.ps1")
        self.assertRegex(isl, r"function Hata-Bildir[\s\S]*?Read-Host")
        self.assertRegex(isl, r"function Hata-Bildir[\s\S]*?\$script:ADIM")
        for ad in ("kur", "kaldir"):
            s = oku(WIN / f"{ad}.ps1")
            self.assertNotIn("Start-Sleep -Seconds 20", s, ad)
            self.assertRegex(s, r"Hata-Bildir [^\n]*\$Gunluk \$Yukseltildi", ad)

    def test_adim_numarasi_izlenir(self):
        s = oku(WIN / "kur.ps1")
        adimlar = re.findall(r"^\s*Adim '(\d)/8'", s, re.M)
        self.assertEqual(adimlar, [str(i) for i in range(1, 9)])
        self.assertNotRegex(s, r"Write-Host '\d/8")

    def test_yerel_program_ciktisi_gunluge_duser(self):
        # PowerShell 5.1 transcript'i dogrudan konsola yazan yerel programin ciktisini almaz.
        s = oku(WIN / "islevler.ps1")
        self.assertIn("function Yerel-Calistir", s)
        self.assertNotIn("& $pb[0] @a", s)
        self.assertNotRegex(s, r"strateji\.py'\) sec [^\n]*\| Write-Host")

    def test_cmd_hatada_enter_bekler(self):
        for ad, dosya in CMD.items():
            s = oku(WIN / dosya)
            self.assertIn("set KOD=%ERRORLEVEL%", s, dosya)
            hata = s.split(":hata", 1)
            self.assertEqual(len(hata), 2, dosya)
            self.assertIn("pause", hata[1], dosya)
            self.assertNotIn("timeout", hata[1], dosya)
            self.assertIn("exit /b %KOD%", hata[1], dosya)


class MacGunluk(unittest.TestCase):
    def test_her_betik_gunluk_tutar(self):
        for ad in ISLER:
            s = oku(MAC / f"{ad}.sh")
            self.assertRegex(s, r"gunluk_baslat " + re.escape(ad) + r" ", ad)

    def test_kaldirma_gunlugu_silinen_klasorde_degil(self):
        s = oku(MAC / "kaldir.sh")
        satir = [x for x in s.splitlines() if x.startswith("gunluk_baslat")][0]
        self.assertNotIn("$APP", satir)

    def test_kur_adimlari_izlenir(self):
        s = oku(MAC / "kur.sh")
        self.assertEqual(re.findall(r'^adim "(\d)/9"', s, re.M), [str(i) for i in range(1, 10)])
        # Ayri EXIT trap'i gunluk_bitis'i ezer.
        self.assertNotIn("trap 'rm -rf", s)

    @unittest.skipUnless(sys.platform == "darwin", "mac/hizmetler.sh yalniz macOS icin")
    def test_hata_adimi_ve_log_yolu_yazilir(self):
        with tempfile.TemporaryDirectory() as d:
            betik = Path(d) / "b.sh"
            betik.write_text(
                '#!/bin/bash\nset -euo pipefail\n. "$1/hizmetler.sh"\n'
                'gunluk_baslat deneme "$2/log"\nadim "1/2" "Bir"\necho ekran-satiri\n'
                'echo hata-satiri >&2\nadim "2/2" "Iki"\nfalse\n', encoding="utf-8")
            r = subprocess.run(["bash", str(betik), str(MAC), d], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(r.returncode, 0)
            loglar = list((Path(d) / "log").glob("deneme-*.log"))
            self.assertEqual(len(loglar), 1)
            for _ in range(50):  # tee arka planda yazar
                icerik = loglar[0].read_text(encoding="utf-8")
                if "HATA" in icerik:
                    break
                subprocess.run(["sleep", "0.1"])
            for parca in ("ekran-satiri", "hata-satiri", "2/2 Iki", "HATA: adim 2/2", str(loglar[0])):
                self.assertIn(parca, icerik)
                self.assertIn(parca, r.stdout)


if __name__ == "__main__":
    unittest.main()
