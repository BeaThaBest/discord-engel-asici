"""
Alan listesi (alanlar.txt) okuma ve alan secimi. Tek kaynak, PAC ureticisi, SNI dinleyici
ve hizmet bunu kullanir. Yalniz standart kutuphane.

Satir bicimi: <alan> <socks_port> [hosts]
  * Isaretsiz satir: sonek (ya da "*" iceren glob) eslesmesi, en uzun satir kazanir.
  * "hosts" isaretli satir: TAM ad. hosts dosyasina yazilir, PAC'te DIRECT doner ve
    yerel 443 SNI dinleyici yalniz bu adlari kabul eder.
"""
import fnmatch
import os
import re
from collections import namedtuple

VARSAYILAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alanlar.txt")
Kayit = namedtuple("Kayit", "desen port hosts")
_TAM_AD = re.compile(r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$")


def oku(yol=VARSAYILAN):
    """alanlar.txt dosyasini [Kayit(desen, port, hosts)] listesi olarak dondurur."""
    kayitlar = []
    with open(yol, encoding="utf-8") as f:
        for no, satir in enumerate(f, 1):
            satir = satir.split("#", 1)[0].strip()
            if not satir:
                continue
            parca = satir.split()
            if len(parca) not in (2, 3) or (len(parca) == 3 and parca[2] != "hosts"):
                raise ValueError(f"{yol}:{no}: gecersiz satir: {satir!r}")
            desen = parca[0].lower()
            hosts = len(parca) == 3
            if hosts and not _TAM_AD.match(desen):
                raise ValueError(f"{yol}:{no}: hosts satiri tam ad olmali: {desen!r}")
            kayitlar.append(Kayit(desen, int(parca[1]), hosts))
    return kayitlar


def host_temizle(host):
    h = host.strip().lower()
    if h.startswith("[") and "]" in h:
        return h[1:h.index("]")]
    if h.count(":") == 1:
        h = h.split(":", 1)[0]
    return h.rstrip(".")


def _eslesir(kayit, host):
    if kayit.hosts:
        return host == kayit.desen
    if "*" in kayit.desen:
        return fnmatch.fnmatchcase(host, kayit.desen)
    return host == kayit.desen or host.endswith("." + kayit.desen)


def sec(host, kayitlar):
    """En uzun eslesen Kayit, yoksa None. Esit uzunlukta hosts satiri once gelir."""
    h = host_temizle(host)
    en_iyi = None
    for k in kayitlar:
        if _eslesir(k, h) and (en_iyi is None or (len(k.desen), k.hosts) > (len(en_iyi.desen), en_iyi.hosts)):
            en_iyi = k
    return en_iyi


def socks_port(host, kayitlar):
    """Discord alani ise en uzun eslesen satirin portu, degilse None (DIRECT)."""
    k = sec(host, kayitlar)
    return k.port if k else None


def dinleyici_port(host, kayitlar):
    """SNI dinleyici icin: yalniz hosts isaretli TAM adlar. Port ya da None (reddet)."""
    h = host_temizle(host)
    for k in kayitlar:
        if k.hosts and k.desen == h:
            return k.port
    return None


def hosts_adlari(kayitlar):
    """hosts isaretli adlar, dosya sirasiyla, tekrarsiz."""
    adlar = []
    for k in kayitlar:
        if k.hosts and k.desen not in adlar:
            adlar.append(k.desen)
    return adlar
