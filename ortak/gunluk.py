"""Ortak log kurulumu. Boyut sinirli dosya, varsayilan duzey WARNING (yalniz hatalar)."""
import logging
import logging.handlers
import os
import sys

# Log boyut siniri: 1 MB x (1 + 2 yedek). Bakim istemez.
LOG_BOYUT = 1_000_000
LOG_YEDEK = 2
log = logging.getLogger("discord-engel-asici")


def gunluk_kur(yol=None, ayrinti=False):
    """Logu kurar. yol verilirse boyut sinirli dosya, yoksa stderr.
    Varsayilan duzey WARNING: her baglanti degil, yalniz hatalar yazilir."""
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    if yol:
        os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
        h = logging.handlers.RotatingFileHandler(
            yol, maxBytes=LOG_BOYUT, backupCount=LOG_YEDEK, encoding="utf-8")
    elif sys.stderr is not None:
        h = logging.StreamHandler(sys.stderr)
    else:  # pythonw: stderr yok
        h = logging.NullHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.DEBUG if ayrinti else logging.WARNING)
    log.propagate = False
    return h
