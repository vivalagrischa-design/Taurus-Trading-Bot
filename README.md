TAURUS Trading Lab v0.5

- Fixes orange error banner caused by missing DOM node access.
- Adds logo/favicon.
- Uses dark UI with violet accents.

# OMAR LIVE 0.1 – Chart-first Dashboard

**Installierbarer Prototyp für GitHub + Render**. Das Dashboard visualisiert Nasdaq-Futures-Signale mit Candlesticks, Breakout, Retest, Entry, SL, TP und Historie. Responsive für iPhone/Mac. **Keine echten Live-Daten oder Push-Alarme in V0.1.**

## Installation ohne lokale VS-Code-Installation

1. `omar-live.zip` entpacken.
2. Auf GitHub ein neues Repository erstellen (z.B. `omar-live`). Im Browser **Add file → Upload files** auswählen. **Den Inhalt des entpackten Ordners** samt Unterordner `static` hochladen, nicht das ZIP selbst. Commit ausführen.
3. Auf https://dashboard.render.com **New → Web Service** wählen und das GitHub-Repo verbinden.
4. Als Laufzeit `Python 3` wählen, Free-Plan, Build `pip install -r requirements.txt`, Start `uvicorn main:app --host 0.0.0.0 --port $PORT`. Alternativ Render Blueprint `render.yaml`.
5. **Deploy**; danach die `onrender.com`-URL öffnen. `/health` liefert einen Prüfpunkt.

Hinweis: Render Free schläft bei Inaktivität ein und ist ungeeignet für durchgängige Überwachung/Alarme. Ohne einen geeigneten lizenzierten Kursfeed und einen durchgängigen Worker gibt es keinen echten Live-Assistenten. Kostenloser Demo-Betrieb ist davon unabhängig möglich.

## CSV-Datei hochladen

Button **5M-CSV laden**, UTF-8 mit Spalten `time,open,high,low,close,volume` verwenden. `time` ist Unix-Sekunden oder ISO-8601 mit expliziter UTC-Zeitzone, z.B. `2026-10-20T12:00:00+00:00`. Das Import-Modul verlangt mindestens 75 **aufeinanderfolgende** 5-Minuten-Kerzen und maximal 5000 Zeilen. Nur abgeschlossene Kerzen importieren. Keine Overnight-Lücken im Prototyp; Marktpausen werden in einer späteren Version unterstützt. Daten liegen nur im Arbeitsspeicher und gehen bei Restart verloren. Öffentliche URL ohne Authentisierung: keine vertraulichen Daten hochladen.

## Strategie – ausdrücklich PROTOTYP

1. Trendfilter aus **abgeschlossenen** 1H-Kerzen; vereinfachte Strukturbedingung (noch keine echte bestätigte Trendlinie/Hoch-Tief-Pivotfolge).
2. 5M-Pivot-Level (2 bestätigende Kerzen), 5M-Breakout, Retest und Kerzenschluss auf der richtigen Level-Seite.
3. Entry zum Schluss der bestätigenden Retest-Kerze, SL hinter lokalem Extrem + Toleranz, TP 2R. MNQ-Kontraktzahl durch Abrunden von $200 / (Stop-Distanz in Punkten × $2) – **Kosten nicht berücksichtigt**.
4. Alle Signale sind simulierte Markierungen; kein Gebührenmodell, kein echtes Ausführungsmodell, kein Orderrouting, kein historisch validierter Edge.

**Wichtig:** Durch den simplen Prototypfilter und die erneute Berechnung von Levels können Duplikate oder unpassende Signale auftreten. Für einen produktiven Live-Assistenten sind vollständige Oman-Trenddefinition, Zeitfenster, Futures-Handelssitzungen, realistische Ausführung, Speicherung, Authentisierung, Datenprovider und ein kontinuierlicher Worker noch umzusetzen. Die Bridge ist *optional*, nicht Bestandteil dieses Pakets.

## Lokal testen (optional)

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Dann http://127.0.0.1:8000 öffnen.

## Version 0.2 – Multi-Strategie

- Menü: Live Übersicht, Omar, RSI + EMA, EMA20, ORB und Vergleich (Live zeigt die farbige Gesamtübersicht, Vergleich eine gemeinsame Signalzählung ohne Performancebehauptungen).
- Farbige Strategie- und Bedingungskacheln: **grün** bedeutet Regel/Bedingung erfüllt, **rot** Gegenbedingung oder Prüfbedarf, **gelb** Setup in Vorbereitung, **grau** neutral/keine Daten. Farben **sind keine Handelsempfehlung** und keine Winrate.
- `/api/strategies` liefert die einzelnen Strategien und historische Kandidaten. RSI+EMA und EMA20 sind **explorative Regelprototypen**, keine aus früheren Chats übernommenen validierten Modelle. ORB bleibt bewusst deaktiviert, bis Sitzungszeiten und exakte Regeln definiert sind.
- Kein Live-Marktdatenanbieter angeschlossen; Demo/CSV werden nur im Speicher gehalten, Upload ist auf 3 MB begrenzt; Render-Neustart löscht Upload-Daten. Kein kontinuierliches Scannen, keine Trades, keine gemessenen Gewinne oder Backtests.
- Für Live-Betrieb später: bezahlte/lizenzierte MNQ-/NQ-Daten, persistente Datenbank, laufender Prozess, Tests über getrennte Datenperioden, Gebühren, Slippage und Sicherheitskontrollen.


## Yahoo-Forschungsmodus (v0.3)

- Nach Render-Deploy im Dashboard auf **Yahoo 5M einschalten** klicken. Dann zeigt die App historische, möglicherweise verzögerte NQ=F-Kerzen von Yahoo statt der Demo.
- Abruf maximal alle fünf Minuten pro Prozess, solange der Render-Service aktiv ist. Der Knopf **Aktualisieren** aktualisiert die Darstellung, erzwingt aber kein sofortiges Abrufen.
- Es werden nur abgeschlossene 5-Minuten-Kerzen verwendet. Zeiten sind UTC. Yahoo kann Lücken, Änderungen, Ausfälle und verzögerte Daten liefern.
- Falls Yahoo nicht verfügbar ist, zeigt die App ausdrücklich gekennzeichnete **Demodaten** und einen Fehlerhinweis, keine erfundenen Livekurse.
- Bei Neustart/Schlafmodus von Render Free startet die App wieder im DEMO-Modus; Yahoo muss neu ausgewählt werden. Kein 24/7-Signalwächter oder Push-Alarm.
- Yahoo/yfinance ist für private Forschung gedacht; Datenrechte und Nutzungsbedingungen für Veröffentlichungen beachten.
- Strategien sind noch **experimentelle Prototypen** (Omar 1H-Trend nicht vollständig), keine geprüften Entry-Signale. NQ=F-Continuous-Kontrakt unterscheidet sich von konkreten Futures-Kontrakten.
- Keine TradingView-MCP-Bridge und keine ChatGPT-Verbindung benötigt.
