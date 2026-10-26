"""TAURUS LAB research: confirmed EMA/VWAP cross on completed 3-minute bars.

Only uses the Yahoo 1-minute FUTURES proxy. EMA period was not specified in
source discussion, so default EMA20 is an explicitly configurable research
assumption (TAURUS_VWAP_EMA_PERIOD). No real orders, no look-ahead.
"""
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
STRATEGY = 'vwap_ema_cross_3m'
TICKS = {'nq': .25, 'mes': .25, 'mgc': .10}


def period():
    try:
        p = int(os.environ.get('TAURUS_VWAP_EMA_PERIOD', '20'))
    except (ValueError, TypeError):
        p = 20
    return min(max(p, 2), 200)


def to_3m(bars1m):
    """Group only three consecutive, complete 1M bars into 3M OHLCV.

    The input feed guarantees that each 1M bar is already completed. Groups
    with a missing minute or a duplicate are discarded, not forward-filled.
    """
    groups = defaultdict(list)
    for bar in bars1m:
        t = int(bar['time'])
        groups[(t // 180) * 180].append(bar)
    out = []
    for t in sorted(groups):
        rows = sorted(groups[t], key=lambda b: b['time'])
        if len(rows) != 3 or [int(x['time']) for x in rows] != [t, t + 60, t + 120]:
            continue
        out.append({'time': t, 'open': float(rows[0]['open']),
                    'high': max(float(x['high']) for x in rows),
                    'low': min(float(x['low']) for x in rows),
                    'close': float(rows[-1]['close']),
                    'volume': sum(max(0., float(x.get('volume') or 0)) for x in rows)})
    return out


def _session(ts):
    # CME trading session starts at 18:00 New York time, incl. DST changes.
    local = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(NY)
    return (local - timedelta(hours=18)).date()


def detect(bars3m, market='nq', ema_period=None):
    """EMA crosses session VWAP on a COMPLETED 3M candle.

    EMA is seeded after a full period, VWAP is volume-weighted and resets at
    18:00 NY. The next 3M OPEN is the paper fill; stop behind signal candle;
    nominal 1.5R target, recalculated from actual next-bar entry by engine.
    """
    p = ema_period or period()
    if market not in TICKS:
        return []
    tick = TICKS[market]
    if len(bars3m) < p + 2:
        return []
    k = 2.0 / (p + 1)
    closes = [float(b['close']) for b in bars3m]
    emas = [None] * len(bars3m)
    emas[p-1] = sum(closes[:p]) / p
    for i in range(p, len(bars3m)):
        emas[i] = emas[i-1] + k * (closes[i] - emas[i-1])
    vwaps = [None] * len(bars3m)
    sessions = [_session(int(b['time'])) for b in bars3m]
    cum_pv = cum_v = 0.0
    for i, b in enumerate(bars3m):
        if i == 0 or sessions[i] != sessions[i-1]:
            cum_pv = cum_v = 0.0
        vol = max(0., float(b.get('volume') or 0))
        typical = (float(b['high']) + float(b['low']) + float(b['close'])) / 3
        cum_pv += typical * vol
        cum_v += vol
        if cum_v > 0:
            vwaps[i] = cum_pv / cum_v
    signals = []
    for i in range(p, len(bars3m)):
        if sessions[i] != sessions[i-1]:
            continue
        a, b, av, bv = emas[i-1], emas[i], vwaps[i-1], vwaps[i]
        if None in (a,b,av,bv):
            continue
        side = ('LONG' if a <= av and b > bv else
                'SHORT' if a >= av and b < bv else None)
        if not side:
            continue
        candle = bars3m[i]
        price = float(candle['close'])
        stop = float(candle['low']) - tick if side == 'LONG' else float(candle['high']) + tick
        risk = (price-stop) if side == 'LONG' else (stop-price)
        if risk <= 0:
            continue
        tp = price + 1.5 * risk if side == 'LONG' else price - 1.5 * risk
        signals.append(dict(id=f'{STRATEGY}-{candle["time"]}',strategy=STRATEGY,
            time=int(candle['time']),side=side,entry=round(price,4),
            stop=round(stop,4),tp=round(tp,4),level=round(bv,4),
            breakout_time=int(candle['time']),timeframe='3m',mnq_contracts=None,
            status='HISTORISCHES TESTSIGNAL',
            reason=f'3M EMA{p} kreuzt Session-VWAP; Einstieg nächste 3M-Eröffnung, SL hinter Signalkerze, 1.5R TP + Trailing'))
    return signals


def build(bars1m,market='nq'):
    bars3m = to_3m(bars1m)
    signals = detect(bars3m,market)
    recent = bool(bars3m and signals and signals[-1]['time'] == bars3m[-1]['time'])
    return dict(id=STRATEGY,name=f'VWAP × EMA{period()} (3M)',
        state='green' if recent else 'neutral',
        details=f'Bestätigtes 3M-Kreuz · nächste Kerze OPEN · SL hinter Signalkerze · 1,5R + Trailing · EMA{period()} ist ein Testparameter',
        signals=signals[::-1],
        checks=[('3M vollständig', 'green' if bars3m else 'neutral'),
                ('VWAP-Volumen verfügbar', 'green' if any(b['volume']>0 for b in bars3m) else 'neutral'),
                ('Neues Kreuz', 'green' if recent else 'neutral')])
