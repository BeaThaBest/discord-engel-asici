"""
hosts dosyasini ATLAYAN IPv4 (A) cozucu. Sistem cozucusu hosts yuzunden 127.0.0.1 dondurur,
SNI dinleyicinin gercek adrese ihtiyaci var.
  * Mac ve Linux: /etc/resolv.conf (yoksa `scutil --dns`) nameserver'larina dogrudan UDP sorgusu.
  * Windows: dnsapi.DnsQuery_W, DNS_QUERY_NO_HOSTS_FILE | DNS_QUERY_BYPASS_CACHE.
Cozucu bir fonksiyondur: cozucu(ad) -> ["93.184.216.34", ...], hata olursa OSError (DnsHata).
Yalniz standart kutuphane.
"""
import ipaddress
import re
import secrets
import socket
import struct
import subprocess
import sys
import threading
import time

TTL_EN_AZ = 10
TTL_EN_COK = 300


class DnsHata(OSError):
    pass


def sorgu_kur(ad, kimlik):
    """Tek soruluk A sorgusu paketi (RD bayragi acik)."""
    govde = b""
    for etiket in ad.rstrip(".").encode("ascii").split(b"."):
        if not 0 < len(etiket) <= 63:
            raise DnsHata(f"gecersiz ad: {ad!r}")
        govde += bytes([len(etiket)]) + etiket
    return struct.pack(">HHHHHH", kimlik, 0x0100, 1, 0, 0, 0) + govde + b"\x00" + struct.pack(">HH", 1, 1)


def _ad_oku(paket, poz):
    """(ad, sonraki_konum). Sikistirma isaretcilerini izler, dongu korumali."""
    etiketler = []
    sonraki = None
    atlama = 0
    while True:
        if poz >= len(paket):
            raise DnsHata("kesik paket")
        n = paket[poz]
        if n & 0xC0 == 0xC0:
            if poz + 1 >= len(paket):
                raise DnsHata("kesik isaretci")
            if sonraki is None:
                sonraki = poz + 2
            poz = ((n & 0x3F) << 8) | paket[poz + 1]
            atlama += 1
            if atlama > 32:
                raise DnsHata("isaretci dongusu")
        elif n == 0:
            return ".".join(etiketler).lower(), (sonraki if sonraki is not None else poz + 1)
        elif n & 0xC0:
            raise DnsHata("gecersiz etiket")
        else:
            if poz + 1 + n > len(paket):
                raise DnsHata("kesik etiket")
            etiketler.append(paket[poz + 1:poz + 1 + n].decode("ascii", "replace"))
            poz += 1 + n


def yanit_ayristir(paket, kimlik, ad):
    """(ipler, en_kucuk_ttl). Kimlik ya da soru uyusmazsa, rcode != 0 ya da A yoksa DnsHata."""
    if len(paket) < 12:
        raise DnsHata("kisa yanit")
    kim, bayrak, soru, cevap, _, _ = struct.unpack_from(">HHHHHH", paket, 0)
    if kim != kimlik or not bayrak & 0x8000:
        raise DnsHata("kimlik uyusmuyor")
    rcode = bayrak & 0xF
    if rcode != 0:
        raise DnsHata(f"dns rcode {rcode} ({ad})")
    poz = 12
    for _ in range(soru):
        qad, poz = _ad_oku(paket, poz)
        poz += 4
        if qad != ad.rstrip(".").lower():
            raise DnsHata("soru uyusmuyor")
    ipler = []
    ttl = None
    for _ in range(cevap):
        _, poz = _ad_oku(paket, poz)
        if poz + 10 > len(paket):
            raise DnsHata("kesik kayit")
        tur, sinif, t, uzun = struct.unpack_from(">HHIH", paket, poz)
        poz += 10
        if poz + uzun > len(paket):
            raise DnsHata("kesik veri")
        if tur == 1 and sinif == 1 and uzun == 4:
            ipler.append(socket.inet_ntoa(paket[poz:poz + 4]))
            ttl = t if ttl is None else min(ttl, t)
        poz += uzun
    if not ipler:
        raise DnsHata(f"A kaydi yok ({ad})")
    return ipler, ttl


def resolv_ayristir(metin):
    return re.findall(r"^\s*nameserver\s+(\S+)", metin, re.M)


def scutil_ayristir(metin):
    return re.findall(r"nameserver\[\d+\]\s*:\s*(\S+)", metin)


def sunucular_bul(resolv="/etc/resolv.conf"):
    """Nameserver listesi (sirayla, tekrarsiz). Bulunamazsa DnsHata."""
    liste = []
    try:
        with open(resolv, encoding="utf-8", errors="replace") as f:
            liste = resolv_ayristir(f.read())
    except OSError:
        pass
    if not liste and sys.platform == "darwin":
        try:
            cikti = subprocess.run(["/usr/sbin/scutil", "--dns"], capture_output=True, text=True,
                                   timeout=5).stdout
            liste = scutil_ayristir(cikti)
        except (OSError, subprocess.SubprocessError):
            pass
    liste = list(dict.fromkeys(liste))
    if not liste:
        raise DnsHata("nameserver bulunamadi")
    return liste


def _guvenli(ipler):
    """Dongu korumasi: loopback ve belirsiz adresler gercek adres degildir."""
    sonuc = []
    for ip in ipler:
        a = ipaddress.ip_address(ip)
        if not (a.is_loopback or a.is_unspecified):
            sonuc.append(ip)
    return sonuc


class UdpCozucu:
    """Dogrudan UDP A sorgusu. TTL onbellekli, birden cok sunucu, zaman asimli.
    sunucular: liste ya da cagrilabilir (onbellek kacirinca yeniden okunur).
    Sunucu ogesi "ip" ya da (ip, port)."""

    def __init__(self, sunucular=None, zaman_asimi=2.0, tur=2, saat=time.monotonic):
        self._sunucular = sunucular if sunucular is not None else sunucular_bul
        self.zaman_asimi = zaman_asimi
        self.tur = tur
        self._saat = saat
        self._onbellek = {}
        self._kilit = threading.Lock()

    def _liste(self):
        s = self._sunucular() if callable(self._sunucular) else self._sunucular
        return [(x, 53) if isinstance(x, str) else tuple(x) for x in s]

    def _sor(self, sunucu, ad):
        kimlik = secrets.randbits(16)
        paket = sorgu_kur(ad, kimlik)
        ai = socket.getaddrinfo(sunucu[0], sunucu[1], type=socket.SOCK_DGRAM)[0]
        s = socket.socket(ai[0], socket.SOCK_DGRAM)
        try:
            s.settimeout(self.zaman_asimi)
            s.connect(ai[4])  # baska kaynaktan gelen paketler cekirdekte elenir
            s.send(paket)
            son = self._saat() + self.zaman_asimi
            while True:
                kalan = son - self._saat()
                if kalan <= 0:
                    raise socket.timeout("dns zaman asimi")
                s.settimeout(kalan)
                yanit = s.recv(4096)
                if len(yanit) >= 2 and struct.unpack_from(">H", yanit)[0] == kimlik:
                    return yanit_ayristir(yanit, kimlik, ad)
        finally:
            s.close()

    def __call__(self, ad):
        ad = ad.rstrip(".").lower()
        simdi = self._saat()
        with self._kilit:
            kayit = self._onbellek.get(ad)
            if kayit and kayit[0] > simdi:
                return list(kayit[1])
        son_hata = DnsHata("sunucu yok")
        for _ in range(self.tur):
            for sunucu in self._liste():
                try:
                    ipler, ttl = self._sor(sunucu, ad)
                except (OSError, DnsHata) as e:
                    son_hata = e
                    continue
                ipler = _guvenli(ipler)
                if not ipler:
                    son_hata = DnsHata(f"yalniz loopback adres dondu ({ad})")
                    continue
                omur = min(max(ttl or 0, TTL_EN_AZ), TTL_EN_COK)
                with self._kilit:
                    self._onbellek[ad] = (self._saat() + omur, ipler)
                return list(ipler)
        raise DnsHata(f"{ad} cozulemedi: {son_hata}")


def windows_sorgu(ad):
    """(ipler, ttl). hosts dosyasi ve sistem DNS onbellegi atlanir."""
    import ctypes
    from ctypes import POINTER, Structure, byref, c_int, c_ubyte, c_uint32, c_ushort, c_void_p, c_wchar_p

    class DNS_RECORDW(Structure):
        pass

    DNS_RECORDW._fields_ = [
        ("pNext", POINTER(DNS_RECORDW)), ("pName", c_wchar_p),
        ("wType", c_ushort), ("wDataLength", c_ushort),
        ("Flags", c_uint32), ("dwTtl", c_uint32), ("dwReserved", c_uint32),
        ("Ip", c_ubyte * 4),  # DNS_A_DATA (A kaydi icin yeterli)
    ]
    DNS_TYPE_A = 1
    NO_HOSTS_FILE = 0x40
    BYPASS_CACHE = 0x8
    dnsapi = ctypes.WinDLL("dnsapi")
    sorgu = dnsapi.DnsQuery_W
    sorgu.argtypes = [c_wchar_p, c_ushort, c_uint32, c_void_p, POINTER(POINTER(DNS_RECORDW)), c_void_p]
    sorgu.restype = c_int
    sil = dnsapi.DnsRecordListFree
    sil.argtypes = [c_void_p, c_int]
    sil.restype = None
    liste = POINTER(DNS_RECORDW)()
    durum = sorgu(ad, DNS_TYPE_A, NO_HOSTS_FILE | BYPASS_CACHE, None, byref(liste), None)
    if durum != 0:
        raise DnsHata(f"DnsQuery_W hata {durum} ({ad})")
    ipler = []
    ttl = None
    try:
        k = liste
        while k:
            r = k.contents
            if r.wType == DNS_TYPE_A:
                ipler.append(".".join(str(b) for b in r.Ip))
                ttl = r.dwTtl if ttl is None else min(ttl, r.dwTtl)
            k = r.pNext
    finally:
        sil(ctypes.cast(liste, c_void_p), 1)  # DnsFreeRecordList
    if not ipler:
        raise DnsHata(f"A kaydi yok ({ad})")
    return ipler, ttl


class WindowsCozucu(UdpCozucu):
    """UdpCozucu ile ayni onbellek ve filtre, sorgu DnsQuery_W ile."""

    def __init__(self, saat=time.monotonic):
        super().__init__(sunucular=["-"], tur=1, saat=saat)

    def _sor(self, sunucu, ad):
        return windows_sorgu(ad)


def varsayilan_cozucu():
    if sys.platform == "win32":
        return WindowsCozucu()
    return UdpCozucu()
