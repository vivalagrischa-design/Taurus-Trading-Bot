# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: an · Volumen-0-Kerzen: frozen (entfernt: {'nq_5m': 1, 'nq_1m': 1, 'mes_5m': 2, 'mes_1m': 1, 'mgc_5m': 2, 'mgc_1m': 2}) · max. Kostenanteil: 1.0
Geschlossene Trades: 1464 · Summe: 20,719 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| orb5 | 90 | 41% | +0.01 | -0.33 … +0.35 | -145 | TENDENZ_PLUS |
| trend_engulf_fade | 406 | 58% | +0.05 | -0.04 … +0.14 | 3,300 | TENDENZ_PLUS |
| ema20 | 210 | 50% | +0.09 | -0.08 … +0.26 | 3,626 | TENDENZ_PLUS |
| trend_breakout_1h | 322 | 48% | +0.10 | -0.04 … +0.23 | 5,244 | TENDENZ_PLUS |
| omar | 393 | 48% | +0.10 | -0.02 … +0.23 | 7,663 | TENDENZ_PLUS |
| bb_only_long | 43 | 49% | +0.12 | -0.25 … +0.50 | 1,031 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| bb_only_long | +0.00 | 0 | +0.12 | 43 |
| ema20 | +0.10 | 110 | +0.07 | 100 |
| omar | +0.04 | 190 | +0.16 | 203 |
| orb5 | +0.07 | 46 | -0.06 | 44 |
| trend_breakout_1h | +0.11 | 187 | +0.08 | 135 |
| trend_engulf_fade | +0.08 | 198 | +0.02 | 208 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | TREND_RUNTER | 43 | 49% | +0.12 | -0.25 … +0.50 | 1,031 | TENDENZ_PLUS |
| ema20 | TREND_RUNTER | 210 | 50% | +0.09 | -0.08 … +0.26 | 3,626 | TENDENZ_PLUS |
| omar | TREND_RUNTER | 393 | 48% | +0.10 | -0.02 … +0.23 | 7,663 | TENDENZ_PLUS |
| orb5 | CHOP | 13 | 38% | -0.42 | -0.85 … +0.02 | -808 | ZU_WENIG |
| orb5 | RANGE | 14 | 50% | +0.66 | -0.84 … +2.15 | 1,314 | ZU_WENIG |
| orb5 | TREND_HOCH | 15 | 47% | +0.07 | -0.61 … +0.76 | 78 | ZU_WENIG |
| orb5 | TREND_RUNTER | 20 | 40% | -0.09 | -0.69 … +0.50 | -424 | TENDENZ_MINUS |
| orb5 | UEBERGANG | 28 | 36% | -0.08 | -0.60 … +0.45 | -304 | TENDENZ_MINUS |
| trend_breakout_1h | TREND_HOCH | 322 | 48% | +0.10 | -0.04 … +0.23 | 5,244 | TENDENZ_PLUS |
| trend_engulf_fade | TREND_RUNTER | 406 | 58% | +0.05 | -0.04 … +0.14 | 3,300 | TENDENZ_PLUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **TREND_HOCH**: trend_breakout_1h (+0.10 R, n=322, TENDENZ_PLUS, A +0.11 / B +0.08, stabil)
- **TREND_RUNTER**: bb_only_long (+0.12 R, n=43, TENDENZ_PLUS, A +0.00 / B +0.12, NICHT stabil), omar (+0.10 R, n=393, TENDENZ_PLUS, A +0.04 / B +0.16, stabil), ema20 (+0.09 R, n=210, TENDENZ_PLUS, A +0.10 / B +0.07, stabil), trend_engulf_fade (+0.05 R, n=406, TENDENZ_PLUS, A +0.08 / B +0.02, stabil)
