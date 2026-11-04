# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: an · Volumen-0-Kerzen: frozen (entfernt: {'nq_5m': 1, 'nq_1m': 1, 'mes_5m': 2, 'mes_1m': 1, 'mgc_5m': 2, 'mgc_1m': 2}) · max. Kostenanteil: 1.0
Geschlossene Trades: 3161 · Summe: -18,956 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| imom_last30 | 91 | 36% | -0.16 | -0.31 … -0.00 | -2,069 | ROT |
| range_bb_reentry | 299 | 39% | -0.15 | -0.28 … -0.03 | -8,459 | ROT |
| range_rsi2 | 771 | 47% | -0.14 | -0.21 … -0.08 | -19,805 | ROT |
| trend_ema_pullback | 413 | 40% | -0.06 | -0.18 … +0.06 | -3,154 | TENDENZ_MINUS |
| trend_breakout_1h | 719 | 44% | +0.00 | -0.09 … +0.09 | 329 | TENDENZ_PLUS |
| orb5 | 89 | 42% | +0.02 | -0.32 … +0.36 | 9 | TENDENZ_PLUS |
| trend_pullback_mtf | 133 | 47% | +0.04 | -0.17 … +0.25 | 1,403 | TENDENZ_PLUS |
| ema20 | 209 | 50% | +0.09 | -0.08 … +0.26 | 3,732 | TENDENZ_PLUS |
| omar | 393 | 48% | +0.10 | -0.02 … +0.23 | 7,663 | TENDENZ_PLUS |
| bb_only_long | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| bb_only_long | +0.00 | 0 | +0.17 | 44 |
| ema20 | +0.10 | 111 | +0.08 | 98 |
| imom_last30 | +0.07 | 47 | -0.39 | 44 |
| omar | +0.03 | 192 | +0.17 | 201 |
| orb5 | +0.03 | 48 | +0.01 | 41 |
| range_bb_reentry | -0.14 | 141 | -0.17 | 158 |
| range_rsi2 | -0.16 | 356 | -0.13 | 415 |
| trend_breakout_1h | +0.01 | 399 | -0.01 | 320 |
| trend_ema_pullback | -0.05 | 214 | -0.06 | 199 |
| trend_pullback_mtf | +0.05 | 72 | +0.02 | 61 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | TREND_RUNTER | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |
| ema20 | TREND_RUNTER | 209 | 50% | +0.09 | -0.08 … +0.26 | 3,732 | TENDENZ_PLUS |
| imom_last30 | CHOP | 14 | 36% | -0.10 | -0.35 … +0.15 | -224 | ZU_WENIG |
| imom_last30 | RANGE | 27 | 33% | -0.26 | -0.54 … +0.02 | -981 | TENDENZ_MINUS |
| imom_last30 | TREND_HOCH | 12 | 42% | -0.06 | -0.66 … +0.54 | -81 | ZU_WENIG |
| imom_last30 | TREND_RUNTER | 15 | 40% | -0.18 | -0.56 … +0.21 | -483 | ZU_WENIG |
| imom_last30 | UEBERGANG | 23 | 35% | -0.11 | -0.41 … +0.19 | -300 | TENDENZ_MINUS |
| omar | TREND_RUNTER | 393 | 48% | +0.10 | -0.02 … +0.23 | 7,663 | TENDENZ_PLUS |
| orb5 | CHOP | 12 | 42% | -0.37 | -0.82 … +0.09 | -654 | ZU_WENIG |
| orb5 | RANGE | 14 | 50% | +0.66 | -0.84 … +2.15 | 1,314 | ZU_WENIG |
| orb5 | TREND_HOCH | 15 | 47% | +0.07 | -0.61 … +0.76 | 78 | ZU_WENIG |
| orb5 | TREND_RUNTER | 20 | 40% | -0.09 | -0.69 … +0.50 | -424 | TENDENZ_MINUS |
| orb5 | UEBERGANG | 28 | 36% | -0.08 | -0.60 … +0.45 | -304 | TENDENZ_MINUS |
| range_bb_reentry | CHOP | 21 | 38% | +0.04 | -0.62 … +0.70 | 168 | TENDENZ_PLUS |
| range_bb_reentry | RANGE | 278 | 40% | -0.17 | -0.29 … -0.04 | -8,627 | ROT |
| range_rsi2 | CHOP | 69 | 51% | -0.04 | -0.26 … +0.19 | -602 | TENDENZ_MINUS |
| range_rsi2 | RANGE | 702 | 47% | -0.15 | -0.22 … -0.09 | -19,203 | ROT |
| trend_breakout_1h | TREND_HOCH | 320 | 48% | +0.10 | -0.04 … +0.23 | 5,356 | TENDENZ_PLUS |
| trend_breakout_1h | TREND_RUNTER | 399 | 41% | -0.08 | -0.19 … +0.04 | -5,028 | TENDENZ_MINUS |
| trend_ema_pullback | TREND_HOCH | 193 | 36% | -0.17 | -0.33 … -0.00 | -5,299 | ROT |
| trend_ema_pullback | TREND_RUNTER | 220 | 43% | +0.04 | -0.13 … +0.21 | 2,145 | TENDENZ_PLUS |
| trend_pullback_mtf | TREND_RUNTER | 133 | 47% | +0.04 | -0.17 … +0.25 | 1,403 | TENDENZ_PLUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **CHOP**: range_bb_reentry (+0.04 R, n=21, TENDENZ_PLUS, A +0.71 / B -0.23, NICHT stabil)
- **TREND_HOCH**: trend_breakout_1h (+0.10 R, n=320, TENDENZ_PLUS, A +0.13 / B +0.05, stabil)
- **TREND_RUNTER**: bb_only_long (+0.17 R, n=44, TENDENZ_PLUS, A +0.00 / B +0.17, NICHT stabil), omar (+0.10 R, n=393, TENDENZ_PLUS, A +0.03 / B +0.17, stabil), ema20 (+0.09 R, n=209, TENDENZ_PLUS, A +0.10 / B +0.08, stabil), trend_ema_pullback (+0.04 R, n=220, TENDENZ_PLUS, A +0.09 / B -0.01, NICHT stabil), trend_pullback_mtf (+0.04 R, n=133, TENDENZ_PLUS, A +0.05 / B +0.02, stabil)
