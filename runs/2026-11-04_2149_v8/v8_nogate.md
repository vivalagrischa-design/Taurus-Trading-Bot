# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: AUS · Volumen-0-Kerzen: frozen (entfernt: {'nq_5m': 1, 'nq_1m': 1, 'mes_5m': 2, 'mes_1m': 1, 'mgc_5m': 2, 'mgc_1m': 2}) · max. Kostenanteil: 0.1
Geschlossene Trades: 3386 · Summe: -6,361 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| bb_only_long | 73 | 40% | -0.13 | -0.40 … +0.14 | -1,607 | TENDENZ_MINUS |
| ema20 | 1182 | 45% | -0.04 | -0.11 … +0.03 | -8,562 | TENDENZ_MINUS |
| omar | 1192 | 43% | -0.01 | -0.08 … +0.06 | -1,716 | TENDENZ_MINUS |
| trend_breakout_1h | 585 | 45% | +0.01 | -0.09 … +0.11 | 784 | TENDENZ_PLUS |
| trend_engulf_fade | 282 | 58% | +0.08 | -0.03 … +0.19 | 3,821 | TENDENZ_PLUS |
| orb5 | 72 | 43% | +0.09 | -0.31 … +0.49 | 918 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| bb_only_long | +0.00 | 0 | -0.13 | 73 |
| ema20 | -0.03 | 614 | -0.05 | 568 |
| omar | +0.02 | 587 | -0.03 | 605 |
| orb5 | +0.15 | 42 | +0.01 | 30 |
| trend_breakout_1h | +0.02 | 315 | -0.01 | 270 |
| trend_engulf_fade | +0.05 | 135 | +0.11 | 147 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | RANGE | 10 | 30% | -0.27 | -1.05 … +0.51 | -447 | ZU_WENIG |
| bb_only_long | TREND_RUNTER | 41 | 46% | +0.05 | -0.33 … +0.42 | 417 | TENDENZ_PLUS |
| bb_only_long | UEBERGANG | 17 | 29% | -0.54 | -0.93 … -0.16 | -1,631 | ZU_WENIG |
| ema20 | CHOP | 168 | 42% | -0.10 | -0.28 … +0.08 | -2,837 | TENDENZ_MINUS |
| ema20 | RANGE | 351 | 45% | -0.07 | -0.19 … +0.05 | -4,077 | TENDENZ_MINUS |
| ema20 | TREND_HOCH | 149 | 37% | -0.14 | -0.33 … +0.06 | -4,029 | TENDENZ_MINUS |
| ema20 | TREND_RUNTER | 194 | 48% | +0.04 | -0.14 … +0.21 | 1,440 | TENDENZ_PLUS |
| ema20 | UEBERGANG | 320 | 47% | +0.02 | -0.12 … +0.15 | 942 | TENDENZ_PLUS |
| omar | CHOP | 120 | 42% | -0.04 | -0.25 … +0.18 | -290 | TENDENZ_MINUS |
| omar | RANGE | 294 | 42% | -0.10 | -0.23 … +0.03 | -5,278 | TENDENZ_MINUS |
| omar | TREND_HOCH | 186 | 40% | -0.05 | -0.23 … +0.12 | -1,910 | TENDENZ_MINUS |
| omar | TREND_RUNTER | 290 | 50% | +0.18 | +0.03 … +0.33 | 9,426 | GRUEN |
| omar | UEBERGANG | 302 | 41% | -0.06 | -0.20 … +0.08 | -3,663 | TENDENZ_MINUS |
| orb5 | CHOP | 12 | 42% | -0.37 | -0.82 … +0.09 | -630 | ZU_WENIG |
| orb5 | TREND_HOCH | 11 | 55% | +0.33 | -0.53 … +1.19 | 538 | ZU_WENIG |
| orb5 | TREND_RUNTER | 16 | 44% | +0.02 | -0.69 … +0.74 | -20 | ZU_WENIG |
| orb5 | UEBERGANG | 24 | 38% | +0.01 | -0.58 … +0.61 | 186 | TENDENZ_PLUS |
| trend_breakout_1h | TREND_HOCH | 256 | 49% | +0.12 | -0.04 … +0.27 | 4,975 | TENDENZ_PLUS |
| trend_breakout_1h | TREND_RUNTER | 329 | 41% | -0.08 | -0.21 … +0.05 | -4,191 | TENDENZ_MINUS |
| trend_engulf_fade | TREND_RUNTER | 282 | 58% | +0.08 | -0.03 … +0.19 | 3,821 | TENDENZ_PLUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **TREND_HOCH**: trend_breakout_1h (+0.12 R, n=256, TENDENZ_PLUS, A +0.14 / B +0.08, stabil)
- **TREND_RUNTER**: omar (+0.18 R, n=290, GRUEN, A +0.14 / B +0.22, stabil), trend_engulf_fade (+0.08 R, n=282, TENDENZ_PLUS, A +0.05 / B +0.11, stabil), bb_only_long (+0.05 R, n=41, TENDENZ_PLUS, A +0.00 / B +0.05, NICHT stabil), ema20 (+0.04 R, n=194, TENDENZ_PLUS, A -0.05 / B +0.14, NICHT stabil)
- **UEBERGANG**: ema20 (+0.02 R, n=320, TENDENZ_PLUS, A +0.05 / B -0.03, NICHT stabil), orb5 (+0.01 R, n=24, TENDENZ_PLUS, A -0.01 / B +0.05, NICHT stabil)
