"""Regresyon: kapat.sh/ac.sh yarisi. bootout hemen doner ama ByeDPI birkac saniye yasar;
o sirada bootstrap 5 ile basarisiz olur. ac.sh bunu yutmamali, ortak islev beklemeli ve
YENI PID'in portu dinledigini dogrulamali. Sahte launchctl ve lsof ile calisir."""
import os
import re
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

MAC = Path(__file__).resolve().parent.parent / "mac"
ETIKET = "com.discord-engel-asici"

SAHTE_LAUNCHCTL = r"""#!/bin/bash
S="$DURUM"
case "$1" in
  list) cat "$S/list" 2>/dev/null; exit 0;;
  print) [ -e "$S/yuklu_${2##*/}" ]; exit $?;;
  bootout) rm -f "$S/yuklu_${2##*/}"; exit 0;;
  bootstrap)
    if [ -e "$S/bootstrap_hata" ]; then echo "Bootstrap failed: 5: Input/output error" >&2; exit 5; fi
    l="$(basename "$3" .plist)"; touch "$S/yuklu_$l"
    printf '%s\t0\t%s\n' "$(cat "$S/yeni_pid")" "$l" > "$S/list"
    [ -e "$S/yeni_port_sahibi" ] && cp "$S/yeni_port_sahibi" "$S/port"
    exit 0;;
esac
exit 0
"""
SAHTE_LSOF = r"""#!/bin/bash
cat "$DURUM/port" 2>/dev/null
exit 0
"""


class HizmetIslevleri(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bin = Path(self.tmp.name, "bin")
        self.durum = Path(self.tmp.name, "durum")
        self.bin.mkdir()
        self.durum.mkdir()
        for ad, icerik in (("launchctl", SAHTE_LAUNCHCTL), ("lsof", SAHTE_LSOF)):
            p = self.bin / ad
            p.write_text(icerik)
            p.chmod(0o755)

    def kos(self, govde, sure="6"):
        env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}", DURUM=str(self.durum),
                   HOME=self.tmp.name, DURMA_SURESI=sure, BASLAMA_SURESI=sure)
        betik = f'set -u\n. "{MAC}/hizmetler.sh"\n{govde}\n'
        return subprocess.run(["bash", "-c", betik], env=env, capture_output=True, text=True, timeout=30)

    def yaz(self, ad, deger):
        (self.durum / ad).write_text(deger)

    def test_bootstrap_hatasi_yutulmaz(self):
        self.yaz("bootstrap_hata", "")
        r = self.kos(f'hizmet_baslat {ETIKET} 1080 ""; echo "rc=$?"')
        self.assertIn("rc=1", r.stdout)
        self.assertIn("HATA", r.stderr)

    def test_eski_pid_portu_tutuyorsa_yalanci_yesil_yok(self):
        # bootstrap "basarili" ama listede ve portta hala eski PID var.
        self.yaz("yeni_pid", "111")
        self.yaz("port", "111\n")
        r = self.kos(f'hizmet_baslat {ETIKET} 1080 111; echo "rc=$?"', sure="2")
        self.assertIn("rc=1", r.stdout)
        self.assertIn("calismadi", r.stderr)

    def test_yeni_pid_portu_dinlerse_basarili(self):
        self.yaz("yeni_pid", "222")
        self.yaz("yeni_port_sahibi", "222\n")
        r = self.kos(f'hizmet_baslat {ETIKET} 1080 111; echo "rc=$?"')
        self.assertIn("rc=0", r.stdout, r.stderr)
        self.assertIn("PID 222", r.stdout)

    def test_durdur_eski_surecin_bitmesini_bekler(self):
        eski = subprocess.Popen(["sleep", "1.5"])
        self.addCleanup(eski.kill)
        # Cikinca hemen toplansin (zombi PID kill -0'a canli gorunur).
        threading.Thread(target=eski.wait, daemon=True).start()
        self.yaz("list", f"{eski.pid}\t0\t{ETIKET}\n")
        self.yaz(f"yuklu_{ETIKET}", "")
        bas = time.monotonic()
        r = self.kos(f'hizmet_durdur {ETIKET} 1080; echo "rc=$? eski=$HIZMET_ESKI_PID"', sure="10")
        eski.wait()
        self.assertIn(f"rc=0 eski={eski.pid}", r.stdout, r.stderr)
        self.assertGreaterEqual(time.monotonic() - bas, 1.0)

    def test_durdur_surec_olmezse_hata(self):
        self.yaz("port", "999\n")
        r = self.kos(f'hizmet_durdur {ETIKET} 1080; echo "rc=$?"', sure="2")
        self.assertIn("rc=1", r.stdout)
        self.assertIn("durmadi", r.stderr)


class BetikYapisi(unittest.TestCase):
    def oku(self, ad):
        return (MAC / ad).read_text(encoding="utf-8")

    def test_tek_kaynak(self):
        for ad in ("kur.sh", "ac.sh", "kapat.sh"):
            self.assertIn('. "$MAC/hizmetler.sh"', self.oku(ad), ad)
        tanimlar = [p.name for p in MAC.glob("*.sh") if re.search(r"^pid_of\(\)", p.read_text(encoding="utf-8"), re.M)]
        self.assertEqual(tanimlar, ["hizmetler.sh"])

    def test_ac_hata_yutmaz(self):
        s = self.oku("ac.sh")
        self.assertNotIn("|| true", s)
        self.assertNotRegex(s, r"bootstrap[^\n]*2>/dev/null")
        self.assertIn("hizmetleri_yeniden_yukle", s)

    def test_kapat_bekler(self):
        self.assertIn("hizmetleri_durdur", self.oku("kapat.sh"))

    def test_bootstrap_hatasi_hicbir_yerde_yutulmaz(self):
        for p in MAC.glob("*.sh"):
            self.assertNotRegex(p.read_text(encoding="utf-8"), r"launchctl bootstrap[^\n]*\|\| true", p.name)


if __name__ == "__main__":
    unittest.main()
