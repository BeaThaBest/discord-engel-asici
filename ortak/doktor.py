#!/usr/bin/env python3
"""
Kurulum kontrolu (doktor). Mac: mac/kontrol.sh, Windows: windows\\kontrol.ps1 bunu cagirir.
Her madde GECTI ya da KALDI yazar; her KALDI icin tek satir ne yapilacagi.
Hicbir ayari degistirmez. Cikis: hepsi gectiyse 0, degilse 1.
Kullanim: python3 doktor.py --app <calisma klasoru>
Yalniz standart kutuphane.
"""
import argparse
import os
import socket
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alanlar  # noqa: E402
import hosts_blok  # noqa: E402
import strateji  # noqa: E402

PAC_PORT = 1099
SNI_PORT = 443
PAC_URL = f"http://127.0.0.1:{PAC_PORT}/proxy.pac"
MAC_AJANLAR = ("com.discord-engel-asici", "com.discord-engel-asici-dl", "com.discord-engel-asici-pac")
MAC_DAEMON = "/Library/LaunchDaemons/com.discord-engel-asici-sni.plist"
WIN_GOREV = "DiscordEngelAsici"
MAC = sys.platform == "darwin"

if MAC:
    KUR, YENIDEN, KAPAT_DIS = "mac/KUR.command", "mac/yeniden-ayarla.sh", "Cmd+Q"
else:
    KUR, YENIDEN, KAPAT_DIS = r"windows\KUR.cmd (sag tik, Yonetici olarak calistir)", \
        r"windows\YENIDEN-AYARLA.cmd", "tepsi ikonundan Cikis"


def _calistir(komut, sure=15):
    try:
        r = subprocess.run(komut, capture_output=True, text=True, timeout=sure,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError) as e:
        return -1, str(e)


def hizmet_kontrol():
    """(gecti, ayrinti)"""
    if MAC:
        _, cikti = _calistir(["launchctl", "list"])
        pidli = {p[2] for p in (s.split("\t") for s in cikti.splitlines()) if len(p) == 3 and p[0] != "-"}
        eksik = [a for a in MAC_AJANLAR if a not in pidli]
        if not os.path.exists(MAC_DAEMON):
            eksik.append("com.discord-engel-asici-sni (LaunchDaemon dosyasi)")
        return not eksik, "3 ajan calisiyor, 443 LaunchDaemon kurulu" if not eksik else "eksik: " + ", ".join(eksik)
    _, cikti = _calistir(["powershell.exe", "-NoProfile", "-Command",
                          f"(Get-ScheduledTask -TaskName {WIN_GOREV} -ErrorAction SilentlyContinue).State"])
    durum = cikti.strip() or "gorev yok"
    return durum == "Running", f"gorev {WIN_GOREV}: {durum}"


def socks_yanitliyor(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2) as s:
            s.settimeout(2)
            s.sendall(b"\x05\x01\x00")
            return s.recv(2) == b"\x05\x00"
    except OSError:
        return False


def tcp_acik(port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=2).close()
        return True
    except OSError:
        return False


def port_kontrol():
    durum = {1080: socks_yanitliyor(1080), 1091: socks_yanitliyor(1091),
             PAC_PORT: tcp_acik(PAC_PORT), SNI_PORT: tcp_acik(SNI_PORT)}
    kapali = [str(p) for p, v in durum.items() if not v]
    return not kapali, "1080, 1091, 1099, 443 dinliyor" if not kapali else "yanit vermeyen: " + ", ".join(kapali)


def pac_sunucu_kontrol():
    try:
        with socket.create_connection(("127.0.0.1", PAC_PORT), timeout=3) as s:
            s.settimeout(3)
            s.sendall(b"GET /proxy.pac HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
            veri = b""
            while len(veri) < 65536:
                p = s.recv(4096)
                if not p:
                    break
                veri += p
        ok = b" 200 " in veri.split(b"\r\n", 1)[0] and b"FindProxyForURL" in veri
        return ok, "proxy.pac sunuluyor" if ok else "proxy.pac yaniti gecersiz"
    except OSError as e:
        return False, f"PAC sunucusuna baglanilamadi: {e}"


def pac_ayar_kontrol():
    if MAC:
        _, cikti = _calistir(["networksetup", "-listallnetworkservices"])
        acik = []
        for s in cikti.splitlines()[1:]:
            if not s or s.startswith("*"):
                continue
            _, c = _calistir(["networksetup", "-getautoproxyurl", s])
            if f"URL: {PAC_URL}" in c and "Enabled: Yes" in c:
                acik.append(s)
        return bool(acik), ("acik: " + ", ".join(acik)) if acik else "hicbir ag hizmetinde acik degil"
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as k:
            deger = winreg.QueryValueEx(k, "AutoConfigURL")[0]
    except OSError:
        deger = None
    return deger == PAC_URL, f"AutoConfigURL = {deger or 'yok'}"


def hosts_kontrol(app):
    yol = hosts_blok.varsayilan_hosts()
    try:
        with open(yol, "rb") as f:
            veri = f.read()
    except OSError as e:
        return False, f"{yol} okunamadi: {e}"
    alan_yolu = _alanlar_yolu(app)
    adlar = alanlar.hosts_adlari(alanlar.oku(alan_yolu))
    if hosts_blok.BASLA not in veri:
        return False, "hosts dosyasinda bizim blok yok"
    eksik = [a for a in adlar if f"127.0.0.1 {a}".encode() not in veri]
    return not eksik, ("blok var: " + ", ".join(adlar)) if not eksik else "blokta eksik: " + ", ".join(eksik)


def _alanlar_yolu(app):
    for y in (os.path.join(app, "alanlar.txt"), os.path.join(app, "ortak", "alanlar.txt")):
        if os.path.exists(y):
            return y
    return alanlar.VARSAYILAN


def strateji_kontrol(app):
    try:
        a = strateji.oku(os.path.join(app, "strateji.json"))
    except strateji.StratejiHatasi as e:
        return False, str(e)
    return True, f"{a.ad}: ana {' '.join(a.ana)} | indirme {' '.join(a.indirme)}"


def gateway_kontrol():
    kod, hata = strateji.olc(*strateji.GATEWAY, socks=("127.0.0.1", strateji.ANA_PORT))
    return kod == 200, f"discord.com/api/v9/gateway (1080 uzerinden): {kod or '000'} {hata}".rstrip()


def discord_disi_kontrol():
    kod, hata = strateji.olc(*strateji.DISCORD_DISI)
    return kod == 200, f"https://{strateji.DISCORD_DISI[0]}/ dogrudan: {kod or '000'} {hata}".rstrip()


def maddeler(app):
    """[(ad, kontrol, oneri)] sirayla."""
    return [
        ("Hizmet calisiyor", hizmet_kontrol,
         f"Kurulumu yeniden calistir: {KUR}. Bilgisayari yeni actiysan 1 dakika bekleyip tekrar kontrol et."),
        ("Yerel portlar", port_kontrol,
         f"Kurulumu yeniden calistir: {KUR}. 443 doluysa onu kullanan programi (VMware, IIS, Skype) kapat."),
        ("PAC sunucusu", pac_sunucu_kontrol, f"Kurulumu yeniden calistir: {KUR}."),
        ("Sistem PAC ayari", pac_ayar_kontrol,
         f"Gecici kapattiysan ac betigini calistir, degilse kurulumu yeniden calistir: {KUR}."),
        ("hosts blogu", lambda: hosts_kontrol(app), f"Kurulumu yeniden calistir: {KUR} (yonetici izni ister)."),
        ("Secili strateji", lambda: strateji_kontrol(app),
         f"Stratejiyi yeniden sec: {YENIDEN}. Kurulum bu ozellikten eskiyse once {KUR}."),
        ("Discord gateway 200", gateway_kontrol,
         f"Stratejiyi yeniden sec: {YENIDEN}. Yine olmazsa saglayici IP ya da DNS engeli uyguluyor olabilir."),
        ("Discord disi site 200", discord_disi_kontrol,
         "Internet baglantini kontrol et; bu madde bizim sistemden bagimsizdir, kapatip deneyebilirsin."),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Discord Engel Asici kontrol")
    ap.add_argument("--app", required=True, help="calisma klasoru")
    a = ap.parse_args(argv)
    print("Discord Engel Asici kontrol")
    print(f"Klasor: {a.app}")
    if not os.path.isdir(a.app):
        print(f"[KALDI] Kurulum klasoru yok.\n        Ne yapmali: Kur: {KUR}")
        return 1
    gecen = 0
    liste = maddeler(a.app)
    for ad, kontrol, oneri in liste:
        try:
            ok, ayrinti = kontrol()
        except Exception as e:  # kontrol kendisi hata verirse KALDI say, gizleme
            ok, ayrinti = False, f"kontrol hatasi: {type(e).__name__}: {e}"
        print(f"[{'GECTI' if ok else 'KALDI'}] {ad}: {ayrinti}")
        if ok:
            gecen += 1
        else:
            print(f"        Ne yapmali: {oneri}")
    print(f"Sonuc: {gecen}/{len(liste)} GECTI")
    if gecen == len(liste):
        print(f"Her sey yolunda. Discord acilmiyorsa onu tamamen kapatip ({KAPAT_DIS}) yeniden ac.")
    return 0 if gecen == len(liste) else 1


if __name__ == "__main__":
    sys.exit(main())
