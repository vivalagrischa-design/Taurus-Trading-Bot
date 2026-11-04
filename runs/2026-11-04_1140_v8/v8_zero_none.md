# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: an · Volumen-0-Kerzen: none (entfernt: {'nq_5m': 0, 'nq_1m': 0, 'mes_5m': 0, 'mes_1m': 0, 'mgc_5m': 0, 'mgc_1m': 0}) · max. Kostenanteil: 0.1
Geschlossene Trades: 2458 · Summe: -2,549 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| range_bb_reentry | 158 | 36% | -0.19 | -0.37 … -0.02 | -5,334 | ROT |
| imom_last30 | 87 | 38% | -0.12 | -0.28 … +0.04 | -1,382 | TENDENZ_MINUS |
| range_rsi2 | 496 | 47% | -0.11 | -0.19 … -0.03 | -9,272 | ROT |
| trend_ema_pullback | 341 | 40% | -0.04 | -0.17 … +0.09 | -1,274 | TENDENZ_MINUS |
| trend_breakout_1h | 585 | 44% | +0.00 | -0.10 … +0.10 | 552 | TENDENZ_PLUS |
| trend_pullback_mtf | 120 | 47% | +0.02 | -0.20 … +0.25 | 1,067 | TENDENZ_PLUS |
| ema20 | 207 | 50% | +0.08 | -0.09 … +0.25 | 3,172 | TENDENZ_PLUS |
| orb5 | 71 | 44% | +0.10 | -0.30 … +0.51 | 1,073 | TENDENZ_PLUS |
| omar | 349 | 48% | +0.12 | -0.02 … +0.25 | 7,456 | TENDENZ_PLUS |
| bb_only_long | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| bb_only_long | +0.00 | 0 | +0.17 | 44 |
| ema20 | +0.07 | 110 | +0.09 | 97 |
| imom_last30 | +0.09 | 46 | -0.36 | 41 |
| omar | +0.05 | 167 | +0.17 | 182 |
| orb5 | +0.22 | 38 | -0.03 | 33 |
| range_bb_reentry | -0.21 | 83 | -0.17 | 75 |
| range_rsi2 | -0.10 | 239 | -0.12 | 257 |
| trend_breakout_1h | +0.01 | 306 | +0.00 | 279 |
| trend_ema_pullback | -0.03 | 173 | -0.05 | 168 |
| trend_pullback_mtf | +0.01 | 66 | +0.04 | 54 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | TREND_RUNTER | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |
| ema20 | TREND_RUNTER | 207 | 50% | +0.08 | -0.09 … +0.25 | 3,172 | TENDENZ_PLUS |
| imom_last30 | CHOP | 14 | 36% | -0.10 | -0.35 … +0.15 | -224 | ZU_WENIG |
| imom_last30 | RANGE | 26 | 35% | -0.23 | -0.51 … +0.05 | -809 | TENDENZ_MINUS |
| imom_last30 | TREND_HOCH | 11 | 45% | +0.03 | -0.61 … +0.66 | 108 | ZU_WENIG |
| imom_last30 | TREND_RUNTER | 14 | 43% | -0.12 | -0.51 … +0.27 | -288 | ZU_WENIG |
| imom_last30 | UEBERGANG | 22 | 36% | -0.08 | -0.39 … +0.23 | -170 | TENDENZ_MINUS |
| omar | TREND_RUNTER | 349 | 48% | +0.12 | -0.02 … +0.25 | 7,456 | TENDENZ_PLUS |
| orb5 | CHOP | 11 | 45% | -0.31 | -0.80 … +0.18 | -475 | ZU_WENIG |
| orb5 | TREND_HOCH | 11 | 55% | +0.33 | -0.53 … +1.19 | 538 | ZU_WENIG |
| orb5 | TREND_RUNTER | 16 | 44% | +0.02 | -0.69 … +0.74 | -20 | ZU_WENIG |
| orb5 | UEBERGANG | 24 | 38% | +0.01 | -0.58 … +0.61 | 186 | TENDENZ_PLUS |
| range_bb_reentry | CHOP | 17 | 47% | +0.29 | -0.48 … +1.06 | 917 | ZU_WENIG |
| range_bb_reentry | RANGE | 141 | 35% | -0.25 | -0.42 … -0.08 | -6,251 | ROT |
| range_rsi2 | CHOP | 55 | 51% | -0.02 | -0.28 … +0.24 | -312 | TENDENZ_MINUS |
| range_rsi2 | RANGE | 441 | 47% | -0.12 | -0.21 … -0.03 | -8,960 | ROT |
| trend_breakout_1h | TREND_HOCH | 255 | 49% | +0.12 | -0.04 … +0.27 | 4,912 | TENDENZ_PLUS |
| trend_breakout_1h | TREND_RUNTER | 330 | 41% | -0.08 | -0.21 … +0.05 | -4,359 | TENDENZ_MINUS |
| trend_ema_pullback | TREND_HOCH | 156 | 38% | -0.10 | -0.29 … +0.09 | -2,063 | TENDENZ_MINUS |
| trend_ema_pullback | TREND_RUNTER | 185 | 42% | +0.01 | -0.17 … +0.19 | 789 | TENDENZ_PLUS |
| trend_pullback_mtf | TREND_RUNTER | 120 | 47% | +0.02 | -0.20 … +0.25 | 1,067 | TENDENZ_PLUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **TREND_HOCH**: trend_breakout_1h (+0.12 R, n=255, TENDENZ_PLUS, A +0.16 / B +0.06, stabil)
- **TREND_RUNTER**: bb_only_long (+0.17 R, n=44, TENDENZ_PLUS, A +0.00 / B +0.17, NICHT stabil), omar (+0.12 R, n=349, TENDENZ_PLUS, A +0.05 / B +0.17, stabil), ema20 (+0.08 R, n=207, TENDENZ_PLUS, A +0.07 / B +0.09, stabil), trend_pullback_mtf (+0.02 R, n=120, TENDENZ_PLUS, A +0.01 / B +0.04, stabil), trend_ema_pullback (+0.01 R, n=185, TENDENZ_PLUS, A +0.03 / B -0.01, NICHT stabil)
- **UEBERGANG**: orb5 (+0.01 R, n=24, TENDENZ_PLUS, A -0.01 / B +0.05, NICHT stabil)
