# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: an · Volumen-0-Kerzen: frozen (entfernt: {'nq_5m': 1, 'nq_1m': 0, 'mes_5m': 2, 'mes_1m': 0, 'mgc_5m': 2, 'mgc_1m': 0}) · max. Kostenanteil: 0.1
Geschlossene Trades: 1046 · Summe: -20,885 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| crt_reclaim_mid | 412 | 48% | -0.16 | -0.25 … -0.06 | -11,816 | ROT |
| crt_reclaim_full | 426 | 43% | -0.11 | -0.22 … +0.01 | -8,910 | TENDENZ_MINUS |
| crt_retest_mid | 103 | 43% | -0.08 | -0.31 … +0.15 | -1,940 | TENDENZ_MINUS |
| crt_retest_full | 105 | 40% | +0.14 | -0.21 … +0.48 | 1,780 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| crt_reclaim_full | -0.08 | 204 | -0.13 | 222 |
| crt_reclaim_mid | -0.17 | 200 | -0.14 | 212 |
| crt_retest_full | -0.07 | 59 | +0.39 | 46 |
| crt_retest_mid | -0.24 | 58 | +0.12 | 45 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| crt_reclaim_full | CHOP | 36 | 44% | -0.16 | -0.50 … +0.19 | -798 | TENDENZ_MINUS |
| crt_reclaim_full | RANGE | 71 | 45% | -0.14 | -0.39 … +0.11 | -2,370 | TENDENZ_MINUS |
| crt_reclaim_full | TREND_HOCH | 91 | 46% | -0.04 | -0.29 … +0.21 | -916 | TENDENZ_MINUS |
| crt_reclaim_full | TREND_RUNTER | 93 | 41% | -0.02 | -0.30 … +0.26 | -662 | TENDENZ_MINUS |
| crt_reclaim_full | UEBERGANG | 135 | 42% | -0.18 | -0.36 … -0.00 | -4,163 | ROT |
| crt_reclaim_mid | CHOP | 33 | 55% | -0.12 | -0.42 … +0.17 | -646 | TENDENZ_MINUS |
| crt_reclaim_mid | RANGE | 67 | 45% | -0.28 | -0.49 … -0.08 | -3,620 | ROT |
| crt_reclaim_mid | TREND_HOCH | 92 | 48% | -0.12 | -0.33 … +0.09 | -2,125 | TENDENZ_MINUS |
| crt_reclaim_mid | TREND_RUNTER | 96 | 45% | -0.12 | -0.33 … +0.10 | -1,859 | TENDENZ_MINUS |
| crt_reclaim_mid | UEBERGANG | 124 | 50% | -0.16 | -0.32 … +0.00 | -3,566 | TENDENZ_MINUS |
| crt_retest_full | RANGE | 24 | 42% | -0.13 | -0.61 … +0.35 | -630 | TENDENZ_MINUS |
| crt_retest_full | TREND_HOCH | 20 | 40% | +0.03 | -0.61 … +0.68 | 241 | TENDENZ_PLUS |
| crt_retest_full | TREND_RUNTER | 25 | 44% | +0.80 | -0.28 … +1.88 | 3,084 | TENDENZ_PLUS |
| crt_retest_full | UEBERGANG | 29 | 38% | -0.00 | -0.52 … +0.51 | -273 | TENDENZ_MINUS |
| crt_retest_mid | RANGE | 24 | 42% | -0.31 | -0.66 … +0.04 | -1,310 | TENDENZ_MINUS |
| crt_retest_mid | TREND_HOCH | 20 | 45% | -0.06 | -0.55 … +0.43 | -138 | TENDENZ_MINUS |
| crt_retest_mid | TREND_RUNTER | 25 | 44% | +0.26 | -0.41 … +0.93 | 941 | TENDENZ_PLUS |
| crt_retest_mid | UEBERGANG | 27 | 44% | -0.09 | -0.47 … +0.30 | -687 | TENDENZ_MINUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **TREND_HOCH**: crt_retest_full (+0.03 R, n=20, TENDENZ_PLUS, A -0.14 / B +0.45, NICHT stabil)
- **TREND_RUNTER**: crt_retest_full (+0.80 R, n=25, TENDENZ_PLUS, A -0.32 / B +1.83, NICHT stabil), crt_retest_mid (+0.26 R, n=25, TENDENZ_PLUS, A -0.47 / B +0.93, NICHT stabil)

## Kausalitäts-Check (Fenster-Auswertung vs. Kerze für Kerze)

Abweichungen = Strategie liefert je nach Fensterlänge andere Signale (Lookahead oder Fenster-Effekt).

- nq: 80 Stichproben, keine Abweichungen
- mes: 80 Stichproben, keine Abweichungen
- mgc: 80 Stichproben, keine Abweichungen
