# TAURUS LAB: VWAP × EMA 3M (research only)

Based on the user's 2026-10-26 discussion: confirmed 3-minute cross, paper entry at the **next** 3-minute candle open, stop behind the signal candle, initial 1.5R take-profit, and the existing one-way trailing stop logic.

The source reel did **not** specify which EMA period to use. The current default **EMA20** is a transparent research assumption and is configurable with `TAURUS_VWAP_EMA_PERIOD`. No claims of profitability are made.

- Tradeable research markets only: MNQ via NQ=F, MES via ES=F, MGC via GC=F.
- Completed 1M bars are grouped into full consecutive 3M bars. Incomplete/gapped 3M candles are excluded.
- VWAP is volume-weighted from typical price (H+L+C)/3 and resets at 18:00 New York time; zero-volume feeds cannot produce a VWAP signal.
- EMA crosses the VWAP on a **closed** 3M candle, LONG upwards, SHORT downwards. A new trade is queued for the next 3M bar open.
- SL is one market tick behind the 3M signal candle low/high. TP is 1.5× the actual fill-to-stop distance (adjusted for next-open gaps). The engine's existing trailing rule arms after a confirmed close at +1R.
- The LAB uses the existing $200 **per-trade** planned-risk sizing, with no aggregate Lucid contract cap or daily account loss stop.
- Uses a separate `market:3m` progress watermark and new strategy id; does not reset V6 experiment or replay old signals as paper fills.
- Existing V6 strategies remain unchanged. No real orders.

## Deployment safety
The latest verified V6 export reports `persistence: /tmp/taurus_paper.db`, an ephemeral Render path. Deploying to the same service would restart the app and can erase all papertrading history accrued after the export. **Do not merge into auto-deploying main until a current full backup and durable storage/isolated preview are confirmed.**

Files: `vwap_ema_cross.py`, `test_vwap_ema_cross.py`, `paper_engine.py`, `main.py`, `strategies.py`, `static/index.html`.
