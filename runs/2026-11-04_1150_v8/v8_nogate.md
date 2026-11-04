# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: AUS · Volumen-0-Kerzen: frozen (entfernt: {'nq_5m': 1, 'nq_1m': 1, 'mes_5m': 2, 'mes_1m': 1, 'mgc_5m': 2, 'mgc_1m': 2}) · max. Kostenanteil: 0.1
Geschlossene Trades: 3363 · Summe: -4,054 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| bb_only_long | 74 | 41% | -0.10 | -0.37 … +0.17 | -1,244 | TENDENZ_MINUS |
| ema20 | 1167 | 45% | -0.04 | -0.10 … +0.03 | -7,533 | TENDENZ_MINUS |
| omar | 1186 | 44% | -0.01 | -0.08 … +0.06 | -1,068 | TENDENZ_MINUS |
| trend_breakout_1h | 583 | 45% | +0.01 | -0.09 … +0.11 | 897 | TENDENZ_PLUS |
| trend_engulf_fade | 282 | 58% | +0.08 | -0.03 … +0.19 | 3,821 | TENDENZ_PLUS |
| orb5 | 71 | 44% | +0.10 | -0.30 … +0.51 | 1,073 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| bb_only_long | +0.00 | 0 | -0.10 | 74 |
| ema20 | -0.03 | 610 | -0.05 | 557 |
| omar | +0.02 | 584 | -0.03 | 602 |
| orb5 | +0.16 | 40 | +0.03 | 31 |
| trend_breakout_1h | +0.02 | 312 | -0.01 | 271 |
| trend_engulf_fade | +0.05 | 135 | +0.11 | 147 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | RANGE | 10 | 30% | -0.27 | -1.05 … +0.51 | -447 | ZU_WENIG |
| bb_only_long | TREND_RUNTER | 42 | 48% | +0.09 | -0.28 … +0.47 | 780 | TENDENZ_PLUS |
| bb_only_long | UEBERGANG | 17 | 29% | -0.54 | -0.93 … -0.16 | -1,631 | ZU_WENIG |
| ema20 | CHOP | 160 | 44% | -0.07 | -0.26 … +0.12 | -2,040 | TENDENZ_MINUS |
| ema20 | RANGE | 350 | 45% | -0.07 | -0.19 … +0.04 | -4,346 | TENDENZ_MINUS |
| ema20 | TREND_HOCH | 146 | 37% | -0.14 | -0.33 … +0.06 | -3,999 | TENDENZ_MINUS |
| ema20 | TREND_RUNTER | 193 | 49% | +0.04 | -0.13 … +0.21 | 1,546 | TENDENZ_PLUS |
| ema20 | UEBERGANG | 318 | 47% | +0.02 | -0.11 … +0.16 | 1,307 | TENDENZ_PLUS |
| omar | CHOP | 118 | 42% | -0.04 | -0.26 … +0.17 | -312 | TENDENZ_MINUS |
| omar | RANGE | 294 | 42% | -0.10 | -0.23 … +0.03 | -5,278 | TENDENZ_MINUS |
| omar | TREND_HOCH | 185 | 41% | -0.05 | -0.23 … +0.13 | -1,744 | TENDENZ_MINUS |
| omar | TREND_RUNTER | 290 | 50% | +0.18 | +0.03 … +0.33 | 9,426 | GRUEN |
| omar | UEBERGANG | 299 | 41% | -0.05 | -0.19 … +0.09 | -3,160 | TENDENZ_MINUS |
| orb5 | CHOP | 11 | 45% | -0.31 | -0.80 … +0.18 | -475 | ZU_WENIG |
| orb5 | TREND_HOCH | 11 | 55% | +0.33 | -0.53 … +1.19 | 538 | ZU_WENIG |
| orb5 | TREND_RUNTER | 16 | 44% | +0.02 | -0.69 … +0.74 | -20 | ZU_WENIG |
| orb5 | UEBERGANG | 24 | 38% | +0.01 | -0.58 … +0.61 | 186 | TENDENZ_PLUS |
| trend_breakout_1h | TREND_HOCH | 254 | 49% | +0.12 | -0.03 … +0.27 | 5,088 | TENDENZ_PLUS |
| trend_breakout_1h | TREND_RUNTER | 329 | 41% | -0.08 | -0.21 … +0.05 | -4,191 | TENDENZ_MINUS |
| trend_engulf_fade | TREND_RUNTER | 282 | 58% | +0.08 | -0.03 … +0.19 | 3,821 | TENDENZ_PLUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **TREND_HOCH**: trend_breakout_1h (+0.12 R, n=254, TENDENZ_PLUS, A +0.16 / B +0.06, stabil)
- **TREND_RUNTER**: omar (+0.18 R, n=290, GRUEN, A +0.14 / B +0.22, stabil), bb_only_long (+0.09 R, n=42, TENDENZ_PLUS, A +0.00 / B +0.09, NICHT stabil), trend_engulf_fade (+0.08 R, n=282, TENDENZ_PLUS, A +0.05 / B +0.11, stabil), ema20 (+0.04 R, n=193, TENDENZ_PLUS, A -0.05 / B +0.15, NICHT stabil)
- **UEBERGANG**: ema20 (+0.02 R, n=318, TENDENZ_PLUS, A +0.05 / B -0.02, NICHT stabil), orb5 (+0.01 R, n=24, TENDENZ_PLUS, A -0.01 / B +0.05, NICHT stabil)
