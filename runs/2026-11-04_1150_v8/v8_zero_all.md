# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: an · Volumen-0-Kerzen: all (entfernt: {'nq_5m': 49, 'nq_1m': 28, 'mes_5m': 50, 'mes_1m': 29, 'mgc_5m': 47, 'mgc_1m': 28}) · max. Kostenanteil: 0.1
Geschlossene Trades: 1203 · Summe: 21,311 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| trend_engulf_fade | 283 | 57% | +0.06 | -0.06 … +0.17 | 2,780 | TENDENZ_PLUS |
| orb5 | 71 | 44% | +0.10 | -0.30 … +0.51 | 1,073 | TENDENZ_PLUS |
| trend_breakout_1h | 253 | 48% | +0.11 | -0.05 … +0.27 | 4,346 | TENDENZ_PLUS |
| ema20 | 204 | 51% | +0.11 | -0.06 … +0.29 | 4,123 | TENDENZ_PLUS |
| omar | 348 | 48% | +0.12 | -0.01 … +0.25 | 7,595 | TENDENZ_PLUS |
| bb_only_long | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| bb_only_long | +0.00 | 0 | +0.17 | 44 |
| ema20 | +0.14 | 110 | +0.08 | 94 |
| omar | +0.06 | 172 | +0.18 | 176 |
| orb5 | +0.16 | 40 | +0.03 | 31 |
| trend_breakout_1h | +0.16 | 143 | +0.05 | 110 |
| trend_engulf_fade | +0.03 | 136 | +0.08 | 147 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | TREND_RUNTER | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |
| ema20 | TREND_RUNTER | 204 | 51% | +0.11 | -0.06 … +0.29 | 4,123 | TENDENZ_PLUS |
| omar | TREND_RUNTER | 348 | 48% | +0.12 | -0.01 … +0.25 | 7,595 | TENDENZ_PLUS |
| orb5 | CHOP | 11 | 45% | -0.31 | -0.80 … +0.18 | -475 | ZU_WENIG |
| orb5 | TREND_HOCH | 11 | 55% | +0.33 | -0.53 … +1.19 | 538 | ZU_WENIG |
| orb5 | TREND_RUNTER | 16 | 44% | +0.02 | -0.69 … +0.74 | -20 | ZU_WENIG |
| orb5 | UEBERGANG | 24 | 38% | +0.01 | -0.58 … +0.61 | 186 | TENDENZ_PLUS |
| trend_breakout_1h | TREND_HOCH | 253 | 48% | +0.11 | -0.05 … +0.27 | 4,346 | TENDENZ_PLUS |
| trend_engulf_fade | TREND_RUNTER | 283 | 57% | +0.06 | -0.06 … +0.17 | 2,780 | TENDENZ_PLUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **TREND_HOCH**: trend_breakout_1h (+0.11 R, n=253, TENDENZ_PLUS, A +0.16 / B +0.05, stabil)
- **TREND_RUNTER**: bb_only_long (+0.17 R, n=44, TENDENZ_PLUS, A +0.00 / B +0.17, NICHT stabil), omar (+0.12 R, n=348, TENDENZ_PLUS, A +0.06 / B +0.18, stabil), ema20 (+0.11 R, n=204, TENDENZ_PLUS, A +0.14 / B +0.08, stabil), trend_engulf_fade (+0.06 R, n=283, TENDENZ_PLUS, A +0.03 / B +0.08, stabil)
- **UEBERGANG**: orb5 (+0.01 R, n=24, TENDENZ_PLUS, A -0.01 / B +0.05, NICHT stabil)
