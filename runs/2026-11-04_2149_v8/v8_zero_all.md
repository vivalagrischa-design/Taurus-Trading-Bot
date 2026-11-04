# TAURUS Backtest

Daten: yahoo · 2026-08-26 bis 2026-11-04 · Märkte: nq, mes, mgc
Marktlagen-Filter: an · Volumen-0-Kerzen: all (entfernt: {'nq_5m': 50, 'nq_1m': 24, 'mes_5m': 51, 'mes_1m': 25, 'mgc_5m': 48, 'mgc_1m': 24}) · max. Kostenanteil: 0.1
Geschlossene Trades: 1206 · Summe: 20,575 USD (200 USD Risiko je Trade, je Strategie getrennt)

R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.

## Strategien gesamt

| Strategie | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|
| trend_engulf_fade | 283 | 57% | +0.06 | -0.06 … +0.17 | 2,780 | TENDENZ_PLUS |
| orb5 | 72 | 43% | +0.09 | -0.31 … +0.49 | 918 | TENDENZ_PLUS |
| trend_breakout_1h | 255 | 48% | +0.11 | -0.05 … +0.26 | 4,234 | TENDENZ_PLUS |
| ema20 | 205 | 51% | +0.11 | -0.06 … +0.28 | 4,017 | TENDENZ_PLUS |
| omar | 348 | 48% | +0.12 | -0.01 … +0.25 | 7,595 | TENDENZ_PLUS |
| bb_only_long | 43 | 49% | +0.12 | -0.25 … +0.50 | 1,031 | TENDENZ_PLUS |

## Stabilität: erste vs. zweite Hälfte des Zeitraums

| Strategie | Ø R Hälfte A | n A | Ø R Hälfte B | n B |
|---|---|---|---|---|
| bb_only_long | +0.00 | 0 | +0.12 | 43 |
| ema20 | +0.12 | 112 | +0.09 | 93 |
| omar | +0.06 | 172 | +0.18 | 176 |
| orb5 | +0.16 | 40 | -0.00 | 32 |
| trend_breakout_1h | +0.16 | 143 | +0.04 | 112 |
| trend_engulf_fade | +0.03 | 136 | +0.08 | 147 |

## Strategie × Marktlage (n ≥ 10)

| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |
|---|---|---|---|---|---|---|---|
| bb_only_long | TREND_RUNTER | 43 | 49% | +0.12 | -0.25 … +0.50 | 1,031 | TENDENZ_PLUS |
| ema20 | TREND_RUNTER | 205 | 51% | +0.11 | -0.06 … +0.28 | 4,017 | TENDENZ_PLUS |
| omar | TREND_RUNTER | 348 | 48% | +0.12 | -0.01 … +0.25 | 7,595 | TENDENZ_PLUS |
| orb5 | CHOP | 12 | 42% | -0.37 | -0.82 … +0.09 | -630 | ZU_WENIG |
| orb5 | TREND_HOCH | 11 | 55% | +0.33 | -0.53 … +1.19 | 538 | ZU_WENIG |
| orb5 | TREND_RUNTER | 16 | 44% | +0.02 | -0.69 … +0.74 | -20 | ZU_WENIG |
| orb5 | UEBERGANG | 24 | 38% | +0.01 | -0.58 … +0.61 | 186 | TENDENZ_PLUS |
| trend_breakout_1h | TREND_HOCH | 255 | 48% | +0.11 | -0.05 … +0.26 | 4,234 | TENDENZ_PLUS |
| trend_engulf_fade | TREND_RUNTER | 283 | 57% | +0.06 | -0.06 … +0.17 | 2,780 | TENDENZ_PLUS |

## Playbook: positive Strategien je Marktlage (n ≥ 20; stabil = in beiden Hälften positiv)

- **TREND_HOCH**: trend_breakout_1h (+0.11 R, n=255, TENDENZ_PLUS, A +0.16 / B +0.04, stabil)
- **TREND_RUNTER**: bb_only_long (+0.12 R, n=43, TENDENZ_PLUS, A +0.00 / B +0.12, NICHT stabil), omar (+0.12 R, n=348, TENDENZ_PLUS, A +0.06 / B +0.18, stabil), ema20 (+0.11 R, n=205, TENDENZ_PLUS, A +0.12 / B +0.09, stabil), trend_engulf_fade (+0.06 R, n=283, TENDENZ_PLUS, A +0.03 / B +0.08, stabil)
- **UEBERGANG**: orb5 (+0.01 R, n=24, TENDENZ_PLUS, A -0.01 / B +0.05, NICHT stabil)
