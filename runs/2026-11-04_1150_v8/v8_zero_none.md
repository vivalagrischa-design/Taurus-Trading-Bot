# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: an · Volumen-0-Kerzen: none (entfernt: {'nq_5m': 0, 'nq_1m': 0, 'mes_5m': 0, 'mes_1m': 0, 'mgc_5m': 0, 'mgc_1m': 0}) · max. Kostenanteil: 0.1
Geschlossene Trades: 1208 · Summe: 21,828 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| trend_engulf_fade | 282 | 58% | +0.08 | -0.03 … +0.19 | 3,821 | TENDENZ_PLUS |
| ema20 | 207 | 50% | +0.08 | -0.09 … +0.25 | 3,172 | TENDENZ_PLUS |
| orb5 | 71 | 44% | +0.10 | -0.30 … +0.51 | 1,073 | TENDENZ_PLUS |
| omar | 349 | 48% | +0.12 | -0.02 … +0.25 | 7,456 | TENDENZ_PLUS |
| trend_breakout_1h | 255 | 49% | +0.12 | -0.04 … +0.27 | 4,912 | TENDENZ_PLUS |
| bb_only_long | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| bb_only_long | +0.00 | 0 | +0.17 | 44 |
| ema20 | +0.03 | 115 | +0.14 | 92 |
| omar | +0.04 | 171 | +0.18 | 178 |
| orb5 | +0.16 | 40 | +0.03 | 31 |
| trend_breakout_1h | +0.16 | 144 | +0.06 | 111 |
| trend_engulf_fade | +0.05 | 134 | +0.10 | 148 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | TREND_RUNTER | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |
| ema20 | TREND_RUNTER | 207 | 50% | +0.08 | -0.09 … +0.25 | 3,172 | TENDENZ_PLUS |
| omar | TREND_RUNTER | 349 | 48% | +0.12 | -0.02 … +0.25 | 7,456 | TENDENZ_PLUS |
| orb5 | CHOP | 11 | 45% | -0.31 | -0.80 … +0.18 | -475 | ZU_WENIG |
| orb5 | TREND_HOCH | 11 | 55% | +0.33 | -0.53 … +1.19 | 538 | ZU_WENIG |
| orb5 | TREND_RUNTER | 16 | 44% | +0.02 | -0.69 … +0.74 | -20 | ZU_WENIG |
| orb5 | UEBERGANG | 24 | 38% | +0.01 | -0.58 … +0.61 | 186 | TENDENZ_PLUS |
| trend_breakout_1h | TREND_HOCH | 255 | 49% | +0.12 | -0.04 … +0.27 | 4,912 | TENDENZ_PLUS |
| trend_engulf_fade | TREND_RUNTER | 282 | 58% | +0.08 | -0.03 … +0.19 | 3,821 | TENDENZ_PLUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **TREND_HOCH**: trend_breakout_1h (+0.12 R, n=255, TENDENZ_PLUS, A +0.16 / B +0.06, stabil)
- **TREND_RUNTER**: bb_only_long (+0.17 R, n=44, TENDENZ_PLUS, A +0.00 / B +0.17, NICHT stabil), omar (+0.12 R, n=349, TENDENZ_PLUS, A +0.04 / B +0.18, stabil), ema20 (+0.08 R, n=207, TENDENZ_PLUS, A +0.03 / B +0.14, stabil), trend_engulf_fade (+0.08 R, n=282, TENDENZ_PLUS, A +0.05 / B +0.10, stabil)
- **UEBERGANG**: orb5 (+0.01 R, n=24, TENDENZ_PLUS, A -0.01 / B +0.05, NICHT stabil)
