# Break & Retest Paper Scanner (MVP)

This package contains:
- `break_retest_mnq_mes.pine`: TradingView Pine v6 indicator for a 5-minute chart, filtering signals with the last completed 1-hour EMA trend. It emits LONG/SHORT retest-entry events and up to five candle updates.
- `server.js` + `index.html`: Render web service that receives TradingView alerts and displays a newest-first table. Paper only; no broker or order execution.
- `render.yaml`: Render Blueprint. Requires a persistent disk and a `WEBHOOK_TOKEN` secret.

## Important status
This is an initial integration prototype. Pine Script needs to be added and compiled in the user's TradingView account, then checked against chart examples and Bar Replay before any alert is trusted. The app accepts webhook events; it does not fetch a market feed by itself. It does not place orders.

The default level logic pairs the latest confirmed pivot with the preceding pivot when they are within 0.25 ATR. Retests are processed on confirmed 5m candle closes, so this version is not a tick-level touch/limit-order simulator. Long and short logic are symmetric. The initial stop uses the candle rule. Once price reaches +1R, the stop moves to break-even after estimated round-trip commission, then trails behind confirmed 5m swing lows/highs. It only tightens. Stop/target precedence assumes stop first when both lie inside a candle. The trade remains monitored until stop or target; only the first five post-entry candles are shown as arrows.

## Render deployment
1. Push this folder to a GitHub repository.
2. In Render, create a Blueprint from that repository and review the plan/disk.
3. Set a long random `WEBHOOK_TOKEN` in Render.
4. Deploy and copy the service URL.
5. In Pine, set the same token, then create one alert per active chart (MNQ, MES), select “Any alert() function call”, and enter `https://YOUR-SERVICE.onrender.com/webhook` as webhook URL.
6. TradingView's webhook feature requires account 2FA. Do not put brokerage passwords or API keys in alerts.

Signals appear in the dashboard at the Render service root. Only MNQ/MES symbols are accepted by the receiver.

## Decision workflow inspired by the OPUS demo
The dashboard now makes the six stages visible as a transparent checklist:
1. Scout: receives MNQ/MES candidates from TradingView chart alerts. It does not scan hundreds of markets by itself.
2. News: not connected in this MVP; every candidate is explicitly marked `News offen`.
3. Charts: the Pine indicator applies the completed 1h trend filter and 5m level/breakout/retest rules.
4. Strategy: entry, candle-structure stop, 2R target, and trailing-stop updates are calculated by fixed rules.
5. Risk: the server blocks a candidate if configured per-trade, daily-loss, or MLL-reserve limits fail.
6. Final result: paper observation only. No order routing or live approval.

These stages are ordinary deterministic software checks, not separate AI agents. The social post labels its result self-reported and its rebuild simulated; its displayed performance is not independently verified and is not used by this scanner.
