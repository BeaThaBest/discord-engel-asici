#!/usr/bin/env python3
"""alanlar.txt dosyasindan proxy.pac uretir. Discord disi her sey DIRECT."""
import argparse
import os

import importlib.util

_yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "connect-bridge.py")
_spec = importlib.util.spec_from_file_location("connect_bridge", _yol)
alan_secimi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(alan_secimi)


def uret(kayitlar):
    # En uzun desen once, boylece ozel alanlar genel alanlardan once eslesir.
    sirali = sorted(kayitlar, key=lambda k: -len(k[0]))
    satirlar = ["function FindProxyForURL(url, host) {"]
    for desen, port in sirali:
        donus = f'return "SOCKS5 127.0.0.1:{port}; SOCKS 127.0.0.1:{port}";'
        if "*" in desen:
            kosul = f'shExpMatch(host, "{desen}")'
        else:
            kosul = f'host === "{desen}" || dnsDomainIs(host, ".{desen}")'
        satirlar.append(f"    if ({kosul}) {donus}")
    satirlar.append('    return "DIRECT";')
    satirlar.append("}")
    return "\n".join(satirlar) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alanlar", default=alan_secimi.VARSAYILAN)
    ap.add_argument("--cikti", required=True)
    a = ap.parse_args()
    with open(a.cikti, "w", encoding="utf-8") as f:
        f.write(uret(alan_secimi.oku(a.alanlar)))


if __name__ == "__main__":
    main()
