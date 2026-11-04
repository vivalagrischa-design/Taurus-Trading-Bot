# TAURUS Kerzen-Studie (5M)

Daten: cache · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc · 40410 Kerzen

Messung: Einstieg nächste Kerze (Open). Was kommt zuerst innerhalb 1 Stunde: +1 ATR oder −1 ATR? p_up/p_down = Anteil. Bei 50 % hat ein Muster keine Richtung. Netto-R = Erwartung bei Stop = Ziel = 1 ATR nach Kommission und Slippage. Basis = alle Kerzen derselben Marktlage. „Schlägt Basis“ = unteres 95%-KI über der Basisrate.

## Basisraten je Marktlage (alle Kerzen)

| Marktlage | n | p_up | p_down | Kosten R |
|---|---|---|---|---|
| ALLE | 38385 | 47.4% | 51.7% | 0.114 |
| CHOP | 2894 | 45.5% | 53.5% | 0.068 |
| RANGE | 11254 | 48.4% | 50.6% | 0.142 |
| TREND_HOCH | 6800 | 48.4% | 50.6% | 0.114 |
| TREND_RUNTER | 7862 | 46.0% | 53.1% | 0.098 |
| UEBERGANG | 9575 | 47.2% | 51.9% | 0.110 |

## Höchste Trefferquoten (n ≥ 100)

| Marktlage | Muster | n | Richtung | Trefferquote | KI | vs. Basis | Netto-R | Hälfte A / B | stabil | schlägt Basis |
|---|---|---|---|---|---|---|---|---|---|---|
| TREND_RUNTER | bull_engulfing | 478 | SHORT | 58.4% | 54–63% | +5.2 Pkt | +0.066 | +0.09 / +0.04 | ja | ja |
| TREND_HOCH | three_down | 563 | SHORT | 57.4% | 53–61% | +6.8 Pkt | +0.042 | -0.05 / +0.15 | nein | ja |
| TREND_RUNTER | bull_marubozu | 226 | SHORT | 56.6% | 50–63% | +3.5 Pkt | +0.034 | +0.01 / +0.05 | ja | nein |
| TREND_HOCH | big_range_up | 122 | SHORT | 56.6% | 48–65% | +6.0 Pkt | +0.025 | -0.09 / +0.16 | nein | nein |
| CHOP | inside_bar | 320 | SHORT | 56.2% | 51–62% | +2.8 Pkt | +0.060 | +0.02 / +0.09 | ja | nein |
| CHOP | close_at_high | 162 | SHORT | 56.2% | 48–64% | +2.7 Pkt | +0.053 | +0.16 / -0.06 | nein | nein |
| TREND_RUNTER | hammer | 641 | SHORT | 56.2% | 52–60% | +3.0 Pkt | +0.026 | -0.01 / +0.05 | nein | nein |
| UEBERGANG | outside_bar_down | 495 | SHORT | 56.2% | 52–60% | +4.3 Pkt | +0.022 | -0.01 / +0.05 | nein | nein |
| TREND_HOCH | bull_marubozu | 285 | LONG | 56.1% | 50–62% | +7.7 Pkt | +0.007 | +0.03 / -0.03 | nein | ja |
| CHOP | doji | 273 | SHORT | 56.0% | 50–62% | +2.6 Pkt | +0.052 | +0.11 / +0.01 | ja | nein |
| CHOP | outside_bar_up | 136 | SHORT | 55.9% | 47–64% | +2.4 Pkt | +0.052 | +0.17 / -0.04 | nein | nein |
| TREND_RUNTER | outside_bar_up | 347 | SHORT | 55.6% | 50–61% | +2.5 Pkt | +0.021 | -0.01 / +0.05 | nein | nein |
| UEBERGANG | hammer | 712 | SHORT | 54.6% | 51–58% | +2.8 Pkt | -0.025 | -0.06 / +0.01 | nein | nein |
| TREND_RUNTER | close_at_high | 464 | SHORT | 54.3% | 50–59% | +1.2 Pkt | -0.009 | -0.01 / -0.01 | nein | nein |
| RANGE | shooting_star | 779 | SHORT | 54.2% | 51–58% | +3.5 Pkt | -0.071 | -0.01 / -0.13 | nein | ja |
| CHOP | bear_engulfing | 206 | SHORT | 53.9% | 47–61% | +0.4 Pkt | +0.007 | -0.11 / +0.11 | nein | nein |
| TREND_RUNTER | shooting_star | 485 | SHORT | 53.8% | 49–58% | +0.7 Pkt | -0.028 | -0.10 / +0.04 | nein | nein |
| TREND_RUNTER | inside_bar | 971 | SHORT | 53.7% | 51–57% | +0.5 Pkt | -0.016 | -0.07 / +0.04 | nein | nein |
| CHOP | shooting_star | 176 | SHORT | 53.4% | 46–61% | -0.1 Pkt | -0.000 | +0.04 / -0.03 | nein | nein |
| TREND_HOCH | bear_engulfing | 465 | LONG | 53.3% | 49–58% | +4.9 Pkt | -0.051 | -0.06 / -0.04 | nein | ja |
| ALLE | hammer | 2927 | SHORT | 53.3% | 52–55% | +1.7 Pkt | -0.054 | -0.05 / -0.05 | nein | nein |
| ALLE | outside_bar_down | 1868 | SHORT | 53.3% | 51–56% | +1.7 Pkt | -0.038 | -0.08 / +0.02 | nein | nein |
| CHOP | close_at_low | 169 | LONG | 53.3% | 46–61% | +7.8 Pkt | +0.003 | -0.04 / +0.04 | nein | ja |
| UEBERGANG | bear_engulfing | 634 | SHORT | 53.2% | 49–57% | +1.3 Pkt | -0.050 | -0.07 / -0.03 | nein | nein |
| TREND_HOCH | hammer | 491 | SHORT | 53.0% | 49–57% | +2.4 Pkt | -0.061 | +0.01 / -0.14 | nein | nein |
| TREND_RUNTER | doji | 769 | SHORT | 52.9% | 49–56% | -0.2 Pkt | -0.040 | -0.08 / -0.01 | nein | nein |
| RANGE | outside_bar_down | 516 | SHORT | 52.9% | 49–57% | +2.3 Pkt | -0.064 | -0.09 / -0.04 | nein | nein |
| ALLE | shooting_star | 2677 | SHORT | 52.9% | 51–55% | +1.2 Pkt | -0.067 | -0.07 / -0.06 | nein | nein |
| UEBERGANG | three_down | 1102 | SHORT | 52.8% | 50–56% | +0.9 Pkt | -0.049 | -0.14 / +0.03 | nein | nein |
| RANGE | doji | 1034 | SHORT | 52.8% | 50–56% | +2.2 Pkt | -0.081 | -0.03 / -0.12 | nein | nein |
| ALLE | three_down | 4063 | SHORT | 52.8% | 51–54% | +1.1 Pkt | -0.049 | -0.10 / +0.00 | nein | nein |
| RANGE | big_range_up | 163 | LONG | 52.8% | 45–60% | +4.3 Pkt | -0.074 | -0.03 / -0.13 | nein | nein |
| UEBERGANG | inside_bar | 1122 | SHORT | 52.7% | 50–56% | +0.8 Pkt | -0.050 | -0.00 / -0.10 | nein | nein |
| CHOP | bear_marubozu | 114 | SHORT | 52.6% | 44–62% | -0.9 Pkt | -0.011 | +0.05 / -0.05 | nein | nein |
| ALLE | inside_bar | 4481 | SHORT | 52.5% | 51–54% | +0.9 Pkt | -0.055 | -0.06 / -0.05 | nein | nein |
| CHOP | bull_engulfing | 198 | SHORT | 52.5% | 46–59% | -1.0 Pkt | -0.025 | -0.05 / +0.00 | nein | nein |
| ALLE | doji | 3518 | SHORT | 52.5% | 51–54% | +0.8 Pkt | -0.063 | -0.05 / -0.08 | nein | nein |
| UEBERGANG | three_up | 1056 | SHORT | 52.5% | 49–55% | +0.6 Pkt | -0.051 | +0.01 / -0.10 | nein | nein |
| TREND_HOCH | inside_bar | 784 | SHORT | 52.4% | 49–56% | +1.9 Pkt | -0.054 | -0.06 / -0.04 | nein | nein |
| TREND_HOCH | three_up | 954 | LONG | 52.4% | 49–56% | +4.0 Pkt | -0.060 | -0.06 / -0.06 | nein | ja |

## Kandidaten mit positivem Netto-R, stabil in beiden Hälften und besser als die Basis

- TREND_RUNTER · bull_engulfing → SHORT: Netto +0.066 R, n=478

Höchste gemessene Trefferquote eines Musters mit n ≥ 100: 58.4%.
