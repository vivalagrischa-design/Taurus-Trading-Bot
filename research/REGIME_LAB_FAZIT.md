# Regime-Lab – Fazit (7.11.2026)

14 Lehrbuch-Strategien × LONG/SHORT × 5 Marktlagen (regime.py), nach Kosten,
Playbook nur bei positivem In-Sample (erste 60 %) UND Out-of-Sample (letzte 40 %),
t ≥ 1.5 und mind. Hälfte der Märkte positiv. Detailtabellen: `regime_lab_<tf>.md`.

## Kernbefunde
1. **5M/15M: keine Chance.** Kosten 0.5–1.7 R pro Trade; vor Kosten liegen die Strategien bei ~0.
   Darum ist bisher alles durchgefallen – nicht die Ideen, der Zeitrahmen.
2. **1h Futures (NQ/ES/GC, 2 Jahre): Kosten nur ~0.02 R – hier gibt es Kandidaten.**
3. **1h Krypto: nichts** (Gebühren 0.24 % pro Rundreise fressen alles).
4. **Mit dem Trend handeln, wenn regime.py bereits TREND meldet, funktioniert fast nie** –
   das Label kommt zu spät. Vorteile zeigen sich (a) bei Ausbrüchen aus RANGE/UEBERGANG,
   (b) beim Kaufen von Überverkauft-Umkehrungen im kurzfristigen Abwärtstrend.

## Kandidaten (Futures, für Forward-Test)
| Marktlage (1h) | Strategie | n | Ø R | IS / OOS | Märkte |
|---|---|---|---|---|---|
| TREND_RUNTER | bb_reentry LONG (Bollinger-Rückkehr, Ziel SMA20) | 285 | +0.21 | +0.19 / +0.23 | 3/3 |
| TREND_RUNTER | stoch_fade LONG (Stoch 14/3 kreuzt 20) | 464 | +0.15 | +0.17 / +0.12 | 3/3 |
| UEBERGANG | macd_trend LONG (MACD-Kreuz über EMA200, Trailing) | 205 | +0.28 | +0.32 / +0.22 | 3/3 |
| CHOP | keltner_break LONG | 70 | +0.50 | +0.59 / +0.39 | 3/3 |
| CHOP | macd_trend SHORT | 100 | +0.31 | +0.13 / +0.57 | 3/3 |
| RANGE | supertrend SHORT | 127 | +0.19 | +0.15 / +0.25 | 3/3 |

Tageskerzen (10 Jahre): Ausbruchs-Strategien LONG klar positiv, v. a. aus RANGE/UEBERGANG
(Donchian +1.18 R, Keltner +1.01 R) – aber die SHORT-Seite derselben Regeln ist ~0:
grosser Teil davon ist der Bullenmarkt 2016–2026. Connors RSI(2) LONG im TREND_HOCH:
+0.09 R, 74 % Treffer, 6/6 Märkte, t 2.8 (klein, aber robust).

## Vorbehalte
- 140 Zellen je Gruppe getestet → einige Treffer sind Zufall. Nur Forward-Test entscheidet.
- 2024–2026 war für Indizes ein Bullenmarkt; „Dip kaufen im Abwärtstrend“ profitiert davon.
- Marktlage hier auf 1h berechnet; live rechnet Taurus sie auf 5M → für den Einsatz 1h-Marktlage nötig.
