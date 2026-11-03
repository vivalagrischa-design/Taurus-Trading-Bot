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
