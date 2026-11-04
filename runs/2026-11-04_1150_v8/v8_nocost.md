# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: an · Volumen-0-Kerzen: frozen (entfernt: {'nq_5m': 1, 'nq_1m': 1, 'mes_5m': 2, 'mes_1m': 1, 'mgc_5m': 2, 'mgc_1m': 2}) · max. Kostenanteil: 1.0
Geschlossene Trades: 1461 · Summe: 21,455 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| orb5 | 89 | 42% | +0.02 | -0.32 … +0.36 | 9 | TENDENZ_PLUS |
| trend_engulf_fade | 406 | 58% | +0.05 | -0.04 … +0.14 | 3,300 | TENDENZ_PLUS |
| ema20 | 209 | 50% | +0.09 | -0.08 … +0.26 | 3,732 | TENDENZ_PLUS |
| trend_breakout_1h | 320 | 48% | +0.10 | -0.04 … +0.23 | 5,356 | TENDENZ_PLUS |
| omar | 393 | 48% | +0.10 | -0.02 … +0.23 | 7,663 | TENDENZ_PLUS |
| bb_only_long | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| bb_only_long | +0.00 | 0 | +0.17 | 44 |
| ema20 | +0.10 | 110 | +0.08 | 99 |
| omar | +0.04 | 190 | +0.16 | 203 |
| orb5 | +0.07 | 46 | -0.04 | 43 |
| trend_breakout_1h | +0.09 | 185 | +0.11 | 135 |
| trend_engulf_fade | +0.08 | 198 | +0.02 | 208 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | TREND_RUNTER | 44 | 50% | +0.17 | -0.21 … +0.54 | 1,394 | TENDENZ_PLUS |
| ema20 | TREND_RUNTER | 209 | 50% | +0.09 | -0.08 … +0.26 | 3,732 | TENDENZ_PLUS |
| omar | TREND_RUNTER | 393 | 48% | +0.10 | -0.02 … +0.23 | 7,663 | TENDENZ_PLUS |
| orb5 | CHOP | 12 | 42% | -0.37 | -0.82 … +0.09 | -654 | ZU_WENIG |
| orb5 | RANGE | 14 | 50% | +0.66 | -0.84 … +2.15 | 1,314 | ZU_WENIG |
| orb5 | TREND_HOCH | 15 | 47% | +0.07 | -0.61 … +0.76 | 78 | ZU_WENIG |
| orb5 | TREND_RUNTER | 20 | 40% | -0.09 | -0.69 … +0.50 | -424 | TENDENZ_MINUS |
| orb5 | UEBERGANG | 28 | 36% | -0.08 | -0.60 … +0.45 | -304 | TENDENZ_MINUS |
| trend_breakout_1h | TREND_HOCH | 320 | 48% | +0.10 | -0.04 … +0.23 | 5,356 | TENDENZ_PLUS |
| trend_engulf_fade | TREND_RUNTER | 406 | 58% | +0.05 | -0.04 … +0.14 | 3,300 | TENDENZ_PLUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **TREND_HOCH**: trend_breakout_1h (+0.10 R, n=320, TENDENZ_PLUS, A +0.09 / B +0.11, stabil)
- **TREND_RUNTER**: bb_only_long (+0.17 R, n=44, TENDENZ_PLUS, A +0.00 / B +0.17, NICHT stabil), omar (+0.10 R, n=393, TENDENZ_PLUS, A +0.04 / B +0.16, stabil), ema20 (+0.09 R, n=209, TENDENZ_PLUS, A +0.10 / B +0.08, stabil), trend_engulf_fade (+0.05 R, n=406, TENDENZ_PLUS, A +0.08 / B +0.02, stabil)
