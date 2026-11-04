# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: an · Volumen-0-Kerzen: frozen (entfernt: {'nq_5m': 1, 'nq_1m': 0, 'mes_5m': 2, 'mes_1m': 0, 'mgc_5m': 2, 'mgc_1m': 0}) · max. Kostenanteil: 1.0
Geschlossene Trades: 1362 · Summe: -32,848 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| crt_reclaim_mid | 559 | 44% | -0.18 | -0.26 … -0.09 | -18,084 | ROT |
| crt_reclaim_full | 565 | 41% | -0.13 | -0.23 … -0.03 | -14,303 | ROT |
| crt_retest_mid | 118 | 42% | -0.08 | -0.29 … +0.14 | -2,109 | TENDENZ_MINUS |
| crt_retest_full | 120 | 40% | +0.11 | -0.20 … +0.42 | 1,647 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| crt_reclaim_full | -0.11 | 275 | -0.15 | 290 |
| crt_reclaim_mid | -0.19 | 277 | -0.16 | 282 |
| crt_retest_full | -0.05 | 65 | +0.30 | 55 |
| crt_retest_mid | -0.19 | 64 | +0.06 | 54 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| crt_reclaim_full | CHOP | 38 | 42% | -0.17 | -0.50 … +0.15 | -995 | TENDENZ_MINUS |
| crt_reclaim_full | RANGE | 121 | 39% | -0.28 | -0.46 … -0.10 | -6,962 | ROT |
| crt_reclaim_full | TREND_HOCH | 107 | 45% | +0.02 | -0.25 … +0.29 | 269 | TENDENZ_PLUS |
| crt_reclaim_full | TREND_RUNTER | 136 | 36% | -0.12 | -0.35 … +0.12 | -3,420 | TENDENZ_MINUS |
| crt_reclaim_full | UEBERGANG | 163 | 43% | -0.12 | -0.30 … +0.06 | -3,194 | TENDENZ_MINUS |
| crt_reclaim_mid | CHOP | 36 | 50% | -0.14 | -0.42 … +0.13 | -855 | TENDENZ_MINUS |
| crt_reclaim_mid | RANGE | 118 | 38% | -0.33 | -0.51 … -0.15 | -7,433 | ROT |
| crt_reclaim_mid | TREND_HOCH | 110 | 45% | -0.07 | -0.31 … +0.17 | -1,469 | TENDENZ_MINUS |
| crt_reclaim_mid | TREND_RUNTER | 140 | 39% | -0.20 | -0.38 … -0.02 | -5,086 | ROT |
| crt_reclaim_mid | UEBERGANG | 155 | 50% | -0.12 | -0.27 … +0.04 | -3,241 | TENDENZ_MINUS |
| crt_retest_full | RANGE | 29 | 38% | -0.12 | -0.57 … +0.33 | -721 | TENDENZ_MINUS |
| crt_retest_full | TREND_HOCH | 22 | 45% | +0.13 | -0.48 … +0.74 | 632 | TENDENZ_PLUS |
| crt_retest_full | TREND_RUNTER | 29 | 45% | +0.69 | -0.25 … +1.64 | 3,110 | TENDENZ_PLUS |
| crt_retest_full | UEBERGANG | 32 | 38% | -0.05 | -0.53 … +0.43 | -561 | TENDENZ_MINUS |
| crt_retest_mid | RANGE | 29 | 38% | -0.32 | -0.64 … -0.01 | -1,701 | ROT |
| crt_retest_mid | TREND_HOCH | 22 | 50% | +0.04 | -0.44 … +0.52 | 268 | TENDENZ_PLUS |
| crt_retest_mid | TREND_RUNTER | 29 | 45% | +0.27 | -0.33 … +0.88 | 1,205 | TENDENZ_PLUS |
| crt_retest_mid | UEBERGANG | 30 | 43% | -0.12 | -0.48 … +0.24 | -962 | TENDENZ_MINUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **TREND_HOCH**: crt_retest_full (+0.13 R, n=22, TENDENZ_PLUS, A -0.05 / B +0.74, NICHT stabil), crt_retest_mid (+0.04 R, n=22, TENDENZ_PLUS, A -0.08 / B +0.45, NICHT stabil), crt_reclaim_full (+0.02 R, n=107, TENDENZ_PLUS, A -0.11 / B +0.19, NICHT stabil)
- **TREND_RUNTER**: crt_retest_full (+0.69 R, n=29, TENDENZ_PLUS, A -0.22 / B +1.55, NICHT stabil), crt_retest_mid (+0.27 R, n=29, TENDENZ_PLUS, A -0.31 / B +0.81, NICHT stabil)
