# TAURUS Trading Lab v1.1 – Opening Strategien integriert

Diese Version erweitert TAURUS um:

- **ORB / Opening Range Breakout** aktiviert
- **Opening Drop Short** als eigene Strategie
- **Opening Reversal Long** als eigene Strategie
- **1-Minuten-Daten für die Opening-Strategien bei Nasdaq (Yahoo verzögert)**
- **Strategie-spezifische Papertrading-Auswertungen unten auf jeder Seite**
- **Mehr Abstand / mehr Übersicht im Layout**

## Enthalten

- FastAPI-Webapp
- Binance-Spot-Feeds für BTC, ETH, SOL, XRP, TAO, ADA, AVAX, LINK, DOGE, SUI
- Yahoo NQ=F Feed in 5M plus 1M (verzögert)
- Papertrading-Motor mit SQLite/PostgreSQL-Persistenz
- Getrennte Protokollierung und Auswertung je Strategie

## Wichtige Hinweise

- **Keine Echtgeld-Orders**
- Nasdaq bleibt **verzögerte Simulation**
- Für dauerhafte Datenhaltung auf Render möglichst **PostgreSQL / Persistent Storage** verwenden
- Startbefehl weiterhin mit **einem Worker**:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
```

## Installation lokal

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Dann im Browser öffnen:

- http://127.0.0.1:8000


## v1.2 – Bollinger/RSI reversal scanners
- Added independent `bb_rsi_short` and `bb_rsi_long` tiles and papertrading, 1-minute candles with completed 5M/15M RSI(14) and BB(20,2) on 1M.
- SHORT: RSI(1M,5M,15M)>85 and close >= upper band. LONG: all <15 and close <= lower band.
- Signal fires once on entering the qualifying condition; it can rearm after conditions reset. Entry simulated at NEXT 1M open, no lookahead.
- 1H price direction is recorded per signal as a comparison attribute, not an entry gate. 1H RSI only appears when enough complete 1H bars are present; otherwise `n/v`.
- Paper engine uses initial swing stop, activates a one-way trailing stop after 1% favorable price movement; 1% is not a fixed profit-taking exit. Slippage/fees and existing risk sizing still apply.
- Public Binance 1M klines added for crypto markets. Existing Yahoo 1M feed used for NQ. The 1000-bar crypto history is insufficient for RSI14 on 1H; this metric is marked unavailable, never guessed.
- On deployment, existing papertrade watermark means only NEW signals will be simulated. Restart does not replay old signals. Existing strategies preserved.
- Note: Trailing on OHLC bars is an approximation, not tick-accurate. No actual orders.


## Backtest & Simulation (Branch feature/backtest-sim)

Forschungswerkzeuge, die nichts am Live-LAB ändern und nie auf die Live-Datenbank zugreifen.

- `backtest.py` spielt die echten Strategien auf historischen Kerzen ab und führt jedes Signal mit den Regeln aus `paper_engine.py` aus (nächster Open + 1 Tick, 200 USD Risiko, Stop vor Ziel, Trailing ab +1R, Stornos wie live). Jeder Trade bekommt die Marktlage aus `regime.py`. Ausgabe: `backtest_out/backtest.md` (Tabellen Strategie × Marktlage, Playbook, Kausalitäts-Check) und `backtest.json`.
  - `python backtest.py --source yahoo` – 60 Tage 5M, 29 Tage 1M (yfinance)
  - `python backtest.py --source archive --archive-dir archives --compare-live` – Tagesarchive, mit Abgleich gegen die Live-Trades
- `sim.py` – Monte-Carlo:
  - `trades`: Streuung des Ergebnisses einer Strategie (optional je Marktlage)
  - `lucid`: Wahrscheinlichkeit, das Lucid-25K-Ziel vor dem Max Loss zu erreichen
  - `path`: „Time Machine“ – Rest eines Trades 10'000-mal aus Kerzen derselben Tageszeit und Marktlage
- GitHub Action `TAURUS Backtest (60 Tage Yahoo)` läuft bei jedem Push auf den Branch und manuell; der Bericht landet im Run-Summary und auf dem Branch `taurus-backtests` (`latest.md`).


## V8 – Strategien je Marktlage (Branch feature/v8-regime)

- Neues Experiment `taurus_v8_regime_20261104`, neues Lucid-Konto `lucid_independent_25k_v2_regime`.
- Aktiv im LAB: `omar` und `ema20` (nur TREND_RUNTER), `trend_breakout_1h` (nur TREND_HOCH), `orb5`, `trend_engulf_fade` (nur TREND_RUNTER), `bb_only_long` (1M, nur TREND_RUNTER).
- Lucid: `omar`, `ema20`, `trend_breakout_1h` – je nur in ihrer Marktlage.
- Marktlagen-Filter: `regime_gate.py` (abschaltbar mit `TAURUS_REGIME_GATE=off`).
- Kostenregel: Kommission + Slippage > 10 % des Risikos → `COST_TOO_HIGH` (`TAURUS_MAX_COST_SHARE`).
- Eingefrorene Yahoo-Kerzen (Volumen 0 und Hoch = Tief) werden entfernt (`feed_quality.py`).
- `candle_study.py`: misst Kerzenmuster × Marktlage gegen die Basisrate.
- Workflow `TAURUS V8 Backtest + Kerzen-Studie` rechnet alles auf 60 Tagen neu; Berichte auf Branch `taurus-backtests` (`latest_v8.md`, `latest_candles.md`).


## PO3 10:00 – Forward-Test (Branch feature/po3-10am)

- Neue Strategie `po3_10am` (`po3_10am.py`): ICT „Power of 3“ um die 4H-Kerze 10:00 New York, aus der PO3-Checkliste in feste Regeln übersetzt.
- Regeln: Volatilität (Index-ATR14 im Rang ≥ 33 % der letzten 250 Tage) · Bias (Vortag 09:30–16:00 und 4H 06–10 gleichgerichtet) · HTF-Level (Vortagesextrem oder 4H-FVG getappt) · enge Accumulation 09:30–10:00 (≤ 0,35 × ATR) · Manipulation ab 10:00 (Sweep oder 5M-FVG-Tap) · Entry bis 12:00 per 1M-IFVG, sonst BOS · Stop hinter dem Manipulations-Extrem, **Ziel 3R ohne Trailing**, Ausstieg 15:55.
- Backtest SPY 1M 2010–2026 (Variante 3R + Volatilitätsfilter): n=519, +0,12 R je Trade nach Kosten, 95 %-KI −0,02…+0,29 R. Die Variante wurde nach Sicht auf alle Jahre gewählt → **der Forward-Test ist die eigentliche Prüfung, Regeln nicht nachoptimieren.**
- Märkte: MNQ und MES. Nur LAB (eigene 1M-Engine `advance_po3`, Fortschrittsschlüssel `nq:po3`/`mes:po3`), nicht im Lucid-Konto.
- Tagesdaten für den Volatilitätsfilter: Yahoo `^NDX` / `^GSPC` (2 Jahre, alle 6 h). Ohne Tagesdaten gibt die Strategie keine Signale.
- Auswertung nach ca. 6 Monaten bzw. ≥ 15 Trades gegen die Backtest-Erwartung von +0,12 R.
