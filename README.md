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


## V9 – Strategien je 1h-Marktlage (Branch feature/v9-regime-1h)

- Grundlage: Regime-Lab (`regime_lab.py`, Ergebnisse in `research/`), 1h-Kerzen über 2 Jahre, NQ/ES/GC,
  nach Kosten, In-Sample **und** Out-of-Sample positiv, in allen drei Märkten positiv.
- Neue 1h-Marktlage: `regime.py` auf 1h-Kerzen (Yahoo, 60 Tage, alle 10 Min.); `v9_regime.regime_now()`.
- Sechs Strategien, nur LAB, nur Futures, jede nur in ihrer 1h-Marktlage:
  `v9_bb_dip`, `v9_stoch_dip` (TREND_RUNTER), `v9_macd_long` (UEBERGANG), `v9_st_short` (RANGE),
  `v9_keltner_long`, `v9_macd_short` (CHOP). Für TREND_HOCH gab es auf 1h keinen Kandidaten.
- Signal auf der 1h-Kerze, Einstieg zum nächsten 5M-Open (= 1h-Open), Ausstiege wie im Backtest:
  fester Zielkurs bzw. Trailing 3 ATR(1h) ab Einstieg, Zeitstopp. Das allgemeine 1R-Trailing gilt für V9 nicht.
- Grösse: mindestens 1 Mikro-Kontrakt, solange dessen Risiko ≤ `TAURUS_V9_MAX_RISK_USD` (Standard 1000).
  Auswertung daher in R.
- Abschalten des 1h-Feeds: `TAURUS_V9_FEED=off`; Marktlagen-Filter wie bisher mit `TAURUS_REGIME_GATE=off`.
