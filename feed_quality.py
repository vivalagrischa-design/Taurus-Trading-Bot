"""Kerzen-Qualitaet fuer die verzoegerten Yahoo-Futures-Proxies.

Befund (Archive 28.10.-3.11.2026): rund 60 % der 1M-Kerzen und rund 13 % der
5M-Kerzen haben Volumen 0, tragen aber echte Preisbewegung (Yahoo meldet fuer
Futures oft kein Volumen). Nur ein Bruchteil ist wirklich eingefroren
(Volumen 0 UND Hoch = Tief), meist Platzhalter ausserhalb der Handelszeit.

Modi:
  frozen  (Standard) entfernt nur eingefrorene Kerzen: Volumen 0 und Hoch == Tief
  all     entfernt jede Kerze mit Volumen 0 (zerstoert echte Preisdaten, nur zum Vergleich)
  none    laesst alles drin
"""
import os

MODE = os.environ.get('TAURUS_ZERO_VOLUME', 'frozen')


def is_frozen(b):
    return not float(b.get('volume') or 0) and float(b['high']) == float(b['low'])


def clean(bars, mode=None):
    mode = mode or MODE
    if mode == 'none':
        return list(bars)
    if mode == 'all':
        return [b for b in bars if float(b.get('volume') or 0) > 0]
    return [b for b in bars if not is_frozen(b)]
