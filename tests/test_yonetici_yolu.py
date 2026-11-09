"""Regresyon: root yetki adimi repo icinden (TCC korumali ~/Desktop) calistirilmamali."""
import re
import unittest
from pathlib import Path

MAC = Path(__file__).resolve().parent.parent / "mac"


class YoneticiYoluTest(unittest.TestCase):
    def _cagrilar(self, ad):
        s = (MAC / ad).read_text(encoding="utf-8")
        return s, re.findall(r'"([^"\n]*)/yonetici\.sh"\s+(?:kur|kaldir)', s)

    def test_kur_ve_kaldir_temp_kopyayi_cagirir(self):
        for ad in ("kur.sh", "kaldir.sh"):
            s, yollar = self._cagrilar(ad)
            self.assertTrue(yollar, ad)
            for y in yollar:
                self.assertEqual(y, "$TMP", f"{ad}: repo yolu ({y}) yetki adimina verilmis")
            self.assertIn('cp "$MAC/yonetici.sh" "$TMP/yonetici.sh"', s)
            self.assertIn('chmod 700 "$TMP"', s)
            self.assertIn('chmod 700 "$TMP/yonetici.sh"', s)

    def test_yonetici_kardes_dosya_okumaz(self):
        s = (MAC / "yonetici.sh").read_text(encoding="utf-8")
        self.assertNotIn("dirname", s.replace('SELF="$(cd "$(dirname "$0")"', ""))


if __name__ == "__main__":
    unittest.main()
