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

