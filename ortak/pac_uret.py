#!/usr/bin/env python3
"""alanlar.txt dosyasindan proxy.pac uretir. Discord disi her sey DIRECT.
hosts isaretli tam adlar da DIRECT doner: hosts dosyasi onlari yerel SNI dinleyiciye
cevirir, SOCKS'a verilirse ByeDPI sistem cozucuyle 127.0.0.1'e doner."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alanlar  # noqa: E402


def uret(kayitlar):
    # En uzun desen once, boylece ozel alanlar genel alanlardan once eslesir.
    sirali = sorted(kayitlar, key=lambda k: (-len(k.desen), not k.hosts))
    satirlar = ["function FindProxyForURL(url, host) {"]
    for k in sirali:
        if k.hosts:
            satirlar.append(f'    if (host === "{k.desen}") return "DIRECT";')
            continue
        donus = f'return "SOCKS5 127.0.0.1:{k.port}; SOCKS 127.0.0.1:{k.port}";'
        if "*" in k.desen:
            kosul = f'shExpMatch(host, "{k.desen}")'
        else:
            kosul = f'host === "{k.desen}" || dnsDomainIs(host, ".{k.desen}")'
        satirlar.append(f"    if ({kosul}) {donus}")
    satirlar.append('    return "DIRECT";')
    satirlar.append("}")
    return "\n".join(satirlar) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alanlar", default=alanlar.VARSAYILAN)
    ap.add_argument("--cikti", required=True)
    a = ap.parse_args()
    with open(a.cikti, "w", encoding="utf-8") as f:
        f.write(uret(alanlar.oku(a.alanlar)))


if __name__ == "__main__":
    main()
