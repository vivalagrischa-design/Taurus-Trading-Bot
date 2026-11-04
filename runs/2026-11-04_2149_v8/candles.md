# TAURUS Kerzen-Studie (5M)

Daten: cache · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc · 40776 Kerzen

Messung: Einstieg nächste Kerze (Open). Was kommt zuerst innerhalb 1 Stunde: +1 ATR oder −1 ATR? p_up/p_down = Anteil. Bei 50 % hat ein Muster keine Richtung. Netto-R = Erwartung bei Stop = Ziel = 1 ATR nach Kommission und Slippage. Basis = alle Kerzen derselben Marktlage. „Schlägt Basis“ = unteres 95%-KI über der Basisrate.

## Basisraten je Marktlage (alle Kerzen)

| Marktlage | n | p_up | p_down | Kosten R |
|---|---|---|---|---|
| ALLE | 38738 | 47.4% | 51.7% | 0.114 |
| CHOP | 3055 | 45.5% | 53.5% | 0.067 |
| RANGE | 11266 | 48.5% | 50.6% | 0.142 |
| TREND_HOCH | 6889 | 48.1% | 50.8% | 0.113 |
| TREND_RUNTER | 7869 | 46.1% | 53.1% | 0.098 |
| UEBERGANG | 9659 | 47.3% | 51.8% | 0.109 |

## Höchste Trefferquoten (n ≥ 100)

| Marktlage | Muster | n | Richtung | Trefferquote | KI | vs. Basis | Netto-R | Hälfte A / B | stabil | schlägt Basis |
|---|---|---|---|---|---|---|---|---|---|---|
| TREND_RUNTER | bull_engulfing | 478 | SHORT | 58.4% | 54–63% | +5.3 Pkt | +0.066 | +0.09 / +0.04 | ja | ja |
| TREND_HOCH | three_down | 568 | SHORT | 57.6% | 53–62% | +6.7 Pkt | +0.046 | -0.05 / +0.16 | nein | ja |
| UEBERGANG | outside_bar_down | 498 | SHORT | 56.4% | 52–61% | +4.6 Pkt | +0.027 | -0.01 / +0.06 | nein | ja |
| TREND_RUNTER | bull_marubozu | 227 | SHORT | 56.4% | 50–63% | +3.3 Pkt | +0.029 | +0.01 / +0.04 | ja | nein |
| TREND_HOCH | bull_marubozu | 286 | LONG | 56.3% | 50–62% | +8.2 Pkt | +0.010 | +0.03 / -0.02 | nein | ja |
| CHOP | inside_bar | 343 | SHORT | 56.3% | 51–61% | +2.8 Pkt | +0.061 | +0.02 / +0.08 | ja | nein |
| TREND_HOCH | big_range_up | 123 | SHORT | 56.1% | 47–65% | +5.2 Pkt | +0.016 | -0.09 / +0.14 | nein | nein |
| TREND_RUNTER | hammer | 642 | SHORT | 56.1% | 52–60% | +3.0 Pkt | +0.024 | -0.00 / +0.05 | nein | nein |
| CHOP | doji | 289 | SHORT | 56.1% | 50–62% | +2.6 Pkt | +0.052 | +0.11 / +0.01 | ja | nein |
| CHOP | outside_bar_up | 139 | SHORT | 55.4% | 47–63% | +1.9 Pkt | +0.043 | +0.17 / -0.05 | nein | nein |
| TREND_RUNTER | outside_bar_up | 349 | SHORT | 55.3% | 50–60% | +2.2 Pkt | +0.015 | -0.01 / +0.04 | nein | nein |
| CHOP | close_at_high | 172 | SHORT | 55.2% | 48–62% | +1.8 Pkt | +0.035 | +0.16 / -0.08 | nein | nein |
| TREND_RUNTER | close_at_high | 465 | SHORT | 54.2% | 50–59% | +1.1 Pkt | -0.012 | -0.01 / -0.02 | nein | nein |
| RANGE | shooting_star | 779 | SHORT | 54.2% | 51–58% | +3.6 Pkt | -0.071 | -0.03 / -0.11 | nein | ja |
| UEBERGANG | hammer | 720 | SHORT | 54.2% | 51–58% | +2.4 Pkt | -0.033 | -0.07 / +0.00 | nein | nein |
| CHOP | bear_engulfing | 220 | SHORT | 54.1% | 47–61% | +0.6 Pkt | +0.012 | -0.11 / +0.11 | nein | nein |
| CHOP | close_at_low | 176 | LONG | 54.0% | 47–61% | +8.5 Pkt | +0.018 | -0.04 / +0.07 | nein | ja |
| TREND_RUNTER | shooting_star | 486 | SHORT | 53.7% | 49–58% | +0.6 Pkt | -0.030 | -0.10 / +0.04 | nein | nein |
| TREND_HOCH | hammer | 503 | SHORT | 53.7% | 49–58% | +2.8 Pkt | -0.045 | +0.01 / -0.10 | nein | nein |
| TREND_RUNTER | inside_bar | 972 | SHORT | 53.6% | 50–57% | +0.5 Pkt | -0.017 | -0.07 / +0.04 | nein | nein |
| ALLE | outside_bar_down | 1883 | SHORT | 53.4% | 51–56% | +1.7 Pkt | -0.035 | -0.09 / +0.02 | nein | nein |
| ALLE | hammer | 2966 | SHORT | 53.3% | 52–55% | +1.6 Pkt | -0.053 | -0.06 / -0.05 | nein | nein |
| UEBERGANG | bear_engulfing | 636 | SHORT | 53.1% | 49–57% | +1.3 Pkt | -0.050 | -0.07 / -0.03 | nein | nein |
| RANGE | outside_bar_down | 517 | SHORT | 53.0% | 49–57% | +2.4 Pkt | -0.062 | -0.09 / -0.03 | nein | nein |
| TREND_HOCH | bear_engulfing | 470 | LONG | 53.0% | 48–57% | +4.9 Pkt | -0.057 | -0.06 / -0.06 | nein | ja |
| CHOP | shooting_star | 187 | SHORT | 52.9% | 46–60% | -0.5 Pkt | -0.009 | +0.04 / -0.04 | nein | nein |
| TREND_RUNTER | doji | 769 | SHORT | 52.9% | 49–56% | -0.2 Pkt | -0.040 | -0.08 / -0.01 | nein | nein |
| RANGE | doji | 1034 | SHORT | 52.8% | 50–56% | +2.2 Pkt | -0.081 | -0.04 / -0.12 | nein | nein |
| ALLE | shooting_star | 2699 | SHORT | 52.8% | 51–55% | +1.1 Pkt | -0.068 | -0.08 / -0.06 | nein | nein |
| ALLE | three_down | 4099 | SHORT | 52.8% | 51–54% | +1.1 Pkt | -0.049 | -0.10 / +0.00 | nein | nein |
| RANGE | big_range_up | 163 | LONG | 52.8% | 45–60% | +4.3 Pkt | -0.074 | -0.03 / -0.13 | nein | nein |
| UEBERGANG | three_down | 1111 | SHORT | 52.7% | 50–56% | +0.9 Pkt | -0.050 | -0.14 / +0.03 | nein | nein |
| UEBERGANG | inside_bar | 1130 | SHORT | 52.7% | 50–56% | +0.9 Pkt | -0.048 | -0.01 / -0.09 | nein | nein |
| TREND_HOCH | inside_bar | 789 | SHORT | 52.6% | 49–56% | +1.7 Pkt | -0.051 | -0.06 / -0.04 | nein | nein |
| ALLE | inside_bar | 4519 | SHORT | 52.6% | 51–54% | +0.9 Pkt | -0.054 | -0.06 / -0.05 | nein | nein |
| ALLE | doji | 3552 | SHORT | 52.5% | 51–54% | +0.8 Pkt | -0.062 | -0.05 / -0.07 | nein | nein |
| CHOP | hammer | 221 | SHORT | 52.5% | 46–59% | -1.0 Pkt | -0.018 | -0.03 / -0.01 | nein | nein |
| RANGE | big_range_down | 107 | LONG | 52.3% | 43–62% | +3.9 Pkt | -0.086 | -0.05 / -0.11 | nein | nein |
| TREND_RUNTER | outside_bar_down | 413 | SHORT | 52.3% | 47–57% | -0.8 Pkt | -0.049 | -0.16 / +0.08 | nein | nein |
| UEBERGANG | three_up | 1069 | SHORT | 52.3% | 49–55% | +0.5 Pkt | -0.053 | +0.02 / -0.11 | nein | nein |

## Kandidaten mit positivem Netto-R, stabil in beiden Hälften und besser als die Basis

- TREND_RUNTER · bull_engulfing → SHORT: Netto +0.066 R, n=478

Höchste gemessene Trefferquote eines Musters mit n ≥ 100: 58.4%.
