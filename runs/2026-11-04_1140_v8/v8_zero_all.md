# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: an · Volumen-0-Kerzen: all (entfernt: {'nq_5m': 50, 'nq_1m': 28, 'mes_5m': 51, 'mes_1m': 29, 'mgc_5m': 48, 'mgc_1m': 28}) · max. Kostenanteil: 0.1
Geschlossene Trades: 2449 · Summe: -2,898 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| range_bb_reentry | 158 | 35% | -0.27 | -0.48 … -0.06 | -7,524 | ROT |
| imom_last30 | 87 | 38% | -0.12 | -0.28 … +0.04 | -1,382 | TENDENZ_MINUS |
| range_rsi2 | 494 | 48% | -0.11 | -0.20 … -0.03 | -9,484 | ROT |
| trend_ema_pullback | 338 | 41% | -0.02 | -0.16 … +0.11 | -405 | TENDENZ_MINUS |
| trend_breakout_1h | 587 | 44% | -0.01 | -0.11 … +0.09 | -572 | TENDENZ_MINUS |
| trend_pullback_mtf | 118 | 49% | +0.09 | -0.14 … +0.32 | 2,284 | TENDENZ_PLUS |
| orb5 | 71 | 44% | +0.10 | -0.30 … +0.51 | 1,073 | TENDENZ_PLUS |
| ema20 | 204 | 51% | +0.11 | -0.06 … +0.29 | 4,123 | TENDENZ_PLUS |
| omar | 348 | 48% | +0.12 | -0.01 … +0.25 | 7,595 | TENDENZ_PLUS |
| bb_only_long | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| bb_only_long | +0.00 | 0 | +0.17 | 44 |
| ema20 | +0.15 | 108 | +0.07 | 96 |
| imom_last30 | +0.09 | 46 | -0.36 | 41 |
| omar | +0.07 | 168 | +0.17 | 180 |
| orb5 | +0.16 | 40 | +0.03 | 31 |
| range_bb_reentry | -0.25 | 81 | -0.29 | 77 |
| range_rsi2 | -0.12 | 239 | -0.11 | 255 |
| trend_breakout_1h | +0.01 | 308 | -0.02 | 279 |
| trend_ema_pullback | +0.01 | 171 | -0.06 | 167 |
| trend_pullback_mtf | +0.12 | 62 | +0.06 | 56 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | TREND_RUNTER | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |
| ema20 | TREND_RUNTER | 204 | 51% | +0.11 | -0.06 … +0.29 | 4,123 | TENDENZ_PLUS |
| imom_last30 | CHOP | 14 | 36% | -0.10 | -0.35 … +0.15 | -224 | ZU_WENIG |
| imom_last30 | RANGE | 26 | 35% | -0.23 | -0.51 … +0.05 | -809 | TENDENZ_MINUS |
| imom_last30 | TREND_HOCH | 11 | 45% | +0.03 | -0.61 … +0.66 | 108 | ZU_WENIG |
| imom_last30 | TREND_RUNTER | 14 | 43% | -0.12 | -0.51 … +0.27 | -288 | ZU_WENIG |
| imom_last30 | UEBERGANG | 22 | 36% | -0.08 | -0.39 … +0.23 | -170 | TENDENZ_MINUS |
| omar | TREND_RUNTER | 348 | 48% | +0.12 | -0.01 … +0.25 | 7,595 | TENDENZ_PLUS |
| orb5 | CHOP | 11 | 45% | -0.31 | -0.80 … +0.18 | -475 | ZU_WENIG |
| orb5 | TREND_HOCH | 11 | 55% | +0.33 | -0.53 … +1.19 | 538 | ZU_WENIG |
| orb5 | TREND_RUNTER | 16 | 44% | +0.02 | -0.69 … +0.74 | -20 | ZU_WENIG |
| orb5 | UEBERGANG | 24 | 38% | +0.01 | -0.58 … +0.61 | 186 | TENDENZ_PLUS |
| range_bb_reentry | CHOP | 20 | 40% | +0.09 | -0.59 … +0.78 | 410 | TENDENZ_PLUS |
| range_bb_reentry | RANGE | 138 | 34% | -0.32 | -0.54 … -0.10 | -7,934 | ROT |
| range_rsi2 | CHOP | 53 | 51% | -0.02 | -0.29 … +0.24 | -289 | TENDENZ_MINUS |
| range_rsi2 | RANGE | 441 | 47% | -0.12 | -0.21 … -0.03 | -9,194 | ROT |
| trend_breakout_1h | TREND_HOCH | 253 | 48% | +0.11 | -0.05 … +0.27 | 4,346 | TENDENZ_PLUS |
| trend_breakout_1h | TREND_RUNTER | 334 | 40% | -0.09 | -0.22 … +0.04 | -4,918 | TENDENZ_MINUS |
| trend_ema_pullback | TREND_HOCH | 156 | 38% | -0.10 | -0.29 … +0.10 | -1,974 | TENDENZ_MINUS |
| trend_ema_pullback | TREND_RUNTER | 182 | 43% | +0.04 | -0.15 … +0.23 | 1,569 | TENDENZ_PLUS |
| trend_pullback_mtf | TREND_RUNTER | 118 | 49% | +0.09 | -0.14 … +0.32 | 2,284 | TENDENZ_PLUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **CHOP**: range_bb_reentry (+0.09 R, n=20, TENDENZ_PLUS, A +0.71 / B -0.17, NICHT stabil)
- **TREND_HOCH**: trend_breakout_1h (+0.11 R, n=253, TENDENZ_PLUS, A +0.16 / B +0.05, stabil)
- **TREND_RUNTER**: bb_only_long (+0.17 R, n=44, TENDENZ_PLUS, A +0.00 / B +0.17, NICHT stabil), omar (+0.12 R, n=348, TENDENZ_PLUS, A +0.07 / B +0.17, stabil), ema20 (+0.11 R, n=204, TENDENZ_PLUS, A +0.15 / B +0.07, stabil), trend_pullback_mtf (+0.09 R, n=118, TENDENZ_PLUS, A +0.12 / B +0.06, stabil), trend_ema_pullback (+0.04 R, n=182, TENDENZ_PLUS, A +0.10 / B -0.02, NICHT stabil)
- **UEBERGANG**: orb5 (+0.01 R, n=24, TENDENZ_PLUS, A -0.01 / B +0.05, NICHT stabil)
