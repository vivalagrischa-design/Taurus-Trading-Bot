# TAURUS Backtest

Daten: yahoo · 2026-08-25 bis 2026-11-03 · Märkte: nq, mes, mgc
Geschlossene Trades: 24253 · Summe: -540,243 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| rsi_ema | 2 | 0% | -1.00 | -1.00 … -1.00 | -305 | ZU_WENIG |
| rosi_new_york | 46 | 17% | -0.51 | -0.85 … -0.17 | -4,076 | ROT |
| opening_reversal | 9 | 33% | -0.21 | -0.98 … +0.57 | -291 | ZU_WENIG |
| orb | 73 | 34% | -0.19 | -0.47 … +0.09 | -2,667 | TENDENZ_MINUS |
| omar_v2_volume_retest | 8 | 38% | -0.17 | -1.04 … +0.69 | -290 | ZU_WENIG |
| rev_bounce | 3029 | 32% | -0.16 | -0.21 … -0.11 | -87,971 | ROT |
| rev_engulfing_confirmed | 1145 | 37% | -0.15 | -0.22 … -0.09 | -31,739 | ROT |
| rev_engulfing | 2746 | 38% | -0.15 | -0.20 … -0.10 | -72,078 | ROT |
| rev_bounce_confirmed | 2630 | 36% | -0.15 | -0.19 … -0.10 | -70,945 | ROT |
| rev_pinbar_confirmed | 606 | 36% | -0.14 | -0.24 … -0.05 | -15,512 | ROT |
| opening_drop | 11 | 36% | -0.14 | -0.85 … +0.57 | -177 | ZU_WENIG |
| trend_pullback | 430 | 41% | -0.13 | -0.25 … -0.02 | -9,846 | ROT |
| rev_exhaustion | 3628 | 38% | -0.12 | -0.16 … -0.08 | -80,482 | ROT |
| rosi_frankfurt | 28 | 32% | -0.12 | -0.73 … +0.49 | -960 | TENDENZ_MINUS |
| rev_pinbar | 3115 | 38% | -0.12 | -0.18 … -0.07 | -70,944 | ROT |
| bb_only_long | 72 | 40% | -0.12 | -0.39 … +0.15 | -1,436 | TENDENZ_MINUS |
| rev_exhaustion_confirmed | 3372 | 38% | -0.11 | -0.16 … -0.07 | -70,955 | ROT |
| bb_reversal_long | 71 | 45% | -0.08 | -0.35 … +0.18 | -978 | TENDENZ_MINUS |
| bb_only_short | 55 | 38% | -0.08 | -0.41 … +0.24 | -888 | TENDENZ_MINUS |
| trend_pullback_mtf | 559 | 43% | -0.05 | -0.15 … +0.05 | -4,543 | TENDENZ_MINUS |
| rosi_london | 22 | 45% | -0.04 | -0.51 … +0.43 | -16 | TENDENZ_MINUS |
| ema20 | 1181 | 45% | -0.03 | -0.10 … +0.03 | -7,136 | TENDENZ_MINUS |
| omar | 1362 | 42% | -0.03 | -0.09 … +0.04 | -6,282 | TENDENZ_MINUS |
| bb_reversal_short | 53 | 45% | +0.03 | -0.30 … +0.36 | 275 | TENDENZ_PLUS |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | RANGE | 10 | 30% | -0.27 | -1.05 … +0.51 | -447 | ZU_WENIG |
| bb_only_long | TREND_RUNTER | 40 | 48% | +0.08 | -0.31 … +0.46 | 587 | TENDENZ_PLUS |
| bb_only_long | UEBERGANG | 17 | 29% | -0.54 | -0.93 … -0.16 | -1,631 | ZU_WENIG |
| bb_only_short | TREND_HOCH | 26 | 31% | -0.14 | -0.63 … +0.35 | -701 | TENDENZ_MINUS |
| bb_only_short | UEBERGANG | 14 | 21% | -0.49 | -1.07 … +0.09 | -1,291 | ZU_WENIG |
| bb_reversal_long | TREND_RUNTER | 42 | 50% | -0.04 | -0.37 … +0.30 | -147 | TENDENZ_MINUS |
| bb_reversal_long | UEBERGANG | 17 | 29% | -0.40 | -0.86 … +0.05 | -1,237 | ZU_WENIG |
| bb_reversal_short | TREND_HOCH | 26 | 42% | -0.01 | -0.47 … +0.46 | -51 | TENDENZ_MINUS |
| bb_reversal_short | UEBERGANG | 14 | 43% | -0.11 | -0.73 … +0.52 | -298 | ZU_WENIG |
| ema20 | CHOP | 160 | 44% | -0.05 | -0.24 … +0.14 | -1,515 | TENDENZ_MINUS |
| ema20 | RANGE | 355 | 45% | -0.07 | -0.19 … +0.05 | -4,225 | TENDENZ_MINUS |
| ema20 | TREND_HOCH | 150 | 37% | -0.15 | -0.34 … +0.05 | -4,200 | TENDENZ_MINUS |
| ema20 | TREND_RUNTER | 197 | 48% | +0.04 | -0.13 … +0.22 | 1,731 | TENDENZ_PLUS |
| ema20 | UEBERGANG | 319 | 47% | +0.02 | -0.12 … +0.15 | 1,072 | TENDENZ_PLUS |
| omar | CHOP | 129 | 41% | -0.05 | -0.26 … +0.15 | -591 | TENDENZ_MINUS |
| omar | RANGE | 345 | 41% | -0.10 | -0.22 … +0.03 | -5,758 | TENDENZ_MINUS |
| omar | TREND_HOCH | 216 | 38% | -0.10 | -0.26 … +0.06 | -3,768 | TENDENZ_MINUS |
| omar | TREND_RUNTER | 321 | 50% | +0.18 | +0.04 … +0.32 | 10,105 | GRUEN |
| omar | UEBERGANG | 351 | 40% | -0.09 | -0.21 … +0.04 | -6,269 | TENDENZ_MINUS |
| orb | CHOP | 25 | 24% | -0.49 | -0.88 … -0.10 | -1,979 | ROT |
| orb | TREND_HOCH | 11 | 18% | -0.52 | -1.15 … +0.12 | -997 | ZU_WENIG |
| orb | UEBERGANG | 25 | 44% | +0.06 | -0.48 … +0.61 | 81 | TENDENZ_PLUS |
| rev_bounce_confirmed | CHOP | 148 | 42% | -0.02 | -0.22 … +0.18 | -312 | TENDENZ_MINUS |
| rev_bounce_confirmed | RANGE | 632 | 35% | -0.18 | -0.27 … -0.09 | -20,645 | ROT |
| rev_bounce_confirmed | TREND_HOCH | 507 | 41% | -0.00 | -0.11 … +0.11 | -374 | TENDENZ_MINUS |
| rev_bounce_confirmed | TREND_RUNTER | 617 | 30% | -0.32 | -0.41 … -0.24 | -35,658 | ROT |
| rev_bounce_confirmed | UEBERGANG | 726 | 37% | -0.10 | -0.19 … -0.01 | -13,957 | ROT |
| rev_bounce | CHOP | 159 | 33% | -0.10 | -0.30 … +0.10 | -2,445 | TENDENZ_MINUS |
| rev_bounce | RANGE | 634 | 29% | -0.24 | -0.33 … -0.15 | -27,215 | ROT |
| rev_bounce | TREND_HOCH | 662 | 37% | -0.01 | -0.11 … +0.09 | -1,206 | TENDENZ_MINUS |
| rev_bounce | TREND_RUNTER | 767 | 28% | -0.30 | -0.43 … -0.17 | -42,289 | ROT |
| rev_bounce | UEBERGANG | 807 | 34% | -0.10 | -0.19 … -0.01 | -14,817 | ROT |
| rev_engulfing_confirmed | CHOP | 70 | 41% | -0.15 | -0.41 … +0.11 | -1,735 | TENDENZ_MINUS |
| rev_engulfing_confirmed | RANGE | 324 | 35% | -0.17 | -0.30 … -0.05 | -9,682 | ROT |
| rev_engulfing_confirmed | TREND_HOCH | 209 | 39% | -0.08 | -0.25 … +0.08 | -3,438 | TENDENZ_MINUS |
| rev_engulfing_confirmed | TREND_RUNTER | 250 | 37% | -0.17 | -0.32 … -0.03 | -7,497 | ROT |
| rev_engulfing_confirmed | UEBERGANG | 292 | 36% | -0.17 | -0.30 … -0.03 | -9,388 | ROT |
| rev_engulfing | CHOP | 216 | 40% | -0.20 | -0.35 … -0.05 | -7,858 | ROT |
| rev_engulfing | RANGE | 737 | 36% | -0.16 | -0.24 … -0.07 | -21,593 | ROT |
| rev_engulfing | TREND_HOCH | 456 | 38% | -0.13 | -0.23 … -0.02 | -9,583 | ROT |
| rev_engulfing | TREND_RUNTER | 606 | 38% | -0.18 | -0.30 … -0.05 | -15,613 | ROT |
| rev_engulfing | UEBERGANG | 731 | 39% | -0.12 | -0.21 … -0.03 | -17,431 | ROT |
| rev_exhaustion_confirmed | CHOP | 181 | 44% | -0.02 | -0.20 … +0.16 | -438 | TENDENZ_MINUS |
| rev_exhaustion_confirmed | RANGE | 689 | 36% | -0.17 | -0.25 … -0.08 | -20,396 | ROT |
| rev_exhaustion_confirmed | TREND_HOCH | 684 | 40% | -0.02 | -0.12 … +0.07 | -3,403 | TENDENZ_MINUS |
| rev_exhaustion_confirmed | TREND_RUNTER | 869 | 35% | -0.22 | -0.30 … -0.13 | -34,615 | ROT |
| rev_exhaustion_confirmed | UEBERGANG | 949 | 39% | -0.07 | -0.15 … +0.01 | -12,103 | TENDENZ_MINUS |
| rev_exhaustion | CHOP | 185 | 48% | +0.04 | -0.13 … +0.22 | 1,370 | TENDENZ_PLUS |
| rev_exhaustion | RANGE | 707 | 34% | -0.22 | -0.30 … -0.14 | -27,160 | ROT |
| rev_exhaustion | TREND_HOCH | 797 | 40% | -0.03 | -0.12 … +0.06 | -4,521 | TENDENZ_MINUS |
| rev_exhaustion | TREND_RUNTER | 955 | 35% | -0.23 | -0.30 … -0.15 | -40,058 | ROT |
| rev_exhaustion | UEBERGANG | 984 | 40% | -0.06 | -0.13 … +0.02 | -10,113 | TENDENZ_MINUS |
| rev_pinbar_confirmed | CHOP | 34 | 26% | -0.41 | -0.75 … -0.07 | -2,318 | ROT |
| rev_pinbar_confirmed | RANGE | 146 | 37% | -0.14 | -0.33 … +0.05 | -3,424 | TENDENZ_MINUS |
| rev_pinbar_confirmed | TREND_HOCH | 106 | 39% | -0.10 | -0.33 … +0.14 | -2,013 | TENDENZ_MINUS |
| rev_pinbar_confirmed | TREND_RUNTER | 147 | 32% | -0.27 | -0.46 … -0.08 | -7,001 | ROT |
| rev_pinbar_confirmed | UEBERGANG | 173 | 40% | -0.02 | -0.20 … +0.17 | -756 | TENDENZ_MINUS |
| rev_pinbar | CHOP | 263 | 38% | -0.09 | -0.24 … +0.06 | -3,519 | TENDENZ_MINUS |
| rev_pinbar | RANGE | 837 | 38% | -0.10 | -0.18 … -0.02 | -15,577 | ROT |
| rev_pinbar | TREND_HOCH | 566 | 36% | -0.16 | -0.25 … -0.06 | -16,316 | ROT |
| rev_pinbar | TREND_RUNTER | 669 | 37% | -0.24 | -0.41 … -0.06 | -29,358 | ROT |
| rev_pinbar | UEBERGANG | 780 | 42% | -0.03 | -0.12 … +0.05 | -6,174 | TENDENZ_MINUS |
| rosi_frankfurt | RANGE | 13 | 38% | -0.08 | -0.92 … +0.77 | -325 | ZU_WENIG |
| rosi_new_york | TREND_HOCH | 11 | 0% | -1.00 | -1.00 … -1.00 | -1,919 | ZU_WENIG |
| rosi_new_york | UEBERGANG | 15 | 27% | -0.31 | -0.97 … +0.36 | -988 | ZU_WENIG |
| trend_pullback_mtf | CHOP | 53 | 38% | -0.26 | -0.60 … +0.08 | -1,768 | TENDENZ_MINUS |
| trend_pullback_mtf | RANGE | 164 | 46% | -0.06 | -0.24 … +0.12 | -1,805 | TENDENZ_MINUS |
| trend_pullback_mtf | TREND_HOCH | 81 | 37% | -0.09 | -0.36 … +0.18 | -1,254 | TENDENZ_MINUS |
| trend_pullback_mtf | TREND_RUNTER | 125 | 48% | +0.05 | -0.17 … +0.27 | 1,044 | TENDENZ_PLUS |
| trend_pullback_mtf | UEBERGANG | 136 | 40% | -0.04 | -0.25 … +0.17 | -760 | TENDENZ_MINUS |
| trend_pullback | CHOP | 49 | 43% | -0.24 | -0.64 … +0.17 | -2,127 | TENDENZ_MINUS |
| trend_pullback | RANGE | 181 | 42% | -0.13 | -0.30 … +0.04 | -4,318 | TENDENZ_MINUS |
| trend_pullback | TREND_HOCH | 52 | 31% | -0.16 | -0.49 … +0.17 | -1,882 | TENDENZ_MINUS |
| trend_pullback | TREND_RUNTER | 54 | 43% | -0.06 | -0.40 … +0.28 | -179 | TENDENZ_MINUS |
| trend_pullback | UEBERGANG | 94 | 41% | -0.10 | -0.34 … +0.13 | -1,340 | TENDENZ_MINUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20)

- **CHOP**: rev_exhaustion (+0.04 R, n=185, TENDENZ_PLUS)
- **TREND_RUNTER**: omar (+0.18 R, n=321, GRUEN), bb_only_long (+0.08 R, n=40, TENDENZ_PLUS), trend_pullback_mtf (+0.05 R, n=125, TENDENZ_PLUS), ema20 (+0.04 R, n=197, TENDENZ_PLUS)
- **UEBERGANG**: orb (+0.06 R, n=25, TENDENZ_PLUS), ema20 (+0.02 R, n=319, TENDENZ_PLUS)

## Kausalitäts-Check (Fenster-Auswertung vs. Kerze für Kerze)

Abweichungen = Strategie liefert je nach Fensterlänge andere Signale (Lookahead oder Fenster-Effekt).

- nq: 80 Stichproben, Abweichungen: trend_pullback_mtf (nur Backtest 0, nur live 1, gleich 3), omar_v2_volume_retest (nur Backtest 0, nur live 1, gleich 0)
- mes: 80 Stichproben, Abweichungen: trend_pullback_mtf (nur Backtest 0, nur live 1, gleich 3)
- mgc: 80 Stichproben, keine Abweichungen
